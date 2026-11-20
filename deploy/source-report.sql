-- 内测运营复核：按运行开始时刻取最近 14 天，不写库；不输出活动、用户或凭据。
\set ON_ERROR_STOP on
BEGIN TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY;
SET LOCAL TIME ZONE 'Asia/Shanghai';
SELECT now() - interval '14 days' AS since_inclusive, now() AS until_exclusive;
WITH batches AS (
    SELECT source_id,
        count(*) FILTER (WHERE status='ok') AS ok,
        count(*) FILTER (WHERE status='failed') AS failed,
        count(*) FILTER (WHERE status='running') AS running,
        count(*) FILTER (WHERE status='paused') AS paused,
        count(*) FILTER (WHERE status='partial') AS partial,
        count(DISTINCT started::date) FILTER (WHERE status='ok') AS ok_days,
        max(finished) FILTER (WHERE status='ok') AS last_ok
    FROM discovery_run
    WHERE started >= now()-interval '14 days' AND started < now()
    GROUP BY source_id
), cohort AS (
    SELECT o.source_id,
        count(*) FILTER (WHERE r.status='manual') AS manual_candidates,
        count(*) FILTER (WHERE r.status IN ('ok','partial') AND o.baseline) AS baseline_candidates,
        count(*) FILTER (WHERE r.status IN ('ok','partial') AND NOT o.baseline) AS new_candidates,
        count(*) FILTER (WHERE r.status IN ('ok','partial') AND NOT o.baseline AND f.channel='verified' AND f.review_state='available'
            AND (f.starts_at IS NULL OR f.starts_at <= now()) AND f.ends_at > now()) AS new_verified_live
    FROM discovery_observation o
    JOIN discovery_run r ON r.id=o.first_run_id AND r.status IN ('ok','partial','manual')
    LEFT JOIN discovery_offer f ON f.observation_id=o.id
    WHERE r.started >= now()-interval '14 days' AND r.started < now()
    GROUP BY o.source_id
)
SELECT s.key, s.enabled, coalesce(ok,0) AS ok, coalesce(failed,0) AS failed,
    coalesce(running,0) AS running, coalesce(paused,0) AS paused, coalesce(partial,0) AS partial,
    coalesce(ok_days,0) AS ok_days, last_ok,
    round(100.0*ok/nullif(ok+failed,0),1) AS completed_ok_pct,
    coalesce(manual_candidates,0) AS manual_candidates, coalesce(baseline_candidates,0) AS baseline_candidates, coalesce(new_candidates,0) AS new_candidates,
    coalesce(new_verified_live,0) AS new_verified_live
FROM discovery_source s LEFT JOIN batches b ON b.source_id=s.id
LEFT JOIN cohort c ON c.source_id=s.id ORDER BY s.key;
-- 仅完整目录型源；新出现不等于活动刚刚首发。上次请求开始→本次成功结束
-- 包含网络与处理时间，失败/暂停不缩短区间，允许上一批在报告窗口外。
WITH arrivals AS (
    SELECT o.id, r.finished,
        (SELECT p.started FROM discovery_run p
         WHERE p.source_id=r.source_id AND p.id<>r.id AND p.status='ok' AND p.finished <= r.started
         ORDER BY p.finished DESC, p.id DESC LIMIT 1) AS prior_start
    FROM discovery_observation o JOIN discovery_run r ON r.id=o.first_run_id
    JOIN discovery_source s ON s.id=o.source_id AND s.id=r.source_id
    WHERE s.key='gamerpower' AND NOT o.baseline AND r.status='ok'
      AND r.started >= now()-interval '14 days' AND r.started < now()
), bounds AS (
    SELECT CASE WHEN prior_start <= finished THEN extract(epoch FROM finished-prior_start)/60 END AS upper_min
    FROM arrivals
)
SELECT count(*) AS new_seen, count(upper_min) AS bounded, count(*)-count(upper_min) AS unknown_bound,
    round((percentile_cont(0.9) WITHIN GROUP (ORDER BY upper_min))::numeric,2) AS listing_window_p90_min,
    round(max(upper_min),2) AS listing_window_max_min
FROM bounds;
COMMIT;
