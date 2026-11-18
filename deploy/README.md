# 8kraw.cloud 邀请内测
仅 Caddy 暴露 80/443；全站 HTTPS Basic Auth（账号 preview），公网不开放 Django admin 和注册。预览密码只在服务器 /opt/haotoday/preview-password（0600）内。不要复制数据库凭据或将口令写入 Git。
应用镜像从仓库根目录 docker build -t haotoday-app:<版本> . 构建，部署到同架构服务器。compose.yaml、Caddyfile 位于服务器 /opt/haotoday，.env 由部署人员在服务器生成，包含 APP_IMAGE、PGPASSWORD、DJANGO_SECRET_KEY、PREVIEW_HASH（对应 Caddy hash-password 输出，使用单引号防止变量展开）。禁止打印 compose config 的展开结果。
更新：先备份数据库，保留旧镜像，确认新迁移向后兼容。检查目标主机空闲端口和卷；设置 APP_IMAGE 后执行 docker compose run --rm app python manage.py migrate --noinput，再 docker compose up -d。通过 HTTPS 验证匿名请求 401，认证用户可看频道和详情。回退应用选回原 APP_IMAGE 启动；涉及不兼容数据时使用已验证备份恢复，不删除卷。仅停止本站：在此目录 docker compose stop；不可全局清理 Docker。
这不是公众运营放行记录。没有开启公开注册、匿名活动阅读或系统推送。上线管理员 MFA 前后台不通过反代开放。

## 定时发现
服务器 systemd 使用本目录同名前缀的 service/timer，每 30 分钟完成一次非重叠的单次采集，写入独立 Run。状态：systemctl list-timers --all haotoday-discovery.timer；日志：journalctl -u haotoday-discovery.service。仅停止调度：systemctl disable --now haotoday-discovery.timer。停用来源另用 Source.enabled；这些操作都不影响网站。

## 智谱规则摘录（可选）
模型固定 glm-4.7-flash，使用智谱国内 BigModel 的 chat/completions。由服务器管理员用编辑器将 ZHIPUAI_API_KEY 写入 /opt/haotoday/.env（0600），在同目录执行 docker compose up -d app 使环境生效。不要使用带明文密钥的命令、不要粘贴到聊天、不要打印 docker inspect 或展开后的 compose 配置。
把**经审核可发给智谱的公开条款**通过标准输入传入 docker compose exec -T app python manage.py analyze_rules；不要发送 HAR、订单、个人账号、密钥。当前只按需调用，不会自动扣费处理每次采集。失败不影响站点，结果只是待审核摘录。模型使用了多少 token 以成功响应的 usage 记录为准。

## 账号邮件
默认不开放注册或邮件找回。运营方在服务器私有 .env 配置 HAOTODAY_SMTP_HOST、HAOTODAY_SMTP_PORT、HAOTODAY_SMTP_USER、HAOTODAY_SMTP_PASSWORD、HAOTODAY_FROM_EMAIL。465 使用 TLS，其他端口要求 STARTTLS。先在受保护内测环境向获同意的测试邮箱试发；HAOTODAY_MAIL_ENABLED=1 控制邮件找回，HAOTODAY_REGISTRATION_OPEN=1 另外控制注册。修改后 docker compose up -d app。运营放行之前不撤销站点邀请认证。不要提交密钥、令牌链接、收件人地址或邮件内容。
注册邮件令牌有效 30 分钟，点开后由邮箱持有人设置密码，不预创建可登录账号；重复发送会替换旧令牌。注销须重验密码，管理员不能自助注销。账号相关限速计数在项目数据库中按十分钟窗口存放不可逆键；注册/找回每账号每窗口 3 次，登录 12 次，另有 IP 总量限制。
