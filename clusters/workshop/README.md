# Workshop 集群

本机 checkout 的集群入口是 `~/Projects/perish.lab/manifests/clusters/workshop`。根 [Kustomization](kustomization.yaml) 组合 [平台组件](platform/kustomization.yaml) 和 [命名空间](namespaces/kustomization.yaml)。`dev` 的 [父入口](namespaces/dev/ingress.yaml) 统一处理泳道的 HTTPS，服务声明各自用子 IngressRoute 匹配完整 Host。无 selector 的预览 Service 接收按现场动态连接的 EndpointSlice。接线命令见 [Workshop 本机入口](https://github.com/PerishLab/workshop/blob/main/instances/personal/README.md)。

[Ensign 实例配置](ensign/README.md) 由产品 Helm chart 读取，独立于根 Kustomization。当前活动资源和操作者身份以现场查询为准。对既有资源迁入声明前，先核实 owner、原生任务和控制器。

## 检查与应用

```sh
cd ~/Projects/perish.lab/manifests/clusters/workshop
runseal :kube.workshop kubectl kustomize .
runseal :kube.workshop kubectl kustomize namespaces/dev
runseal :kube.workshop kubectl auth can-i patch endpointslices -n dev
runseal :kube.workshop kubectl apply --dry-run=server -k namespaces/dev
```

服务端校验使用拥有对应资源权限的账户。变更只应用本次拥有的入口，例如对 dev 使用 `runseal :kube.workshop kubectl apply -k namespaces/dev`。Traefik 定制走 K3s AddOn 原路径。

## HTTPS 与诊断

[Traefik HelmChartConfig](platform/traefik/config.yaml) 由 K3s AddOn 从 `/var/lib/rancher/k3s/server/manifests/traefik-config.yaml` 读取。校验后发布到原路径，核对 Helm Job、Traefik rollout 和 TLSStore。配置保留 RequireDualStack；默认 TLSStore 使用 `kube-system/workshop-wildcard-tls`。宿主同步证书的维护入口见 [Workshop 设备文档](https://github.com/PerishLab/workshop/blob/main/devices/personal/README.md)。

排查按公共 AAAA 和 WAN 入站、证书链和 SAN、IngressRoute、Service 与 EndpointSlice、后端 HTTP/API 的顺序核验。外部可达性用独立 IPv6 客户端验证。证书同步失败时先保留当前有效 Secret，仅查询 metadata、公有指纹和有效期。

```sh
runseal :kube.workshop kubectl logs -n kube-system deployment/traefik
runseal :kube.workshop kubectl logs -n workshop-ensign deployment/ensign-api
runseal :kube.workshop kubectl logs -n workshop-ensign ensign-pg-0
runseal :locus.workshop locus query locus.trace --producer plumb
```

Traefik 运行日志和 Ensign API 启动日志的覆盖范围以实际配置为准。容器日志会轮转，长期取证走授权存储。任务只登记脱敏状态、时间及关联标识。

## 恢复

先通过独立宿主维护入口恢复 K3s。datastore 与 server token 配套恢复，Ensign 的 PostgreSQL 和签名材料则按[实例恢复说明](ensign/README.md)处理。核对 Node Ready、双栈 Pod 和 Service、DNS、控制面路径，再验证共享入口与各应用。从 Git 取待恢复修订的声明，按控制器和叶子入口恢复，分别核对管理者与工作负载。具体部署与验收历史见 [Workshop #6](https://github.com/PerishLab/workshop/issues/6)。
