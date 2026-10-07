#!/bin/sh
set -eu
umask 077

mode=${1:?mode required}
image=${2:?image required}
commit_sha=${3:?commit required}
container=Floppy
template=/boot/config/plugins/dockerMan/templates-user/my-Floppy.xml
backup_dir=/mnt/user/appdata/floppy/backups
stamp=$(date +%Y%m%d-%H%M%S)

env_file=""
restore_sql_tmp=""
restore_script=""
restore_log=""
in_rollback=0
deploy_phase="INIT"
database_backup=""
template_backup=""
current_id=""
previous_sha=""

cleanup() {
    if [ -n "$env_file" ] && [ -f "$env_file" ]; then rm -f "$env_file" || true; fi
    if [ -n "$restore_sql_tmp" ] && [ -f "$restore_sql_tmp" ]; then rm -f "$restore_sql_tmp" || true; fi
    if [ -n "$restore_script" ] && [ -f "$restore_script" ]; then rm -f "$restore_script" || true; fi
    if [ -n "$restore_log" ] && [ -f "$restore_log" ]; then rm -f "$restore_log" || true; fi
}

on_failure_trap() {
    exit_status=$1
    trap - EXIT INT TERM
    # Keep connection configuration available until recovery has finished.
    trap cleanup EXIT
    if [ "$exit_status" -ne 0 ] && [ "$in_rollback" -eq 0 ]; then
        if [ "$deploy_phase" = "PRE_ACTIVATION" ]; then
            echo "Activation interrupted before schema changes; recovering previous release." >&2
            if ! cp "$template_backup" "$template" ||
               ! docker start "$container" >/dev/null 2>&1 ||
               ! wait_for_health "$container"; then
                echo "Recovery failed: previous container or template could not be restored." >&2
                exit 5
            fi
            recovered_sha=$(docker exec "$container" printenv COMMIT_SHA 2>/dev/null || true)
            if [ -n "$previous_sha" ] && [ "$recovered_sha" != "$previous_sha" ]; then
                echo "Recovery failed: previous container identity does not match." >&2
                exit 5
            fi
        elif [ "$deploy_phase" = "ACTIVATED" ]; then
            echo "Activation interrupted; restoring previous release and database." >&2
            rollback
        fi
    fi
    exit "$exit_status"
}
trap 'on_failure_trap $?' EXIT
trap 'on_failure_trap 130' INT
trap 'on_failure_trap 143' TERM

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

ensure_container_stopped() {
    target=$1
    docker stop "$target" >/dev/null 2>&1 || true

    inspect_exit=0
    status=$(docker inspect --format '{{.State.Status}}' "$target" 2>&1) || inspect_exit=$?
    if [ "$inspect_exit" -ne 0 ]; then
        if echo "$status" | grep -Eqi "no such (container|object)"; then
            return 0
        fi
        echo "Docker daemon error inspecting $target: $status" >&2
        return 1
    fi

    case "$status" in
        exited|dead|created) return 0 ;;
        *)
            echo "Container $target is $status; refusing database modification." >&2
            return 1
            ;;
    esac
}

set_repository() {
    repository=$1
    sed -i "s#<Repository>[^<]*</Repository>#<Repository>${repository}</Repository>#" "$template"
    grep -Fq "<Repository>${repository}</Repository>" "$template"
}

restore_sqlite() {
    if ! sqlite3 "$database_file" ".restore '$database_backup'" ||
       [ "$(sqlite3 "$database_file" 'PRAGMA quick_check;' 2>/dev/null || true)" != "ok" ]; then
        echo "SQLite restore failed." >&2
        return 1
    fi
    return 0
}

