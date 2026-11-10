"""Recherche « Album » / « Titre » dans Ma bibliothèque (comic.customer.album)."""

from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged("post_install", "-at_install", "comics_collections", "library_search")
class TestLibrarySearch(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        partner = cls.env["res.partner"].create({"name": "Lecteur recherche"})
        serie_a = cls.env["comic.serie"].create({"name": "Série Alpha Recherche"})
        serie_b = cls.env["comic.serie"].create({"name": "Série Beta Recherche"})
        cls.work_a = cls.env["comic.work"].create(
            {"serie_id": serie_a.id, "titre_canonique": "Le Sarcophage perdu", "tome": 1}
        )
        cls.work_b = cls.env["comic.work"].create(
            {"serie_id": serie_b.id, "titre_canonique": "La Forteresse", "tome": 1}
        )
        cls.env["comic.isbn"].create({"edition_id": cls.work_a.primary_edition_id.id, "isbn_13": "9782800152851"})
        Album = cls.env["comic.customer.album"]
        cls.lib_a = Album.create({"partner_id": partner.id, "edition_id": cls.work_a.primary_edition_id.id})
        cls.lib_b = Album.create({"partner_id": partner.id, "edition_id": cls.work_b.primary_edition_id.id})
        cls.mine = cls.lib_a | cls.lib_b

    def _find(self, field, value):
        return self.env["comic.customer.album"].search([("id", "in", self.mine.ids), (field, "ilike", value)])

    def test_search_album_by_title_series_and_isbn(self):
        self.assertEqual(self._find("edition_id", "Sarcophage"), self.lib_a)
        self.assertEqual(self._find("edition_id", "Beta Recherche"), self.lib_b)
        self.assertEqual(self._find("edition_id", "9782800152851"), self.lib_a)
        self.assertFalse(self._find("edition_id", "Introuvable"))

    def test_search_title_by_title_or_series(self):
        self.assertEqual(self._find("work_id", "Forteresse"), self.lib_b)
        self.assertEqual(self._find("work_id", "Alpha Recherche"), self.lib_a)
