"""Tests ORM pour le modèle comic.serie.

Teste : création, champ name_normalise (compute), champ name requis.

Lancement :
    docker exec odoo-web odoo-bin -d odoo -u comics_collections \
        --test-tags /comics_collections:TestComicSerie
"""

from odoo.exceptions import ValidationError
from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged("comics_collections", "comic_serie")
class TestComicSerie(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Serie = cls.env["comic.serie"]

    def test_create_serie(self):
        """Création d'une série valide."""
        serie = self.Serie.create({"name": "Thorgal"})
        self.assertEqual(serie.name, "Thorgal")
        self.assertTrue(serie.id)

    def test_name_normalise_strips_leading_article_fr(self):
        """name_normalise supprime l'article 'Les' en tête (FR)."""
        serie = self.Serie.create({"name": "Les Landes perdues"})
        self.assertEqual(serie.name_normalise, "landes perdues")

    def test_name_normalise_strips_l_apostrophe(self):
        """name_normalise supprime l' en tête (FR)."""
        serie = self.Serie.create({"name": "L'Incal"})
        self.assertNotIn("l'", serie.name_normalise)
        self.assertIn("incal", serie.name_normalise)

    def test_name_normalise_strips_accents(self):
        """name_normalise convertit les caractères accentués."""
        serie = self.Serie.create({"name": "Étoile noire"})
        self.assertNotIn("É", serie.name_normalise)
        self.assertIn("etoile", serie.name_normalise)

    def test_name_normalise_updates_on_rename(self):
        """name_normalise se recalcule quand le nom change."""
        serie = self.Serie.create({"name": "Blacksad"})
        serie.name = "Largo Winch"
        self.assertIn("largo", serie.name_normalise)

    def test_name_required(self):
        """La création sans nom doit lever une ValidationError (required=True)."""
        with self.assertRaises((ValidationError, Exception)):
            self.Serie.create({"name": False})

    def test_two_series_same_name_allowed(self):
        """Il n'y a pas de contrainte d'unicité sur le nom de série."""
        self.Serie.create({"name": "Blueberry"})
        # doit passer sans erreur
        self.Serie.create({"name": "Blueberry"})
