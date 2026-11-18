#!/usr/bin/env bash
# 同机保留 7 天，仅清理本脚本命名的归档；升级前备份独立管理。
set -euo pipefail
cd /opt/haotoday
umask 077
mkdir -p backups
exec 9>backups/.daily.lock
flock -n 9 || exit 1
out="backups/daily-$(date -u +%Y%m%d).dump"
if [[ ! -e "$out" ]]; then
    tmp=$(mktemp backups/.daily-XXXXXXXX)
    trap 'unlink "$tmp" 2>/dev/null || :' EXIT
    docker compose exec -T db pg_dump -U haotoday -Fc haotoday > "$tmp"
    docker compose exec -T db pg_restore -l < "$tmp" >/dev/null
    mv "$tmp" "$out"
else
    docker compose exec -T db pg_restore -l < "$out" >/dev/null
fi
find backups -maxdepth 1 -type f -name 'daily-[0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9].dump' -mmin +10080 -delete
printf '归档：%s；%s 字节（目录可读不等于整库恢复成功）\n' "$out" "$(stat -c %s "$out")"
