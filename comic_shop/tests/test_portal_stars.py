"""Portail /my/library : saisie de la note en étoiles (US-067).

Lancement :
    docker exec odoo-web odoo -d odoo -u comic_shop --test-tags /comic_shop:TestPortalStars
"""

from odoo import http
from odoo.tests import HttpCase, new_test_user, tagged


@tagged("post_install", "-at_install", "comic_shop", "portal_stars")
class TestPortalStars(HttpCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.login = "comic_portal_stars"
        cls.user = new_test_user(cls.env, login=cls.login, groups="base.group_portal")
        cls.partner = cls.user.partner_id
        serie = cls.env["comic.serie"].create({"name": "Série Portail Étoiles"})
        work = cls.env["comic.work"].create({"serie_id": serie.id, "titre_canonique": "Album Étoiles", "tome": 1})
        cls.album = cls.env["comic.customer.album"].create(
            {"partner_id": cls.partner.id, "edition_id": work.primary_edition_id.id, "note": 3.0}
        )

    def test_detail_page_renders_star_radios(self):
        self.authenticate(self.login, self.login)
        resp = self.url_open(f"/my/library/{self.album.id}")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("o_comic_star_rating", resp.text)
        self.assertIn(f'id="note-edit-{self.album.id}-3" checked="checked"', resp.text)
        self.assertNotIn('type="number" name="note"', resp.text)

    def test_update_with_integer_note(self):
        self.authenticate(self.login, self.login)
        resp = self.url_open(
            f"/my/library/{self.album.id}/update",
            data={
                "etat_lecture": "lu",
                "dans_collection": "1",
                "note": "4",
                "csrf_token": http.Request.csrf_token(self),
            },
        )
        self.assertEqual(resp.status_code, 200)
        self.album.invalidate_recordset()
        self.assertEqual(self.album.note, 4.0)
        self.assertEqual(self.album.note_etoiles, "4")

    def test_update_with_zero_clears_note(self):
        self.authenticate(self.login, self.login)
        self.url_open(
            f"/my/library/{self.album.id}/update",
            data={"dans_collection": "1", "note": "0", "csrf_token": http.Request.csrf_token(self)},
        )
        self.album.invalidate_recordset()
        self.assertEqual(self.album.note, 0.0)
