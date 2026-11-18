#!/usr/bin/env bash
# 只向新建的无网络临时容器恢复。没有“生产目标库”参数。
set -euo pipefail
file=${1:?请提供受信任的 HaoToday 0013 或更新版本归档}
[[ -s "$file" && -r "$file" ]]
quarantine="$(dirname "$0")/quarantine-restored-push.sql"
[[ -r "$quarantine" ]]
SECONDS=0
id=$(docker run -d --network none --log-driver none --label haotoday.task=restore-drill \
    --tmpfs /var/lib/postgresql/data:rw,size=256m --memory=512m --memory-swap=512m \
    -e POSTGRES_HOST_AUTH_METHOD=trust -e POSTGRES_USER=haotoday -e POSTGRES_DB=haotoday_recovery postgres:17-bookworm)
cleanup(){ docker rm -fv "$id" >/dev/null; }
trap cleanup EXIT
psql=(docker exec -i "$id" psql -X -qAt -v ON_ERROR_STOP=1 -U haotoday -d haotoday_recovery)
for ((n=0;n<40;n++)); do
    docker exec "$id" pg_isready -q -h 127.0.0.1 -U haotoday -d haotoday_recovery && break
    sleep 1
done
# 不输出恢复失败的 COPY 行/账号资料；保留原档，错误退出。
if ! docker exec -i "$id" pg_restore -U haotoday -d haotoday_recovery --exit-on-error --single-transaction <"$file" 2>/dev/null; then
    echo "归档恢复失败；生产库未改动" >&2; exit 1
fi
"${psql[@]}" <<'SQL'
DO $$
BEGIN
 IF NOT EXISTS (SELECT FROM django_migrations WHERE app='discovery' AND name='0013_start_wake')
 OR NOT EXISTS (SELECT FROM pg_trigger WHERE tgrelid='discovery_inboxmessage'::regclass
                AND tgname='haotoday_devices_on_message' AND tgenabled='O')
 OR EXISTS (SELECT FROM discovery_offer o WHERE NOT EXISTS (SELECT FROM discovery_offerrevision r WHERE r.offer_id=o.id))
 THEN RAISE EXCEPTION '项目迁移、投递触发器或版本链校验失败'; END IF;
END $$;
SELECT '恢复记录数：来源='||count(*) FROM discovery_source;
SELECT '活动='||count(*)||'，已验证='||count(*) FILTER (WHERE channel='verified') FROM discovery_offer;
SELECT '待投递='||count(*) FILTER (WHERE state='pending') FROM discovery_pushdelivery;
SQL
"${psql[@]}" <"$quarantine"
printf '隔离恢复检查通过，耗时 %s 秒；未启动应用或投递进程。\n' "$SECONDS"
