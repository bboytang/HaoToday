# 8kraw.cloud 邀请内测
仅 Caddy 暴露 80/443；不再使用外层预览口令，游客可读，个人功能使用 /account/login/ 登录。公网不开放 Django admin 和注册。不要复制数据库凭据或将口令写入 Git。
应用镜像从仓库根目录 docker build -t haotoday-app:<版本> . 构建，部署到同架构服务器。compose.yaml、Caddyfile 位于服务器 /opt/haotoday，.env 由部署人员在服务器生成，包含 APP_IMAGE、PGPASSWORD、DJANGO_SECRET_KEY。禁止打印 compose config 的展开结果。
更新：先备份数据库，保留旧镜像，确认新迁移向后兼容。检查目标主机空闲端口和卷；设置 APP_IMAGE 后执行 docker compose run --rm app python manage.py migrate --noinput，再 docker compose up -d。通过 HTTPS 验证匿名可读频道及用户登录页、管理后台仍 404，个人用户可以登录。回退应用选回原 APP_IMAGE 启动；涉及不兼容数据时使用已验证备份恢复，不删除卷。仅停止本站：在此目录 docker compose stop；不可全局清理 Docker。
这不是公众运营放行记录。公开注册和真实邮件仍未开启；匿名活动阅读已按用户要求开放，推送 worker 已运行但真机送达待验。上线管理员 MFA 前后台不通过反代开放。

## 定时发现
服务器 systemd 使用本目录同名前缀的 service/timer，每 30 分钟完成一次非重叠的单次采集，写入独立 Run。状态：systemctl list-timers --all haotoday-discovery.timer；日志：journalctl -u haotoday-discovery.service。仅停止调度：systemctl disable --now haotoday-discovery.timer。停用来源另用 Source.enabled；这些操作都不影响网站。

## 智谱规则摘录（可选）
模型固定 glm-4.7-flash，使用智谱国内 BigModel 的 chat/completions。由服务器管理员用编辑器将 ZHIPUAI_API_KEY 写入 /opt/haotoday/.env（0600），在同目录执行 docker compose up -d app 使环境生效。不要使用带明文密钥的命令、不要粘贴到聊天、不要打印 docker inspect 或展开后的 compose 配置。
把**经审核可发给智谱的公开条款**通过标准输入传入 docker compose exec -T app python manage.py analyze_rules；不要发送 HAR、订单、个人账号、密钥。当前只按需调用，不会自动扣费处理每次采集。失败不影响站点，结果只是待审核摘录。模型使用了多少 token 以成功响应的 usage 记录为准。

## 账号邮件
默认不开放注册或邮件找回。运营方在服务器私有 .env 配置 HAOTODAY_SMTP_HOST、HAOTODAY_SMTP_PORT、HAOTODAY_SMTP_USER、HAOTODAY_SMTP_PASSWORD、HAOTODAY_FROM_EMAIL。465 使用 TLS，其他端口要求 STARTTLS。先在受保护内测环境向获同意的测试邮箱试发；HAOTODAY_MAIL_ENABLED=1 控制邮件找回，HAOTODAY_REGISTRATION_OPEN=1 另外控制注册。修改后 docker compose up -d app。运营放行之前不撤销站点邀请认证。不要提交密钥、令牌链接、收件人地址或邮件内容。
注册邮件令牌有效 30 分钟，点开后由邮箱持有人设置密码，不预创建可登录账号；重复发送会替换旧令牌。注销须重验密码，管理员不能自助注销。账号相关限速计数在项目数据库中按十分钟窗口存放不可逆键；注册/找回每账号每窗口 3 次，登录 12 次，另有 IP 总量限制。

## Web Push 内测
内测者先确认邮箱归属，在服务器用 `/opt/haotoday/create-tester.sh` 创建自己的**普通账号**（需交互终端、不发邮件、不覆盖同名账号）。与外层 preview 口令独立。进入 /devices/，iPhone 先添加到主屏幕，从图标启动；点“在本机开启提醒”，再点该设备的测试按钮。测试请求受理与通知栏可见是不同证据。
服务器专有 HAOTODAY_VAPID_KEY 是 P-256 原始私钥的 base64url 编码，保存在私有 .env，不能传到浏览器或提交。不要随意轮换 VAPID 与 DJANGO_SECRET_KEY，否则须重新订阅或迁移加密材料。devices 表仅保存摘要和加密的端点/密钥。支持列表：Apple web.push.apple.com、Chrome fcm.googleapis.com、Mozilla updates.push.services.mozilla.com；不支持的服务仍可用站内消息。
haotoday-push.timer 每 30 秒触发有限批次，状态检查 `systemctl list-timers --all haotoday-push.timer`，停外推用 `systemctl disable --now haotoday-push.timer` 并确认已运行的 service 结束。设备关闭将清除该设备和对应投递日志；站内消息保留。accepted 不代表人已看到；测试时另记录设备、网络、时刻及实际可见性。收到提醒只打开本站固定路径。

迁移 0013 起，dispatch_push 每次先处理最多 20 个到点预告，再处理最多 20 条设备投递。日志 opened 为处理的预告数（不等于有匹配用户），processed 为处理的投递数（不等于送达）。停该定时器也会暂停预告唤醒；恢复后已过期项目不发送。应用回退 t06-quiet-2 时可保留兼容的 0013；旧 worker 不消费预告。

