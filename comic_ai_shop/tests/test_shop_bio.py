"""Biographie / histoire de la maison sur les pages publiques du shop (US-091)."""

from odoo import Command
from odoo.tests import HttpCase, tagged


@tagged("post_install", "-at_install", "comic_ai_shop")
class TestShopBio(HttpCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.auteur = cls.env["res.partner"].create(
            {"name": "Auteur Public", "comic_bio": "<p>Biographie publique.</p>"}
        )
        cls.sans_bio = cls.env["res.partner"].create({"name": "Auteur Sans Bio"})
        cls.editeur = cls.env["comic.editeur"].create(
            {"name": "Maison Publique", "comic_histoire": "<p>Histoire publique.</p>"}
        )
        serie = cls.env["comic.serie"].create({"name": "Série Publique", "editeur_id": cls.editeur.id})
        work = cls.env["comic.work"].create(
            {
                "serie_id": serie.id,
                "titre_canonique": "Album Public",
                "tome": 1,
                "auteur_line_ids": [
                    Command.create({"partner_id": cls.auteur.id, "role": "scenariste"}),
                    Command.create({"partner_id": cls.sans_bio.id, "role": "dessinateur"}),
                ],
            }
        )
        edition = work.primary_edition_id
        edition.editeur_id = cls.editeur
        product = cls.env["product.template"].create({"name": "Album Public", "is_published": True})
        edition.product_tmpl_id = product

    def test_author_page_shows_bio(self):
        html = self.url_open(f"/shop/auteurs/{self.auteur.id}").text
        self.assertIn("Biographie publique.", html)
        self.assertNotIn("o_comic_shop_bio", self.url_open(f"/shop/auteurs/{self.sans_bio.id}").text)

    def test_publisher_page_shows_history(self):
        html = self.url_open(f"/shop/editeurs/{self.editeur.id}").text
        self.assertIn("Histoire publique.", html)
