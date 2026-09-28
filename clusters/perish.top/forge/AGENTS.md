# forge — Forgejo control plane（perish-top）

> 本文的 `kubectl` 均针对 **perish-top** 集群。原文写作 `deno task infra kube perish-top …`,
> 该命令随 Infra 一同退役;等价形式是先取 Hardrig 生成的 kubeconfig:
>
> ```sh
> export KUBECONFIG=$HOME/Projects/perish.code/hardrig/.local/kube/perish-top.yaml
> ```

域内 Forgejo:`git.perish.top`。Forgejo 是 app 源码与 Deployment manifest 的自治入口;本仓库只维护平台侧
Forgejo server、runner、ingress 与必要 Secret。

## 组成

- `forgejo.yaml`:`Namespace forge` + Forgejo HelmChart(OCI `code.forgejo.org/forgejo-helm/forgejo` `17.1.1`)
  + `git.perish.top` IngressRoute。用**共享 Postgres**(db/role `forgejo`),内建 leveldb 队列 + 内存 cache
  (不用 redis)。**git-over-SSH 已启用**(rootless 内建 SSH server,pod 内 `SSH_LISTEN_PORT=2222`),经
  额外的 `forgejo-ssh-public` **LoadBalancer**(k3s ServiceLB)发布在宿主机 **`:22`**;clone URL 用 `:22`
  (`SSH_PORT=22`)。为让出 `:22`,宿主机 admin sshd 于 2026-07-07 移到 `:2077`——该事实现由 Hardrig 的 `hosts/zxiyun/us-02/host.toml`
  声明(稳态 SSH 2077,重建入口 22),Infra 的同名目录已随其退役。
  HTTP 走 IngressRoute。LFS/attachments 暂用本地 PVC(20Gi),minio 接线延后。
- **us-02 runner 已退役并迁出**(2026-07-07):Forgejo Actions runner 现由 `hosts/zxiyun/hk-01`
  和 `hosts/zxiyun/hk-04` 的两台对等 CI appliance 承载（同 label `docker`，依赖走各自
  本地镜像站,其清单仍在冻结的 Infra 远端 `clusters/mirror.perish.lan/`,尚未迁入本仓库）。us-02 的带宽留给 Forgejo/个人访问，
  本目录不保存 runner manifest、注册 Secret 或运行时状态。
- `secrets/forgejo-sealedsecret.yaml`:admin(username/password)+ db-password。

## 首登

用户 `perishadmin`,密码 = `.local/secrets/forgejo.env` 的 `FORGEJO_ADMIN_PASSWORD`。

## 认证 / 注册策略

Forgejo 登录源 `authentik`(OAuth2 source ID 1)是当前主账号入口。普通自助注册关闭,但全局
`DISABLE_REGISTRATION=false`:这是为了允许 OAuth 自动建号;真正的限制由
`ALLOW_ONLY_EXTERNAL_REGISTRATION=true`、`SHOW_REGISTRATION_BUTTON=false`、
`REQUIRE_EXTERNAL_REGISTRATION_PASSWORD=false`、`ENABLE_INTERNAL_SIGNIN=false`、
`ENABLE_BASIC_AUTHENTICATION=false` 和 `[oauth2_client] ENABLE_AUTO_REGISTRATION=true` 共同完成。

当前 auth source 继承 authentik 组:

- `RequiredClaimName=forgejo_access`, `RequiredClaimValue=allowed`。
- `GroupClaimName=forgejo_groups`, `AdminGroup=admin`, `RestrictedGroup=restricted`。
- authentik 侧组 `forgejo:user`、`forgejo:admin`、`forgejo:restricted` 经自定义 `forgejo` scope mapping
  映射成上述 claim;`SuperAdmin` 也映射为 Forgejo admin。

授权必须在 authentik 侧显式加入预定义组，不在 Forgejo 数据库手改账号：

原先有一个 `deno task infra authentik user group add <username> forgejo:user|forgejo:admin`
的命令行,随 Infra 一同退役,**没有继任者**。加组现在直接在 authentik 里做——身份系统本身即权威。
authentik 这个平面不属本仓库;本目录只记 Forgejo 侧
依赖哪些组名:`forgejo:user`(普通用户)、`forgejo:admin`(Forgejo admin,低于域级 SuperAdmin)、
`forgejo:restricted`。

无 `forgejo:*` / `SuperAdmin` 组时，OAuth required claim 会拒绝登录；界面可能显示
`Account is suspended`，但这不等价于一个已入库的 Forgejo 账号被手工停用。

`perishadmin` 本地管理员保留作 DB/CLI break-glass,但 Web 内部登录和 HTTP Basic 密码认证已关闭;
人类网页登录入口必须走 authentik。Git HTTPS 应使用 token/OAuth 派生凭据,不要依赖本地密码。

## 仓库控制面

