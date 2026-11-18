# 工作记录（追加）
## 2026-11-18 UTC｜T01
- 初态：pwd、ls -la、git status -sb、git ls-remote 确认工作区为空、未初始化且远端无引用。clone 指定仓库，在 main 初始化。
- Python 3.12 虚拟环境内安装并锁定 Django 5.2.19、psycopg 3.3.9 等实际依赖；项目内未保存任何真实凭据。
- 实现 DB 健康检查和环境配置；建立产品基线、质量口径、任务台账、交接材料。
- scripts/check.sh 退出 0：在一次性 PostgreSQL 17 上 check 无问题；auth/admin/contenttypes/sessions 的全部初始迁移 OK；makemigrations --check --dry-run 无差异；2 项测试通过（真实数据库健康响应、模拟数据库故障返回 503）。后者只覆盖错误处理，不是现网故障测试。
- 未部署、未采集活动、未验证手机推送。此前只读检查显示域名 A 记录指向目标服务器但 HTTPS 不通；部署前重查。

## 2026-11-18 UTC｜T02 本机首源采集
- 开工检查 main 跟踪 origin/main 且干净；审阅 GamerPower 官方 API 的自动访问、署名、使用和速率条款，准入卡见 SOURCES_AND_QUALITY。
- 新增 discovery 模型、只读观察后台、来源停用开关、迁移和 sync_gamerpower 命令。首次成功批次为基线，后续按来源 ID 更新；事务回滚时保留失败运行、不推进水位。命令只产生候选，不产生发布或推送。
- 生成迁移时未连接数据库，Django 警告无法检查迁移历史；随后在真实 PostgreSQL 上运行 scripts/check.sh，退出 0，迁移成功、无缺失迁移、5 项测试通过。模拟错误恢复/变化/暂停与外部实测分开。
- 建本机专用容器及数据卷 haotoday-dev-pg，仅回环监听，配置在忽略的 .env（0600）。在此库 migrate --noinput 成功。连续两次 manage.py sync_gamerpower 均退出 0：第一次 baseline=14/new=0；第二次 unchanged=14/new=0。此次真实新增为 0；未测大陆领取、持续自动调度、HTTPS、真机。
