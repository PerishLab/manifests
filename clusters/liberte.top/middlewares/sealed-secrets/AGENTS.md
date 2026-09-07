# middlewares/sealed-secrets(liberte.top 集群)

sealed-secrets 控制器(`kube-system`):secret 以加密 `SealedSecret` 入库,集群内解封为
真实 Secret。封印密钥对是**本集群专属**——本树下的密文只对 liberte.top 集群的证书有效,
与 perish.top 集群互不通用。

分箱:`sealed-secrets.yaml`(manifest)+ `resources/pub-cert.pem`(封印公证,资产)。

原先的 DR 操作是 `scripts/backup-keys.ts`,一个 Deno task。它从一个正在退役的已发布 Deno 运维命名空间
取依赖,随 Infra 一同消失,**未迁入本仓库**——它是脚本而非清单,而本仓库只收清单。
其动作以 kubectl 表述如下,与它当初所做的相同。

- 封印:`kubeseal --cert resources/pub-cert.pem --format yaml < plain-secret.yaml`
  (离线,只需公钥)。公钥也可从控制器取:箱上
  `curl http://<controller-clusterip>:8080/v1/cert.pem`,或 `kubeseal --fetch-cert`。
- 明文源不入库:生成的明文(pg 口令、authentik key/bootstrap)放 `.local/secrets/`
  (gitignored overlay),密文放各组件 `secrets/` 子目录(name+namespace 严格绑定)。
- **封印私钥灾备**:装好后立刻备份 → `.local/secrets/liberte-top-sealed-secrets-keys.yaml`
  (单节点 SPOF;轮换后重跑):

  ```sh
  export KUBECONFIG=$HOME/Projects/perish.code/hardrig/.local/kube/liberte-top.yaml
  kubectl -n kube-system get secret -l sealedsecrets.bitnami.com/sealed-secrets-key -o yaml \
    > .local/secrets/liberte-top-sealed-secrets-keys.yaml
  ```

  2026-09-07 核对:该备份持有一把密钥,指纹 `2D:6B:6E:06:D6:D5:A9:94`,与 `resources/pub-cert.pem`
  一致,证书有效至 2036-06-29。**未核对集群侧此后是否已轮转。**
