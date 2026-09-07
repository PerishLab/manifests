# data — 共享数据层（perish-top）

> 本文的 `kubectl` 均针对 **perish-top** 集群。原文写作 `deno task infra kube perish-top …`,
> 该命令随 Infra 一同退役;等价形式是先取 Hardrig 生成的 kubeconfig:
>
> ```sh
> export KUBECONFIG=$HOME/Projects/perish.code/hardrig/.local/kube/perish-top.yaml
> ```

单节点 estate 的**平台共享数据服务**:postgres + redis + minio。postgres/redis 仅集群内可达;MinIO
S3 API / OSS console 通过 authentik OIDC 对外开放。数据落 `local-path` PVC(`/mnt/k3s` 90G 盘)。

## 组成

- `postgres.yaml`：`Namespace data` + 无头 `Service postgres`(`postgres.data.svc.cluster.local:5432`)+
  `StatefulSet postgres`(`postgres:17-alpine`,PVC 20Gi,`perish-platform-high` 优先级——no-swap 下永不被
  runner 挤掉)+ `ConfigMap postgres-initdb`(首启建租户 db/role)。
- `redis.yaml`：**共享** redis(`redis.data.svc:6379`,appendonly,PVC 2Gi,无认证、无 eviction)。cache/broker。
- `minio.yaml`：**共享** minio(standalone,`minio.data.svc:9000` API / `:9001` console,PVC 20Gi)。
  对外 `s3.perish.top`(API) / `config.perish.top`(`vpn-config` bucket 稳定路径) /
  `oss.perish.top`(console)。`oss` Console 直达 MinIO,由 MinIO 自身 OIDC 登录入口跳转
  authentik。S3 对象。
- `minio-policies.yaml`：MinIO OIDC 人类用户与专用机器身份的 policy JSON。由一次性 `mc`
  初始化 Pod 应用;MinIO 不会直接读取该 ConfigMap。
- `secrets/`：`postgres-secret`(superuser + 各租户 role 密码)、`minio-secret`(root user/pass)的 SealedSecret。

## 租户模型（postgres）

每 app = 一个 database + 一个 LOGIN role。**首启**(PVC 空)时 initdb 脚本按租户建 db/role,密码从 env
(注入自 `postgres-secret`)取:

- authentik:db/role `authentik`,密码键 `AUTHENTIK_DB_PASSWORD`(同值封进 ns `authentik`)。
- forgejo:db/role `forgejo`,密码键 `FORGEJO_DB_PASSWORD`(同值封进 ns `forge`)。

⚠️ initdb 只在首启跑。PG 已初始化后**新增租户**需手动 `CREATE ROLE/DATABASE` + 补 initdb 脚本(为重建留底)。

## 消费方

- postgres:authentik、forgejo。
- redis:authentik(cache + celery broker,`AUTHENTIK_REDIS__HOST=redis.data.svc`,DB 0)。将来其它 app 用不同 DB index。
- minio:forgejo LFS/Actions artifacts(**接线延后**)。

## MinIO 初始化(mc + OSS console)

主客户端选官方 `mc`。当前不引入第三方文件浏览器;人类浏览器入口使用 MinIO OSS 自带 console。
MinIO 镜像固定为 `quay.io/minio/minio:RELEASE.2025-04-22T22-12-26Z`:该版本已验证 Console API
返回 `loginStrategy=redirect` 并暴露 authentik 登录入口。不要改回 `latest`:2026-07-05 实测
`quay.io/minio/minio:latest`(`RELEASE.2025-09-07T16-13-09Z`)在同样 OIDC 配置下只返回
`loginStrategy=form`,不会显示浏览器 OIDC 登录按钮。

当前域名:

- `s3.perish.top` → MinIO S3 API(`minio.data.svc:9000`)。
- `config.perish.top/<path>` → MinIO API `/vpn-config/<path>`；供 VPN 两个固定 profile 路径使用。
- `oss.perish.top` → HTTP redirects to HTTPS → MinIO OSS console(`minio.data.svc:9001`) → authentik OIDC。

authentik 权限模型参考 Forgejo,但 MinIO 直接读取 `policy` claim:

