#!/usr/bin/env bash
# 只创建会话临时表，不更改开发库。样本为规则测试，不能计入来源产量。
set -euo pipefail
cd "$(dirname "$0")/.."
out=$(mktemp); trap 'rm -f "$out"' EXIT
{
cat <<'SQL'
CREATE TEMP TABLE discovery_source(id int,key text,enabled bool);
CREATE TEMP TABLE discovery_run(id int,source_id int,status text,started timestamptz,finished timestamptz);
CREATE TEMP TABLE discovery_observation(id int,source_id int,first_run_id int,baseline bool);
CREATE TEMP TABLE discovery_offer(observation_id int,channel text,review_state text,starts_at timestamptz,ends_at timestamptz);
INSERT INTO discovery_source VALUES(1,'gamerpower',true),(2,'manual-official',false);
INSERT INTO discovery_run SELECT id,1,status,now()-age*interval '1 minute',now()-(age-1)*interval '1 minute'
FROM (VALUES (1,'ok',140),(2,'failed',120),(3,'ok',110),(4,'paused',100),(5,'ok',50)) v(id,status,age);
INSERT INTO discovery_run VALUES(6,2,'manual',now()-interval '1 hour',now());
INSERT INTO discovery_observation VALUES (1,1,1,true),(2,1,1,false),(3,1,3,false),(4,1,5,false),(5,2,6,false);
SQL
cat deploy/source-report.sql
} | docker exec -i haotoday-dev-pg psql -XqAt -v ON_ERROR_STOP=1 -U haotoday -d haotoday > "$out"
# 31/61 分钟两次上界，P90=58；没有上一批的新增单独计数。
grep -Fx '3|2|1|58.00|61.00' "$out"
