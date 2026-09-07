# secrets — sealed-secrets（lab-perish-top）

让 secret 以加密 `SealedSecret` 入库,控制器在集群内用 RSA 私钥解密成真正的 Secret。明文与私钥都不入库。
形制照抄 perish-top,只是密钥独立。

## 组成

- `sealed-secrets.yaml`：k3s `HelmChart` 装 sealed-secrets 控制器(`kube-system`,`fullnameOverride=
  sealed-secrets-controller`,chart `2.18.6`)。仓库地址是 `bitnami`(旧 `bitnami-labs` 已 404)。
- `pub-cert.pem`：本集群控制器**公钥**(可公开、入库)。kubeseal 用它离线封装。
- `dnspod-sealedsecret.yaml`：DNSPod `secretId`/`secretKey` 的密文,供 `../ingress/` 的 DNS-01 用。

## 为什么是重封而不是复制

封印密钥**按集群独立**:`clusters/perish.top/secrets/dnspod-sealedsecret.yaml` 的密文在本集群解不开。
所以走的是 perish-top 记过的同一套动作——从活集群抠明文、用本集群公钥重封、密文入库:

```sh
export KUBECONFIG=$HOME/Projects/perish.code/hardrig/.local/kube/lab-perish-top.yaml
KUBECONFIG=$PWD/.local/kube/perish-top.yaml kubectl get secret dnspod-secret -n cert-manager -o json \
  | jq '{apiVersion:"v1",kind:"Secret",metadata:{name:"dnspod-secret",namespace:"cert-manager"},type:.type,data:.data}' \
  | kubeseal --cert clusters/lab.perish.top/secrets/pub-cert.pem -o yaml \
  > clusters/lab.perish.top/secrets/dnspod-sealedsecret.yaml
```

明文只在管道内存里流过,两端都不落盘。凭据本身是**同一个**腾讯云 DNSPod 账号——两个集群共用账号、各自封印。

## kubeseal 工作流

`kubeseal` 不在 runseal 的 `allow-run` 白名单里,按 perish-top 的先例直接跑,`KUBECONFIG` 指向本集群。
重建集群后要重取公钥:

```sh
kubeseal --controller-name sealed-secrets-controller --controller-namespace kube-system \
  --fetch-cert > clusters/lab.perish.top/secrets/pub-cert.pem
```

作用域 **strict**：密文绑 `name`+`namespace`。

## ⚠️ 灾备:封印私钥(单节点必读)

私钥在 `kube-system` 带标签 `sealedsecrets.bitnami.com/sealed-secrets-key` 的 Secret。**重建集群/丢私钥 →
所有已入库 SealedSecret 永久不可解密。** 已备份到 `.local/secrets/lab-perish-top-sealed-secrets-keys.yaml`
(gitignored)。恢复:`kubectl apply -f` 该文件后 `rollout restart deploy/sealed-secrets-controller`。
私钥每 30 天轮转,轮转后重新备份。

## 两种"删掉重来"，代价完全不同

实验面上**删清单再 apply 是常态,重建 k3s 是罕见**。两者不要混为一谈:

- **删清单(常态)**——封印私钥在集群里没动,已入库的密文照样能解。`kubectl apply -f clusters/lab.perish.top/secrets/` 即可复原,**不需要重封**。注意派生的 Secret 由
  SealedSecret 持有 ownerReference,所以删 SealedSecret 会连带回收 `dnspod-secret`;重新 apply 就回来了。
- **重建 k3s(罕见)**——封印私钥随集群消失,所有已入库密文永久不可解。此时才需要重取公钥、重封
  dnspod 密文。若备份还在,优先走上面的恢复流程而不是重封。

## 2026-09-07 核对

备份 `.local/secrets/lab-perish-top-sealed-secrets-keys.yaml` 持有一把密钥,指纹
`99:BE:F5:11:21:BE:E0:5D`,与本目录 `pub-cert.pem` 一致,证书有效至 2036-07-18。
**未核对集群侧此后是否已轮转。** 轮转后重新备份:

```sh
kubectl -n kube-system get secret -l sealedsecrets.bitnami.com/sealed-secrets-key -o yaml \
  > .local/secrets/lab-perish-top-sealed-secrets-keys.yaml
```
