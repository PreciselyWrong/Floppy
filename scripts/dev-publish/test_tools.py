import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


class ProjectToolContractTests(unittest.TestCase):
    def read(self, relative_path: str) -> str:
        path = ROOT / relative_path
        self.assertTrue(path.is_file(), f"Missing {relative_path}")
        return path.read_text(encoding="utf-8")

    def test_dev_script_contract(self) -> None:
        script = self.read("dev.ps1")
        for token in (
            "[CmdletBinding()]",
            "$Dummy",
            "$NonInteractive",
            "$Plan",
            "Set-StrictMode -Version Latest",
            "$PSScriptRoot",
            "DEV_READY",
        ):
            self.assertIn(token, script)
        self.assertIn("docker compose", script)

    def test_publish_script_contract(self) -> None:
        script = self.read("publish.ps1")
        for token in (
            "[CmdletBinding()]",
            "$NonInteractive",
            "$Plan",
            "$Confirm",
            "$Destination",
            "Set-StrictMode -Version Latest",
            "$PSScriptRoot",
            "PUBLISH_OK",
            "PUBLISH_FAILED",
        ):
            self.assertIn(token, script)
        self.assertIn("git push --set-upstream origin custom", script)
        self.assertIn("api.github.com/repos/PreciselyWrong/Floppy/actions/runs", script)
        self.assertIn("git credential fill", script)
        self.assertIn('Authorization = "Bearer $GitHubToken"', script)
        self.assertIn("ssh unraid-server", script)
        self.assertIn("tr -d '\\r'", script)
        self.assertIn("pre-custom", script)
        self.assertIn("ghcr.io/dannyvfilms/floppy:latest", script)
        self.assertIn("sha-$CommitSha", script)

    def test_custom_workflow_is_fork_safe_and_immutable(self) -> None:
        workflow = self.read(".github/workflows/custom-image.yml")
        self.assertIn('- "custom"', workflow)
        self.assertIn("PreciselyWrong/floppy", workflow)
        self.assertIn("type=raw,value=custom", workflow)
        self.assertIn("type=sha,format=long,prefix=sha-", workflow)
        self.assertIn("needs: smoke", workflow)
        self.assertIn("packages: write", workflow)
        self.assertIn("secrets.GITHUB_TOKEN", workflow)
        self.assertIn("python scripts/dev-publish/test_tools.py", workflow)
        self.assertNotIn("run: scripts/test.sh", workflow)
        self.assertNotIn("dannyvfilms/yamtrack", workflow)

    def test_custom_deployment_document_has_safe_rollback(self) -> None:
        document = self.read("docs/custom-deployment.md")
        self.assertIn("ghcr.io/preciselywrong/floppy:custom", document.lower())
        self.assertIn("sha-", document)
        self.assertIn("ghcr.io/dannyvfilms/floppy:latest", document)
        self.assertIn("/mnt/user/appdata/floppy/db", document)
        self.assertNotIn("SECRET=", document)

    def test_deploy_unraid_script_contract(self) -> None:
        script = self.read("scripts/dev-publish/deploy-unraid.sh")
        for token in (
            "umask 077",
            "DROP SCHEMA public CASCADE",
            "CREATE SCHEMA public",
            "--single-transaction",
            "--set=ON_ERROR_STOP=1",
            "--clean --if-exists --no-owner --no-privileges",
            'docker stop "$container"',
            "prune_redundant_images",
            "UNRAID_READY",
        ):
            self.assertIn(token, script)
        self.assertNotIn("DROP DATABASE", script)
        self.assertNotIn("createdb", script)
        self.assertNotIn("dropdb", script)


# Expose runtime simulation tests to unittest test discovery

DEV_PUBLISH_DIR = Path(__file__).resolve().parent
if str(DEV_PUBLISH_DIR) not in sys.path:
    sys.path.insert(0, str(DEV_PUBLISH_DIR))

from test_deploy_unraid_runtime import DeployUnraidRuntimeTests  # noqa: F401, E402

if __name__ == "__main__":
    unittest.main()
