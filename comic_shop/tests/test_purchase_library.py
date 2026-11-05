"""Tests lot 5 : achats ↔ bibliothèque client, synchro produit.

Lancement :
    docker exec odoo-web odoo -d odoo -u comic_shop --test-tags /comic_shop:TestPurchaseLibrary
"""

from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged("post_install", "-at_install", "comic_shop", "purchase_library")
class TestPurchaseLibrary(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.serie = cls.env["comic.serie"].create({"name": "Série Achat"})
        cls.work = cls.env["comic.work"].create({"serie_id": cls.serie.id, "titre_canonique": "Album Achat", "tome": 1})
        cls.edition = cls.work.edition_ids[:1] or cls.env["comic.edition"].create({"work_id": cls.work.id})
        cls.edition.action_create_product()
        cls.product = cls.edition.product_tmpl_id.product_variant_id
        cls.partner = cls.env["res.partner"].create({"name": "Client BD", "comic_auto_library": True})
        cls.Album = cls.env["comic.customer.album"]

    def _order(self):
        return self.env["sale.order"].create(
            {
                "partner_id": self.partner.id,
                "order_line": [(0, 0, {"product_id": self.product.id, "product_uom_qty": 1})],
            }
        )

    def _album(self):
        return self.Album.search([("partner_id", "=", self.partner.id), ("edition_id", "=", self.edition.id)])

    # ── Commandes en ligne ───────────────────────────────────────────────────

    def test_confirm_adds_album_and_leaves_wishlist(self):
        self.Album.create({"partner_id": self.partner.id, "edition_id": self.edition.id,
                           "dans_wishlist": True, "dans_collection": False})
        self._order().action_confirm()
        album = self._album()
        self.assertEqual(album.source, "achete_ici")
        self.assertTrue(album.dans_collection)
        self.assertFalse(album.dans_wishlist)
        self.assertFalse(album.auto_created, "L'entrée existait avant l'achat")

    def test_cancel_removes_untouched_auto_entry(self):
        order = self._order()
        order.action_confirm()
        self.assertTrue(self._album().auto_created)
        order._action_cancel()
        self.assertFalse(self._album())

    def test_cancel_keeps_entry_touched_by_customer(self):
        order = self._order()
        order.action_confirm()
        self._album().write({"note": 4.0})
        order._action_cancel()
        album = self._album()
        self.assertTrue(album)
        self.assertEqual(album.source, "inconnu")

    def test_upsert_is_idempotent(self):
        rec1, created1 = self.Album._upsert(self.partner, self.edition, {"source": "cadeau"})
        rec2, created2 = self.Album._upsert(self.partner, self.edition, {"source": "cadeau"})
        self.assertTrue(created1)
        self.assertFalse(created2)
        self.assertEqual(rec1, rec2)

    # ── Synchro produit ──────────────────────────────────────────────────────

    def test_sync_keeps_manual_barcode_without_isbn(self):
        tmpl = self.edition.product_tmpl_id
        tmpl.barcode = "MANUEL-001"
        self.edition._sync_to_product()
        self.assertEqual(tmpl.barcode, "MANUEL-001")

    def test_sync_does_not_force_pos_availability(self):
        tmpl = self.edition.product_tmpl_id
        tmpl.available_in_pos = False
        self.edition.write({"synopsis": "<p>Nouveau</p>"})
        self.assertFalse(tmpl.available_in_pos)

    def test_new_isbn_updates_barcode(self):
        self.env["comic.isbn"].create({"edition_id": self.edition.id, "isbn_13": "9782800152851"})
        self.assertEqual(self.edition.product_tmpl_id.barcode, "9782800152851")

    def test_rename_serie_and_work_updates_product_name(self):
        self.serie.name = "Série Renommée"
        self.assertIn("Série Renommée", self.edition.product_tmpl_id.name)
        self.work.titre_canonique = "Titre Renommé"
        self.assertIn("Titre Renommé", self.edition.product_tmpl_id.name)
