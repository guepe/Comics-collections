"""Portail : « Découvrir de nouvelles BD » (US-029) — page, isolation, limite, création modérée."""

import json
import types
from unittest.mock import patch

from odoo import http
from odoo.tests import HttpCase, new_test_user, tagged

from odoo.addons.comic_ai.tests.common import configure_ai, make_fake_sdk, patch_sdk
from odoo.addons.comic_ai.wizards.comic_ai_discovery_wizard import ComicAiDiscoveryLine
from odoo.addons.comic_datasource.sources.base import ComicSourceResult

ISBN_T1 = "9782205049428"


def _reply(*titles):
    return json.dumps(
        {"suggestions": [{"titre": t, "auteurs": "Auteur", "genre": "Aventure", "raison": "Pour vous"} for t in titles]}
    )


@tagged("post_install", "-at_install", "comic_ai_shop", "portal_discover")
class TestPortalDiscover(HttpCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = new_test_user(cls.env, login="portal_discover", groups="base.group_portal")
        cls.other = new_test_user(cls.env, login="portal_discover_other", groups="base.group_portal")
        cls.liked = cls.env["comic.serie"].create({"name": "Série Préférée Portail"})
        cls.other_serie = cls.env["comic.serie"].create({"name": "Série Autre Client"})
        cls.catalog = cls.env["comic.serie"].create({"name": "Série Catalogue Existante"})
        cls.catalog_t1 = cls.env["comic.work"].create(
            {"serie_id": cls.catalog.id, "titre_canonique": "Catalogue T1", "tome": 1}
        )
        cls._entry(cls.user, cls.liked, note=5)
        cls._entry(cls.other, cls.other_serie, note=5)

    @classmethod
    def _entry(cls, user, serie, note):
        work = cls.env["comic.work"].create({"serie_id": serie.id, "titre_canonique": "%s T1" % serie.name, "tome": 1})
        return cls.env["comic.customer.album"].create(
            {"partner_id": user.partner_id.id, "edition_id": work.primary_edition_id.id, "note": note}
        )

    def setUp(self):
        super().setUp()
        configure_ai(self.env)

    def _post(self, path, **data):
        data["csrf_token"] = http.Request.csrf_token(self)
        return self.url_open("/my/library/discover" + path, data=data)

    def _suggest(self, sdk, serie_ids=None):
        serie_ids = [self.liked.id] if serie_ids is None else serie_ids
        with patch_sdk(self.env, sdk):
            return self._post("/suggest", serie_ids=serie_ids)

    def _lines(self, user):
        return self.env["comic.ai.discovery.line"].search([("wizard_id.partner_id", "=", user.partner_id.id)])

    def _wishlist(self, user):
        return self.env["comic.customer.album"].search(
            [("partner_id", "=", user.partner_id.id), ("dans_wishlist", "=", True)]
        )

    def test_login_required(self):
        response = self.url_open("/my/library/discover")
        self.assertIn("/web/login", response.url)

    def test_page_and_library_button(self):
        self.authenticate("portal_discover", "portal_discover")
        self.assertIn('href="/my/library/discover"', self.url_open("/my/library").text)
        page = self.url_open("/my/library/discover")
        self.assertEqual(page.status_code, 200)
        self.assertIn("Série Préférée Portail", page.text)
        self.assertNotIn("Série Autre Client", page.text)
        self.assertIn("5 recherche(s) restante(s)", page.text)

    def test_suggest_verify_and_add_with_moderation(self):
        self.authenticate("portal_discover", "portal_discover")
        response = self._suggest(
            make_fake_sdk(_reply("Série Préférée Portail", "Nouvelle Série IA", "Série Catalogue Existante"))
        )
        self.assertIn("Nouvelle Série IA", response.text)
        self.assertIn("Vérifier sur les sources", response.text)
        lines = self._lines(self.user)
        self.assertEqual(lines.mapped("name"), ["Nouvelle Série IA", "Série Catalogue Existante"])
        new_line, catalog_line = lines

        result = ComicSourceResult(
            source="google", title="Le Début", serie_name="Nouvelle Série IA", tome=1, isbn=ISBN_T1, editeur="Casterman"
        )
        aggregator = types.SimpleNamespace(search_list=lambda title, author=None: [result])
        with patch.object(ComicAiDiscoveryLine, "_get_aggregator", lambda self: aggregator):
            response = self._post("/verify", verify_line_id=new_line.id)
        self.assertIn("Trouvée sur Google Books", response.text)

        response = self._post("/add", line_ids=[new_line.id, catalog_line.id])
        self.assertIn("2 série(s) ajoutée(s)", response.text)
        serie = self.env["comic.serie"].search([("name", "=", "Nouvelle Série IA")])
        self.assertTrue(serie.a_valider, "Série créée depuis le portail : à valider")
        self.assertEqual(serie.portal_partner_id, self.user.partner_id)
        work = serie.work_ids
        self.assertEqual((work.tome, work.titre_canonique, work.a_valider), (1, "Le Début", True))
        self.assertEqual(work.primary_edition_id.isbn_ids.isbn_13, ISBN_T1)
        self.assertEqual(work.primary_edition_id.editeur_id.name, "Casterman")
        wishlist = self._wishlist(self.user)
        self.assertIn(work.primary_edition_id, wishlist.edition_id)
        self.assertIn(self.catalog_t1.primary_edition_id, wishlist.edition_id)
        self.assertFalse(wishlist.filtered("dans_collection"))
        self.assertFalse(self.catalog.a_valider, "Une série existante n'est pas modifiée")

    def test_daily_limit(self):
        self.env["ir.config_parameter"].sudo().set_param("comic_ai.discovery_daily_limit", "1")
        self.authenticate("portal_discover", "portal_discover")
        self._suggest(make_fake_sdk(_reply("Nouvelle Série IA")))
        sdk = make_fake_sdk(_reply("Autre Série IA"))
        response = self._suggest(sdk)
        self.assertFalse(sdk.calls, "Limite atteinte : aucun appel IA")
        self.assertIn("limite de 1 recherches", response.text)
        self.assertIn("Limite quotidienne atteinte", response.text)
        # Un autre client garde son quota
        self.assertEqual(self.other.partner_id._comic_ai_discovery_remaining(), 1)

    def test_ai_error_is_clear(self):
        self.authenticate("portal_discover", "portal_discover")
        response = self._suggest(make_fake_sdk(raise_exc="APITimeoutError"))
        self.assertIn("Délai dépassé", response.text)

    def test_empty_profile(self):
        self.authenticate("portal_discover", "portal_discover")
        sdk = make_fake_sdk(_reply("X"))
        # Série d'un autre client : hors de la bibliothèque, ignorée → profil vide
        response = self._suggest(sdk, serie_ids=[self.other_serie.id])
        self.assertIn("notez au moins une BD 4★", response.text)
        self.assertFalse(sdk.calls)
        self.assertEqual(self.user.partner_id._comic_ai_discovery_remaining(), 5, "Pas d'appel, pas de quota consommé")

    def test_isolation_between_customers(self):
        self.authenticate("portal_discover", "portal_discover")
        self._suggest(make_fake_sdk(_reply("Nouvelle Série IA")))
        line = self._lines(self.user)
        self.authenticate("portal_discover_other", "portal_discover_other")
        page = self.url_open("/my/library/discover")
        self.assertNotIn("Nouvelle Série IA", page.text)
        response = self._post("/add", line_ids=[line.id])
        self.assertIn("expiré", response.text)
        self._post("/verify", verify_line_id=line.id)
        self.assertEqual(line.verify_state, "todo")
        self.assertFalse(line.added)
        self.assertFalse(self._wishlist(self.other))

    def test_csrf_required(self):
        self.authenticate("portal_discover", "portal_discover")
        sdk = make_fake_sdk(_reply("X"))
        with patch_sdk(self.env, sdk):
            response = self.url_open("/my/library/discover/suggest", data={"serie_ids": [self.liked.id]})
        self.assertEqual(response.status_code, 400)
        self.assertFalse(sdk.calls)
