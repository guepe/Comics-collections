"""US-070 : bouton « Scanner » sur /my/library/add (scan d'ISBN à la caméra).

La lecture caméra (getUserMedia, HTTPS requis) n'est pas testable sans
navigateur : on vérifie le rendu (bouton masqué par défaut, message de repli,
saisie manuelle intacte) et la présence du JS dans le bundle frontend.
"""

from odoo import http
from odoo.tests import HttpCase, new_test_user, tagged


@tagged("post_install", "-at_install", "comic_shop", "isbn_scan")
class TestPortalIsbnScan(HttpCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.login = "comic_portal_isbn_scan"
        new_test_user(cls.env, login=cls.login, groups="base.group_portal")
        # Album local : la recherche par titre aboutit sans appel aux sources externes
        serie = cls.env["comic.serie"].create({"name": "Série Scan US070"})
        cls.env["comic.work"].create({"serie_id": serie.id, "titre_canonique": "Album Scan US070", "tome": 1})

    def test_add_page_renders_scan_button(self):
        self.authenticate(self.login, self.login)
        resp = self.url_open("/my/library/add")
        self.assertEqual(resp.status_code, 200)
        html = resp.text
        self.assertIn("o_comic_isbn_scan", html)
        # Bouton masqué tant que le JS n'a pas détecté la caméra
        self.assertRegex(html, r'class="[^"]*o_comic_isbn_scan_btn[^"]*d-none')
        self.assertIn("o_comic_isbn_scan_unavailable", html)
        # Repli : la saisie manuelle reste disponible
        self.assertIn('name="isbn"', html)
        self.assertIn('name="title"', html)

    def test_results_page_keeps_scan_button(self):
        self.authenticate(self.login, self.login)
        resp = self.url_open(
            "/my/library/add/search",
            data={"isbn": "", "title": "Album Scan US070", "csrf_token": http.Request.csrf_token(self)},
        )
        self.assertEqual(resp.status_code, 200)
        self.assertIn("Album Scan US070", resp.text)
        self.assertIn("o_comic_isbn_scan_btn", resp.text)

    def test_frontend_bundle_contains_scan_js(self):
        paths = [p[0] for p in self.env["ir.asset"]._get_asset_paths("web.assets_frontend", {})]
        self.assertIn("/comic_shop/static/src/js/portal_isbn_scan.js", paths)
        self.assertIn("/comics_collections/static/src/isbn_scan/isbn_scan_dialog.js", paths)
        self.assertIn("/comics_collections/static/src/isbn_scan/isbn_scan_dialog.xml", paths)
        # Le scanner vidéo d'Odoo (BarcodeDetector / ZXing) est disponible côté frontend
        self.assertIn("/web/static/src/core/barcode/barcode_video_scanner.js", paths)

    def test_frontend_bundle_compiles_scan_modules(self):
        bundle = self.env["ir.qweb"]._get_asset_bundle("web.assets_frontend", css=False, js=True, debug_assets=True)
        content = bundle.js().raw.decode()
        self.assertIn("@comic_shop/js/portal_isbn_scan", content)
        self.assertIn("@comics_collections/isbn_scan/isbn_scan_dialog", content)
        self.assertIn("comics_collections.IsbnScanDialog", content)

    def test_datasource_wizard_uses_isbn_scan_widget(self):
        view = self.env.ref("comic_datasource.view_comic_datasource_search_wizard_form")
        arch = self.env["comic.datasource.search.wizard"].get_view(view.id, "form")["arch"]
        self.assertIn('widget="isbn_scan"', arch)
