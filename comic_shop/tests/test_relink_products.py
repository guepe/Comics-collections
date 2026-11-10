"""Reconnexion produit ↔ édition après réinstallation de comic_shop."""

from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install", "comic_shop")
class TestRelinkProducts(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        Work, Product = cls.env["comic.work"], cls.env["product.template"]
        serie = cls.env["comic.serie"].create({"name": "Série Relink"})
        cls.w1, cls.w2, cls.w3, cls.w4 = Work.create(
            [{"serie_id": serie.id, "titre_canonique": f"Relink {i}", "tome": i} for i in (1, 2, 3, 4)]
        )
        cls.e1, cls.e2, cls.e3, cls.e4 = (w.primary_edition_id for w in (cls.w1, cls.w2, cls.w3, cls.w4))
        cls.env["comic.isbn"].create({"edition_id": cls.e1.id, "isbn_13": "9782800152851"})
        cls.env["comic.isbn"].create({"edition_id": cls.e2.id, "isbn_13": "9782803612208"})
        # Produits sans lien (état après désinstallation / réinstallation)
        cls.p_isbn13 = Product.create({"name": "Nom quelconque A", "barcode": "9782800152851"})
        cls.p_isbn10 = Product.create({"name": "Nom quelconque B", "barcode": "2803612208"})
        cls.p_name = Product.create({"name": cls.e3._get_product_name()})
        cls.p_unknown = Product.create({"name": "Produit sans rapport", "barcode": "1234567890128"})
        # Lien existant : jamais modifié
        cls.p_linked = Product.create({"name": "Déjà relié", "comic_edition_id": cls.e4.id})
        cls.e4.product_tmpl_id = cls.p_linked
        # Lien coupé par l'uninstall_hook simulé
        for product in (cls.p_isbn13, cls.p_isbn10, cls.p_name):
            product.comic_edition_id = False
        (cls.e1 | cls.e2 | cls.e3).product_tmpl_id = False

    def test_relink_by_isbn13_isbn10_and_name(self):
        count = self.env["product.template"]._comic_relink_editions()
        self.assertEqual(count, 3)
        self.assertEqual(self.p_isbn13.comic_edition_id, self.e1)
        self.assertEqual(self.e1.product_tmpl_id, self.p_isbn13)
        self.assertEqual(self.p_isbn10.comic_edition_id, self.e2)
        self.assertEqual(self.p_name.comic_edition_id, self.e3)
        self.assertFalse(self.p_unknown.comic_edition_id)
        self.assertEqual(self.e4.product_tmpl_id, self.p_linked)
        # Idempotent
        self.assertEqual(self.env["product.template"]._comic_relink_editions(), 0)

    def test_never_two_products_for_one_edition(self):
        # Ce produit vise e1 par le nom, mais e1 revient déjà au produit qui porte son ISBN
        twin = self.env["product.template"].create({"name": self.e1._get_product_name()})
        self.env["product.template"]._comic_relink_editions()
        self.assertEqual(self.env["product.template"].search([("comic_edition_id", "=", self.e1.id)]), self.p_isbn13)
        self.assertFalse(twin.comic_edition_id)

    def test_ambiguous_name_is_skipped(self):
        # Deux éditions du même album → même nom généré : pas de lien par le nom
        self.env["comic.edition"].create({"work_id": self.w3.id})
        self.assertEqual(self.env["product.template"]._comic_relink_editions(), 2)
        self.assertFalse(self.p_name.comic_edition_id)

    def test_action_notification(self):
        action = self.env["product.template"].action_comic_relink_editions()
        self.assertEqual(action["params"]["type"], "success")
