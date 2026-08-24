from pathlib import Path
import unittest


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


if __name__ == "__main__":
    unittest.main()
