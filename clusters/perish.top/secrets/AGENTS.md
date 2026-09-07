# secrets — sealed-secrets（perish-top）

让 secret 以加密 `SealedSecret` 入库,控制器在集群内用 RSA 私钥解密成真正的 Secret。明文与私钥都不入库。

## 组成

- `sealed-secrets.yaml`：k3s `HelmChart` 装 sealed-secrets 控制器(`kube-system`,`fullnameOverride=
  sealed-secrets-controller`)。**注意**:chart 仓库已从 `bitnami-labs`→`bitnami` 迁移(旧地址 404)。
- `pub-cert.pem`：本集群控制器**公钥**(可公开、入库)。kubeseal 用它离线封装。
  ⚠️ perish-top 的私钥与 liberte.top **独立**——两集群的 SealedSecret 互不通用。

## kubeseal 工作流(`KUBECONFIG` 指向 perish-top）

```sh
export KUBECONFIG=$HOME/Projects/perish.code/hardrig/.local/kube/perish-top.yaml
# 重取公钥(重建集群后)
kubeseal --controller-name sealed-secrets-controller --controller-namespace kube-system \
  --fetch-cert > clusters/perish.top/secrets/pub-cert.pem
# 封装:明文 Secret -> SealedSecret（离线,用公钥）
kubectl create secret generic X -n NS --from-literal=k=v --dry-run=client -o yaml \
  | kubeseal --cert clusters/perish.top/secrets/pub-cert.pem -o yaml > .../X-sealedsecret.yaml
```

作用域 **strict**：密文绑 `name`+`namespace`。

## ⚠️ 灾备:封印私钥(单节点必读)

私钥在 `kube-system` 带标签 `sealedsecrets.bitnami.com/sealed-secrets-key` 的 Secret。**重建集群/丢私钥 →
所有已入库 SealedSecret 永久不可解密。** 已备份到 `.local/secrets/perish-top-sealed-secrets-keys.yaml`
(gitignored)。恢复:`kubectl apply -f` 该文件后 `kubectl -n kube-system rollout restart deploy/sealed-secrets-controller`。
私钥每 30 天轮转,轮转后重新备份:

```sh
kubectl -n kube-system get secret -l sealedsecrets.bitnami.com/sealed-secrets-key -o yaml \
  > .local/secrets/perish-top-sealed-secrets-keys.yaml
```

2026-09-07 核对:该备份持有一把密钥,指纹 `A0:A9:0F:9E:FD:17:82:86`,与本目录 `pub-cert.pem` 一致,
证书有效至 2036-06-29。**未核对集群侧此后是否已轮转**——若已轮转,集群持有更新的密钥而备份没有。
