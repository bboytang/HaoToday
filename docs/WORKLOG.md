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

## 2026-11-18 UTC｜真实周期采集与 T04 版本记录
- 目标主机确认无同名 systemd 定时器；systemd-analyze verify 成功（另一个已有云代理单元有无关 PIDFile 警告，未修改）。安装并启用项目专用 timer/service。systemctl 和 journalctl 确认北京时间 22:57:54 首次自动启动，22:57:56 正常退出，baseline=0/new=0/changed=0/unchanged=14，下一次计划 23:27:56。不能据此声称发现新增或长期稳定。
- 新增 PostgreSQL 活动版本记录：创建、内容实质变更和批量更新均与原事务写快照；无变化与回滚不新增。新迁移为原有活动补当前基线，不伪造历史版本。后台只读查询。
- scripts/check.sh 退出 0，9 项通过；本机持久库 migrate --noinput 成功，实际查询补建记录为 offer_id=1、channel=lead。线上仍是 T03 镜像，无 0003 迁移。真机、AI 和持续产量尚未验收。

## 2026-11-18 UTC｜T04 已验证发布门槛上线
- PostgreSQL 约束要求已验证行包含三项显式成本和四类非空证据；前台已验证卡片/详情统一用整数分相加，不展示自由文本中的估计价。旧线索仍允许金额未知。scripts/check.sh：空库迁移及 10 项测试通过，覆盖 1 分+600 分运费、未填会员费、空白资格及日期依据、批量更新拒绝。
- 构建 t04-evidence-1 上传；首次 SSH heredoc 部署在备份后未继续（stdin 被容器命令使用）。检查发现线上仍 t03-2 和 0002，没有误报成功。以不共享命令输入流的方式续跑：pg_restore 将 pre-evidence-20261118T150032Z.dump 实际还原到独立临时库，活动行数 1，结束后删除临时库。
- 线上迁移 0003、0004 均 OK，查询版本记录数为 1；应用重建后认证 HTTPS /offers/1/ 返回包含 Knightica 的页面。未对正式数据制造测试活动。此为升级前同机备份，不等于异地灾备。真机及 AI 尚未实测。

## 2026-11-18 UTC｜T04 复查状态、智谱适配
- 增加疑似失效、撤回和起止窗口；非活跃详情保留状态/原因，不展示步骤和领取链接。完整采集才判断消失；来源错误不误撤回；恢复出现不自动恢复活动。13 项回归测试通过。初版迁移仅在本机回退并重新生成，在正式 0005 中为新增必填状态设置数据库默认值，以兼容旧站写入。
- 用户确定 GLM-4.7-Flash；核对智谱官方文档 https://docs.bigmodel.cn/cn/guide/models/free/glm-4.7-flash 。仅提供受控的公开文本摘录命令，禁止自动发布；校验逐字引文，按摘要、模型、提示词版本去重，保存响应使用量。无密钥不发送请求。临时 PostgreSQL 全量迁移与 15 个测试通过（AI 使用模拟响应，不是线上模型验收）。
- 已备份、迁移并部署 haotoday-app:t04-glm-1，0005/0006 均 OK，管理检查成功。线上仅检查项目密钥有无，结果为未设置；未实际调用智谱。真实采集 unchanged=14、missing_for_review=0。外部认证 HTTPS 详情仍返回 Knightica。备份位于服务器 backups/pre-upgrade-20261118T150542Z.dump，本次检查目录可读，未在本次重复做完整恢复。
