"""Tests ORM de l'enrichissement (lot 3 de la revue fonctionnelle).

Lancement :
    docker exec odoo-web odoo -d odoo -u comic_datasource --test-tags /comic_datasource
"""

from unittest.mock import patch

from odoo.tests import tagged
from odoo.tests.common import TransactionCase

from odoo.addons.comic_datasource.models.comic_edition import _best_title_match, _find_or_create_author
from odoo.addons.comic_datasource.sources.base import ComicSourceResult
from odoo.addons.comic_datasource.sources.google_books import GoogleBooksQuotaError


@tagged("post_install", "-at_install", "comic_datasource")
class TestEnrichment(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.serie = cls.env["comic.serie"].create({"name": "Blacksad"})
        cls.work = cls.env["comic.work"].create(
            {"serie_id": cls.serie.id, "titre_canonique": "Arctic-Nation", "tome": 2}
        )
        cls.edition = cls.work.edition_ids[:1] or cls.env["comic.edition"].create({"work_id": cls.work.id})

    # ── _apply_datasource_data : ne remplit que les champs vides ─────────────

    def test_apply_does_not_overwrite_user_data(self):
        self.edition.write({"synopsis": "<p>Mon synopsis</p>", "nb_pages": 48})
        self.edition._apply_datasource_data({"synopsis": "Synopsis source", "nb_pages": 56})
        self.assertIn("Mon synopsis", self.edition.synopsis)
        self.assertEqual(self.edition.nb_pages, 48)

    def test_apply_fills_empty_fields(self):
        self.edition.write({"synopsis": False, "nb_pages": 0})
        self.edition._apply_datasource_data({"synopsis": "Synopsis source", "nb_pages": 56})
        self.assertIn("Synopsis source", self.edition.synopsis)
        self.assertEqual(self.edition.nb_pages, 56)

    # ── Rapprochement par titre strict ───────────────────────────────────────

    def _result(self, **kw):
        return ComicSourceResult(source="google", **kw)

    def test_title_match_rejects_other_title(self):
        results = [self._result(title="Arctic Monkeys", isbn="9782205049657")]
        self.assertIsNone(_best_title_match(results, self.work))

    def test_title_match_rejects_other_tome(self):
        results = [self._result(title="Arctic-Nation", tome=5, isbn="9782205049657")]
        self.assertIsNone(_best_title_match(results, self.work))

    def test_title_match_rejects_other_serie(self):
        results = [self._result(title="Arctic Nation", serie_name="Autre série", isbn="9782205049657")]
        self.assertIsNone(_best_title_match(results, self.work))

    def test_title_match_accepts_normalized_title(self):
        good = self._result(title="Arctic Nation", serie_name="Blacksad", tome=2, isbn="9782205049657")
        self.assertIs(_best_title_match([good], self.work), good)

    # ── Auteurs : correspondance exacte ──────────────────────────────────────

    def test_author_exact_match_only(self):
        morrison = self.env["res.partner"].create({"name": "Morrison"})
        morris = _find_or_create_author(self.env, "Morris")
        self.assertNotEqual(morris, morrison)
        self.assertEqual(_find_or_create_author(self.env, "morris"), morris)

    # ── Réglages : décocher une source la désactive vraiment ─────────────────

    def test_settings_toggle_persists_false(self):
        icp = self.env["ir.config_parameter"].sudo()
        settings = self.env["res.config.settings"].create({"comic_bnf_enabled": False, "comic_openlibrary_enabled": True})
        settings.set_values()
        self.assertEqual(icp.get_param("comic.bnf_enabled"), "False")
        self.assertEqual(icp.get_param("comic.openlibrary_enabled"), "True")
        self.assertFalse(self.env["res.config.settings"].create({}).comic_bnf_enabled)

    # ── Cron : rotation du lot et coupe-circuit quota ────────────────────────

    def test_cron_rotates_and_stops_on_quota(self):
        Edition = self.env["comic.edition"]
        Edition.create({"work_id": self.work.id})  # au moins 2 éditions incomplètes
        Edition.search([]).write({"datasource_last_try": False})
        agg = "odoo.addons.comic_datasource.aggregator.ComicDataAggregator"
        quota = GoogleBooksQuotaError("quota")
        with patch(f"{agg}.search", side_effect=quota) as m_search, patch(
            f"{agg}.search_list", side_effect=quota
        ) as m_list:
            Edition._cron_update_editions(batch_size=50)
        # Coupe-circuit : un seul appel réseau malgré plusieurs éditions incomplètes
        self.assertEqual(m_search.call_count + m_list.call_count, 1)
        # Rotation : seule l'édition tentée est marquée, les autres passent en premier ensuite
        self.assertEqual(Edition.search_count([("datasource_last_try", "!=", False)]), 1)
