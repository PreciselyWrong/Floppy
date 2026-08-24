from pathlib import Path

from django.conf import settings
from django.test import SimpleTestCase


class HorizontalScrollContractTests(SimpleTestCase):
    def setUp(self):
        self.root = Path(settings.BASE_DIR)

    def read(self, relative_path):
        return self.root.joinpath(relative_path).read_text()

    def test_shared_card_rows_are_directly_scrollable(self):
        shared_row = self.read("templates/app/components/_scrollable_row.html")
        preview = self.read("templates/app/components/discover_row_preview.html")
        highlights = self.read("templates/app/components/statistics/highlight_set.html")

        for template in (shared_row, preview, highlights):
            self.assertIn('data-horizontal-scroll="true"', template)
            self.assertIn('tabindex="0"', template)
            self.assertIn('role="region"', template)

    def test_global_controller_supports_drag_without_breaking_touch(self):
        base = self.read("templates/base.html")
        controller = self.read("static/js/horizontal-scroll.js")

        self.assertIn("js/horizontal-scroll.js", base)
        self.assertIn("pointerdown", controller)
        self.assertIn("pointermove", controller)
        self.assertIn("pointerup", controller)
        self.assertIn("pointercancel", controller)
        self.assertIn('event.pointerType === "touch"', controller)
        self.assertIn("event.preventDefault()", controller)
        self.assertIn("suppressClick", controller)
        self.assertIn("ArrowLeft", controller)
        self.assertIn("ArrowRight", controller)

    def test_scroll_surface_has_momentum_snap_and_reduced_motion(self):
        css = self.read("static/css/input.css")

        self.assertIn('[data-horizontal-scroll="true"] {', css)
        self.assertIn("-webkit-overflow-scrolling: touch", css)
        self.assertIn("scroll-snap-type: x proximity", css)
        self.assertIn('[data-horizontal-scroll="true"] > * {', css)
        self.assertIn("scroll-snap-align: start", css)
        self.assertIn("prefers-reduced-motion: reduce", css)
