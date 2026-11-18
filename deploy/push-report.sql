-- 最近 14 天入队的记录；不读取账号、端点、标题或消息正文。
\set ON_ERROR_STOP on
BEGIN TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY;
WITH jobs AS (
    SELECT CASE WHEN message_id IS NULL THEN 'test' ELSE 'subscription' END AS kind,
        state, CASE WHEN state='accepted' AND accepted_at>=created_at
            THEN extract(epoch FROM accepted_at-created_at) END AS lag_s
    FROM discovery_pushdelivery
    WHERE created_at>=now()-interval '14 days' AND created_at<now()
)
SELECT k.kind, count(j.state) AS queued, count(*) FILTER (WHERE j.state='pending') AS pending,
    count(*) FILTER (WHERE j.state='accepted') AS accepted, count(j.lag_s) AS timed,
    round((percentile_cont(0.9) WITHIN GROUP (ORDER BY j.lag_s))::numeric,1) AS queue_to_accept_p90_s
FROM (VALUES ('subscription'), ('test')) k(kind)
LEFT JOIN jobs j USING(kind)
GROUP BY k.kind ORDER BY k.kind;
COMMIT;
