#!/usr/bin/env bash
# 故障注入仅使用临时目录和替身命令，不停生产服务。
set -euo pipefail
monitor=$(realpath "$(dirname "$0")/../deploy/monitor.sh")
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
cd "$tmp"; mkdir bin backups
export PATH="$PWD/bin:$PATH"
cat > bin/systemctl <<'SH'
#!/usr/bin/env bash
case "$*" in
    *is-active*) [[ ${DOWN:-} != "${!#}" ]];;
    *Timestamp*) echo "${HEART:-$(python3 -c 'import time; print(time.monotonic_ns() // 1000)')}";;
    *) echo success;;
esac
SH
printf '#!/bin/sh\necho "${FRESH:-t}"\n' > bin/docker
chmod +x bin/*
echo fixture > backups/daily-20261118.dump
"$monitor"
if DOWN=haotoday-shopping.timer "$monitor" > result; then exit 1; fi
grep -F "shopping.timer inactive" result
touch -d '27 hours ago' backups/daily-20261118.dump
if DOWN=haotoday-discovery.timer HEART=1 FRESH=f "$monitor" > result; then exit 1; fi
for msg in 'discovery.timer inactive' 'push worker no recent exit' 'discovery no confirmed success' 'daily backup missing or stale' 'shopping no completed sample'; do
    grep -F "$msg" result
done
