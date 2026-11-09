"""Wishlist partageable par lien secret (US-073).

Lancement :
    docker exec odoo-web odoo -d odoo -u comic_shop --test-tags /comic_shop:TestWishlistShare
"""

import base64

from odoo import http
from odoo.tests import HttpCase, new_test_user, tagged

# PNG 1×1 transparent
_PNG = base64.b64encode(
    base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg==")
)


@tagged("post_install", "-at_install", "comic_shop", "wishlist_share")
class TestWishlistShare(HttpCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.login = "comic_wish_share"
        cls.user = new_test_user(cls.env, login=cls.login, groups="base.group_portal", name="Gaston Lagaffe")
        cls.partner = cls.user.partner_id
        cls.partner.email = "gaston.secret@example.com"
        cls.other_login = "comic_wish_share_other"
        cls.other_user = new_test_user(
            cls.env, login=cls.other_login, groups="base.group_portal", name="Jeanne Fantasio"
        )
        cls.other_partner = cls.other_user.partner_id

        serie = cls.env["comic.serie"].create({"name": "Série Wishlist Partagée"})
        Work = cls.env["comic.work"]
        titles = ["Souhait Alpha", "Souhait Beta", "Possédé Gamma", "Voisin Delta"]
        works = Work.create(
            [{"serie_id": serie.id, "titre_canonique": t, "tome": i} for i, t in enumerate(titles, start=1)]
        )
        editions = works.mapped("primary_edition_id")
        editions[0].image_couverture = _PNG
        product = cls.env["product.template"].create({"name": "Produit Souhait Beta", "is_published": True})
        editions[1].product_tmpl_id = product
        cls.product = product

        Album = cls.env["comic.customer.album"]
        cls.wish_alpha, cls.wish_beta, cls.owned = Album.create(
            [
                {
                    "partner_id": cls.partner.id,
                    "edition_id": editions[0].id,
                    "dans_collection": False,
                    "dans_wishlist": True,
                    "commentaire": "Commentaire très privé",
                },
                {
                    "partner_id": cls.partner.id,
                    "edition_id": editions[1].id,
                    "dans_collection": False,
                    "dans_wishlist": True,
                },
                {"partner_id": cls.partner.id, "edition_id": editions[2].id, "dans_collection": True},
            ]
        )
        Album.create(
            {
                "partner_id": cls.other_partner.id,
                "edition_id": editions[3].id,
                "dans_collection": False,
                "dans_wishlist": True,
            }
        )

    # ── helpers ─────────────────────────────────────────────────────────────

    def _post(self, url):
        return self.url_open(url, data={"csrf_token": http.Request.csrf_token(self)})

    def _share_as(self, login, partner):
        self.authenticate(login, login)
        resp = self._post("/my/library/wishlist/share")
        self.assertEqual(resp.status_code, 200)
        partner.invalidate_recordset()
        self.assertTrue(partner.comic_wishlist_shared)
        self.assertTrue(partner.comic_wishlist_token)
        return partner.comic_wishlist_token

    def _open_anonymous(self, url):
        self.authenticate(None, None)
        return self.url_open(url)

    # ── tests ───────────────────────────────────────────────────────────────

    def test_share_then_anonymous_view(self):
        token = self._share_as(self.login, self.partner)
        # Le lien complet et le bouton de révocation sont affichés sur /my/library
        resp = self.url_open("/my/library")
        self.assertIn("/wishlist/%s" % token, resp.text)
        self.assertIn("Révoquer le lien", resp.text)
        # Bouton « Copier » piloté par portal_wishlist_copy.js (plus de JS inline)
        self.assertIn("o_comic_wishlist_copy_btn", resp.text)
        self.assertNotIn("navigator.clipboard", resp.text)

        resp = self._open_anonymous("/wishlist/%s" % token)
        self.assertEqual(resp.status_code, 200)
        html = resp.text
        self.assertIn("La wishlist BD de Gaston", html)
        self.assertIn("Souhait Alpha", html)
        self.assertIn("Souhait Beta", html)
        self.assertIn('name="robots" content="noindex"', html)
        # Produit publié : lien boutique ; couverture servie via la route contrôlée
        self.assertIn("Voir dans la boutique", html)
        self.assertIn(self.product.website_url, html)
        self.assertIn("/wishlist/%s/cover/%d" % (token, self.wish_alpha.id), html)

    def test_no_other_data_exposed(self):
        token = self._share_as(self.login, self.partner)
        html = self._open_anonymous("/wishlist/%s" % token).text
        self.assertNotIn("Possédé Gamma", html)
        self.assertNotIn("gaston.secret@example.com", html)
        self.assertNotIn("Commentaire très privé", html)
        self.assertNotIn("Lagaffe", html)

    def test_cover_route_restricted_to_shared_wishlist(self):
        token = self._share_as(self.login, self.partner)
        self.authenticate(None, None)
        resp = self.url_open("/wishlist/%s/cover/%d" % (token, self.wish_alpha.id))
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.headers.get("Content-Type", "").startswith("image/"))
        # Album de la collection (hors wishlist) : refusé
        resp = self.url_open("/wishlist/%s/cover/%d" % (token, self.owned.id))
        self.assertEqual(resp.status_code, 404)

    def test_revoke_then_reshare_gives_new_token(self):
        token = self._share_as(self.login, self.partner)
        resp = self._post("/my/library/wishlist/revoke")
        self.assertEqual(resp.status_code, 200)
        self.partner.invalidate_recordset()
        self.assertFalse(self.partner.comic_wishlist_shared)
        self.assertFalse(self.partner.comic_wishlist_token)
        self.assertIn("Créer un lien de partage", self.url_open("/my/library").text)

        self.assertEqual(self._open_anonymous("/wishlist/%s" % token).status_code, 404)

        new_token = self._share_as(self.login, self.partner)
        self.assertNotEqual(token, new_token)
        self.assertEqual(self._open_anonymous("/wishlist/%s" % token).status_code, 404)
        self.assertEqual(self._open_anonymous("/wishlist/%s" % new_token).status_code, 200)

    def test_unknown_token_404(self):
        self.assertEqual(self._open_anonymous("/wishlist/jeton-invente-123").status_code, 404)
        self.assertEqual(self._open_anonymous("/wishlist/jeton-invente-123/cover/1").status_code, 404)

    def test_copy_script_in_frontend_bundle(self):
        paths = [p[0] for p in self.env["ir.asset"]._get_asset_paths("web.assets_frontend", {})]
        self.assertIn("/comic_shop/static/src/js/portal_wishlist_copy.js", paths)
        bundle = self.env["ir.qweb"]._get_asset_bundle("web.assets_frontend", css=False, js=True, debug_assets=True)
        self.assertIn("@comic_shop/js/portal_wishlist_copy", bundle.js().raw.decode())

    def test_shared_flag_without_token_404(self):
        self.partner.write({"comic_wishlist_shared": True, "comic_wishlist_token": False})
        self.assertEqual(self._open_anonymous("/wishlist/False").status_code, 404)

    def test_post_routes_require_login(self):
        self.authenticate(None, None)
        for url in ("/my/library/wishlist/share", "/my/library/wishlist/revoke"):
            resp = self.url_open(url, data={"csrf_token": http.Request.csrf_token(self)}, allow_redirects=False)
            self.assertIn(resp.status_code, (302, 303))
            self.assertIn("/web/login", resp.headers.get("Location", ""))
        self.partner.invalidate_recordset()
        self.assertFalse(self.partner.comic_wishlist_shared)

    def test_two_partners_each_see_own_wishlist(self):
        token = self._share_as(self.login, self.partner)
        other_token = self._share_as(self.other_login, self.other_partner)
        self.assertNotEqual(token, other_token)

        html = self._open_anonymous("/wishlist/%s" % token).text
        self.assertIn("Souhait Alpha", html)
        self.assertNotIn("Voisin Delta", html)

        html = self._open_anonymous("/wishlist/%s" % other_token).text
        self.assertIn("La wishlist BD de Jeanne", html)
        self.assertIn("Voisin Delta", html)
        self.assertNotIn("Souhait Alpha", html)
        self.assertNotIn("Souhait Beta", html)

    def test_empty_wishlist_message(self):
        self.wish_alpha.dans_wishlist = False
        self.wish_beta.dans_wishlist = False
        token = self._share_as(self.login, self.partner)
        resp = self._open_anonymous("/wishlist/%s" % token)
        self.assertEqual(resp.status_code, 200)
        self.assertIn("Cette wishlist est vide", resp.text)
