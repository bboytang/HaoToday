# 当前交接
T03 进行中。本机正式模型、审核后台和双频道 SSR 页面已建。数据库为 haotoday-dev-pg；本机加载 set -a; source .env; set +a，按 ARCHITECTURE 启动。scripts/check.sh 用一次性 PostgreSQL 验证 8 项测试。已核对观察 3850 并建立 Offer #1，只是线索，截止北京时间 11 月 20 日 00:00，过期不要续日期。
下一步：为 8kraw.cloud 配置隔离的 HTTPS 内测部署（应用非 root、数据库不暴露、域名未放行前不开放注册），先核对域名解析、安全组及可用容器镜像；刚检查服务器未见 80/443 监听。发布前重新核查活动时间与原链，导入审核行以来源 ID 映射而非假设服务器主键相同。通过公网实际打开首页/详情，并记录手机验证。不能仅以本机 200 宣称 T03 完成。
当前未启用周期采集、AI、注册或推送。来源条款及运行命令见 SOURCES_AND_QUALITY、ARCHITECTURE 和 WORKLOG。不要把 .env 或私钥提交到 Git。
