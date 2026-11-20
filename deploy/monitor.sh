#!/usr/bin/env bash
# WorkingDirectory 须为部署目录。只读检查，不重启任务，不发送用户通知。
set -eu -o pipefail
failed=0
alarm() { printf 'ALERT %s\n' "$1"; failed=1; }

for name in discovery push backup shopping; do
    systemctl is-active --quiet "haotoday-$name.timer" || alarm "$name.timer inactive"
    result=$(systemctl show --value -p Result "haotoday-$name.service") || result=unknown
    [[ $result == success ]] || alarm "$name.service not successful"
done

# 即便 timer 仍 active，也检查实际完成时刻；不把上一次成功当成 worker 仍活着。
exit_us=$(systemctl show --value -p ExecMainExitTimestampMonotonic haotoday-push.service) || exit_us=0
now_us=$(python3 -c "import time; print(time.monotonic_ns() // 1000)")
if ! [[ $exit_us =~ ^[1-9][0-9]*$ ]] || (( now_us < exit_us || now_us-exit_us > 180000000 )); then
    alarm 'push worker no recent exit (3m)'
fi

# GamerPower 完整批次水位；人工线索或失败批次不能刷新。
fresh=$(docker compose exec -T db psql -XAt -v ON_ERROR_STOP=1 -U haotoday -d haotoday -c "
    SELECT EXISTS(SELECT 1 FROM discovery_run r JOIN discovery_source s ON r.source_id=s.id
    WHERE s.key='gamerpower' AND s.enabled AND r.status='ok'
      AND r.finished BETWEEN now()-interval '90 minutes' AND now());") || fresh=unknown
[[ $fresh == t ]] || alarm 'discovery no confirmed success (90m) or database unavailable'

# 购物是有限窗口：仅检查最近批次确实完成，不将 partial 当作完整目录。
shopping=$(docker compose exec -T db psql -XAt -v ON_ERROR_STOP=1 -U haotoday -d haotoday -c "
    SELECT EXISTS(SELECT 1 FROM discovery_run r JOIN discovery_source s ON r.source_id=s.id
    WHERE s.key='zhetaoke-jd' AND s.enabled AND r.status='partial'
      AND r.finished BETWEEN now()-interval '10 minutes' AND now());") || shopping=unknown
[[ $shopping == t ]] || alarm 'shopping no completed sample (10m) or database unavailable'

# 只认定时任务命名的非空归档，不用升级前备份冒充；可恢复性由独立演练验证。
archive=$(find backups -maxdepth 1 -type f -name 'daily-[0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9].dump' -size +0c -mmin -1560 ! -newermt now -print -quit) || archive=
[[ -n $archive ]] || alarm 'daily backup missing or stale (26h)'
if (( failed )); then exit 1; fi
echo 'OK timers, worker heartbeat, discovery watermark, shopping sample heartbeat, daily archive'
