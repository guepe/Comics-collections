"""Bouton « Compléter les infos » (album / édition) : sources, champs vides seulement."""

from unittest.mock import patch

from odoo.exceptions import UserError
from odoo.tests import TransactionCase, tagged

from odoo.addons.comic_datasource.sources.google_books import GoogleBooksQuotaError

AGG = "odoo.addons.comic_datasource.aggregator.ComicDataAggregator"


class _Agg:
    def __init__(self, data):
        self.data = data


@tagged("post_install", "-at_install", "comic_datasource")
class TestCompleteFromSources(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.work = cls.env["comic.work"].create({"titre_canonique": "Complétable", "tome": 1})
        cls.edition = cls.work.primary_edition_id
        cls.env["comic.isbn"].create({"edition_id": cls.edition.id, "isbn_13": "9782800152851"})

    def test_fills_empty_fields_and_reports(self):
        data = {
            "synopsis": "Synopsis source",
            "nb_pages": 48,
            "auteurs": [{"name": "Auteur Source", "role": "scenariste"}],
        }
        with patch(f"{AGG}.search", return_value=_Agg(data)) as m_search:
            action = self.work.action_complete_from_sources()
        m_search.assert_called_once_with(isbn="9782800152851")
        self.assertIn("Synopsis source", self.edition.synopsis)
        self.assertEqual(self.edition.nb_pages, 48)
        message = action["params"]["message"]
        self.assertIn("synopsis", message)
        self.assertIn("number of pages", message)
        self.assertIn("authors", message)
        self.assertEqual(action["params"]["type"], "success")

    def test_never_overwrites(self):
        self.edition.write({"synopsis": "<p>Le mien</p>", "nb_pages": 10})
        with patch(f"{AGG}.search", return_value=_Agg({"synopsis": "Autre", "nb_pages": 99})):
            action = self.edition.action_complete_from_sources()
        self.assertIn("Le mien", self.edition.synopsis)
        self.assertEqual(self.edition.nb_pages, 10)
        self.assertEqual(action["params"]["type"], "info")

    def test_not_found_and_quota(self):
        with patch(f"{AGG}.search", return_value=None):
            self.assertEqual(self.work.action_complete_from_sources()["params"]["type"], "warning")
        with patch(f"{AGG}.search", side_effect=GoogleBooksQuotaError("quota")):
            with self.assertRaisesRegex(UserError, "quota reached"):
                self.work.action_complete_from_sources()


@tagged("post_install", "-at_install", "comic_datasource")
class TestDatasourceSettingsView(TransactionCase):
    def test_source_toggles_labelled_once(self):
        """#10 : <setting> affiche déjà le libellé de la case — pas de <label> en double."""
        arch = self.env.ref("comic_datasource.res_config_settings_view_form_comic_datasource").arch_db
        for field_name in ("comic_openlibrary_enabled", "comic_bnf_enabled"):
            self.assertNotIn(f'<label for="{field_name}"', arch)
