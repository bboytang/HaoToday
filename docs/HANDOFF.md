# 当前交接
线上地址 https://8kraw.cloud/?channel=lead ，外层邀请预览账号 preview；密码仅存服务器 /opt/haotoday/preview-password。外层口令与 Django 个人账户不是同一身份。项目运行在 /opt/haotoday（镜像 haotoday-app:t05-account-1、迁移 0008），最近升级备份为 backups/pre-upgrade-20261118T150924Z.dump。部署脚本与回滚条件见 deploy/README.md。
已启用 30 分钟采集、版本记录、复查停展、双频道首页和详情。真实 #1 是 Epic PC 限免的基线线索，不是自动新增，地区留空。11 月 20 日北京时间 00:00 后自动停展，不延长以供演示。T03 公网通过，用户真机反馈待收集。
T05 已通过公网测试：访客按关键词/板块/平台/地区/确定零支出查找；已开通个人账号的用户可登录、收藏/取消、退出。“我的”只列本人的非草稿活动。临时验收账号已删除，未创建共享个人账号。下一步优先做结构化反馈与订阅匹配，再实现可开关的邮箱验证注册、密码重置、注销和登录限速；邮件通道未实测前不开放公众注册。
T04 智谱 glm-4.7-flash 适配已部署，仅待服务器管理员安全配置 ZHIPUAI_API_KEY 后做真实调用与质量抽测；模型不决定发布。T06 推送尚未启用。真实营运成本、持续产量、双端手机测试均未达成。
本机使用独立 Docker 开发库 haotoday-dev-pg（set -a; source .env; set +a）；scripts/check.sh 使用一次性 PostgreSQL。不要将凭据、浏览器会话或用户资料写进日志。
