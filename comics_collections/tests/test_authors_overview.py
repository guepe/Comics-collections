"""Auteurs d'une série, co-auteurs d'un auteur (séries cliquables)."""

from odoo import Command
from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install", "comics_collections")
class TestAuthorsOverview(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        Partner = cls.env["res.partner"]
        cls.leo, cls.rodolphe, cls.icar = Partner.create([{"name": "Leo"}, {"name": "Rodolphe"}, {"name": "Icar"}])
        cls.editeur = cls.env["comic.editeur"].create({"name": "Dargaud Test"})
        cls.serie = cls.env["comic.serie"].create({"name": "Aldébaran Test"})

        def work(tome, lines):
            w = cls.env["comic.work"].create(
                {
                    "serie_id": cls.serie.id,
                    "titre_canonique": f"Tome {tome}",
                    "tome": tome,
                    "auteur_line_ids": [Command.create({"partner_id": p.id, "role": r}) for p, r in lines],
                }
            )
            w.primary_edition_id.editeur_id = cls.editeur
            return w

        work(1, [(cls.leo, "scenariste"), (cls.leo, "dessinateur")])
        work(2, [(cls.leo, "scenariste"), (cls.rodolphe, "scenariste"), (cls.icar, "dessinateur")])
        work(3, [(cls.rodolphe, "scenariste"), (cls.leo, "dessinateur")])

    def test_serie_authors_union_with_roles(self):
        self.assertEqual(set(self.serie.auteur_ids), {self.leo, self.rodolphe, self.icar})
        names = self.serie.auteur_names
        self.assertEqual(names.count("Leo"), 1, "Chaque auteur une seule fois")
        self.assertIn("Leo (Scénariste, Dessinateur)", names)
        self.assertIn("Rodolphe (Scénariste)", names)

    def test_coauthors_sorted_by_shared_albums(self):
        html = str(self.leo.comic_coauthors_html)
        self.assertIn("Rodolphe", html)
        self.assertIn("Icar", html)
        self.assertLess(html.index("Rodolphe"), html.index("Icar"), "Rodolphe : 2 albums, Icar : 1")
        self.assertNotIn(">Leo<", html)
        # Auteurs et séries cliquables
        self.assertIn(f"/odoo/res.partner/{self.rodolphe.id}", html)
        self.assertIn(f'/odoo/comic.serie/{self.serie.id}">Aldébaran Test</a>', html)
        self.assertIn("Aucun co-auteur", str(self.env["res.partner"].create({"name": "Solo"}).comic_coauthors_html))