restore_postgres() {
    if ! docker run --rm -v "$backup_dir:/backup:ro" "$postgres_image" \
        pg_restore --list "/backup/$(basename "$database_backup")" >/dev/null 2>&1; then
        echo "PostgreSQL backup validation failed prior to restore." >&2
        return 1
    fi

    restore_sql_tmp="$backup_dir/.restore-$stamp.sql.tmp"
    restore_script="$backup_dir/.restore-$stamp.sql"
    restore_log="$backup_dir/.restore-$stamp.log"
    touch "$restore_sql_tmp" "$restore_script" "$restore_log"
    chmod 600 "$restore_sql_tmp" "$restore_script" "$restore_log"

    if ! docker run --rm -v "$backup_dir:/backup:ro" "$postgres_image" \
        pg_restore --file=- --clean --if-exists --no-owner --no-privileges "/backup/$(basename "$database_backup")" \
        >"$restore_sql_tmp" 2>"$restore_log"; then
        echo "PostgreSQL restore SQL generation failed." >&2
        rm -f "$restore_sql_tmp" "$restore_script"
        return 1
    fi

    if [ ! -s "$restore_sql_tmp" ]; then
        echo "PostgreSQL restore SQL generation produced an empty script." >&2
        rm -f "$restore_sql_tmp" "$restore_script"
        return 1
    fi

    {
        printf 'DROP SCHEMA public CASCADE;\nCREATE SCHEMA public;\n'
        cat "$restore_sql_tmp"
    } > "$restore_script"
    rm -f "$restore_sql_tmp"

    restore_success=0
    if docker run -i --rm --network nicolab --env-file "$env_file" "$postgres_image" \
        psql --single-transaction --set=ON_ERROR_STOP=1 < "$restore_script" >"$restore_log" 2>&1; then
        restore_success=1
    fi
    rm -f "$restore_script"

    if [ "$restore_success" -ne 1 ]; then
        echo "PostgreSQL database restore failed; transactional rollback preserved pre-restore database state." >&2
        return 1
    fi
    rm -f "$restore_log"
    return 0
}

rollback() {
    if [ "$in_rollback" -eq 1 ]; then
        return
    fi
    in_rollback=1

    echo "Activation failed; initiating rollback to previous release." >&2

    # Stop failed app and verify absence or stoppage
    if ! ensure_container_stopped "$container"; then
        echo "Rollback failed: failed application container could not be stopped or confirmed stopped. Database restore aborted." >&2
        exit 5
    fi

    # Restore application DB backup first
    if [ "$is_postgres" -eq 1 ]; then
        if ! restore_postgres; then
            echo "Rollback failed: database restore was unsuccessful. Old container will NOT be started on unrestored database." >&2
            exit 5
        fi
    else
        if ! restore_sqlite; then
            echo "Rollback failed: SQLite database restore was unsuccessful. Old container will NOT be started on unrestored database." >&2
            exit 5
        fi
    fi

    # Restore saved template and rebuild prior container
    cp "$template_backup" "$template"
    if ! php /usr/local/emhttp/plugins/dynamix.docker.manager/scripts/rebuild_container Floppy ||
       ! wait_for_health "$container"; then
        echo "Rollback failed: previous container rebuild or health check failed." >&2
        exit 5
    fi

    # Verify recovered identity
    if [ -n "$previous_sha" ]; then
        recovered_sha=$(docker exec "$container" printenv COMMIT_SHA 2>/dev/null || true)
        if [ "$recovered_sha" != "$previous_sha" ]; then
            echo "Rollback failed: recovered COMMIT_SHA ($recovered_sha) does not match expected prior ($previous_sha)." >&2
            exit 5
        fi
    fi

    # Verify migrations are clean on recovered container
    if ! docker exec "$container" python manage.py migrate --check >/dev/null 2>&1; then
        echo "Rollback failed: unapplied migrations detected after database restore." >&2
        exit 5
    fi

    echo "Rollback completed: previous release and database successfully restored." >&2
    exit 4
}

prune_redundant_images() {
    newest_backup_tag="floppy:pre-custom-$stamp"
    for tag in $(docker images --format '{{.Repository}}:{{.Tag}}' 2>/dev/null | grep '^floppy:pre-custom-' || true); do
        if [ "$tag" != "$newest_backup_tag" ]; then
            docker rmi "$tag" >/dev/null 2>&1 || true
        fi
    done

    # Prune superseded immutable tags for PreciselyWrong/floppy repository
    # Retain active image ID, previous image ID, and required tags
    active_image_id=$(docker inspect "$container" --format '{{.Image}}' 2>/dev/null || true)
    docker images --no-trunc --format '{{.Repository}} {{.Tag}} {{.ID}}' 2>/dev/null |
        grep '^ghcr\.io/preciselywrong/floppy ' |
        while read -r repo tag img_id; do
            if [ -z "$repo" ] || [ -z "$tag" ]; then
                continue
            fi
            if [ "$tag" = "<none>" ]; then
                continue
            fi
            if [ -n "$image" ] && [ "$repo:$tag" = "$image" ]; then
                continue
            fi
            if [ -n "$active_image_id" ] && [ "$img_id" = "$active_image_id" ]; then
                continue
            fi
            if [ -n "$current_id" ] && [ "$img_id" = "$current_id" ]; then
                continue
            fi
            docker rmi "$repo:$tag" >/dev/null 2>&1 || true
        done
}

if [ "$mode" != deploy ]; then
    echo "Unsupported mode: $mode" >&2
    exit 2
