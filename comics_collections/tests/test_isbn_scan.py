"""US-070 : widget back-office `isbn_scan` (scan d'ISBN à la caméra sur mobile).

Le comportement caméra lui-même est côté navigateur (non testable ici) : on
vérifie que les vues l'utilisent et que le code est bien livré dans le bundle.
"""

from odoo.tests import TransactionCase, tagged

ISBN_SCAN_ASSETS = (
    "comics_collections/static/src/isbn_scan/isbn_scan_dialog.js",
    "comics_collections/static/src/isbn_scan/isbn_scan_dialog.xml",
    "comics_collections/static/src/isbn_scan/isbn_scan_field.js",
    "comics_collections/static/src/isbn_scan/isbn_scan_field.xml",
)


@tagged("post_install", "-at_install", "comics_collections", "isbn_scan")
class TestIsbnScanWidget(TransactionCase):

    def test_backend_bundle_contains_widget(self):
        paths = [p[0] for p in self.env["ir.asset"]._get_asset_paths("web.assets_backend", {})]
        for asset in ISBN_SCAN_ASSETS:
            self.assertIn("/" + asset, paths)

    def test_backend_bundle_compiles_widget(self):
        bundle = self.env["ir.qweb"]._get_asset_bundle("web.assets_backend", css=False, js=True, debug_assets=True)
        content = bundle.js().raw.decode()
        self.assertIn("@comics_collections/isbn_scan/isbn_scan_field", content)
        self.assertIn("comics_collections.IsbnScanField", content)
        self.assertIn("comics_collections.IsbnScanDialog", content)

    def test_forms_use_isbn_scan_widget(self):
        for model, xmlid in (
            ("comic.work", "comics_collections.view_comic_work_form"),
            ("comic.edition", "comics_collections.view_comic_edition_form"),
        ):
            arch = self.env[model].get_view(self.env.ref(xmlid).id, "form")["arch"]
            self.assertIn('widget="isbn_scan"', arch, xmlid)
