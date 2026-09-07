# data — 家园共享数据层(liberte.top 集群)

单 StatefulSet 的共享 PostgreSQL(`postgres:17-alpine`,ns `data`,PVC 20Gi 落
`/mnt/k3s`)。多租户:每个应用一个 database + login role。当前租户:`authentik`。

- 连接:`postgres.data.svc.cluster.local:5432`(headless)。
- 口令:`./secrets/postgres-sealedsecret.yaml`(密文入库;明文在
  `.local/secrets/liberte-top-data.env`)。键:`POSTGRES_SUPERUSER_PASSWORD`、
  `AUTHENTIK_DB_PASSWORD`。
- 新租户:initdb 脚本只在首次初始化跑;后加租户手动
  `CREATE ROLE ... LOGIN PASSWORD ...; CREATE DATABASE ... OWNER ...;` 并把口令
  加进 SealedSecret 重新封印。
- redis 未设共享实例:当前唯一消费者是 authentik,用其 ns 内的 app-local redis
  (无持久化,可重建)。出现第二个消费者时再提升为本层共享实例。