- `minio:readonly` → `perish-minio-readonly`。
- `minio:readwrite` → `perish-minio-readwrite`。
- `minio:admin` → MinIO 内置 `consoleAdmin`。
- `SuperAdmin` → MinIO 内置 `consoleAdmin`。

机器身份不复用上述人类角色，也不复用 root：

- `vpn-config-publisher` → 同名 policy，仅允许 `s3:PutObject` 到
  `vpn-config/clash/{caigou,perish}.yml` 两个对象。它没有 list/delete/bucket admin 权限；
  发布前读取和发布后验证走 `config.perish.top` 的公开只读链路。

OIDC Provider/Application 约定(已接 live):

- authentik application slug:`oss`。
- callback:`https://oss.perish.top/oauth_callback`。
- MinIO OIDC env:
  - `MINIO_BROWSER_REDIRECT_URL=https://oss.perish.top`
  - `MINIO_SERVER_URL=https://s3.perish.top`
  - `MINIO_IDENTITY_OPENID_CONFIG_URL=https://auth.perish.top/application/o/oss/.well-known/openid-configuration`
  - `MINIO_IDENTITY_OPENID_DISPLAY_NAME=authentik`
  - `MINIO_IDENTITY_OPENID_CLAIM_NAME=policy`
  - `MINIO_IDENTITY_OPENID_SCOPES=openid,profile,email,minio`
  - `MINIO_IDENTITY_OPENID_REDIRECT_URI=https://oss.perish.top/oauth_callback`
  - `MINIO_IDENTITY_OPENID_REDIRECT_URI_DYNAMIC=off`
  - `MINIO_IDENTITY_OPENID_CLIENT_ID` / `MINIO_IDENTITY_OPENID_CLIENT_SECRET` 走 `minio-secret` 重封,不入明文。

Policy 初始化用临时 `mc` Pod,从 live `minio-secret` 读 root credential,不把 credential 打到终端:

```sh
kubectl apply -f clusters/perish.top/data/minio-policies.yaml

kubectl -n data run minio-mc-init --image=quay.io/minio/mc:latest \
  --restart=Never --rm -i --overrides='
{
  "spec": {
    "volumes": [
      {"name": "policies", "configMap": {"name": "minio-policies"}}
    ],
    "containers": [
      {
        "name": "minio-mc-init",
        "image": "quay.io/minio/mc:latest",
        "envFrom": [{"secretRef": {"name": "minio-secret"}}],
        "volumeMounts": [{"name": "policies", "mountPath": "/policies", "readOnly": true}],
        "command": ["/bin/sh", "-ec"],
        "args": [
          "mc alias set local http://minio.data.svc:9000 \"$MINIO_ROOT_USER\" \"$MINIO_ROOT_PASSWORD\" >/dev/null; for p in perish-minio-readonly perish-minio-readwrite vpn-config-publisher; do mc admin policy info local \"$p\" >/dev/null 2>&1 || mc admin policy create local \"$p\" \"/policies/$p.json\"; done; mc admin policy list local"
        ]
      }
    ]
  }
}'
```

已存在 policy 时上面会跳过。如果需要变更 policy 内容,先确认没有非预期会话依赖旧策略,再用 `mc admin policy
remove` 后重跑初始化。

`vpn-config-publisher` 用户凭据只进入本仓库
`.local/secrets/vpn-config/publish.env` 与 GitHub environment `vpn-config-production` 的
`VPN_PUBLISH_ENV_B64`；不创建集群常驻 Secret。创建/重置该用户属于凭据变更，必须独立授权，且通过临时
`mc` Pod 的 stdin 传入，避免出现在 Pod spec、命令行或日志中。

## 备份

- PG 逻辑备份:`kubectl -n data exec statefulset/postgres -- pg_dumpall -U postgres | gzip > 备份.sql.gz`(落 `.local`/仓库外)。
- 封印私钥灾备见 `../secrets/AGENTS.md`。app 恢复需 DB 数据 + 各自 PVC 一起考虑。
- 镜像:`postgres`/`redis` 走 docker.io→`mirror.gcr.io`;`minio` 走 quay.io(间歇 flaky,containerd 重试)。
