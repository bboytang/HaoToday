# 当前交接
线上已部署 T03 邀请内测。地址 https://8kraw.cloud/?channel=lead ，账号 preview；密码仅在主机 /opt/haotoday/preview-password，不写入聊天或仓库。服务器 compose 根目录 /opt/haotoday，镜像 haotoday-app:t03-2，运维见 deploy/README.md。已通过外部 TLS 探测，不等于手机实测。
下一步收集用户真机结果：设备、浏览器、列表和详情、是否正确看到成本/资格/入口。活动 #1 截止北京时间 11 月 20 日 00:00，过期不再显示领取按钮；届时用新的真实来源复核，不延长期限。若用户尚未反馈，可先推进不依赖反馈的 T04/T05 工作，不将 T03 标已验收。
本机库：haotoday-dev-pg；配置用 set -a; source .env; set +a。scripts/check.sh 使用一次性数据库。服务器和本机观察库独立，首次真实批次均为基线而不是自动发现，后台通过公网反代封闭。未启用定时采集、AI、邮件注册或推送。
