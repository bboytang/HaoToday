# 架构与启动
Django 模块化单体、服务端模板、PostgreSQL；应用与 worker 独立运行，一个数据库，不引入 Redis/Kubernetes。T01 仅有应用基础和健康检查，worker 和发布事件尚未实现。
数据流：来源 → 运行与观察 → 活动版本及证据 → 发布事件 → 用户消息与设备投递。观察持久化后才推进水位。采用事务、唯一键和任务租约支持故障重跑。
本机：python3 -m venv .venv，再运行 .venv/bin/pip install -r requirements.txt。scripts/check.sh 需要 Docker，自动启动一次性 PostgreSQL 17 并在退出时停止，不接触现网库。
开发启动：创建专用 PostgreSQL 用户和数据库；根据 .env.example 填写 .env（密钥可用 openssl rand -hex 32 生成），set -a; source .env; set +a，然后 .venv/bin/python manage.py migrate 及 .venv/bin/python manage.py runserver 127.0.0.1:8000。用 /health/ 检查数据库可用性。
上线不得用 runserver。独立低权限进程与私有数据库，复用反代 HTTPS；部署前复核现有服务，禁任意 URL 抓取、转义外部内容，后台 MFA、日志脱敏、每日加密异机备份，恢复演练目标 RPO 24 小时/RTO 4 小时。上线前核查备案适用性、隐私告知、投诉注销和来源权利。单源、推送、注册均需独立开关。此处是上线门槛，非上线成绩。
