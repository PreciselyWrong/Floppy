import json
from pathlib import Path

from django.conf import settings
from django.test import SimpleTestCase


class PwaInstallUiTests(SimpleTestCase):
    def setUp(self):
        self.base_template = (
            Path(settings.BASE_DIR) / "templates" / "base.html"
        ).read_text(encoding="utf-8")
        self.public_template = (
            Path(settings.BASE_DIR) / "templates" / "base_public.html"
        ).read_text(encoding="utf-8")
        self.script_path = Path(settings.BASE_DIR) / "static" / "js" / "pwa-install.js"

    def test_base_exposes_install_ui_and_controller(self):
        self.assertIn('data-pwa-install="true"', self.base_template)
        self.assertIn("js/pwa-install.js", self.base_template)
        self.assertTrue(self.script_path.exists())

    def test_controller_supports_browser_prompt_ios_help_and_standalone(self):
        script = self.script_path.read_text(encoding="utf-8")

        self.assertIn("beforeinstallprompt", script)
        self.assertIn("appinstalled", script)
        self.assertIn('matchMedia("(display-mode: standalone)")', script)
        self.assertIn("navigator.standalone", script)
        self.assertIn('data-pwa-ios-help="true"', self.base_template)

    def test_templates_enable_ios_standalone_and_public_worker_registration(self):
        for template in (self.base_template, self.public_template):
            self.assertIn('name="apple-mobile-web-app-capable" content="yes"', template)
            self.assertIn('name="apple-mobile-web-app-title" content="Floppy"', template)
        self.assertIn('.register("/serviceworker.js")', self.public_template)

    def test_manifest_allows_landscape(self):
        manifest = json.loads(
            (Path(settings.BASE_DIR) / "static" / "favicon" / "site.webmanifest").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(manifest["orientation"], "any")
