# 当前交接
线上已部署 T03 邀请内测。地址 https://8kraw.cloud/?channel=lead ，账号 preview；密码仅在主机 /opt/haotoday/preview-password，不写入聊天或仓库。服务器 compose 根目录 /opt/haotoday，镜像 haotoday-app:t04-glm-1，运维见 deploy/README.md。已通过外部 TLS 探测，不等于手机实测。
下一步收集用户真机结果：设备、浏览器、列表和详情、是否正确看到成本/资格/入口。活动 #1 截止北京时间 11 月 20 日 00:00，过期不再显示领取按钮；届时用新的真实来源复核，不延长期限。若用户尚未反馈，可先推进不依赖反馈的 T04/T05 工作，不将 T03 标已验收。
本机库：haotoday-dev-pg；配置用 set -a; source .env; set +a。scripts/check.sh 使用一次性数据库。服务器和本机观察库独立，首次真实批次均为基线而不是自动发现，后台通过公网反代封闭。服务器已启用 30 分钟采集；未启用 AI、邮件注册或推送。

最新：线上已启用版本记录和已验证成本/证据数据库门槛（0003、0004）。现有 #1 为线索，不应擅自升为已验证。升级前数据库备份位于服务器 /opt/haotoday/backups，已用独立临时库实际恢复，非异地备份。systemctl list-timers --all haotoday-discovery.timer 可核对下次调度。
线上已含 0005–0006：复查/撤回原因、起止时间、模型摘录缓存。完整目录移除或关键字段变化会暂停入口，不自动恢复。真实同步仍为 unchanged=14；不能当作失效实测。
下一步：用户已确定智谱 glm-4.7-flash；仅项目专用 ZHIPUAI_API_KEY 待配置，不再问模型。按 deploy/README.md 启用后，用一段获准公开条款验证 analyze_rules 输出、缓存和 token 数，不能把模拟测试说成真实调用。未配期间可推进 T05 搜索、筛选、账户功能。手机反馈与公开运营前置仍待办。
