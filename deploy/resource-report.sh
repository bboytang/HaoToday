#!/usr/bin/env bash
# 只读资源快照，不访问账单，不打印环境变量、活动内容、邮箱或推送端点。
set -euo pipefail
cd /opt/haotoday
date -u '+snapshot_utc=%Y-%m-%dT%H:%M:%SZ'
ids=$(docker compose ps -q --status running app db edge)
if [[ -z "$ids" ]]; then echo '项目容器均未运行' >&2; exit 1; fi
docker stats --no-stream --format '{{.Name}} cpu={{.CPUPerc}} mem={{.MemUsage}} net_rx_tx={{.NetIO}}' $ids
df -B1 --output=size,avail,pcent . | awk 'NR==2{print "host_fs_bytes=" $1, "available_bytes=" $2, "used_pct=" $3}'
du -sb backups | awk '{print "backup_dir_apparent_bytes=" $1}'
find backups -maxdepth 1 -type f -name 'pre-upgrade-*.dump' -printf '.\n' | wc -l | awk '{print "upgrade_archives=" $1}'
docker compose exec -T db psql -XAt -F '|' -P null=unknown -v ON_ERROR_STOP=1 -U haotoday -d haotoday <<'SQL'
BEGIN TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY;
SELECT 'database_bytes',pg_database_size(current_database());
SELECT 'cached_analyses_24h',count(*),'with_reported_usage',count(usage->>'total_tokens'),
    'reported_total_tokens',sum((usage->>'total_tokens')::bigint)
FROM discovery_ruleanalysis WHERE created_at>=now()-interval '24 hours' AND created_at<=now();
SELECT 'auto_first_seen_24h',count(*)
FROM discovery_observation o JOIN discovery_run r ON r.id=o.first_run_id
WHERE r.status='ok' AND NOT o.baseline AND r.started>=now()-interval '24 hours' AND r.started<=now();
COMMIT;
SQL
