# 工作记录（追加）
## 2026-11-18 UTC｜T01
- 初态：pwd、ls -la、git status -sb、git ls-remote 确认工作区为空、未初始化且远端无引用。clone 指定仓库，在 main 初始化。
- Python 3.12 虚拟环境内安装并锁定 Django 5.2.19、psycopg 3.3.9 等实际依赖；项目内未保存任何真实凭据。
- 实现 DB 健康检查和环境配置；建立产品基线、质量口径、任务台账、交接材料。
- scripts/check.sh 退出 0：在一次性 PostgreSQL 17 上 check 无问题；auth/admin/contenttypes/sessions 的全部初始迁移 OK；makemigrations --check --dry-run 无差异；2 项测试通过（真实数据库健康响应、模拟数据库故障返回 503）。后者只覆盖错误处理，不是现网故障测试。
- 未部署、未采集活动、未验证手机推送。此前只读检查显示域名 A 记录指向目标服务器但 HTTPS 不通；部署前重查。
