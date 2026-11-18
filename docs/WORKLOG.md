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

## 2026-11-18 UTC｜T03 审核与公开页面
- 检查 main 工作树、台账和交接。SSH 只读预检：目标服务器有 Docker，根卷约 41G 可用，检查时仅 22 端口对外监听，未修改现网。
- 增加 Offer、审核后台、双频道列表和详情。默认草稿；不展示内部观察原文；过期移出列表并去掉领取按钮。T04 将补充字段级证据和业务版本管理。
- 实际数据库迁移 discovery.0002_offer 成功。按 GamerPower 观察 3850 定位 Epic PC 本体，直接 curl 免费目录返回 403，未重试受限抓取。借官方公开商品页 https://store.epicgames.com/p/knightica-3be45c?lang=en-US 核对本体、免费标注和截止 11/19 16:00 UTC。中国大陆结算未实测，仅作为抢先线索，本机 Offer #1；非自动新增、非已验证。
- scripts/check.sh 退出 0（8 项测试，无迁移差异）；本机持久库通过 Django Client 请求 /?channel=lead、/offers/1/ 均为 200。这不是公网或手机测试。

## 2026-11-18 UTC｜T03 HTTPS 邀请内测
- 复查 git status、交接、DNS、SSH 主机记录、服务器监听及可用资源。部署前仅有 SSH；复用了现有 Caddy 2 和已核对镜像 ID 的 PostgreSQL 17。建立独立 Compose 项目 haotoday，数据库未发布宿主端口，预览凭据仅存服务器。
- 本机 docker build、docker save/load 部署。首次低权限迁移因源码权限 0700 被拒；检查镜像文件权限后仅放宽镜像内应用文件读取权限，重新构建 t03-2。迁移成功，应用进程 UID=10001，Gunicorn 运行。Caddy 成功获取受信任证书。
- 服务器 sync_gamerpower 真实返回 baseline=14/new=0。按 source=gamerpower 与 external_id=3850 关联已有审核结论，full_clean 和期限检查后写入 Offer #1 lead，不覆盖其他数据。
- 公网 HTTP 跳转 308，HTTPS 未认证 401；一次 netrc 输入探测未正常认证，改用 curl 配置传入凭据后，首页、线索列表、详情均返回 200，列表与详情都含 Knightica，TLS verify=0。认证访问 /admin/ 返回 404。scripts/check.sh 退出 0（8 测试）。真机待用户验证，尚无推送或公开注册。
