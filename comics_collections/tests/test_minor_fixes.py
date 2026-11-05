"""Tests des correctifs mineurs (slug, auteurs, contrainte de titre, ISBN-10 → 13,
liens d'achat).

Lancement :
    docker exec odoo-web odoo-bin -d odoo -u comics_collections \
        --test-tags /comics_collections:TestMinorFixes
"""

from odoo.exceptions import ValidationError
from odoo.tests import tagged
from odoo.tests.common import TransactionCase
from odoo.tools.safe_eval import safe_eval


@tagged("post_install", "-at_install", "comics_collections")
class TestMinorFixes(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Work = cls.env["comic.work"]
        cls.serie = cls.env["comic.serie"].create({"name": "Écume des jours"})
        cls.serie_other = cls.env["comic.serie"].create({"name": "Blacksad"})

    # ── 1. Slug ───────────────────────────────────────────────────────────────

    def test_slug_transliterates_accents(self):
        work = self.Work.create({"serie_id": self.serie.id, "titre_canonique": "Slug accent", "tome": 1})
        self.assertEqual(work.slug, "ecume-des-jours-t01")

    def test_slug_regenerated_when_tome_changes(self):
        work = self.Work.create({"serie_id": self.serie.id, "titre_canonique": "Slug tome", "tome": 2})
        work.write({"tome": 7})
        self.assertEqual(work.slug, "ecume-des-jours-t07")

    def test_slug_regenerated_when_serie_changes(self):
        work = self.Work.create({"serie_id": self.serie.id, "titre_canonique": "Slug série", "tome": 3})
        work.write({"serie_id": self.serie_other.id})
        self.assertEqual(work.slug, "blacksad-t03")

    def test_slug_unchanged_on_rewrite_same_values(self):
        work = self.Work.create({"serie_id": self.serie.id, "titre_canonique": "Slug stable", "tome": 4})
        work.write({"tome": 4})
        # Le record lui-même est exclu de la recherche d'unicité : pas de suffixe.
        self.assertEqual(work.slug, "ecume-des-jours-t04")

    def test_slug_explicit_value_kept_on_write(self):
        work = self.Work.create({"serie_id": self.serie.id, "titre_canonique": "Slug manuel", "tome": 5})
        work.write({"tome": 6, "slug": "mon-slug"})
        self.assertEqual(work.slug, "mon-slug")

    # ── 4. Auteurs ────────────────────────────────────────────────────────────

    def test_author_from_menu_context_is_flagged(self):
        partner = (
            self.env["res.partner"]
            .with_context(default_is_comic_author=True)
            .create({"name": "Auteur créé depuis le menu"})
        )
        self.assertTrue(partner.is_comic_author)
        action = self.env.ref("comics_collections.action_comic_auteurs")
        domain = safe_eval(action.domain)
        self.assertIn(partner, self.env["res.partner"].search(domain))

    def test_author_line_flags_partner(self):
        partner = self.env["res.partner"].create({"name": "Auteur crédité"})
        self.assertFalse(partner.is_comic_author)
        work = self.Work.create({"serie_id": self.serie.id, "titre_canonique": "Album crédité", "tome": 8})
        self.env["comic.work.auteur.line"].create({"work_id": work.id, "partner_id": partner.id, "role": "scenariste"})
        self.assertTrue(partner.is_comic_author)

    # ── 6. Contrainte de titre ────────────────────────────────────────────────

    def test_title_duplicate_raises_validation_error(self):
        self.Work.create({"serie_id": self.serie.id, "titre_canonique": "Les Landes perdues", "tome": 9})
        with self.assertRaises(ValidationError):
            self.Work.create({"serie_id": self.serie.id, "titre_canonique": "Landes perdues (Les)", "tome": 10})

    # ── 7. ISBN-10 → ISBN-13 ──────────────────────────────────────────────────

    def _edition(self, tome):
        work = self.Work.create({"serie_id": self.serie_other.id, "titre_canonique": f"ISBN {tome}", "tome": tome})
        return work.edition_ids[:1]

    def test_isbn10_only_computes_isbn13(self):
        isbn = self.env["comic.isbn"].create({"edition_id": self._edition(11).id, "isbn_10": "2-01-210134-8"})
        self.assertEqual(isbn.isbn_10, "2012101348")
        self.assertEqual(isbn.isbn_13, "9782012101340")

    def test_isbn10_does_not_override_given_isbn13(self):
        isbn = self.env["comic.isbn"].create(
            {"edition_id": self._edition(12).id, "isbn_10": "2012101348", "isbn_13": "9782800152950"}
        )
        self.assertEqual(isbn.isbn_13, "9782800152950")

    def test_invalid_isbn10_still_rejected(self):
        with self.assertRaises(ValidationError):
            self.env["comic.isbn"].create({"edition_id": self._edition(13).id, "isbn_10": "0000000001"})

    def test_isbn10_write_fills_empty_isbn13(self):
        isbn = self.env["comic.isbn"].create({"edition_id": self._edition(14).id})
        isbn.write({"isbn_10": "2012101348"})
        self.assertEqual(isbn.isbn_13, "9782012101340")

    # ── 3. Liens d'achat : ISBN principal déterministe ───────────────────────

    def test_primary_isbn_is_oldest_isbn13(self):
        edition = self._edition(15)
        first = self.env["comic.isbn"].create({"edition_id": edition.id, "isbn_13": "9782012101340"})
        self.env["comic.isbn"].create({"edition_id": edition.id, "isbn_13": "9782800152950"})
        self.assertEqual(edition._get_primary_isbn(), first.isbn_13)
