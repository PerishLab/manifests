# Workshop Folio

正式 namespace 为 `dev`，Helm release 为 `folio`，主机为 `folio.workshop.liberte.host`，issuer 为 `https://ensign.workshop.liberte.host/api`。[values.yaml](values.yaml) 声明实例的非秘密参数（含 `storage.existingClaim: folio-data-v2`、`web.client` 与 `locus` 转发配置）；`/client.json` 由 chart 原生挂载 `<release>-web-client` ConfigMap 至 `folio-web` 提供，Locus 中继缓冲持久化在 PVC `/data/locus-relay`。信任公钥快照 `jwks` 与 `folio-locus-key` 凭据留在集群保管，不提交至 Git。

Chart 和镜像从 [Folio 产品声明](https://github.com/PerishLab/folio/blob/main/plumb.toml) 及 Plumb/Wharf 解析。操作前通过 `runseal :kube.workshop helm history folio -n dev` 核对 revision，沿相同 Runseal profile 升级时保留集群内现有 `jwks`（或从受信任快照注入），并核验 `FOLIO_LOCUS_KEY` 与 `fsGroupChangePolicy: OnRootMismatch` 下 `/data/locus-relay` 重启无漂移。
