"""Tests du wizard « Tomes manquants ».

Lancement :
    docker exec odoo-web odoo -d odoo -u comic_datasource --test-tags /comic_datasource
"""

from datetime import timedelta
from unittest.mock import patch

from odoo import Command, fields
from odoo.exceptions import UserError
from odoo.tests import new_test_user, tagged
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

    # ── Alerte nouveautés (US-068) ───────────────────────────────────────────

    def _release_messages(self, work):
        return work.message_ids.filtered(lambda m: "Nouveau tome dans une série que vous suivez" in (m.body or ""))

    def test_cron_new_recent_tome_notifies_followers(self):
        follower = new_test_user(
            self.env, login="missing_release_follower", groups="comics_collections.group_comic_user"
        )
        self.serie.write({"suivi_user_ids": [Command.link(follower.id)]})
        # Seule notre série est à traiter par ce passage du cron
        others = self.env["comic.serie"].search([("id", "!=", self.serie.id)])
        others.write({"missing_last_check": fields.Datetime.now()})
        self.serie.missing_last_check = False

        recent = (fields.Date.context_today(self.serie) - timedelta(days=10)).isoformat()
        bnf = [
            ComicSourceResult(source="bnf", title="Album six", tome=6, isbn=ISBN_C, date_parution=recent),
            ComicSourceResult(source="bnf", title="Album sept", tome=7, isbn=ISBN_B, date_parution="1990-01-01"),
        ]
        with (
            patch.object(GoogleBooksSource, "_fetch", return_value={"totalItems": 0}),
            patch.object(BnfSource, "search_by_serie", return_value=bnf),
        ):
            self.env["comic.serie"]._cron_check_missing_volumes(batch_size=1)

        work_6 = self.serie.work_ids.filtered(lambda w: w.tome == 6)
        work_7 = self.serie.work_ids.filtered(lambda w: w.tome == 7)
        self.assertTrue(work_6 and work_7, "Les tomes avec ISBN confirmé sont ajoutés par le cron")
        message = self._release_messages(work_6)
        self.assertEqual(len(message), 1)
        self.assertIn(follower.partner_id, message.notification_ids.res_partner_id)
        self.assertTrue(work_6.release_notified)
        self.assertFalse(self._release_messages(work_7), "Un vieux tome n'est pas une nouveauté")

    def test_wizard_reused_album_not_notified(self):
        follower = new_test_user(
            self.env, login="missing_release_follower2", groups="comics_collections.group_comic_user"
        )
        self.serie.write({"suivi_user_ids": [Command.link(follower.id)]})
        work_1 = self.serie.work_ids.filtered(lambda w: w.tome == 1)
        work_1.date_parution = fields.Date.context_today(work_1)
        wizard = self.Wizard.create({"serie_id": self.serie.id})
        self._line(wizard, 1, "Album 1", ISBN_A)
        self._line(wizard, 3, "Album 3", ISBN_B).date_parution = fields.Date.context_today(work_1)
        wizard.action_add_to_catalogue()
        self.assertFalse(self._release_messages(work_1), "Album existant réutilisé : pas d'alerte")
        work_3 = self.serie.work_ids.filtered(lambda w: w.tome == 3)
        self.assertEqual(len(self._release_messages(work_3)), 1)

    # ── Quota Google Books ───────────────────────────────────────────────────

    def test_search_and_add_never_duplicate_albums(self):
        """#1 : la complétion d'une série ne doit jamais dédoubler les BD.

        Résultats piégés : tome déjà possédé, ISBN déjà connu dans le catalogue (autre
        série), titre identique à un album existant sous un autre numéro, doublon entre
        deux résultats de sources. Seuls des tomes réellement absents sont proposés, et
        l'ajout ne crée aucun second album pour un tome ou un ISBN déjà présents.
        """
        other = self.env["comic.work"].create({"titre_canonique": "Ailleurs", "tome": 1})
        self.env["comic.isbn"].create({"edition_id": other.primary_edition_id.id, "isbn_13": ISBN_A})
        bnf = [
            ComicSourceResult(source="bnf", title="Album 1", tome=1, isbn=ISBN_C),  # tome possédé
            ComicSourceResult(source="bnf", title="Nouveau 3", tome=3, isbn=ISBN_A),  # ISBN connu ailleurs
            ComicSourceResult(source="bnf", title="Album 2", tome=6),  # même titre que le T2
            ComicSourceResult(source="bnf", title="Nouveau 4", tome=4, isbn=ISBN_B),
            ComicSourceResult(source="bnf", title="Nouveau 4", tome=4, isbn=ISBN_B),  # doublon de source
        ]
        wizard = self._search(bnf_results=bnf)
        lines = wizard.line_ids
        self.assertFalse(lines.filtered(lambda line: line.tome in (0, 1, 2, 5)), "Aucun tome déjà possédé")
        self.assertNotIn(ISBN_A, lines.mapped("isbn"), "Un ISBN déjà au catalogue n'est jamais reproposé")
        self.assertEqual(len(lines.filtered(lambda line: line.tome == 4)), 1, "Un seul candidat par tome")
        self.assertEqual(lines.filtered(lambda line: line.tome == 4).isbn, ISBN_B)
        # Même titre qu'un album existant : c'est cet album (mal numéroté), pas un T6
        self.assertFalse(lines.filtered(lambda line: line.tome == 6))

        wizard.action_add_to_catalogue()
        works = self.serie.with_context(active_test=False).work_ids
        tomes = works.mapped("tome")
        self.assertEqual(len(tomes), len(set(tomes)), "Un seul album par tome")
        self.assertEqual(sorted(t for t in tomes if t), [1, 2, 3, 4, 5])
        self.assertEqual(self.env["comic.isbn"].search_count([("isbn_13", "=", ISBN_A)]), 1)
        self.assertEqual(self.env["comic.isbn"].search([("isbn_13", "=", ISBN_A)]).edition_id.work_id, other)
        # Deuxième passage : la série est complète
        self.assertFalse(self._search().line_ids)

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
