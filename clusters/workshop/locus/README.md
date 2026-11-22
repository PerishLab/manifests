# Workshop Locus 指标试点

试点以单副本 Helm 部署写入独立的 workshop-locus-metrics PVC。入口通过 Kubernetes API 的本机环回 port-forward 暴露给采集器。探测对象为 Workshop 现有的 Locus HTTPS 健康入口。现网日志服务及采集者沿各自部署运行。

在本机准备权限为 0700 的状态目录。执行 setup.py 时传入该目录。脚本核对 Wharf 稳定分发、正式镜像与 chart、实际 Ensign 发行者和 Workshop 机器主体，再为试点的两个来源赋予 append 和 scan。公钥来自该 issuer。凭证及读回文件保留在调用者提供的目录，复盘只导入脱敏材料。

sample.sh 接受相同状态目录。它每 15 秒读取 Kubernetes metrics.k8s.io PodMetrics 和 HTTPS 健康探测，采集 24 小时。CPU 的样本时间使用 Kubernetes 记录时间，单位为核。探测使用客户端时间及完整 HTTP 请求耗时，单位为秒。根据同时在场的容器最多选择 32 条序列。重复的同一序列与来源时间使用同一个证据身份。失败在脱敏 NDJSON 中记录，指标窗显示缺样；零 CPU 或零增量仍可作为正常观测返回。

验收要读回两个来源、独立汇总实际序列数及样本数、测量一小时读的端到端 p95。记录 PVC 实际占用、采样失败间隔、恢复副本的原始样本与来源授权。实际场地参考 Workshop #82 的 1 秒 p95 和 30 秒缺样阈值。现场两用户浏览器验收使用正式 Web 包、同源 /api 与 /auth、Ensign OIDC 客户端和各自的来源授权。

用 review.py 通过试点的环回端口重复读取一小时探测指标窗，并汇总 CPU 和探测样本质量。首小时以前的读数只用于连通性检查。
