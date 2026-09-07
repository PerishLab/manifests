# ingress — cert-manager + DNSPod DNS-01 + Traefik TLS（lab-perish-top）

> 本文的 `kubectl` 均针对 **lab-perish-top** 集群。原文写作 `deno task infra kube lab-perish-top …`,
> 该命令随 Infra 一同退役;等价形式是先取 Hardrig 生成的 kubeconfig:
>
> ```sh
> export KUBECONFIG=$HOME/Projects/perish.code/hardrig/.local/kube/lab-perish-top.yaml
> ```

`*.lab.perish.top` 统一 HTTPS 入口:cert-manager 经 **DNSPod（腾讯云）DNS-01** 签 Let's Encrypt 通配证书,
Traefik(k3s 自带)用默认 TLSStore 承载。形制照抄 `clusters/perish.top/ingress/`。

## 为什么实验集群要有这一层

本目录的存在**修改了 lab 原先「不继承 ingress 层」的边界**,理由是:实验面的意义就是反复装卸 chart,
若 TLS 是每个 chart 自己的事,每个被测 chart 都得为了实验环境长出一块 lab 专属配置——那被测的就不再是
它将来真实部署的样子。通配证书 + 默认 TLSStore 把 TLS 变成**集群属性**:被测 chart 只需声明「我要 TLS」
(一个 `traefik.ingress.kubernetes.io/router.tls: "true"` 注解),不必知道证书叫什么。chart 因此保持可移植。

`*.perish.top` 盖不住这里——通配符只吃一级标签,`ensign.lab.perish.top` 不匹配。两个集群签的名字不相交,
不会争用同一条 `_acme-challenge` TXT。

## 组成

- `cert-manager.yaml`：`Namespace cert-manager` + jetstack cert-manager `v1.20.2`(HelmChart,`crds.enabled`)。
  本集群 k8s 1.35 满足其 ≥1.31 要求。
- `webhook-dnspod.yaml`：imroc dnspod webhook,**钉 1.5.2 且直接指 release tarball**——两处都与 perish-top
  不同,原因写在文件头部注释里(不让版本自己漂;绕开在本主机会卡死的 `helm repo add`)。
- `clusterissuer.yaml`：`letsencrypt-staging` / `letsencrypt-prod`,DNS-01 config 指 `dnspod-secret`。
- `wildcard-certificate.yaml`：`*.lab.perish.top` 通配证书(`kube-system`,prod issuer)。**故意不含 apex**
  `lab.perish.top`——理由同 perish-top:通配+apex 共用同一 TXT 会双 challenge 竞争。
- `tlsstore-default.yaml`：Traefik 默认 TLSStore → 通配证书。
- 凭据:`../secrets/dnspod-sealedsecret.yaml`(密文,本集群密钥重封)。

## 冷启动次序

sealed-secrets 就绪 → cert-manager Ready → webhook Ready → apply dnspod SealedSecret → ClusterIssuer(Ready)
→ 通配证书(DNS-01,~1-3min Ready)→ TLSStore。签发前**先用 staging 验证**再切 prod,避免 LE 限流。

## ⚠️ 反复删清单会烧掉 Let's Encrypt 配额

实验面最常见的操作是删清单再 apply。本目录里**只有 `wildcard-certificate.yaml` 经不起这样反复**:
删掉 Certificate 连同 `wildcard-lab-perish-top-tls` 再 apply,就是向 LE 重新申请一次。两条限额会咬人:

- **相同名字集合的重复证书:每周 5 张。** 迭代时删几次就用光,然后被锁一周,期间整个 lab 没有 TLS。
- **每注册域每周 50 张。** `lab.perish.top` 与 `perish.top` 是**同一个注册域**,这个桶和生产集群
  **共用**——在这里烧配额会影响 perish-top 的签发。

所以:调试 ingress 时删 Ingress、删 TLSStore、删 release 都无所谓,**唯独别动 Certificate 和它的
Secret**。真要重签,先用 `letsencrypt-staging` 验证(staging 有独立且宽松得多的配额),确认无误再碰 prod。
本目录其余清单都是幂等的,随便重 apply。

## 核查

```sh
kubectl -n kube-system get certificate wildcard-lab-perish-top   # Ready=True
echo | openssl s_client -connect 38.76.202.208:443 -servername ensign.lab.perish.top 2>/dev/null \
  | openssl x509 -noout -issuer -subject
```