## 每日归档与隔离恢复演练
haotoday-backup.timer 计划每天北京时间 03:15 执行，漏跑由 systemd 补触发。归档以 UTC 日期命名；同日再次执行只校验目录，不覆盖当天版本。pg_dump 失败不会发布半个归档，0600 保存。同机日档保留约七天，仅轮转 daily-YYYYMMDD.dump，不删 pre-upgrade 归档。检查 `systemctl list-timers haotoday-backup.timer` 及 `journalctl -u haotoday-backup.service`。这是同机明文数据库归档的访问权限控制，不是加密异机容灾。
在 /opt/haotoday 执行 `./restore-drill.sh backups/daily-YYYYMMDD.dump`（替换实际文件名）。它新建无网络、无宿主端口、数据在 256 MiB tmpfs 的 PostgreSQL 17，单事务整库恢复，检查版本、活动版本记录和投递触发器，随后在恢复副本上事务性清空设备注册与全部历史投递，仅输出计数后销毁演练容器。仅接受本项目可信归档；不运行其中的应用、邮件或推送进程。若数据增长导致临时空间不足，先在独立演练主机重新核算容量，不在生产卷“试恢复”。
真正故障切换仍须人工决策：停本站采集和投递及其 timer，暂停账号写入；恢复到新隔离环境，校验业务与迁移，再核对备份时间之后的账号注销、撤权和投递记录。无法确认设备授权或已发状态时，保持投递关闭，禁止盲目重播。保留故障现场和可回切的数据卷。此脚本不会切换站点，不会迁移私有 .env/VAPID、TLS 或邮件凭据；加密异机备份、密钥独立保管、故障切换和告警尚待验收。

## 内测巡检
deploy/monitor.sh 与两份 haotoday-monitor unit 放在 /opt/haotoday，脚本可执行；将 unit 安装至 /etc/systemd/system 后执行 `systemctl daemon-reload && systemctl enable --now haotoday-monitor.timer && systemctl start haotoday-monitor.service`。主机需 python3、GNU find、systemd、Docker Compose。每五分钟检查三个定时器与服务结果、推送 worker 三分钟心跳、已启用 GamerPower 最近九十分钟成功批次、二十六小时内非空日备份。查看 `journalctl -u haotoday-monitor.service --since today`。失败先查对应 service 日志与只读来源报表，不自动重启或重发。若有计划地停源，预期水位告警；新增准入源需更新监控。当前仅本机 journal 告警，不能发现整机掉线或证明手机送达。移除巡检可单独执行 `systemctl disable --now haotoday-monitor.timer`，不影响业务定时器。

恢复副本专用库名为 haotoday_recovery。部署 restore-drill.sh 必须同时提供同目录 quarantine-restored-push.sql。其保守策略是放弃副本中所有旧设备投递历史及积压，不重发；不删除站内消息、收藏或订阅规则。真正切换时，仍须停写、隔离、核对账号注销等备份后的变化，确认后由用户在设备页重新开启提醒。禁止为在现网运行清理语句而改动库名保护。原归档不变。验证非空积压请在本机运行 scripts/test-restore-queue.sh，不向现网造测试设备。

## 录入人工公告（仅服务器操作员）
不再为每则品牌或机构公告编写 Python 入库脚本。人工读原文后准备 UTF-8 JSON 对象，提供：external_id（同一来源公告/场次的稳定正整数，重跑不得换号）、publisher、title、category（购物/生活服务/数字权益）、cost、conditions、steps、official_url、evidence_url、evidence、checked_at、ends_at；可选 starts_at、platform、region。时间用含 +08:00 或 Z 的 ISO 格式；checked_at 填实际核对时刻，ends_at 是停止展示入口的时刻。仅提交可公开事实，不能提交凭据和用户资料。先查后台是否已有同一活动，编号幂等不能替代跨来源查重。
从仓库外的本地公告文件运行：
```sh
ssh -T root@43.143.230.174 'cd /opt/haotoday && docker compose exec -T app python manage.py record_notice' < notice.json
```
默认事务回滚、不产生持久记录（数据库序列号可能跳号）。核对无误后在命令末尾的单引号内加 ` --save-draft`。即使传保存参数，也只存后台草稿，不推送、不计自动新增；审核人须另行核实再发布。相同编号和内容重放不覆盖，内容冲突进后台比较。不能用此命令改旧活动、直接发布或导入网络链接中的内容。

个人账号新密码仅要求至少 6 个字符，允许纯数字；注册激活、重置和 create-tester.sh 使用同一校验。已有密码不修改。外层认证配置回退：先还原服务器 Caddyfile.before-user-login，再执行 caddy validate/reload；旧预览凭据仅服务器保留，不提交。

## 购物线报凭据准备
先用本人折淘客账号确认线报 API 权限和网站展示/通知的使用范围；不要发送密钥到聊天。服务器已放置交互配置脚本，在自己的本机终端执行：
```sh
ssh -t root@43.143.230.174 'python3 /opt/haotoday/configure-shopping-key.py'
```
两次隐藏输入 appkey，保存至服务器 /opt/haotoday/.zhetaoke-key，0600；不覆盖现有文件、不修改 .env、不联网、不启用采集。该文件尚未接入业务容器，保存成功不等于接口或真实商品验证成功。后续只在服务器读取用于小样本测试，不打印完整请求 URL（供应方采用查询参数携带 key）。该文件不属于数据库备份；轮换/删除前先核对未来调用方。不要用 echo key 或命令行参数传入。
