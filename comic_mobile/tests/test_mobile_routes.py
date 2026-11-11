"""Page de l'app mobile et manifeste web (US-093)."""

import json

from odoo.tests import HttpCase, new_test_user, tagged


@tagged("post_install", "-at_install", "comic_mobile")
class TestMobileRoutes(HttpCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        new_test_user(
            cls.env, login="mobile_page", password="mobile_page_pw", groups="comics_collections.group_comic_user"
        )
        new_test_user(cls.env, login="mobile_noaccess", password="mobile_noaccess_pw", groups="base.group_user")

    def test_app_page_for_comic_user(self):
        self.authenticate("mobile_page", "mobile_page_pw")
        res = self.url_open("/comics/app")
        self.assertEqual(res.status_code, 200)
        self.assertIn("/comic_mobile/manifest.webmanifest", res.text)
        self.assertIn("apple-touch-icon", res.text)
        self.assertIn("__session_info__", res.text)

    def test_app_page_redirects_other_users(self):
        self.authenticate("mobile_noaccess", "mobile_noaccess_pw")
        res = self.url_open("/comics/app", allow_redirects=False)
        self.assertIn(res.status_code, (302, 303))
        self.assertTrue(res.headers["Location"].endswith("/odoo"))

    def test_manifest_is_public(self):
        res = self.url_open("/comic_mobile/manifest.webmanifest")
        self.assertEqual(res.status_code, 200)
        manifest = json.loads(res.text)
        self.assertEqual(manifest["start_url"], "/comics/app")
        self.assertEqual(manifest["display"], "standalone")
        self.assertEqual(len(manifest["icons"]), 2)
