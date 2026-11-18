# 当前交接
线上已部署 T03 邀请内测。地址 https://8kraw.cloud/?channel=lead ，账号 preview；密码仅在主机 /opt/haotoday/preview-password，不写入聊天或仓库。服务器 compose 根目录 /opt/haotoday，镜像 haotoday-app:t04-evidence-1，运维见 deploy/README.md。已通过外部 TLS 探测，不等于手机实测。
下一步收集用户真机结果：设备、浏览器、列表和详情、是否正确看到成本/资格/入口。活动 #1 截止北京时间 11 月 20 日 00:00，过期不再显示领取按钮；届时用新的真实来源复核，不延长期限。若用户尚未反馈，可先推进不依赖反馈的 T04/T05 工作，不将 T03 标已验收。
本机库：haotoday-dev-pg；配置用 set -a; source .env; set +a。scripts/check.sh 使用一次性数据库。服务器和本机观察库独立，首次真实批次均为基线而不是自动发现，后台通过公网反代封闭。服务器已启用 30 分钟采集；未启用 AI、邮件注册或推送。

最新：线上已启用版本记录和已验证成本/证据数据库门槛（0003、0004）。现有 #1 为线索，不应擅自升为已验证。升级前数据库备份位于服务器 /opt/haotoday/backups，已用独立临时库实际恢复，非异地备份。systemctl list-timers --all haotoday-discovery.timer 可核对下次调度。
待接手：完善疑似失效/撤回状态和相应前台行为，对接用户已有模型（只询问协议、模型、基础地址和凭据变量名，不要索要明文密钥）。若接口信息尚未提供，继续做与模型无关的功能。收集真机结果，暂不开放公众注册。
