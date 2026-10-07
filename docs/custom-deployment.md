# Custom deployment

`custom` contains `upstream/latest` plus pending feature branches and this deployment tooling. Pushes publish:

- `ghcr.io/preciselywrong/floppy:custom` for the newest tested build;
- `ghcr.io/preciselywrong/floppy:sha-<commit>` for a reproducible rollback.

Unraid runs the immutable commit tag. Publication keeps the existing container settings and `/mnt/user/appdata/floppy/db` mount, creates a database backup, explicitly starts the rebuilt container, then checks container health. Unraid may stop a rebuilt container when its autostart preference is disabled; deployment restores the running state without changing that preference.

## Automated rollback and recovery

Before modifying any configuration or database state:
1. Destination template and existing container health are validated;
2. New immutable image is pulled, its `COMMIT_SHA` verified, and `manage.py check` executes cleanly;
3. Preflight runs on the current release;
4. For PostgreSQL, database capabilities and `public` schema ownership are validated data-free without requiring superuser or `createdb` privileges.
5. The container is stopped before capturing the `pre-custom` backup so restored data represents the consistent shutdown state. If backup fails, the existing container is restarted and deployment fails closed.

If container rebuild, health check, preflight, or `COMMIT_SHA` check fails after schema changes:
1. The failed container is confirmed stopped or absent via Docker daemon inspection; if the daemon cannot confirm stoppage, database restore is aborted and the script fails closed;
2. The database is restored first:
   - For PostgreSQL: SQL is generated privately with `--file=- --clean --if-exists --no-owner --no-privileges`, prepended with `DROP SCHEMA public CASCADE; CREATE SCHEMA public;`, and executed with `psql --single-transaction --set=ON_ERROR_STOP=1`. If restore fails, the transaction rolls back cleanly, the script fails closed with exit code 5, and the old release is never started against a mismatched database;
   - For SQLite: the backup is restored via `sqlite3 .restore` and validated with `PRAGMA quick_check;`;
3. The saved template and previous immutable image are restored via container rebuild and explicit start;
4. Health, previous `COMMIT_SHA` identity, and clean migration status (`manage.py migrate --check`) are verified before completing rollback (exit code 4).
5. On successful deployment, temporary files, older redundant `floppy:pre-custom-*` image tags, and superseded `ghcr.io/preciselywrong/floppy:sha-*` tags are pruned, preserving exactly the active image and the newest backup image without modifying other repositories.

Unexpected failures and handled `SIGINT`/`SIGTERM` signals before activation (phase `PRE_ACTIVATION`) restore the original template and restart the existing container without modifying database state. After activation, the same failures restore the database and prior release before temporary connection files are removed. A running, restarting, paused, or unknown container state prevents database restoration.

### Recovery limitations

Automated rollback requires access to the destination Docker socket and valid local backups. If a host-level failure, hardware reset, or SIGKILL occurs during database replay, manual intervention is required using the preserved `pre-custom` backup in `/mnt/user/appdata/floppy/backups` and the saved template.

## Return to the official image

To manually revert to upstream without automated tooling:
In Unraid, edit `Floppy`, set **Repository** to `ghcr.io/dannyvfilms/floppy:latest`, and apply. Do not delete volumes. If the custom build included a database migration, restore the matching `pre-custom` backup before using older code.
