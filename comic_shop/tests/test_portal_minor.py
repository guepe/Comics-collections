"""Portail /my/library : tri robuste, pagination, messages de filtre vide.

Lancement :
    docker exec odoo-web odoo -d odoo -u comic_shop --test-tags /comic_shop:TestPortalMinor
"""

import re

from odoo import http
from odoo.tests import HttpCase, new_test_user, tagged


@tagged("post_install", "-at_install", "comic_shop", "portal_minor")
class TestPortalMinor(HttpCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.login = "comic_portal_minor"
        cls.user = new_test_user(cls.env, login=cls.login, groups="base.group_portal")
        cls.partner = cls.user.partner_id
        cls.serie = cls.env["comic.serie"].create({"name": "Série Portail Minor"})
        works = cls.env["comic.work"].create(
            [{"serie_id": cls.serie.id, "titre_canonique": "Album Minor %d" % i, "tome": i} for i in range(1, 31)]
        )
        cls.Album = cls.env["comic.customer.album"]
        cls.editions = works.mapped("primary_edition_id")

    def _add_albums(self, count, **vals):
        albums = self.Album.create(
            [{"partner_id": self.partner.id, "edition_id": e.id, **vals} for e in self.editions[:count]]
        )
        return albums

    def test_sort_by_date_with_empty_dates(self):
        albums = self._add_albums(4)
        albums[:2].write({"date_ajout": False})
        self.authenticate(self.login, self.login)
        resp = self.url_open("/my/library?sort=date")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("Album Minor 1", resp.text)
        self.assertIn("Album Minor 4", resp.text)

    def test_pagination_second_page(self):
        self._add_albums(30)
        self.authenticate(self.login, self.login)
        resp = self.url_open("/my/library?sort=serie&page=2")
        self.assertEqual(resp.status_code, 200)
        # Tri par série/tome : la page 2 contient les tomes 25 à 30
        self.assertIn("Album Minor 30", resp.text)
        self.assertIsNone(re.search(r"Album Minor 1\b", resp.text))
        resp = self.url_open("/my/library/page/2?sort=serie")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("Album Minor 30", resp.text)

    def test_wishlist_filter_empty_message(self):
        self._add_albums(2, dans_collection=True, dans_wishlist=False)
        self.authenticate(self.login, self.login)
        resp = self.url_open("/my/library?filter=wishlist")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("Aucun album dans votre wishlist", resp.text)
        self.assertIn("Tout voir", resp.text)
        self.assertNotIn("Votre bibliothèque est vide", resp.text)

    def test_empty_library_message(self):
        self.authenticate(self.login, self.login)
        resp = self.url_open("/my/library")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("Votre bibliothèque est vide", resp.text)

    def _confirm_add(self, edition, ajouter_a):
        return self.url_open(
            "/my/library/add/confirm",
            data={
                "edition_id": edition.id,
                "ajouter_a": ajouter_a,
                "force_update": "1",
                "csrf_token": http.Request.csrf_token(self),
            },
        )

    def test_wishlist_keeps_owned_album_in_collection(self):
        album = self._add_albums(1, dans_collection=True, dans_wishlist=False)
        self.authenticate(self.login, self.login)
        resp = self._confirm_add(album.edition_id, "wishlist")
        self.assertEqual(resp.status_code, 200)
        album.invalidate_recordset()
        self.assertTrue(album.dans_collection)
        self.assertTrue(album.dans_wishlist)

    def test_collection_removes_album_from_wishlist(self):
        album = self._add_albums(1, dans_collection=False, dans_wishlist=True)
        self.authenticate(self.login, self.login)
        self._confirm_add(album.edition_id, "collection")
        album.invalidate_recordset()
        self.assertTrue(album.dans_collection)
        self.assertFalse(album.dans_wishlist)
