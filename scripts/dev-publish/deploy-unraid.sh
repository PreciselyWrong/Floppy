#!/bin/sh
set -eu
umask 077

mode=${1:?mode required}
image=${2:?image required}
commit_sha=${3:?commit required}
container=Floppy
template=/boot/config/plugins/dockerMan/templates-user/my-Floppy.xml
official_image=ghcr.io/dannyvfilms/floppy:latest
backup_dir=/mnt/user/appdata/floppy/backups
stamp=$(date +%Y%m%d-%H%M%S)
smoke_suffix=$(printf '%s' "$commit_sha" | cut -c1-12)
smoke_app=floppy-custom-smoke-app-$smoke_suffix
smoke_redis=floppy-custom-smoke-redis-$smoke_suffix
smoke_network=floppy-custom-smoke-$smoke_suffix
smoke_volume=floppy-custom-smoke-db-$smoke_suffix

cleanup_smoke() {
    docker rm --force "$smoke_app" "$smoke_redis" >/dev/null 2>&1 || true
    docker network rm "$smoke_network" >/dev/null 2>&1 || true
    docker volume rm "$smoke_volume" >/dev/null 2>&1 || true
    if [ -n "${env_file:-}" ]; then rm -f "$env_file"; fi
}
trap cleanup_smoke EXIT INT TERM

wait_for_health() {
    target=$1
    for _ in $(seq 1 180); do
        health=$(docker inspect --format '{{if .State.Health}}{{.State.Health.Status}}{{end}}' "$target" 2>/dev/null || true)
        if [ "$health" = healthy ]; then return 0; fi
        state=$(docker inspect --format '{{.State.Status}}' "$target" 2>/dev/null || true)
        if [ "$state" = exited ] || [ "$state" = dead ]; then return 1; fi
        sleep 2
    done
    return 1
}

set_repository() {
    repository=$1
    sed -i "s#<Repository>[^<]*</Repository>#<Repository>${repository}</Repository>#" "$template"
    grep -Fq "<Repository>${repository}</Repository>" "$template"
}

rollback_container() {
    template_backup=$1
    cp "$template_backup" "$template"
    docker pull "$official_image" >/dev/null
    php /usr/local/emhttp/plugins/dynamix.docker.manager/scripts/rebuild_container Floppy
    wait_for_health "$container"
}

if [ "$mode" != deploy ]; then
    echo "Unsupported mode: $mode" >&2
    exit 2
fi

test -f "$template"
test "$(docker inspect --format '{{.State.Health.Status}}' "$container")" = healthy
docker pull "$image"

cleanup_smoke
docker network create "$smoke_network" >/dev/null
docker volume create "$smoke_volume" >/dev/null
docker run --detach --name "$smoke_redis" --network "$smoke_network" redis:8-alpine >/dev/null
for _ in $(seq 1 30); do
    if docker exec "$smoke_redis" redis-cli ping 2>/dev/null | grep -qx PONG; then break; fi
    sleep 2
done
docker run --detach \
    --name "$smoke_app" \
    --network "$smoke_network" \
    --env SECRET=unraid-custom-smoke-only \
    --env REDIS_URL="redis://$smoke_redis:6379" \
    --env ADMIN_ENABLED=False \
    --env DEMO_ACCOUNT_ENABLED=False \
    --env DEBUG=False \
    --env FLOPPY_RESOURCE_TIER=minimal \
    --volume "$smoke_volume:/floppy/db" \
    "$image" >/dev/null
wait_for_health "$smoke_app"
docker exec "$smoke_app" python manage.py migrate --check --noinput
test "$(docker exec "$smoke_app" printenv COMMIT_SHA)" = "$commit_sha"
cleanup_smoke

docker exec "$container" python manage.py floppy_preflight --json >/dev/null
mkdir -p "$backup_dir"
chmod 700 "$backup_dir"

if docker exec "$container" sh -c 'test -z "${DB_HOST:-}"'; then
    database_file=/mnt/user/appdata/floppy/db/db.sqlite3
    database_backup="$backup_dir/pre-custom-$stamp.sqlite3"
    sqlite3 "$database_file" ".backup '$database_backup'"
    test "$(sqlite3 "$database_backup" 'PRAGMA quick_check;')" = ok
else
    database_backup="$backup_dir/pre-custom-$stamp.dump"
    env_file=$(mktemp)
    chmod 600 "$env_file"
    docker inspect "$container" --format '{{range .Config.Env}}{{println .}}{{end}}' |
        awk -F= '
            $1 == "DB_HOST" {sub(/^[^=]*=/, ""); print "PGHOST=" $0}
            $1 == "DB_PORT" {sub(/^[^=]*=/, ""); print "PGPORT=" $0}
            $1 == "DB_NAME" {sub(/^[^=]*=/, ""); print "PGDATABASE=" $0}
            $1 == "DB_USER" {sub(/^[^=]*=/, ""); print "PGUSER=" $0}
            $1 == "DB_PASSWORD" {sub(/^[^=]*=/, ""); print "PGPASSWORD=" $0}
        ' >"$env_file"
    postgres_image=$(docker inspect postgresql15 --format '{{.Config.Image}}')
    docker run --rm --network nicolab --env-file "$env_file" "$postgres_image" pg_dump -Fc >"$database_backup"
    rm -f "$env_file"
    docker run --rm -v "$backup_dir:/backup:ro" "$postgres_image" pg_restore --list "/backup/$(basename "$database_backup")" >/dev/null
fi
chmod 600 "$database_backup"

template_backup="$template.pre-custom-$stamp"
cp "$template" "$template_backup"
current_id=$(docker inspect "$container" --format '{{.Image}}')
docker tag "$current_id" "floppy:pre-custom-$stamp"
set_repository "$image"

if ! php /usr/local/emhttp/plugins/dynamix.docker.manager/scripts/rebuild_container Floppy ||
   ! wait_for_health "$container" ||
   [ "$(docker exec "$container" printenv COMMIT_SHA 2>/dev/null || true)" != "$commit_sha" ]; then
    echo "Custom image failed; restoring the official image." >&2
    rollback_container "$template_backup"
    exit 4
fi

echo "UNRAID_READY image=$image backup=$database_backup"
