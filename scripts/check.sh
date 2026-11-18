#!/usr/bin/env bash
# 使用一次性、仅回环监听的 PostgreSQL；不使用开发/生产数据。
set -euo pipefail
cd "$(dirname "$0")/.."
export DJANGO_SECRET_KEY=$(openssl rand -hex 32)
export DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1
export PGHOST=127.0.0.1 PGUSER=haotoday PGDATABASE=haotoday
export PGPASSWORD=$(openssl rand -hex 24)
id=$(docker run -d --rm --tmpfs /var/lib/postgresql/data -p 127.0.0.1::5432 -e POSTGRES_DB="$PGDATABASE" -e POSTGRES_USER="$PGUSER" -e POSTGRES_PASSWORD="$PGPASSWORD" postgres:17-bookworm)
trap 'docker stop "$id" >/dev/null' EXIT
export PGPORT=$(docker port "$id" 5432/tcp | cut -d: -f2)
for n in {1..40}; do
  docker exec "$id" pg_isready -h 127.0.0.1 -U "$PGUSER" >/dev/null && break
  sleep 1
done
for args in "check" "migrate --noinput" "makemigrations --check --dry-run" "test haotoday"; do
  .venv/bin/python manage.py $args
done