原先有 `deno task infra forgejo auth check` / `repo list <owner>` / `repo visibility public <owner>...`
一组命令,随 Infra 一同退役。**继任只覆盖了其中一半,这是一处真实的能力缺口,不是改名。**

- **单仓库操作有继任者**:`runseal :perish @forgejo repo show|create|edit|delete`,以及 issue、pull、
  review、status、branch、protection、secret 各动词。改可见性即 `repo edit --body '{"private":false}'`。
- **按 owner 的批量清点与扫描没有继任者**:`@forgejo` 没有 `repo list <owner>`。原命令自动区分 user
  与 org owner、遍历全部 API page、只 PATCH 非 public 的仓库、并在改完后再次全量复核——这套语义
  今天要靠手写脚本重做。

其鉴权纪律值得保留并在任何重做中沿用:**只生成 purpose-scoped 的短期 admin token,仓库变更走
Forgejo API,结束后无论成功失败都按精确 token name 撤销,本地不保存持久 admin token。**

## Runner 注册

重建 Forgejo DB 会使两台 appliance 的注册失效；token 生成在本集群完成，注册与
`runner-reg` Secret 的落点在各 mirror 集群。完整流程只维护于 `clusters/mirror.perish.lan/AGENTS.md`,本目录不复制第二份。
该目录**尚未迁入本仓库**,仍在冻结的 Infra 远端(`github.com/PerishCode/infra`,`main` `2d098f3`);
其归属未定,见 PerishLab/manifests#1。

## Actions 解析（本地镜像，`DEFAULT_ACTIONS_URL=self`）

`[actions] DEFAULT_ACTIONS_URL=self`(forgejo.yaml)：短格式 `uses: owner/repo@vN` 解析到**本实例**
`git.perish.top/owner/repo`,而非内置默认 `data.forgejo.org`(德国)。**动机**:HK runner→data.forgejo.org
跨洲链路曾间歇性失败并集中卡在 checkout 首步；改 self 后 runner 从其正常作业本就使用的
**HK→us-02** Forgejo 路径拉 action。

已镜像的 action(pull-mirror,8h 自动从 github 同步;us-02 到 github 连通性好):

```
actions/checkout · actions/download-artifact · actions/upload-artifact
denoland/setup-deno · dtolnay/rust-toolchain
```

- **新增一个 action 镜像**(某仓库开始 `uses:` 一个还没镜像的 action 时,否则 self 会 404):
  ```sh
  TOK=$(kubectl -n forge exec deploy/forgejo -c forgejo -- \
    forgejo admin user generate-access-token --username perishadmin --raw \
    --scopes write:organization,write:repository | tail -1)
  # org 不存在先建: POST /api/v1/orgs {"username":"<org>","visibility":"public"}
  # 再: POST /api/v1/repos/migrate {"clone_addr":"https://github.com/<org>/<repo>",
  #     "repo_owner":"<org>","repo_name":"<repo>","mirror":true,"service":"git"}
  # 用完 revoke: DELETE /api/v1/users/perishadmin/tokens/<name>
  ```
- **⚠ 硬编码全 URL 绕过本机制**:workflow 写 `uses: https://data.forgejo.org/actions/checkout@v6`
  仍直连德国。要享受本地镜像必须改回**短格式** `uses: actions/checkout@v6`
  (各自仓库改)。

## 核查

```sh
curl -fsS https://git.perish.top/api/healthz        # {"status":"pass"}
git ls-remote https://git.perish.top/actions/checkout v6   # action 本地可解析(替代 data.forgejo.org)
KUBECONFIG=$HOME/Projects/perish.code/hardrig/.local/kube/mirror-lan.yaml \
  kubectl -n ci get deploy/forgejo-runner   # runner 由 actions 拥有,此处只观测
```

## 注意

- DinD 是 privileged RCE 面,只适合受信任的首批内部仓库。开放注册/外部合入前须重设计隔离。
- Forgejo DB + 仓库/PVC 是业务数据。sealed-secrets 只恢复密钥,不恢复 repo 内容——PVC 丢失需从备份/镜像重推。
- OIDC 登录源 canonical callback 为 `https://git.perish.top/user/oauth2/authentik/callback`。
- 2026-07-05 已关闭 Forgejo 内部 Web 登录和 HTTP Basic 密码认证;登录页只保留 authentik OAuth 入口。
- 2026-07-04 已从 chart `17.1.0` 升到 `17.1.1`(Forgejo `15.0.3` security/LTS patch)。
- 2026-07-04 用临时 authentik 用户验证过 OIDC 组继承:无 `forgejo:*` 组不能进入 Forgejo 用户表;
  `forgejo:user` 自动建普通用户;`forgejo:admin` 自动建 Forgejo admin。测试用户已从 authentik 和
  Forgejo 删除。
- 待办:LFS/artifacts 接 `../data/` 的 minio(S3)。
