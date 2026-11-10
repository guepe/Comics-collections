"""Tests ORM pour le modèle comic.work.

Teste : contrainte unique (serie_id, tome), génération de slug, display_name,
titre_normalise, auteur_line_ids et nb_editions.

Lancement :
    docker exec odoo-web odoo-bin -d odoo -u comics_collections \
        --test-tags /comics_collections:TestComicWork
"""

from psycopg2 import IntegrityError

from odoo.tests.common import TransactionCase
from odoo.tests import tagged
from odoo.tools import mute_logger


@tagged("comics_collections", "comic_work")
class TestComicWork(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.serie = cls.env["comic.serie"].create({"name": "Thorgal"})

    # ── Génération de slug ───────────────────────────────────────────────────

    def test_slug_generated_on_create(self):
        work = self.env["comic.work"].create(
            {
                "serie_id": self.serie.id,
                "titre_canonique": "Iles des mers gelées",
                "tome": 99,
            }
        )
        self.assertEqual(work.slug, "thorgal-t99")

    def test_slug_no_serie_uses_tome_only(self):
        work = self.env["comic.work"].create(
            {
                "titre_canonique": "One Shot",
                "tome": 3,
            }
        )
        self.assertTrue(work.slug.startswith("t03"))

    def test_slug_conflict_gets_numeric_suffix(self):
        """Deux séries avec noms similaires → slug base identique → suffixe -1."""
        serie_a = self.env["comic.serie"].create({"name": "Lucky Luke!"})
        serie_b = self.env["comic.serie"].create({"name": "Lucky Luke"})
        # Les deux normalisent en "lucky-luke"
        w1 = self.env["comic.work"].create(
            {
                "serie_id": serie_a.id,
                "titre_canonique": "Titre A",
                "tome": 1,
            }
        )
        w2 = self.env["comic.work"].create(
            {
                "serie_id": serie_b.id,
                "titre_canonique": "Titre B",
                "tome": 1,
            }
        )
        self.assertEqual(w1.slug, "lucky-luke-t01")
        self.assertEqual(w2.slug, "lucky-luke-t01-1")

    def test_custom_slug_preserved_on_create(self):
        work = self.env["comic.work"].create(
            {
                "titre_canonique": "Test",
                "tome": 99,
                "slug": "mon-slug-custom",
            }
        )
        self.assertEqual(work.slug, "mon-slug-custom")

    # ── display_name ─────────────────────────────────────────────────────────

    def test_display_name_with_serie_and_tome(self):
        work = self.env["comic.work"].create(
            {
                "serie_id": self.serie.id,
                "titre_canonique": "La Magicienne trahie",
                "tome": 1,
            }
        )
        self.assertEqual(work.display_name, "Thorgal Vol. 01 — La Magicienne trahie")

    def test_display_name_without_serie_and_tome(self):
        work = self.env["comic.work"].create(
            {
                "titre_canonique": "One Shot pur",
                "tome": 0,
            }
        )
        self.assertEqual(work.display_name, "One Shot pur")

    def test_display_name_tome_only(self):
        work = self.env["comic.work"].create(
            {
                "titre_canonique": "Volume unique",
                "tome": 7,
            }
        )
        self.assertEqual(work.display_name, "Vol. 07 — Volume unique")

    # ── titre_normalise ──────────────────────────────────────────────────────

    def test_titre_normalise_strips_leading_article_fr(self):
        work = self.env["comic.work"].create(
            {
                "titre_canonique": "Les Landes perdues",
                "tome": 1,
            }
        )
        self.assertEqual(work.titre_normalise, "landes perdues")

    def test_titre_normalise_strips_le(self):
        work = self.env["comic.work"].create(
            {
                "titre_canonique": "Le Grand Pouvoir du Chninkel",
                "tome": 1,
            }
        )
        self.assertEqual(work.titre_normalise, "grand pouvoir du chninkel")

    def test_titre_normalise_strips_accents(self):
        work = self.env["comic.work"].create(
            {
                "titre_canonique": "Étoiles lointaines",
                "tome": 1,
            }
        )
        self.assertNotIn("É", work.titre_normalise)
        self.assertIn("etoiles", work.titre_normalise)

    # ── Contrainte unique (serie_id, tome) ───────────────────────────────────

    def test_unique_serie_tome_index_defined(self):
        """L'index unique partiel (serie_id, tome) WHERE tome > 0 existe en DB."""
        self.env.cr.execute("SELECT COUNT(*) FROM pg_indexes WHERE indexname = 'comic_work_unique_serie_tome_numbered'")
        count = self.env.cr.fetchone()[0]
        self.assertEqual(count, 1, "L'index unique (serie_id, tome) doit exister en DB")

    def test_duplicate_numbered_tome_is_refused(self):
        """Deux albums avec le même numéro de tome dans une série : refusé."""
        self.env["comic.work"].create({"serie_id": self.serie.id, "titre_canonique": "Tome 7 A", "tome": 7})
        with self.assertRaises(IntegrityError), mute_logger("odoo.sql_db"):
            self.env["comic.work"].create({"serie_id": self.serie.id, "titre_canonique": "Tome 7 B", "tome": 7})
            self.env.flush_all()

    def test_several_unnumbered_works_allowed(self):
        """Plusieurs hors-série (tome = 0) dans une même série : autorisé."""
        w1 = self.env["comic.work"].create({"serie_id": self.serie.id, "titre_canonique": "Hors-série A"})
        w2 = self.env["comic.work"].create({"serie_id": self.serie.id, "titre_canonique": "Hors-série B"})
        self.env.flush_all()
        self.assertEqual((w1.tome, w2.tome), (0, 0))

    def test_same_tome_different_serie_is_allowed(self):
        """Même numéro de tome pour deux séries différentes : OK."""
        serie2 = self.env["comic.serie"].create({"name": "Blacksad"})
        w1 = self.env["comic.work"].create(
            {
                "serie_id": self.serie.id,
                "titre_canonique": "Thorgal T2",
                "tome": 2,
            }
        )
        w2 = self.env["comic.work"].create(
            {
                "serie_id": serie2.id,
                "titre_canonique": "Blacksad T2",
                "tome": 2,
            }
        )
        self.assertTrue(w1.id != w2.id)

    # ── auteur_line_ids / nb_auteurs ─────────────────────────────────────────

    def test_add_auteur_line(self):
        work = self.env["comic.work"].create(
            {
                "titre_canonique": "Test Auteurs",
                "tome": 1,
            }
        )
        partner = self.env["res.partner"].create({"name": "Van Hamme Jean"})
        line = self.env["comic.work.auteur.line"].create(
            {
                "work_id": work.id,
                "partner_id": partner.id,
                "role": "scenariste",
            }
        )
        self.assertEqual(work.nb_auteurs, 1)
        self.assertEqual(line.role, "scenariste")
        self.assertEqual(line.partner_id, partner)

    def test_remove_auteur_line(self):
        work = self.env["comic.work"].create(
            {
                "titre_canonique": "Test Suppression Auteur",
                "tome": 1,
            }
        )
        partner = self.env["res.partner"].create({"name": "Auteur Test"})
        line = self.env["comic.work.auteur.line"].create(
            {
                "work_id": work.id,
                "partner_id": partner.id,
                "role": "dessinateur",
            }
        )
        self.assertEqual(work.nb_auteurs, 1)
        line.unlink()
        self.assertEqual(work.nb_auteurs, 0)

    # ── nb_editions ──────────────────────────────────────────────────────────

    def test_nb_editions_computed_on_add(self):
        work = self.env["comic.work"].create(
            {
                "serie_id": self.serie.id,
                "titre_canonique": "Test Editions",
                "tome": 20,
            }
        )
        # create() auto-creates a default edition (fr/cartonne)
        self.assertEqual(work.nb_editions, 1)
        self.env["comic.edition"].create({"work_id": work.id, "langue": "nl"})
        self.env["comic.edition"].create({"work_id": work.id, "langue": "en"})
        self.assertEqual(work.nb_editions, 3)

    # ── Façade album : création en une étape, édition principale, suppression ─

    def test_create_with_edition_fields_in_one_step(self):
        editeur = self.env["comic.editeur"].create({"name": "Éditeur Test"})
        work = self.env["comic.work"].create(
            {
                "serie_id": self.serie.id,
                "titre_canonique": "Création directe",
                "tome": 31,
                "editeur_id": editeur.id,
                "nb_pages": 46,
                "synopsis": "<p>Résumé</p>",
                "isbn_ids": [(0, 0, {"isbn_13": "9782800152851"})],
            }
        )
        self.assertEqual(len(work.edition_ids), 1)
        self.assertEqual(work.editeur_id, editeur)
        self.assertEqual(work.nb_pages, 46)
        self.assertIn("Résumé", work.synopsis)
        self.assertEqual(work.isbn_ids.isbn_13, "9782800152851")
        self.assertEqual(work.primary_edition_id.langue, "fr", "Défaut conservé")

    def test_primary_edition_is_stable(self):
        from datetime import date

        work = self.env["comic.work"].create({"serie_id": self.serie.id, "titre_canonique": "Stable", "tome": 32})
        first = work.primary_edition_id
        first.date_parution = date(2020, 1, 1)
        self.env["comic.edition"].create({"work_id": work.id, "date_parution": date(1990, 1, 1)})
        self.assertEqual(work.primary_edition_id, first)

    def test_unlink_album_with_auto_edition(self):
        work = self.env["comic.work"].create({"serie_id": self.serie.id, "titre_canonique": "À supprimer", "tome": 33})
        edition = work.edition_ids
        work.unlink()
        self.assertFalse(work.exists())
        self.assertFalse(edition.exists())

    def test_unlink_blocked_by_loan(self):
        from odoo.exceptions import UserError

        work = self.env["comic.work"].create({"serie_id": self.serie.id, "titre_canonique": "Prêté", "tome": 34})
        partner = self.env["res.partner"].create({"name": "Emprunteur"})
        self.env["comic.pret"].create({"edition_id": work.edition_ids.id, "partner_id": partner.id})
        with self.assertRaises(UserError):
            work.unlink()
