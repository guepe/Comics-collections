"""Tests ORM pour le modèle comic.edition.

Teste : création liée à un work, éditions multiples par work, édition sans ISBN,
nb_isbn, display_name et génération des liens d'achat.

Lancement :
    docker exec odoo-web odoo-bin -d odoo -u comics_collections \
        --test-tags /comics_collections:TestComicEdition
"""

from odoo.tests.common import TransactionCase
from odoo.tests import tagged


@tagged("comics_collections", "comic_edition")
class TestComicEdition(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.serie = cls.env["comic.serie"].create({"name": "Blacksad"})
        cls.editeur = cls.env["comic.editeur"].create({"name": "Dargaud"})
        cls.work = cls.env["comic.work"].create(
            {
                "serie_id": cls.serie.id,
                "titre_canonique": "Quelque part entre les ombres",
                "tome": 1,
            }
        )

    # ── Création et lien work ─────────────────────────────────────────────────

    def test_create_edition_linked_to_work(self):
        edition = self.env["comic.edition"].create(
            {
                "work_id": self.work.id,
                "langue": "fr",
                "format": "cartonne",
            }
        )
        self.assertEqual(edition.work_id, self.work)
        self.assertIn(edition, self.work.edition_ids)

    def test_multiple_editions_per_work(self):
        ed_fr = self.env["comic.edition"].create({"work_id": self.work.id, "langue": "fr"})
        ed_nl = self.env["comic.edition"].create({"work_id": self.work.id, "langue": "nl"})
        ed_col = self.env["comic.edition"].create(
            {
                "work_id": self.work.id,
                "langue": "fr",
                "format": "collector",
            }
        )
        editions = self.work.edition_ids
        self.assertGreaterEqual(len(editions), 3)
        self.assertIn(ed_fr, editions)
        self.assertIn(ed_nl, editions)
        self.assertIn(ed_col, editions)

    # ── ISBN facultatif ───────────────────────────────────────────────────────

    def test_edition_without_isbn_is_valid(self):
        edition = self.env["comic.edition"].create(
            {
                "work_id": self.work.id,
                "langue": "en",
            }
        )
        self.assertFalse(edition.isbn_ids)
        self.assertEqual(edition.nb_isbn, 0)

    def test_nb_isbn_updates_on_add(self):
        edition = self.env["comic.edition"].create(
            {
                "work_id": self.work.id,
                "langue": "fr",
                "editeur_id": self.editeur.id,
            }
        )
        self.assertEqual(edition.nb_isbn, 0)
        self.env["comic.isbn"].create(
            {
                "edition_id": edition.id,
                "isbn_13": "9782012101340",
            }
        )
        self.assertEqual(edition.nb_isbn, 1)

    def test_nb_isbn_updates_on_remove(self):
        edition = self.env["comic.edition"].create(
            {
                "work_id": self.work.id,
                "langue": "fr",
            }
        )
        isbn = self.env["comic.isbn"].create(
            {
                "edition_id": edition.id,
                "isbn_13": "9782012101395",
            }
        )
        self.assertEqual(edition.nb_isbn, 1)
        isbn.unlink()
        self.assertEqual(edition.nb_isbn, 0)

    # ── display_name ─────────────────────────────────────────────────────────

    def test_display_name_includes_work_name(self):
        edition = self.env["comic.edition"].create(
            {
                "work_id": self.work.id,
                "langue": "fr",
                "editeur_id": self.editeur.id,
            }
        )
        self.assertIn("Blacksad", edition.display_name)

    def test_display_name_includes_langue_label(self):
        edition = self.env["comic.edition"].create(
            {
                "work_id": self.work.id,
                "langue": "fr",
            }
        )
        self.assertIn("Français", edition.display_name)

    def test_display_name_includes_editeur(self):
        edition = self.env["comic.edition"].create(
            {
                "work_id": self.work.id,
                "langue": "fr",
                "editeur_id": self.editeur.id,
            }
        )
        self.assertIn("Dargaud", edition.display_name)

    # ── Génération liens d'achat ──────────────────────────────────────────────

    def test_purchase_links_generated_from_isbn(self):
        edition = self.env["comic.edition"].create(
            {
                "work_id": self.work.id,
                "langue": "fr",
            }
        )
        self.env["comic.isbn"].create(
            {
                "edition_id": edition.id,
                "isbn_13": "9782012101340",
            }
        )
        edition.action_generate_purchase_links()
        self.assertIn("9782012101340", edition.url_amazon_be or "")
        self.assertIn("9782012101340", edition.url_fnac_be or "")
        self.assertIn("9782012101340", edition.url_club_be or "")

    def test_purchase_links_empty_without_isbn(self):
        edition = self.env["comic.edition"].create(
            {
                "work_id": self.work.id,
                "langue": "fr",
            }
        )
        edition.action_generate_purchase_links()
        self.assertFalse(edition.url_amazon_be)
        self.assertFalse(edition.url_fnac_be)
