# Custom deployment

`custom` contains `upstream/latest` plus pending feature branches and this deployment tooling. Pushes publish:

- `ghcr.io/preciselywrong/floppy:custom` for the newest tested build;
- `ghcr.io/preciselywrong/floppy:sha-<commit>` for a reproducible rollback.

Unraid runs the immutable commit tag. Publication keeps the existing container settings and `/mnt/user/appdata/floppy/db` mount, creates a database backup, then checks container health.

## Return to the official image

In Unraid, edit `Floppy`, set **Repository** to `ghcr.io/dannyvfilms/floppy:latest`, and apply. Do not delete volumes. If the custom build included a database migration, restore the matching `pre-custom` backup before using older code.
