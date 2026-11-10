"""Tests d'import de bout en bout (wizard + ORM).

Lancement :
    docker exec odoo-web odoo -d odoo -u comics_collections --test-tags /comics_collections:TestImportOrm
"""

import base64

from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged("post_install", "-at_install", "comics_collections", "import_orm")
class TestImportOrm(TransactionCase):

    def _run(self, csv_text, policy="update"):
        wizard = self.env["comic.import.wizard"].create(
            {
                "import_file": base64.b64encode(csv_text.encode("utf-8")),
                "import_filename": "import.csv",
                "import_policy": policy,
            }
        )
        wizard.action_import()
        return wizard

    def test_counters_created_then_updated(self):
        csv_text = "serie_name;tome;titre_canonique\nZorglub Test;1;Premier\nZorglub Test;2;Second\n"
        wizard = self._run(csv_text)
        self.assertIn("<strong>2</strong> album(s) created", wizard.result_html)
        wizard = self._run(csv_text)
        self.assertIn("<strong>0</strong> album(s) created", wizard.result_html)
        self.assertIn("<strong>2</strong> album(s) updated", wizard.result_html)

    def test_skip_policy_leaves_existing_untouched(self):
        self._run("serie_name;tome;titre_canonique\nZorglub Skip;1;Titre original\n")
        wizard = self._run("serie_name;tome;titre_canonique\nZorglub Skip;1;Titre modifié\n", policy="skip")
        self.assertIn("<strong>1</strong> album(s) skipped", wizard.result_html)
        work = self.env["comic.work"].search([("serie_id.name", "=", "Zorglub Skip"), ("tome", "=", 1)])
        self.assertEqual(work.titre_canonique, "Titre original")

    def test_serie_matched_on_normalized_name(self):
        self._run("serie_name;tome;titre_canonique\n" "Agent 999 (L');1;Un\n" "L'Agent 999;2;Deux\n")
        self.assertEqual(self.env["comic.serie"].search_count([("name_normalise", "=", "agent 999")]), 1)

    def test_error_reports_real_file_line(self):
        # ligne 3 vide → la ligne fautive est la 4e du fichier
        wizard = self._run("serie_name;tome;titre_canonique\nZorglub L;1;Un\n;;\n;5;\n")
        self.assertIn("Line 4", wizard.result_html)

    def test_invalid_isbn_imports_album_with_warning(self):
        wizard = self._run("serie_name;tome;titre_canonique;isbn\nZorglub Isbn;1;Un;9782000000000\n")
        self.assertIn("<strong>1</strong> album(s) created", wizard.result_html)
        self.assertIn("Invalid ISBN", wizard.result_html)
        work = self.env["comic.work"].search([("serie_id.name", "=", "Zorglub Isbn")])
        self.assertTrue(work)
        self.assertFalse(work.edition_ids.isbn_ids)

    def test_untitled_albums_get_distinct_titles(self):
        wizard = self._run("serie_name;tome;titre_canonique\nZorglub Vide;1;\nZorglub Vide;2;\n")
        self.assertIn("<strong>2</strong> album(s) created", wizard.result_html)

    def test_several_unnumbered_albums(self):
        wizard = self._run("serie_name;tome;titre_canonique\nZorglub HS;;Hors-série A\nZorglub HS;;Hors-série B\n")
        self.assertIn("<strong>2</strong> album(s) created", wizard.result_html)

    def test_author_does_not_match_company(self):
        company = self.env["res.partner"].create({"name": "Dupuis Auteur", "is_company": True})
        self._run("serie_name;tome;titre_canonique;scenariste\nZorglub Aut;1;Un;Dupuis Auteur\n")
        work = self.env["comic.work"].search([("serie_id.name", "=", "Zorglub Aut")])
        self.assertTrue(work.auteur_line_ids)
        self.assertNotEqual(work.auteur_line_ids.partner_id, company)
