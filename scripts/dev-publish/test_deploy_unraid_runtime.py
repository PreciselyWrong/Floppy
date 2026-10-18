"""Exercise release recovery with isolated command adapters and synthetic data."""

# Standalone script, imported by test_tools rather than an application package.
# ruff: noqa: INP001
import os
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BASH = shutil.which("bash") or "C:/Program Files/Git/bin/bash.exe"


class DeployUnraidRuntimeTests(unittest.TestCase):
    """Verify release failures preserve data and recover the prior application."""

    def setUp(self) -> None:
        """Create private template, database and command fixtures."""
        self.assertTrue(Path(BASH).is_file(), f"Bash not found at {BASH}")
        self.test_dir = tempfile.TemporaryDirectory()
        self.work_path = Path(self.test_dir.name)
        self.bin_dir = self.work_path / "bin"
        self.bin_dir.mkdir(parents=True, exist_ok=True)
        self.events_file = self.work_path / "events.log"
        self.state_dir = self.work_path / "state"
        self.state_dir.mkdir(parents=True, exist_ok=True)

        self.template_dir = self.work_path / "templates-user"
        self.template_dir.mkdir(parents=True, exist_ok=True)
        self.template_file = self.template_dir / "my-Floppy.xml"
        self.template_file.write_text(
            "<Container><Repository>ghcr.io/preciselywrong/floppy:sha-previous</Repository></Container>\n",
            encoding="utf-8",
        )

        self.backup_dir = self.work_path / "backups"
        self.backup_dir.mkdir(parents=True, exist_ok=True)

        self.sqlite_dir = self.work_path / "db"
        self.sqlite_dir.mkdir(parents=True, exist_ok=True)
        self.sqlite_file = self.sqlite_dir / "db.sqlite3"
        conn = sqlite3.connect(self.sqlite_file)
        conn.execute("CREATE TABLE items (id int, name text);")
        conn.execute("INSERT INTO items VALUES (1, 'initial_record');")
        conn.commit()
        conn.close()

        self.pg_sim_dir = self.work_path / "pg_sim"
        self.pg_sim_dir.mkdir(parents=True, exist_ok=True)
        self.pg_data_file = self.pg_sim_dir / "db_content.txt"

    def tearDown(self) -> None:
        """Remove the isolated fixture directory."""
        self.test_dir.cleanup()

    def get_events(self) -> list[str]:
        """Return command events in execution order."""
        if not self.events_file.is_file():
            return []
        return [
            line.strip()
            for line in self.events_file.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]

    def create_mock_commands(
        self,
        is_postgres: bool = False,
        fail_activation: bool = False,
        fail_backup: bool = False,
        fail_restore: bool = False,
        fail_capabilities: bool = False,
        mismatch_sha: bool = False,
        secret_password: str = "synthetic-test-only",  # noqa: S107 - synthetic fixture
        fail_stop_app: bool = False,
        fail_daemon_inspect: bool = False,
        fail_after_stop: bool = False,
        extra_images: list[str] | None = None,
        failed_stop_state: str = "running",
        rebuild_stops_app: bool = False,
        fail_start_app: bool = False,
    ) -> None:
        """Install adapters representing observable Docker and database behavior."""
        python_exe = Path(sys.executable).as_posix()
        events_path = self.events_file.as_posix()
        sqlite_path = self.sqlite_file.as_posix()
        pg_data_path = self.pg_data_file.as_posix()
        state_dir_path = self.state_dir.as_posix()
        template_path = self.template_file.as_posix()
        extra_imgs = extra_images or []

        docker_adapter_py = self.work_path / "docker_adapter.py"
        docker_adapter_py.write_text(
            f"""# Python synthetic docker adapter
import sys
import os
from pathlib import Path

args = sys.argv[1:]
events_file = Path("{events_path}")
pg_data_file = Path("{pg_data_path}")
state_dir = Path("{state_dir_path}")
template_file = Path("{template_path}")

def log(evt):
    with open(events_file, "a", encoding="utf-8") as f:
        f.write(evt + "\\n")

if not args:
    sys.exit(0)

cmd = args[0]

if cmd == "inspect":
    target = next(a for i, a in enumerate(args[1:], 1) if not a.startswith("-") and args[i - 1] != "--format")
    if {fail_daemon_inspect} and (state_dir / "in_rollback").exists():
        sys.stderr.write("docker: daemon error\\n")
        sys.exit(1)
    format_arg = ""
    for i, a in enumerate(args):
        if a == "--format" and i + 1 < len(args):
            format_arg = args[i + 1]
    if "Health.Status" in format_arg:
        if (state_dir / "container_unhealthy").exists() or (state_dir / "container_stopped").exists():
            print("unhealthy")
        else:
            print("healthy")
        sys.exit(0)
    elif "State.Status" in format_arg:
        if {fail_stop_app} and (state_dir / "in_rollback").exists():
            print({failed_stop_state!r})
            sys.exit(0)
        if (state_dir / "container_stopped").exists():
            print("exited")
        elif (state_dir / "container_unhealthy").exists():
            print("exited")
        else:
            print("running")
        sys.exit(0)
    elif "Config.Env" in format_arg:
        if {is_postgres}:
            print("DB_HOST=postgres_host")
            print("DB_PORT=5432")
            print("DB_NAME=floppy_db")
            print("DB_USER=floppy_user")
            print("DB_PASSWORD={secret_password}")
        else:
            print("DB_HOST=")
        print("COMMIT_SHA=old-commit-sha-123")
        sys.exit(0)
    elif "Config.Image" in format_arg and target == "postgresql15":
        print("postgres:15")
        sys.exit(0)
    elif ".Image" in format_arg:
        if (state_dir / "activated").exists() and not (state_dir / "rolled_back").exists():
            print("sha256:new_image_id_67890")
        else:
            print("sha256:previous_image_id_12345")
        sys.exit(0)
    print("ok")
    sys.exit(0)

elif cmd == "pull":
    image = args[-1]
    log(f"docker:pull:{{image}}")
    sys.exit(0)

elif cmd == "tag":
    src = args[1]
    dst = args[2]
    log(f"docker:tag:{{src}}:{{dst}}")
    (state_dir / f"tag_{{dst.replace(':', '_')}}").touch()
    sys.exit(0)

elif cmd == "rmi":
    target = args[-1]
    log(f"docker:rmi:{{target}}")
    sys.exit(0)

elif cmd == "images":
    format_arg = ""
    for i, a in enumerate(args):
        if a == "--format" and i + 1 < len(args):
            format_arg = args[i + 1]
    default_imgs = [
        "floppy\tpre-custom-20260101-100000\tsha256:old_img_1",
        "floppy\tpre-custom-20261001-120000\tsha256:old_img_2",
        "ghcr.io/preciselywrong/floppy\tsha-old111\tsha256:old_img_3",
        "ghcr.io/preciselywrong/floppy\tsha-previous\tsha256:previous_image_id_12345",
        "ghcr.io/preciselywrong/floppy\tsha-new456\tsha256:new_image_id_67890",
        "ghcr.io/dannyvfilms/floppy\tlatest\tsha256:upstream_img_id",
        "redis\t7\tsha256:redis_img_id",
    ]
    custom_imgs = {extra_imgs} if {bool(extra_imgs)} else default_imgs
    for entry in custom_imgs:
        parts = entry.split("\\t")
        repo = parts[0]
        tag = parts[1] if len(parts) > 1 else "latest"
        img_id = parts[2] if len(parts) > 2 else "sha256:dummy"
        if "{{.ID}}" in format_arg:
            if "--no-trunc" not in args:
                img_id = img_id.removeprefix("sha256:")[:12]
            if " " in format_arg:
                print(f"{{repo}} {{tag}} {{img_id}}")
            else:
                print(f"{{repo}}\\t{{tag}}\\t{{img_id}}")
        else:
            print(f"{{repo}}:{{tag}}")
    sys.exit(0)

elif cmd == "stop":
    target = args[-1]
    log(f"docker:stop:{{target}}")
    if {fail_stop_app} and (state_dir / "in_rollback").exists():
        sys.stderr.write("docker: Error response from daemon: cannot stop container\\n")
        sys.exit(1)
    (state_dir / "container_stopped").touch()
    sys.exit(0)

elif cmd == "start":
    target = args[-1]
    log(f"docker:start:{{target}}")
    if {fail_start_app} and (state_dir / "activated").exists() and not (state_dir / "rolled_back").exists():
        (state_dir / "in_rollback").touch()
        sys.exit(1)
    (state_dir / "container_stopped").unlink(missing_ok=True)
    sys.exit(0)

elif cmd == "exec":
    target = args[1]
    subcmd = args[2:]
    joined_sub = " ".join(subcmd)
    if "floppy_preflight" in joined_sub:
        log("docker:exec:preflight")
        sys.exit(0)
    elif "manage.py migrate --check" in joined_sub:
        log("docker:exec:migrate_check")
        sys.exit(0)
    elif "COMMIT_SHA" in joined_sub:
        if (state_dir / "rolled_back").exists() or not (state_dir / "activated").exists():
            print("old-commit-sha-123")
        elif {mismatch_sha}:
            print("wrong-mismatched-sha")
        else:
            print("new-commit-sha-456")
        sys.exit(0)
    elif 'test -z "${{DB_HOST:-}}"' in joined_sub:
        if {is_postgres}:
            sys.exit(1)
        else:
            sys.exit(0)
    sys.exit(0)

elif cmd == "run":
    if "--env-file" in args and not Path(args[args.index("--env-file") + 1]).is_file():
        sys.stderr.write("docker: env file is missing\\n")
        sys.exit(1)
    joined = " ".join(args)
    if "printenv COMMIT_SHA" in joined:
        print("new-commit-sha-456")
        sys.exit(0)
    elif "manage.py check" in joined:
        sys.exit(0)
    elif "psql" in joined:
        if "has_database_privilege" in joined or "pg_has_role" in joined:
            if {fail_capabilities}:
                print("false:false:1")
                sys.exit(0)
            print("true:true:0")
            sys.exit(0)
        elif "--single-transaction" in joined:
            log("docker:run:psql_restore")
            if {fail_restore}:
                sys.stderr.write("psql: error: relation broken_restore_err\\n")
                sys.exit(1)
            content = sys.stdin.read()
            if "DROP SCHEMA public CASCADE" in content:
                pg_data_file.write_text("RESTORED_SCHEMA_PUBLIC\\ntable_items:record1\\n", encoding="utf-8")
            sys.exit(0)
    elif "pg_dump" in joined:
        log("docker:run:pg_dump")
        if {fail_backup}:
            sys.stderr.write("pg_dump failed\\n")
            sys.exit(1)
        sys.stdout.buffer.write(b"PGDUMP_CUSTOM_FORMAT_SYNTHETIC_DATA")
        sys.exit(0)
    elif "pg_restore" in joined:
        if "--list" in joined:
            sys.exit(0)
        elif "--clean" in joined:
            if "--file=-" not in args:
                sys.stderr.write("pg_restore: error: output destination required\\n")
                sys.exit(1)
            log("docker:run:pg_restore_generate")
            print("-- pg_restore generated SQL")
            print("CREATE TABLE items (id integer, name text);")
            print("INSERT INTO items VALUES (1, 'old_record');")
            sys.exit(0)
    sys.exit(0)

sys.exit(0)
""",  # noqa: S608 - fixed synthetic SQL inside adapter source
            encoding="utf-8",
        )

        docker_sh = self.bin_dir / "docker"
        docker_sh.write_text(
            f'#!/bin/sh\nexec "{python_exe}" "{docker_adapter_py.as_posix()}" "$@"\n',
            encoding="utf-8",
        )
        docker_sh.chmod(0o700)

        php_adapter_py = self.work_path / "php_adapter.py"
        php_adapter_py.write_text(
            f"""# Python synthetic php adapter
import sys
import sqlite3
from pathlib import Path

args = sys.argv[1:]
events_file = Path("{events_path}")
state_dir = Path("{state_dir_path}")
template_file = Path("{template_path}")
sqlite_file = Path("{sqlite_path}")
pg_data_file = Path("{pg_data_path}")

def log(evt):
    with open(events_file, "a", encoding="utf-8") as f:
        f.write(evt + "\\n")

if "rebuild_container" in " ".join(args):
    log("php:rebuild:Floppy")
    if {rebuild_stops_app}:
        (state_dir / "container_stopped").touch()
    else:
        (state_dir / "container_stopped").unlink(missing_ok=True)
    if "sha-previous" in template_file.read_text(encoding="utf-8"):
        (state_dir / "rolled_back").touch()
        (state_dir / "container_unhealthy").unlink(missing_ok=True)
        sys.exit(0)
    (state_dir / "activated").touch()
    if {fail_activation}:
        if {is_postgres}:
            pg_data_file.write_text("MIGRATED_SCHEMA_V2\\ntable_items:record1\\ntable_new_v2_feature:data\\n", encoding="utf-8")
        else:
            conn = sqlite3.connect(sqlite_file)
            conn.execute("CREATE TABLE new_v2_feature (id int);")
            conn.execute("INSERT INTO new_v2_feature VALUES (999);")
            conn.commit()
            conn.close()
        (state_dir / "container_unhealthy").touch()
        (state_dir / "in_rollback").touch()
        sys.exit(1)
    elif {mismatch_sha}:
        (state_dir / "in_rollback").touch()
        sys.exit(0)
sys.exit(0)
""",  # noqa: S608 - fixed synthetic SQL inside adapter source
            encoding="utf-8",
        )

        php_sh = self.bin_dir / "php"
        php_sh.write_text(
            f'#!/bin/sh\nexec "{python_exe}" "{php_adapter_py.as_posix()}" "$@"\n',
            encoding="utf-8",
        )
        php_sh.chmod(0o700)

        sqlite_adapter_py = self.work_path / "sqlite_adapter.py"
        sqlite_adapter_py.write_text(
            f"""# SQLite adapter
import sys
import sqlite3
from pathlib import Path

args = sys.argv[1:]
events_file = Path("{events_path}")

def log(evt):
    with open(events_file, "a", encoding="utf-8") as f:
        f.write(evt + "\\n")

if not args:
    sys.exit(0)

db_path = args[0]
cmd = args[1] if len(args) > 1 else ""

if cmd.startswith(".backup"):
    log(f"sqlite:backup:{{db_path}}")
    if {fail_backup}:
        sys.exit(1)
    target = cmd.split("'")[1]
    src_conn = sqlite3.connect(db_path)
    dst_conn = sqlite3.connect(target)
    src_conn.backup(dst_conn)
    dst_conn.close()
    src_conn.close()
    if {fail_after_stop}:
        sys.exit(13)
    sys.exit(0)

elif cmd.startswith(".restore"):
    log(f"sqlite:restore:{{db_path}}")
    if {fail_restore}:
        sys.exit(1)
    backup_file = cmd.split("'")[1]
    src_conn = sqlite3.connect(backup_file)
    dst_conn = sqlite3.connect(db_path)
    src_conn.backup(dst_conn)
    dst_conn.close()
    src_conn.close()
    sys.exit(0)

elif "PRAGMA quick_check" in cmd:
    print("ok")
    sys.exit(0)

sys.exit(0)
""",
            encoding="utf-8",
        )

        sqlite_sh = self.bin_dir / "sqlite3"
        sqlite_sh.write_text(
            f'#!/bin/sh\nexec "{python_exe}" "{sqlite_adapter_py.as_posix()}" "$@"\n',
            encoding="utf-8",
        )
        sqlite_sh.chmod(0o700)
        for adapter in (docker_adapter_py, php_adapter_py, sqlite_adapter_py):
            compile(adapter.read_text(encoding="utf-8"), str(adapter), "exec")

    def run_deploy(self, env_overrides=None, fault=None):
        """Run the real script against private paths with optional interruption."""
        deploy_script = ROOT / "scripts/dev-publish/deploy-unraid.sh"
        env = os.environ.copy()
        env["PATH"] = f"{self.bin_dir.as_posix()}:{env.get('PATH', '')}"
        if env_overrides:
            env.update(env_overrides)
        source = deploy_script.read_text(encoding="utf-8")
        for old, new in (
            (
                "/boot/config/plugins/dockerMan/templates-user/my-Floppy.xml",
                self.template_file.as_posix(),
            ),
            ("/mnt/user/appdata/floppy/backups", self.backup_dir.as_posix()),
            ("/mnt/user/appdata/floppy/db/db.sqlite3", self.sqlite_file.as_posix()),
        ):
            source = source.replace(old, new)
        if fault == "term_before_activation":
            source = source.replace(
                'set_repository "$image"\ndeploy_phase=',
                'set_repository "$image"\nkill -TERM $$\ndeploy_phase=',
                1,
            )
        elif fault in ("term_after_activation", "error_after_activation"):
            trigger = "kill -TERM $$" if fault == "term_after_activation" else "false"
            source = source.replace(
                '\ndeploy_phase="DONE"\n', "\n" + trigger + '\ndeploy_phase="DONE"\n', 1
            )
        patched = self.work_path / "deploy_patched.sh"
        patched.write_text(source, encoding="utf-8", newline="\n")
        return subprocess.run(  # noqa: S603 - task-owned script and fixtures
            [
                BASH,
                patched.as_posix(),
                "deploy",
                "ghcr.io/preciselywrong/floppy:sha-new456",
                "new-commit-sha-456",
            ],
            env=env,
            capture_output=True,
            text=True,
            timeout=45,
            check=False,
        )

    def test_sqlite_rollback_removes_migrated_table_and_preserves_old_records(
        self,
    ) -> None:
        """Confirms that when release fails after migration, rollback cleans migrated tables and restores old record."""
        self.create_mock_commands(is_postgres=False, fail_activation=True)
        res = self.run_deploy()

        self.assertNotEqual(
            res.returncode,
            0,
            f"Expected non-zero return code. Output: {res.stdout} {res.stderr}",
        )

        conn = sqlite3.connect(self.sqlite_file)
        tables = [
            r[0]
            for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        ]
        rows = conn.execute("SELECT * FROM items").fetchall()
        conn.close()

        self.assertNotIn(
            "new_v2_feature",
            tables,
            f"Migrated table new_v2_feature was left in database after failed release! Tables: {tables}",
        )
        self.assertEqual(
            rows, [(1, "initial_record")], f"Old records were not restored: {rows}"
        )

        events = self.get_events()
        self.assertIn("docker:stop:Floppy", events)
        self.assertIn("sqlite:restore:" + self.sqlite_file.as_posix(), events)
        stop_idx = events.index("docker:stop:Floppy")
        restore_idx = events.index("sqlite:restore:" + self.sqlite_file.as_posix())
        rebuild_indices = [i for i, e in enumerate(events) if e == "php:rebuild:Floppy"]
        self.assertGreaterEqual(
            len(rebuild_indices),
            2,
            f"Expected at least 2 rebuilds (failed deploy + rollback): {events}",
        )
        rollback_rebuild_idx = rebuild_indices[1]

        self.assertLess(stop_idx, restore_idx, "App must be stopped before DB restore")
        self.assertLess(
            restore_idx,
            rollback_rebuild_idx,
            "DB must be restored before old app is started",
        )

    def test_postgres_rollback_removes_migrated_schema_and_restores_public(
        self,
    ) -> None:
        """Confirms that Postgres rollback regenerates schema and executes in single transaction."""
        self.pg_data_file.write_text(
            "INITIAL_SCHEMA_PUBLIC\ntable_items:record1\n", encoding="utf-8"
        )
        self.create_mock_commands(is_postgres=True, fail_activation=True)

        res = self.run_deploy()
        self.assertNotEqual(res.returncode, 0)

        final_pg_data = self.pg_data_file.read_text(encoding="utf-8")
        self.assertNotIn("MIGRATED_SCHEMA_V2", final_pg_data)
        self.assertIn("RESTORED_SCHEMA_PUBLIC", final_pg_data)

        events = self.get_events()
        self.assertIn("docker:run:psql_restore", events)

    def test_failed_db_restore_does_not_start_mismatched_old_app_or_succeed(
        self,
    ) -> None:
        """If database restore fails, script must fail closed and NOT rebuild or start old container."""
        self.create_mock_commands(
            is_postgres=True, fail_activation=True, fail_restore=True
        )
        res = self.run_deploy()

        self.assertNotEqual(res.returncode, 0)
        self.assertNotIn("UNRAID_READY", res.stdout)
        self.assertNotIn("PUBLISH_OK", res.stdout)

        events = self.get_events()
        rebuild_indices = [i for i, e in enumerate(events) if e == "php:rebuild:Floppy"]
        self.assertEqual(
            len(rebuild_indices),
            1,
            f"Old app should NOT be rebuilt if restore failed: {events}",
        )

    def test_backup_failure_restarts_old_app(self) -> None:
        """If backup fails while app is stopped, app must be restarted before failing."""
        self.create_mock_commands(is_postgres=False, fail_backup=True)
        res = self.run_deploy()

        self.assertNotEqual(res.returncode, 0)
        events = self.get_events()
        self.assertIn("docker:stop:Floppy", events)
        self.assertIn("docker:start:Floppy", events)
        stop_idx = events.index("docker:stop:Floppy")
        start_idx = events.index("docker:start:Floppy")
        self.assertLess(stop_idx, start_idx)

    def test_sha_mismatch_triggers_rollback(self) -> None:
        """If container starts but COMMIT_SHA does not match, rollback is triggered."""
        self.create_mock_commands(is_postgres=False, mismatch_sha=True)
        res = self.run_deploy()

        self.assertNotEqual(res.returncode, 0)
        events = self.get_events()
        self.assertIn("sqlite:restore:" + self.sqlite_file.as_posix(), events)

    def test_diagnostics_contain_no_fixture_credential_value(self) -> None:
        """Diagnostics and outputs must never leak passwords or credentials."""
        secret = "synthetic-forbidden-output"  # noqa: S105 - diagnostic fixture
        self.create_mock_commands(
            is_postgres=True,
            fail_activation=True,
            fail_restore=True,
            secret_password=secret,
        )
        res = self.run_deploy()

        combined_output = res.stdout + "\n" + res.stderr
        self.assertNotIn(
            secret, combined_output, "Credential leaked in script stdout/stderr!"
        )

    def test_stop_failure_before_rollback_fails_closed_without_db_restore(self) -> None:
        """Rollback must fail closed without restoring DB if failed container cannot be stopped."""
        self.create_mock_commands(
            is_postgres=True, fail_activation=True, fail_stop_app=True
        )
        res = self.run_deploy()

        self.assertNotEqual(res.returncode, 0)
        self.assertNotIn("UNRAID_READY", res.stdout)
        events = self.get_events()
        # Verify docker:run:psql_restore NEVER occurred because stop failed
        self.assertNotIn(
            "docker:run:psql_restore",
            events,
            "Database restore MUST NOT run if stop failed!",
        )

    def test_stop_daemon_failure_fails_closed_without_db_restore(self) -> None:
        """Rollback must fail closed without restoring DB if docker daemon query fails."""
        self.create_mock_commands(
            is_postgres=True, fail_activation=True, fail_daemon_inspect=True
        )
        res = self.run_deploy()

        self.assertNotEqual(res.returncode, 0)
        events = self.get_events()
        self.assertNotIn(
            "docker:run:psql_restore",
            events,
            "Database restore MUST NOT run if daemon query fails!",
        )

    def test_unexpected_failure_in_pre_activation_recovers_template_and_container(
        self,
    ) -> None:
        """An unexpected error after stop/template modification before activation must recover template and app."""
        self.create_mock_commands(is_postgres=False, fail_after_stop=True)
        res = self.run_deploy()

        self.assertNotEqual(res.returncode, 0)
        self.assertNotIn("UNRAID_READY", res.stdout)
        events = self.get_events()
        # Original app must be started/rebuilt, template restored
        self.assertIn("docker:start:Floppy", events)
        # DB restore must NOT be executed because phase was PRE_ACTIVATION
        self.assertNotIn("sqlite:restore:" + self.sqlite_file.as_posix(), events)
        # Template must have been restored
        self.assertIn("sha-previous", self.template_file.read_text(encoding="utf-8"))

    def test_rollback_verifies_migrations_clean_and_identity(self) -> None:
        """Rollback must execute migrate --check and verify COMMIT_SHA before completing."""
        self.create_mock_commands(is_postgres=False, fail_activation=True)
        res = self.run_deploy()

        self.assertEqual(
            res.returncode, 4, f"Expected rollback exit code 4, got {res.returncode}"
        )
        events = self.get_events()
        self.assertIn(
            "docker:exec:migrate_check",
            events,
            "Rollback must run manage.py migrate --check!",
        )

    def test_precise_image_pruning_keeps_active_and_prior_ids_and_does_not_touch_others(
        self,
    ) -> None:
        """Pruning must remove superseded floppy tags/images for the repository while preserving active, prior, and other repos."""
        self.create_mock_commands(
            is_postgres=False,
            extra_images=[
                "floppy\tpre-custom-20260101-100000\tsha256:old_img_1",
                "floppy\tpre-custom-20261001-120000\tsha256:old_img_2",
                "ghcr.io/preciselywrong/floppy\tsha-old111\tsha256:old_img_3",
                "ghcr.io/preciselywrong/floppy\tsha-previous\tsha256:previous_image_id_12345",
                "ghcr.io/preciselywrong/floppy\tsha-new456\tsha256:new_image_id_67890",
                "ghcr.io/preciselywrong/floppy\tcustom\tsha256:new_image_id_67890",
                "ghcr.io/dannyvfilms/floppy\tlatest\tsha256:upstream_img_id",
                "redis\t7\tsha256:redis_img_id",
            ],
        )
        res = self.run_deploy()
        self.assertEqual(res.returncode, 0, f"Deploy failed: {res.stdout} {res.stderr}")
        events = self.get_events()

        # Older superseded tag must be pruned
        self.assertIn("docker:rmi:ghcr.io/preciselywrong/floppy:sha-old111", events)
        # Active and prior must NOT be removed
        self.assertNotIn(
            "docker:rmi:ghcr.io/preciselywrong/floppy:sha-previous", events
        )
        self.assertNotIn("docker:rmi:ghcr.io/preciselywrong/floppy:sha-new456", events)
        self.assertNotIn("docker:rmi:ghcr.io/preciselywrong/floppy:custom", events)
        self.assertNotIn("docker:rmi:sha256:previous_image_id_12345", events)
        self.assertNotIn("docker:rmi:sha256:new_image_id_67890", events)
        # Other repositories must NEVER be touched
        self.assertNotIn("docker:rmi:ghcr.io/dannyvfilms/floppy:latest", events)
        self.assertNotIn("docker:rmi:redis:7", events)
        self.assertNotIn("docker:rmi:sha256:upstream_img_id", events)
        self.assertNotIn("docker:rmi:sha256:redis_img_id", events)

    def test_stale_custom_alias_cannot_retain_a_third_image(self):
        """Remove a mutable alias when it points to a superseded image."""
        self.create_mock_commands(
            extra_images=[
                "ghcr.io/preciselywrong/floppy\tcustom\tsha256:obsolete_image_id",
                "ghcr.io/preciselywrong/floppy\tsha-previous\tsha256:previous_image_id_12345",
                "ghcr.io/preciselywrong/floppy\tsha-new456\tsha256:new_image_id_67890",
            ]
        )
        result = self.run_deploy()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(
            "docker:rmi:ghcr.io/preciselywrong/floppy:custom", self.get_events()
        )
        self.assertNotIn(
            "docker:rmi:ghcr.io/preciselywrong/floppy:sha-previous", self.get_events()
        )

    def test_successful_deploy_prunes_redundant_tags_and_keeps_newest_backup(
        self,
    ) -> None:
        """Successful deploy keeps active image and newest backup image, pruning older pre-custom tags."""
        self.create_mock_commands(is_postgres=False)
        res = self.run_deploy()

        self.assertEqual(res.returncode, 0, f"Deploy failed: {res.stdout} {res.stderr}")
        self.assertIn("UNRAID_READY", res.stdout)
        events = self.get_events()
        self.assertIn("docker:rmi:floppy:pre-custom-20260101-100000", events)
        self.assertIn("docker:rmi:floppy:pre-custom-20261001-120000", events)

    def test_deploy_starts_rebuilt_container_when_autostart_is_disabled(self):
        """Restore the running state even when Unraid rebuild leaves it stopped."""
        self.create_mock_commands(rebuild_stops_app=True)
        result = self.run_deploy()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse((self.state_dir / "container_stopped").exists())
        events = self.get_events()
        self.assertLess(
            events.index("php:rebuild:Floppy"), events.index("docker:start:Floppy")
        )

    def test_rollback_starts_rebuilt_container_after_restoring_database(self):
        """A disabled autostart cannot prevent recovery of the prior release."""
        self.create_mock_commands(
            is_postgres=True, fail_activation=True, rebuild_stops_app=True
        )
        result = self.run_deploy()
        self.assertEqual(result.returncode, 4, result.stderr)
        self.assertFalse((self.state_dir / "container_stopped").exists())
        events = self.get_events()
        self.assertLess(
            events.index("docker:run:psql_restore"), events.index("docker:start:Floppy")
        )
        self.assertLess(
            events.index("docker:start:Floppy"),
            events.index("docker:exec:migrate_check"),
        )

    def test_failed_new_container_start_recovers_the_previous_release(self):
        """A start failure still restores the database and starts the old image."""
        self.create_mock_commands(
            is_postgres=True, rebuild_stops_app=True, fail_start_app=True
        )
        result = self.run_deploy()
        self.assertEqual(result.returncode, 4, result.stderr)
        self.assertFalse((self.state_dir / "container_stopped").exists())
        self.assertEqual(self.get_events().count("docker:start:Floppy"), 2)
        self.assertNotIn("UNRAID_READY", result.stdout)

    def test_term_before_activation_recovers_original_release(self):
        """Recover the original release when activation has not started."""
        self.create_mock_commands()
        result = self.run_deploy(fault="term_before_activation")
        self.assertEqual(result.returncode, 143)
        self.assertIn("docker:start:Floppy", self.get_events())
        self.assertIn("sha-previous", self.template_file.read_text())
        self.assertNotIn("UNRAID_READY", result.stdout)

    def test_unexpected_error_after_activation_keeps_credentials_for_restore(self):
        """Retain connection configuration until the database is restored."""
        self.create_mock_commands(is_postgres=True)
        result = self.run_deploy(fault="error_after_activation")
        self.assertEqual(result.returncode, 4, result.stderr)
        self.assertIn("docker:run:psql_restore", self.get_events())
        self.assertIn("RESTORED_SCHEMA_PUBLIC", self.pg_data_file.read_text())
        self.assertNotIn("UNRAID_READY", result.stdout)

    def test_term_after_activation_restores_database_and_prior_release(self):
        """Recover both database and application after an activation signal."""
        self.create_mock_commands(is_postgres=True)
        result = self.run_deploy(fault="term_after_activation")
        self.assertEqual(result.returncode, 4, result.stderr)
        self.assertIn("docker:run:psql_restore", self.get_events())
        self.assertNotIn("UNRAID_READY", result.stdout)

    def test_paused_application_cannot_allow_database_restore(self):
        """Reject database restoration while the application is paused."""
        self.create_mock_commands(
            is_postgres=True,
            fail_activation=True,
            fail_stop_app=True,
            failed_stop_state="paused",
        )
        result = self.run_deploy()
        self.assertEqual(result.returncode, 5, result.stderr)
        self.assertNotIn("docker:run:psql_restore", self.get_events())


if __name__ == "__main__":
    unittest.main()
