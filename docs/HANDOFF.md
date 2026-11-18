# 当前交接
本机 T01 已通过。先读 IMPLEMENTATION_PLAN 和 WORKLOG，检查 git status -sb。用 scripts/check.sh 复验，Docker 与 .venv 安装要求见 ARCHITECTURE。
下一项为 T02：寻找一个明确允许自动读取并可对外展示必要事实的持续更新入口。先记录条款、来源和适用范围，再实现持久化观察与按期次幂等处理。验证重复、变化、错误恢复及真实目录基线。没观察到新增就不得报持续发现。候选发布者页面本身不是许可。
T03 前核对 8kraw.cloud 的 HTTPS 和现有服务，不能覆盖其他站点。AI 凭据、邮件、手机推送均未配置；后续按需接入，不要把密钥写入交接。
