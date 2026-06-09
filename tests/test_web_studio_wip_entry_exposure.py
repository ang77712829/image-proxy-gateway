"""Web Studio WIP entry exposure source contracts."""
from __future__ import annotations

import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LAYOUT_JS = ROOT / "app" / "www" / "assets" / "studio" / "layout.js"
APP_JS = ROOT / "app" / "www" / "assets" / "studio" / "app.js"
GENERATE_VIDEO_JS = ROOT / "app" / "www" / "assets" / "studio" / "pages" / "generate-video.js"
DIAGNOSTICS_JS = ROOT / "app" / "www" / "assets" / "studio" / "pages" / "diagnostics.js"

WIP_MARKERS = (
    "wip",
    "skeleton",
    "will appear here",
    "coming soon",
    "placeholder",
)


def read_source(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def nav_routes(layout_source: str) -> set[str]:
    return set(re.findall(r"hash:\s*['\"]([^'\"]+)['\"]", layout_source))


def route_is_registered(app_source: str, route: str) -> bool:
    return bool(re.search(rf"router\.register\(\s*['\"]{re.escape(route)}['\"]", app_source))


def is_wip_skeleton(source: str) -> bool:
    lowered = source.lower()
    return any(marker in lowered for marker in WIP_MARKERS)


class WebStudioWipEntryExposureSourceContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.layout_source = read_source(LAYOUT_JS)
        cls.app_source = read_source(APP_JS)
        cls.generate_video_source = read_source(GENERATE_VIDEO_JS)
        cls.diagnostics_source = read_source(DIAGNOSTICS_JS)
        cls.nav = nav_routes(cls.layout_source)

    def assert_wip_page_not_in_formal_nav(self, route: str, page_source: str) -> None:
        is_wip = is_wip_skeleton(page_source)
        exposed = route in self.nav
        self.assertFalse(
            is_wip and exposed,
            f"{route} is still a WIP skeleton and should not be exposed in formal Web Studio navigation.",
        )

    def test_generate_video_wip_skeleton_is_not_exposed_in_formal_nav(self) -> None:
        """Generate Video may remain a route, but WIP skeletons must not appear in formal navigation."""
        self.assert_wip_page_not_in_formal_nav("#/generate/video", self.generate_video_source)

    def test_diagnostics_wip_skeleton_is_not_exposed_in_formal_nav(self) -> None:
        """Diagnostics may remain a route, but WIP skeletons must not appear in formal navigation."""
        self.assert_wip_page_not_in_formal_nav("#/diagnostics", self.diagnostics_source)

    def test_wip_routes_may_remain_registered_for_direct_access(self) -> None:
        """The RC contract does not require deleting WIP routes or files."""
        self.assertTrue(route_is_registered(self.app_source, "#/generate/video"))
        self.assertTrue(route_is_registered(self.app_source, "#/diagnostics"))

    def test_completed_formal_entries_remain_in_navigation(self) -> None:
        """WIP entry cleanup must not remove completed Product RC navigation entries."""
        required_routes = {
            "#/dashboard",
            "#/generate/image",
            "#/jobs",
            "#/assets",
            "#/providers",
            "#/gateway-keys",
        }
        self.assertTrue(required_routes.issubset(self.nav), f"Missing required routes: {sorted(required_routes - self.nav)}")


if __name__ == "__main__":
    unittest.main()
