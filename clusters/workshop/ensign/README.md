# Workshop Ensign

正式 namespace 为 `workshop-ensign`，Helm release 为 `ensign`，issuer 为 `https://ensign.workshop.liberte.host/api`。[values.yaml](values.yaml) 声明实例的非秘密参数（含 `web.client` 与 `locus` 转发配置），PostgreSQL 随该 release 管理；`/client.json` 由 chart 原生挂载 `<release>-web-client` ConfigMap 至 `ensign-web` 提供，无需独立静态覆写。`ensign-locus-key`、签名、sudo 和数据库凭据均留在集群 Secret 保管。

Chart 和镜像从 [Ensign 产品声明](https://github.com/PerishLab/ensign/blob/main/plumb.toml) 及 Plumb/Wharf 解析。升级、bootstrap、保管和回退遵循 [Ensign chart 生命周期](https://github.com/PerishLab/ensign/blob/main/charts/ensign/README.md)。操作前通过 `runseal :kube.workshop helm history ensign -n workshop-ensign` 核对 revision，并检查进行中的 Job。沿相同 Runseal profile 调用 Helm，将 values 参数指向本目录的 `values.yaml`，在 Task 记录实际 chart 与镜像身份。

签名、sudo 和数据库凭据留在产品保管。恢复时先核对 PostgreSQL、签名和 issuer 的连续性，按生命周期恢复工作负载，分别验证健康、API、CLI、浏览器登录、登出、OIDC 与实际权限拒绝。生产和 pilot 分别保有自己的数据库和签名材料。既有恢复材料在 Ensign 受限的 `.local/workshop/recovery/`；离机恢复演练按独立任务验收。
