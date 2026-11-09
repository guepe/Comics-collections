"""Portail /my/library/dashboard : tableau de bord collectionneur (US-065).

Lancement :
    docker exec odoo-web odoo -d odoo -u comic_shop --test-tags /comic_shop:TestPortalDashboard
"""

import re

from odoo.tests import HttpCase, TransactionCase, new_test_user, tagged


@tagged("post_install", "-at_install", "comic_shop", "portal_dashboard")
class TestPortalDashboard(HttpCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.login = "comic_portal_dash"
        cls.user = new_test_user(cls.env, login=cls.login, groups="base.group_portal")
        cls.partner = cls.user.partner_id
        cls.other_login = "comic_portal_dash_other"
        cls.other_user = new_test_user(cls.env, login=cls.other_login, groups="base.group_portal")

        genre = cls.env["comic.genre"].create({"name": "Genre Tableau Bord"})
        Serie = cls.env["comic.serie"]
        Work = cls.env["comic.work"]
        cls.serie_full = Serie.create({"name": "Série Dash Complète", "genre_id": genre.id})
        cls.serie_partial = Serie.create({"name": "Série Dash Partielle"})
        cls.serie_other = Serie.create({"name": "Série Dash Voisin"})
        full = Work.create(
            [{"serie_id": cls.serie_full.id, "titre_canonique": "Dash Complet %d" % i, "tome": i} for i in (1, 2)]
        )
        partial = Work.create(
            [{"serie_id": cls.serie_partial.id, "titre_canonique": "Dash Partiel %d" % i, "tome": i} for i in (1, 2, 3)]
        )
        other = Work.create({"serie_id": cls.serie_other.id, "titre_canonique": "Dash Voisin Secret", "tome": 1})

        Album = cls.env["comic.customer.album"]
        # Utilisateur testé : 3 albums possédés (série complète + 1 tome), 1 en wishlist
        cls.owned = Album.create(
            [
                {"partner_id": cls.partner.id, "edition_id": full[0].primary_edition_id.id, "note": 4.0},
                {
                    "partner_id": cls.partner.id,
                    "edition_id": full[1].primary_edition_id.id,
                    "note": 5.0,
                    "etat_lecture": "lu",
                },
                {"partner_id": cls.partner.id, "edition_id": partial[0].primary_edition_id.id},
            ]
        )
        Album.create(
            {
                "partner_id": cls.partner.id,
                "edition_id": partial[1].primary_edition_id.id,
                "dans_collection": False,
                "dans_wishlist": True,
            }
        )
        # Autre utilisateur : ses données ne doivent jamais apparaître
        Album.create(
            {"partner_id": cls.other_user.partner_id.id, "edition_id": other.primary_edition_id.id, "note": 3.0}
        )

    def _kpi(self, html, key):
        match = re.search(r'data-kpi="%s"[^>]*>\s*(\d+)\s*<' % key, html)
        self.assertTrue(match, "Tuile KPI %s absente" % key)
        return int(match.group(1))

    def test_dashboard_shows_user_figures(self):
        self.authenticate(self.login, self.login)
        resp = self.url_open("/my/library/dashboard")
        self.assertEqual(resp.status_code, 200)
        html = resp.text
        self.assertEqual(self._kpi(html, "nb_albums"), 3)
        self.assertEqual(self._kpi(html, "nb_wishlist"), 1)
        self.assertEqual(self._kpi(html, "series_completes"), 1)
        self.assertEqual(self._kpi(html, "series_en_cours"), 1)
        # Barres : genre (2 albums sur 3 → 67 %) et « Sans genre »
        self.assertIn("Genre Tableau Bord", html)
        self.assertIn("width: 67%", html)
        self.assertIn("Sans genre", html)
        self.assertIn("o_comic_bar_lu", html)
        # Top séries (moyenne 4,5) et derniers ajouts avec lien vers l'entrée
        self.assertIn("Série Dash Complète", html)
        self.assertIn("4.5", html)
        self.assertIn('href="/my/library/%d"' % self.owned[0].id, html)
        self.assertNotIn("o_comic_dashboard_empty", html)

    def test_dashboard_isolated_from_other_users(self):
        self.authenticate(self.login, self.login)
        html = self.url_open("/my/library/dashboard").text
        self.assertNotIn("Dash Voisin Secret", html)
        self.assertNotIn("Série Dash Voisin", html)

        self.authenticate(self.other_login, self.other_login)
        resp = self.url_open("/my/library/dashboard")
        self.assertEqual(resp.status_code, 200)
        html = resp.text
        self.assertEqual(self._kpi(html, "nb_albums"), 1)
        self.assertEqual(self._kpi(html, "nb_wishlist"), 0)
        self.assertIn("Série Dash Voisin", html)
        self.assertNotIn("Série Dash Complète", html)

    def test_dashboard_requires_login(self):
        resp = self.url_open("/my/library/dashboard", allow_redirects=False)
        self.assertIn(resp.status_code, (302, 303))
        self.assertIn("/web/login", resp.headers.get("Location", ""))

    def test_dashboard_empty_state(self):
        new_test_user(self.env, login="comic_portal_dash_empty", groups="base.group_portal")
        self.authenticate("comic_portal_dash_empty", "comic_portal_dash_empty")
        resp = self.url_open("/my/library/dashboard")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("o_comic_dashboard_empty", resp.text)
        self.assertIn('href="/my/library/add"', resp.text)
        self.assertNotIn('data-kpi="nb_albums"', resp.text)

    def test_dashboard_links(self):
        self.authenticate(self.login, self.login)
        self.assertIn('href="/my/library/dashboard"', self.url_open("/my/library").text)
        self.assertIn('href="/my/library/dashboard"', self.url_open("/my").text)

    def test_home_library_card_counts_owned_albums(self):
        """La carte « Ma Bibliothèque BD » de /my affiche le vrai nombre (3 possédés, wishlist exclue)."""
        self.authenticate(self.login, self.login)
        html = self.url_open("/my").text
        self.assertRegex(html, r"\b3\s*</t>\s*album|\b3 album")

    def test_my_counters_returns_only_requested_keys(self):
        """/my/counters ne renvoie que les compteurs demandés : un compteur en trop fait
        planter portal_home_counters (« Cannot set properties of null (textContent) »)."""
        self.authenticate(self.login, self.login)
        result = self.make_jsonrpc_request("/my/counters", {"counters": ["quotation_count"]})
        self.assertNotIn("library_count", result)
        self.assertLessEqual(set(result), {"quotation_count"})
        result = self.make_jsonrpc_request("/my/counters", {"counters": ["library_count"]})
        self.assertEqual(result.get("library_count"), 3)

    def test_site_menu_ma_collection(self):
        """Menu « Ma collection » du site et liens du menu du compte : connectés uniquement."""
        self.authenticate(self.login, self.login)
        html = self.url_open("/shop").text
        self.assertIn("Ma collection", html)
        self.assertIn('href="/my/library/dashboard"', html)  # menu du compte
        self.assertIn("Ma bibliothèque BD", html)
        self.authenticate(None, None)
        self.assertNotIn('href="/my/library/dashboard"', self.url_open("/shop").text)


@tagged("post_install", "-at_install", "comic_shop")
class TestShopCatalogueMenus(TransactionCase):
    def test_full_catalogue_menus_for_comic_users(self):
        """Avec le shop, le catalogue complet est ouvert aux utilisateurs BD (pas seulement au gestionnaire)."""
        user = new_test_user(self.env, login="shop_cat_user", groups="comics_collections.group_comic_user")
        menus = self.env["ir.ui.menu"].with_user(user)._visible_menu_ids()
        for xmlid in ("comic_shop.menu_comic_shop_catalogue_albums", "comic_shop.menu_comic_shop_catalogue_series"):
            self.assertIn(self.env.ref(xmlid).id, menus)
        self.assertNotIn(self.env.ref("comics_collections.menu_comic_referentiel_albums").id, menus)
