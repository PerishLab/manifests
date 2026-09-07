# ingress — cert-manager + DNSPod DNS-01 + Traefik TLS（perish-top）

> 本文的 `kubectl` 均针对 **perish-top** 集群。原文写作 `deno task infra kube perish-top …`,
> 该命令随 Infra 一同退役;等价形式是先取 Hardrig 生成的 kubeconfig:
>
> ```sh
> export KUBECONFIG=$HOME/Projects/perish.code/hardrig/.local/kube/perish-top.yaml
> ```

`*.perish.top` 统一 HTTPS 入口:cert-manager 经 **DNSPod（腾讯云）DNS-01** 签 Let's Encrypt 通配证书,
Traefik(k3s 自带)用默认 TLSStore 承载。

## 组成

- `cert-manager.yaml`：`Namespace cert-manager` + jetstack cert-manager `v1.20.2`(HelmChart,`crds.enabled`)。
- `webhook-dnspod.yaml`：**imroc** dnspod webhook(`groupName acme.dnspod.com`,`solverName dnspod`)。
  ⚠️ 与旧 hk-01 栈里的 reodwind webhook 分叉——**照 hk-03 实跑的 imroc 来**(2026-07-02 证实)。
- `clusterissuer.yaml`：`letsencrypt-staging` / `letsencrypt-prod`,DNS-01 config 用 `secretIdRef`/
  `secretKeyRef` 指 `dnspod-secret`(keys `secretId`/`secretKey`)。
- `secrets/dnspod-sealedsecret.yaml`：DNSPod `secretId`/`secretKey` 的 SealedSecret(密文)。凭据**复用**
  自现有腾讯云账号(从 hk-03 抠明文重封)。
- `wildcard-certificate.yaml`：`*.perish.top` 通配证书(`kube-system`,prod issuer)。**故意不含 apex**
  `perish.top`——通配+apex 共用同一 `_acme-challenge.perish.top` TXT 会双 challenge 竞争失败;应用全是子域。
- `tlsstore-default.yaml`：Traefik 默认 TLSStore → 通配证书。任何 `*.perish.top` IngressRoute `tls: {}` 即自动用它。
- `traefik-config.yaml`：k3s 自带 Traefik 的 `HelmChartConfig`（原为手工 `kubectl apply`，无 git 源，现纳入）。含 `kubernetesCRD.allowCrossNamespace` + **`websecure.readTimeout=0s`**。后者根治容器镜像 push 的间歇 499/502：Traefik v3 默认 `respondingTimeouts.readTimeout=60s`（读整个请求含 body 的上限），一个 blob 上传超 60s（大层 / 慢链路 / docker 并发多流分带宽）即被掐——实测 6MB@58.6s→201、@61.4s→502。改 0s 后 78s 上传通过；`idleTimeout`（默认 180s）仍回收真正停滞的连接。改此文件触发 Traefik 重装（`failurePolicy: reinstall`），全集群 ingress 有数十秒 blip。

## 冷启动次序

sealed-secrets 就绪 → cert-manager Ready → webhook Ready → apply dnspod SealedSecret → ClusterIssuer(Ready)
→ 通配证书(DNS-01,~1-3min Ready)→ TLSStore。签发前**先用 staging 验证**再切 prod,避免 LE 限流。

## 核查

```sh
kubectl -n kube-system get certificate wildcard-perish-top   # Ready=True
echo | openssl s_client -connect 45.205.27.162:443 -servername auth.perish.top 2>/dev/null | openssl x509 -noout -issuer -subject
```

（割接已完成 2026-07-02:旧集群对 perish.top 名的签发已退役——见 `clusters/liberte.top/AGENTS.md` 迁移记录;重建时若两集群再共签同名,注意 LE duplicate-cert 限流与 TXT 争用。）
