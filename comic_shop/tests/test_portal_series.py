"""Portail : suivre / ne plus suivre une série (US-069)."""

from odoo import http
from odoo.tests import HttpCase, new_test_user, tagged


@tagged("post_install", "-at_install", "comic_shop", "portal_series")
class TestPortalSeries(HttpCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = new_test_user(cls.env, login="portal_series", groups="base.group_portal")
        cls.other = new_test_user(cls.env, login="portal_series_other", groups="base.group_portal")
        cls.serie = cls.env["comic.serie"].create({"name": "Série Portail Suivie"})
        cls.library_serie = cls.env["comic.serie"].create({"name": "Série De Ma Bibliothèque"})
        work = cls.env["comic.work"].create(
            {"serie_id": cls.library_serie.id, "titre_canonique": "Album possédé", "tome": 1}
        )
        cls.entry = cls.env["comic.customer.album"].create(
            {"partner_id": cls.user.partner_id.id, "edition_id": work.primary_edition_id.id}
        )

    def _follow(self, serie, follow, redirect="/my/library/series"):
        return self.url_open(
            f"/my/library/series/{serie.id}/follow",
            data={"csrf_token": http.Request.csrf_token(self), "follow": follow, "redirect": redirect},
        )

    def test_follow_unfollow_and_list(self):
        self.authenticate("portal_series", "portal_series")
        response = self.url_open("/my/library/series")
        self.assertEqual(response.status_code, 200)
        # Séries de la bibliothèque proposées, non suivies (pas de suivi automatique au portail)
        self.assertIn("Série De Ma Bibliothèque", response.text)
        self.assertNotIn("Série Portail Suivie", response.text)

        response = self._follow(self.serie, "1")
        self.assertEqual(response.status_code, 200)
        self.assertIn(self.user, self.serie.suivi_user_ids)
        self.assertIn("Série Portail Suivie", response.text)
        self.assertIn("Série suivie", response.text)

        self.serie.suivi_user_ids |= self.other
        self._follow(self.serie, "0")
        self.assertNotIn(self.user, self.serie.suivi_user_ids)
        self.assertIn(self.user, self.serie.suivi_exclu_user_ids)
        self.assertIn(self.other, self.serie.suivi_user_ids, "Seul l'utilisateur courant est désabonné")

    def test_buttons_on_shop_and_library_pages(self):
        response = self.url_open(f"/shop/series/{self.serie.id}")
        self.assertIn("/web/login?redirect=/shop/series/%s" % self.serie.id, response.text)
        self.authenticate("portal_series", "portal_series")
        response = self.url_open(f"/shop/series/{self.serie.id}")
        self.assertIn(f"/my/library/series/{self.serie.id}/follow", response.text)
        response = self.url_open(f"/my/library/{self.entry.id}")
        self.assertIn(f"/my/library/series/{self.library_serie.id}/follow", response.text)
        self.assertIn('href="/my/library/series"', self.url_open("/my/library").text)

    def test_no_open_redirect(self):
        self.authenticate("portal_series", "portal_series")
        response = self._follow(self.serie, "1", redirect="//evil.example.com/x")
        self.assertTrue(response.url.endswith("/my/library/series"))
