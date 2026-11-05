"""Tests du wizard « Tomes manquants ».

Lancement :
    docker exec odoo-web odoo -d odoo -u comic_datasource --test-tags /comic_datasource
"""

from unittest.mock import patch

from odoo.exceptions import UserError
from odoo.tests import tagged
from odoo.tests.common import TransactionCase

from odoo.addons.comic_datasource.sources.base import ComicSourceResult
from odoo.addons.comic_datasource.sources.bnf import BnfSource
from odoo.addons.comic_datasource.sources.google_books import GoogleBooksQuotaError, GoogleBooksSource

ISBN_A = "9782205060010"
ISBN_B = "9782205060027"
ISBN_C = "9782205060034"


@tagged("post_install", "-at_install", "comic_datasource")
class TestMissingTomes(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Wizard = cls.env["comic.serie.missing.wizard"]
        cls.serie = cls.env["comic.serie"].create({"name": "Série test tomes manquants"})
        Work = cls.env["comic.work"]
        for tome in (0, 1, 2, 5):
            Work.create({"serie_id": cls.serie.id, "titre_canonique": f"Album {tome}", "tome": tome})

    # ── Helpers ──────────────────────────────────────────────────────────────

    def _search(self, bnf_results=None):
        """Lance la recherche avec les sources externes simulées (aucun appel réseau)."""
        wizard = self.Wizard.create({"serie_id": self.serie.id})
        with (
            patch.object(GoogleBooksSource, "_fetch", return_value={"totalItems": 0}),
            patch.object(BnfSource, "search_by_serie", return_value=bnf_results or []),
        ):
            wizard.action_search()
        return wizard

    def _line(self, wizard, tome, name, isbn=""):
        return self.env["comic.serie.missing.line"].create(
            {"wizard_id": wizard.id, "tome": tome, "name": name, "isbn": isbn, "selected": True}
        )

    # ── Nombre de tomes attendus ─────────────────────────────────────────────

    def test_expected_uses_max_tome_without_nb_tomes_parus(self):
        # 4 albums en base (tomes 0, 1, 2, 5) : l'ancien calcul (nb d'albums) attendait 4 tomes.
        wizard = self._search()
        self.assertEqual(wizard.nb_expected, 5)
        self.assertEqual(sorted(wizard.line_ids.mapped("tome")), [3, 4])
        self.assertEqual(set(wizard.line_ids.mapped("source")), {"expected"})

    def test_expected_uses_nb_tomes_parus(self):
        self.serie.nb_tomes_parus = 7
        wizard = self._search()
        self.assertEqual(wizard.nb_expected, 7)
        self.assertEqual(sorted(wizard.line_ids.mapped("tome")), [3, 4, 6, 7])

    def test_expected_raised_by_external_results(self):
        bnf = [ComicSourceResult(source="bnf", title="Album huit", tome=8, isbn=ISBN_C)]
        wizard = self._search(bnf_results=bnf)
        self.assertEqual(wizard.nb_expected, 8)
        self.assertEqual(sorted(wizard.line_ids.mapped("tome")), [3, 4, 6, 7, 8])
        line_8 = wizard.line_ids.filtered(lambda line: line.tome == 8)
        self.assertEqual(line_8.source, "bnf")
        self.assertEqual(line_8.isbn, ISBN_C)

    def test_tome_zero_never_missing(self):
        serie = self.env["comic.serie"].create({"name": "Série hors-série seul"})
        self.env["comic.work"].create({"serie_id": serie.id, "titre_canonique": "HS", "tome": 0})
        self.assertEqual(self.Wizard._compute_expected_count(serie, {0}), 0)
        self.assertEqual(self.Wizard._missing_tome_numbers(3, {0, 2}), [1, 3])
        bnf = [ComicSourceResult(source="bnf", title="Hors-série", tome=0, isbn=ISBN_C)]
        wizard = self._search(bnf_results=bnf)
        self.assertNotIn(0, wizard.line_ids.mapped("tome"))

    def test_search_sets_last_check(self):
        self.assertFalse(self.serie.missing_last_check)
        self._search()
        self.assertTrue(self.serie.missing_last_check)

    # ── Ajout : réutilisation de l'album et de l'édition ─────────────────────

    def test_add_reuses_existing_work_and_edition(self):
        work_1 = self.serie.work_ids.filtered(lambda w: w.tome == 1)
        self.assertEqual(len(work_1.edition_ids), 1)
        edition = work_1.edition_ids
        self.assertFalse(edition.isbn_ids)
        nb_works = len(self.serie.work_ids)

        wizard = self.Wizard.create({"serie_id": self.serie.id})
        self._line(wizard, 1, "Album 1", ISBN_A)
        wizard.action_add_to_wishlist()

        self.assertEqual(len(self.serie.work_ids), nb_works, "Aucun album ne doit être créé")
        self.assertEqual(len(work_1.edition_ids), 1, "Aucune édition en double")
        self.assertEqual(edition.isbn_ids.mapped("isbn_13"), [ISBN_A])
        self.assertEqual(wizard.state, "done")

    def test_add_creates_edition_only_for_different_isbn(self):
        work_2 = self.serie.work_ids.filtered(lambda w: w.tome == 2)
        self.env["comic.isbn"].create({"edition_id": work_2.edition_ids[:1].id, "isbn_13": ISBN_A})

        wizard = self.Wizard.create({"serie_id": self.serie.id})
        self._line(wizard, 2, "Album 2 — autre édition", ISBN_B)
        wizard.action_add_to_catalogue()

        self.assertEqual(len(work_2.edition_ids), 2)
        self.assertEqual(sorted(work_2.edition_ids.isbn_ids.mapped("isbn_13")), [ISBN_A, ISBN_B])

    def test_add_new_tome_creates_single_edition(self):
        wizard = self.Wizard.create({"serie_id": self.serie.id})
        self._line(wizard, 3, "Album 3", ISBN_B)
        wizard.action_add_to_wishlist()

        work_3 = self.serie.work_ids.filtered(lambda w: w.tome == 3)
        self.assertEqual(len(work_3), 1)
        self.assertEqual(len(work_3.edition_ids), 1)
        self.assertEqual(work_3.edition_ids.isbn_ids.mapped("isbn_13"), [ISBN_B])

    def test_add_to_wishlist_flags_customer_album(self):
        CustomerAlbum = self.env.get("comic.customer.album")
        if CustomerAlbum is None:
            self.skipTest("comic_shop non installé : pas de bibliothèque client")
        wizard = self.Wizard.create({"serie_id": self.serie.id})
        self.assertTrue(wizard.has_customer_library)
        self._line(wizard, 1, "Album 1")
        wizard.action_add_to_wishlist()

        edition = self.serie.work_ids.filtered(lambda w: w.tome == 1).edition_ids
        entry = CustomerAlbum.search(
            [("partner_id", "=", self.env.user.partner_id.id), ("edition_id", "=", edition.id)]
        )
        self.assertEqual(len(entry), 1)
        self.assertTrue(entry.dans_wishlist)
        self.assertFalse(entry.dans_collection)

    # ── Quota Google Books ───────────────────────────────────────────────────

    def test_quota_error_gives_clean_message(self):
        wizard = self.Wizard.create({"serie_id": self.serie.id})
        with (
            patch.object(GoogleBooksSource, "_fetch", side_effect=GoogleBooksQuotaError("HTTP 429")),
            patch.object(BnfSource, "search_by_serie", return_value=[]),
        ):
            with self.assertRaises(UserError) as ctx:
                wizard.action_search()
        self.assertIn("quota", str(ctx.exception).lower())
        self.assertEqual(wizard.state, "confirm")
