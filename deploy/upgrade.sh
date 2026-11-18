#!/usr/bin/env bash
# 仅供已安装的内测站使用。镜像必须已加载，迁移须先验证向后兼容。
set -euo pipefail
cd /opt/haotoday
image=${1:?请指定 haotoday-app 镜像}
[[ "$image" =~ ^haotoday-app:[a-zA-Z0-9._-]+$ ]]
docker image inspect "$image" >/dev/null
umask 077
mkdir -p backups
dump="backups/pre-upgrade-$(date -u +%Y%m%dT%H%M%SZ).dump"
docker compose exec -T db pg_dump -U haotoday -Fc haotoday > "$dump"
docker compose exec -T db pg_restore -l < "$dump" >/dev/null
old=$(grep '^APP_IMAGE=' .env)
[[ "$old" =~ ^APP_IMAGE=haotoday-app:[a-zA-Z0-9._-]+$ ]]
APP_IMAGE="$image" docker compose run --rm -T app python manage.py migrate --noinput
sed -i "s/^APP_IMAGE=.*/APP_IMAGE=$image/" .env
if ! docker compose up -d app || ! docker compose exec -T app python manage.py check; then
    sed -i "s/^APP_IMAGE=.*/$old/" .env
    docker compose up -d app
    echo '应用切回旧镜像；需核对迁移与流量状态' >&2
    exit 1
fi
echo "备份 $dump；应用 $image。仍需外部 HTTPS 检查。"
