#!/usr/bin/env bash
# 本机需已迁移至 0013+ 的 haotoday-dev-pg；只复制表结构及迁移名，不读取业务记录。
set -euo pipefail
cd "$(dirname "$0")/.."
tmp=$(mktemp -d)
id=$(docker run -d --network none --log-driver none --tmpfs /var/lib/postgresql/data \
    -e POSTGRES_HOST_AUTH_METHOD=trust -e POSTGRES_USER=haotoday -e POSTGRES_DB=haotoday postgres:17-bookworm)
trap 'docker rm -fv "$id" >/dev/null; rm -rf "$tmp"' EXIT
for ((n=0;n<40;n++)); do docker exec "$id" pg_isready -qh 127.0.0.1 && break; sleep 1; done
db=(docker exec -i "$id" psql -XqAt -v ON_ERROR_STOP=1 -U haotoday -d haotoday)
for args in '--schema-only' '--data-only -t django_migrations'; do
    docker exec haotoday-dev-pg pg_dump -U haotoday -d haotoday $args | "${db[@]}" >/dev/null
done
"${db[@]}" <<'SQL'
INSERT INTO auth_user (password,is_superuser,username,first_name,last_name,email,is_staff,is_active,date_joined)
VALUES ('!',false,'drill-fixture','','','',false,true,now());
INSERT INTO discovery_pushdevice (user_id,endpoint_hash,sealed,created_at,timezone,quiet)
SELECT id,'fixture','non-routable fixture',now(),'UTC',false FROM auth_user;
INSERT INTO discovery_pushdelivery(device_id,created_at,state,attempts,next_at)
SELECT id,now(),'pending',0,now() FROM discovery_pushdevice;
SQL
# 专用库名不匹配必须拒绝；原始测试队列必须仍在。
if "${db[@]}" <deploy/quarantine-restored-push.sql >"$tmp/guard" 2>&1; then exit 1; fi
grep -Fq '只允许在专用恢复库执行' "$tmp/guard"
[[ $("${db[@]}" -c 'SELECT count(*) FROM discovery_pushdelivery') == 1 ]]
docker exec "$id" pg_dump -U haotoday -Fc haotoday > "$tmp/nonempty.dump"
deploy/restore-drill.sh "$tmp/nonempty.dump" | tee "$tmp/result"
grep -qx '恢复隔离：移除设备=1' "$tmp/result"
grep -qx '取消重播：移除待投递=1' "$tmp/result"
[[ $("${db[@]}" -c 'SELECT count(*) FROM discovery_pushdelivery') == 1 ]]
