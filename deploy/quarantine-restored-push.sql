-- 只用于隔离的恢复副本；故障切换前需由用户重新授权。
\set ON_ERROR_STOP on
BEGIN;
DO $$ BEGIN
    IF current_database() <> 'haotoday_recovery' THEN
        RAISE EXCEPTION '只允许在专用恢复库执行';
    END IF;
END $$;
LOCK TABLE discovery_pushdevice, discovery_pushdelivery IN ACCESS EXCLUSIVE MODE;
SELECT '恢复隔离：移除设备='||count(*) FROM discovery_pushdevice;
SELECT '取消重播：移除待投递='||count(*) FILTER (WHERE state='pending') FROM discovery_pushdelivery;
DELETE FROM discovery_pushdelivery;
DELETE FROM discovery_pushdevice;
DO $$ BEGIN
    IF EXISTS (SELECT FROM discovery_pushdevice) OR EXISTS (SELECT FROM discovery_pushdelivery) THEN
        RAISE EXCEPTION '旧设备或历史队列未清空';
    END IF;
END $$;
COMMIT;
