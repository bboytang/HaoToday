# 8kraw.cloud 邀请内测
仅 Caddy 暴露 80/443；全站 HTTPS Basic Auth（账号 preview），公网不开放 Django admin 和注册。预览密码只在服务器 /opt/haotoday/preview-password（0600）内。不要复制数据库凭据或将口令写入 Git。
应用镜像从仓库根目录 docker build -t haotoday-app:<版本> . 构建，部署到同架构服务器。compose.yaml、Caddyfile 位于服务器 /opt/haotoday，.env 由部署人员在服务器生成，包含 APP_IMAGE、PGPASSWORD、DJANGO_SECRET_KEY、PREVIEW_HASH（对应 Caddy hash-password 输出，使用单引号防止变量展开）。禁止打印 compose config 的展开结果。
更新：先备份数据库，保留旧镜像，确认新迁移向后兼容。检查目标主机空闲端口和卷；设置 APP_IMAGE 后执行 docker compose run --rm app python manage.py migrate --noinput，再 docker compose up -d。通过 HTTPS 验证匿名请求 401，认证用户可看频道和详情。回退应用选回原 APP_IMAGE 启动；涉及不兼容数据时使用已验证备份恢复，不删除卷。仅停止本站：在此目录 docker compose stop；不可全局清理 Docker。
这不是公众运营放行记录。没有开启公开注册、匿名活动阅读或系统推送。上线管理员 MFA 前后台不通过反代开放。