fi

test -f "$template"
test "$(docker inspect --format '{{.State.Health.Status}}' "$container")" = healthy
docker pull "$image"

test "$(docker run --rm --env SECRET=unraid-custom-smoke-only "$image" printenv COMMIT_SHA)" = "$commit_sha"
docker run --rm --env SECRET=unraid-custom-smoke-only "$image" python manage.py check >/dev/null

docker exec "$container" python manage.py floppy_preflight --json >/dev/null
mkdir -p "$backup_dir"
chmod 700 "$backup_dir"

db_host=$(docker inspect "$container" --format '{{range .Config.Env}}{{println .}}{{end}}' |
    awk -F= '$1 == "DB_HOST" {sub(/^[^=]*=/, ""); print $0}')

if [ -n "$db_host" ]; then
    is_postgres=1
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
    chmod 600 "$env_file"
    postgres_image=$(docker inspect postgresql15 --format '{{.Config.Image}}')

    # Verify ownership/capabilities data-free before stopping app
    capabilities_check=$(docker run --rm --network nicolab --env-file "$env_file" "$postgres_image" \
        psql -v ON_ERROR_STOP=1 -A -t -q -c "
SELECT
    pg_catalog.has_database_privilege(current_user, current_database(), 'CREATE')
    || ':' ||
    COALESCE((SELECT pg_catalog.pg_has_role(current_user, nspowner, 'USAGE') FROM pg_catalog.pg_namespace WHERE nspname = 'public'), false)
    || ':' ||
    (SELECT count(*) FROM pg_catalog.pg_namespace WHERE nspname NOT LIKE 'pg_%' AND nspname NOT IN ('information_schema', 'public'))
;
" 2>/dev/null || true)

    if [ "$capabilities_check" != "true:true:0" ]; then
        echo "Database ownership or schema capability check failed; aborting before changes." >&2
        rm -f "$env_file"
        env_file=""
        exit 3
    fi
else
    is_postgres=0
    database_file=/mnt/user/appdata/floppy/db/db.sqlite3
    if [ ! -f "$database_file" ]; then
        echo "SQLite database file not found: $database_file" >&2
        exit 3
    fi
fi

template_backup="$template.pre-custom-$stamp"
cp "$template" "$template_backup"
current_id=$(docker inspect "$container" --format '{{.Image}}')
previous_sha=$(docker inspect "$container" --format '{{range .Config.Env}}{{println .}}{{end}}' |
    awk -F= '$1 == "COMMIT_SHA" {sub(/^[^=]*=/, ""); print $0}')
docker tag "$current_id" "floppy:pre-custom-$stamp"

# Stop app BEFORE capturing rollback backup
deploy_phase="PRE_ACTIVATION"
docker stop "$container" >/dev/null

backup_failed=0
if [ "$is_postgres" -eq 1 ]; then
    database_backup="$backup_dir/pre-custom-$stamp.dump"
    if ! docker run --rm --network nicolab --env-file "$env_file" "$postgres_image" pg_dump -Fc >"$database_backup" ||
       ! docker run --rm -v "$backup_dir:/backup:ro" "$postgres_image" pg_restore --list "/backup/$(basename "$database_backup")" >/dev/null 2>&1; then
        backup_failed=1
    fi
else
    database_backup="$backup_dir/pre-custom-$stamp.sqlite3"
    if ! sqlite3 "$database_file" ".backup '$database_backup'" ||
       [ "$(sqlite3 "$database_backup" 'PRAGMA quick_check;' 2>/dev/null || true)" != "ok" ]; then
        backup_failed=1
    fi
fi

if [ "$backup_failed" -eq 1 ]; then
    echo "Database backup failed; restarting existing container and failing closed." >&2
    if [ -n "${database_backup:-}" ]; then rm -f "$database_backup"; fi
    exit 3
fi
chmod 600 "$database_backup"

set_repository "$image"
deploy_phase="ACTIVATED"

if ! php /usr/local/emhttp/plugins/dynamix.docker.manager/scripts/rebuild_container Floppy; then
    rollback
fi

if ! wait_for_health "$container"; then
    rollback
fi

current_commit_sha=$(docker exec "$container" printenv COMMIT_SHA 2>/dev/null || true)
if [ "$current_commit_sha" != "$commit_sha" ]; then
    rollback
fi

if ! docker exec "$container" python manage.py floppy_preflight --json >/dev/null 2>&1; then
    rollback
fi

deploy_phase="DONE"
prune_redundant_images

echo "UNRAID_READY image=$image backup=$database_backup"
exit 0
