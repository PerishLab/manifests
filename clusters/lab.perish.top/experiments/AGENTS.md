# experiments — Helm 实验面(lab-perish-top)

一个命名空间,`experiments`,带两个标签声明它属于哪个集群、为何存在。lab 集群上删清单再 apply
是常态,这个命名空间是那些一次性 Helm 试验的落点,不承载任何长期负载。

## 组成

- `namespace.yaml`:`Namespace experiments`,标签 `estate.perish.top/cluster: lab-perish-top`
  与 `estate.perish.top/purpose: helm-experiments`。

## Helm 冒烟

原先有一个 `helm-smoke.ts`(Deno task,id `lab-perish-top.helm-smoke`),用来确认这个集群上
Helm 本身还能装、能读、能卸。它从一个正在退役的已发布 Deno 运维命名空间取依赖,随 Infra 一同
消失,**未迁入本仓库**——它是脚本而非清单,而本仓库只收清单。

它做的事完全可以由几条命令表达,记在这里,以免语义随脚本一起消失:

```sh
export KUBECONFIG=$HOME/Projects/perish.code/hardrig/.local/kube/lab-perish-top.yaml

# 1 造一个最小 chart:只有一个 ConfigMap,值为 ok
d=$(mktemp -d) && mkdir "$d/templates"
printf 'apiVersion: v2\nname: infra-helm-smoke\nversion: 0.1.0\ntype: application\n' > "$d/Chart.yaml"
cat > "$d/templates/configmap.yaml" <<'YAML'
apiVersion: v1
kind: ConfigMap
metadata:
  name: infra-helm-smoke
  labels:
    app.kubernetes.io/managed-by: Helm
data:
  result: ok
YAML

# 2 装,等就绪
helm upgrade --install infra-helm-smoke "$d" -n experiments --wait --timeout 2m

# 3 读回,必须恰为 ok
test "$(kubectl -n experiments get configmap infra-helm-smoke -o jsonpath='{.data.result}')" = ok

# 4 卸,并确认真的没了
helm uninstall infra-helm-smoke -n experiments --wait --timeout 2m
test -z "$(kubectl -n experiments get configmap infra-helm-smoke --ignore-not-found -o name)"

rm -rf "$d"
```

原脚本的几条纪律值得沿用:**不接受任何参数**;整体超时 300 秒;持一把
`lab-perish-top.helm-smoke` 的锁,不与自身并发;**回滚动作恒定为「卸掉冒烟 release 并删掉本地
chart」**,无论前面哪一步失败;禁止重启主机。它是 transient 的——跑完不留任何东西,这正是
第 4 步要复核的原因。
