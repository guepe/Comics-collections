"""Collection privée par défaut (US-087) et suivi automatique des séries (US-088)."""

import importlib.util

from odoo import Command
from odoo.tests import new_test_user, tagged
from odoo.tests.common import TransactionCase
from odoo.tools.misc import file_path
from odoo.tools.safe_eval import safe_eval


@tagged("post_install", "-at_install", "comics_collections")
class TestPrivateCollection(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        groups = "comics_collections.group_comic_user"
        cls.user = new_test_user(cls.env, login="private_user", groups=groups)
        cls.other = new_test_user(cls.env, login="private_other", groups=groups)
        cls.portal = new_test_user(cls.env, login="private_portal", groups="base.group_portal")
        cls.serie_owned = cls.env["comic.serie"].create({"name": "Série Possédée Privée"})
        cls.serie_other = cls.env["comic.serie"].create({"name": "Série Autre Privée"})
        cls.serie_catalogue = cls.env["comic.serie"].create({"name": "Série Catalogue Privée"})
        Work = cls.env["comic.work"]
        cls.work_owned = Work.create({"serie_id": cls.serie_owned.id, "titre_canonique": "Possédé", "tome": 1})
        cls.work_other = Work.create({"serie_id": cls.serie_other.id, "titre_canonique": "À l'autre", "tome": 1})
        cls.work_catalogue = Work.create(
            {"serie_id": cls.serie_catalogue.id, "titre_canonique": "Catalogue", "tome": 1}
        )
        Album = cls.env["comic.customer.album"]
        Album.create({"partner_id": cls.user.partner_id.id, "edition_id": cls.work_owned.primary_edition_id.id})
        Album.create({"partner_id": cls.other.partner_id.id, "edition_id": cls.work_other.primary_edition_id.id})

    def _action_domain(self, xmlid, user):
        action = self.env.ref(xmlid)
        return safe_eval(action.domain, {"uid": user.id})

    def _owns(self, user, work):
        return bool(
            self.env["comic.customer.album"].search_count(
                [
                    ("partner_id", "=", user.partner_id.id),
                    ("edition_id", "=", work.primary_edition_id.id),
                    ("dans_collection", "=", True),
                ]
            )
        )

    # ── US-087 : « Mes albums » / « Mes séries » ────────────────────────────

    def test_my_albums_domain(self):
        action = self.env.ref("comics_collections.action_comic_work")
        self.assertEqual(action.name, "My Albums")
        self.assertNotIn("search_default_ma_collection", action.context)
        self.assertIn("comic_auto_own", action.context)
        domain = self._action_domain("comics_collections.action_comic_work", self.user)
        works = self.env["comic.work"].with_user(self.user).search(domain)
        self.assertIn(self.work_owned, works)
        self.assertNotIn(self.work_catalogue, works)
        self.assertNotIn(self.work_other, works)

    def test_my_series_domain(self):
        action = self.env.ref("comics_collections.action_comic_serie")
        self.assertEqual(action.name, "My Series")
        domain = self._action_domain("comics_collections.action_comic_serie", self.user)
        Serie = self.env["comic.serie"].with_user(self.user)
        series = Serie.search(domain)
        self.assertIn(self.serie_owned, series)
        self.assertNotIn(self.serie_catalogue, series)
        self.assertNotIn(self.serie_other, series)
        # Une série suivie sans album possédé apparaît
        self.serie_catalogue.with_user(self.user).a_suivre = True
        self.assertIn(self.serie_catalogue, Serie.search(domain))

    def test_catalogue_reserved_to_manager(self):
        self.assertFalse(self.env.ref("comics_collections.menu_comic_catalogue_albums", raise_if_not_found=False))
        manager = self.env.ref("comics_collections.group_comic_manager")
        for xmlid in ("menu_comic_referentiel_albums", "menu_comic_referentiel_series"):
            menu = self.env.ref(f"comics_collections.{xmlid}")
            self.assertEqual(menu.parent_id, self.env.ref("comics_collections.menu_comic_catalogues"))
            # Gestionnaire dans le cœur ; comic_shop y ajoute les utilisateurs BD
            self.assertIn(manager, menu.group_ids)
        self.assertFalse(self.env.ref("comics_collections.action_comic_serie_catalogue").domain)

    def test_create_with_auto_own(self):
        Work = self.env["comic.work"].with_user(self.user)
        owned = Work.with_context(comic_auto_own=True).create(
            {"serie_id": self.serie_catalogue.id, "titre_canonique": "Créé possédé", "tome": 2}
        )
        self.assertTrue(self._owns(self.user, owned))
        not_owned = Work.create({"serie_id": self.serie_catalogue.id, "titre_canonique": "Créé libre", "tome": 3})
        self.assertFalse(self._owns(self.user, not_owned))

    def test_auto_own_from_serie_form(self):
        """Inline album created on a series opened from « Mes séries » is owned."""
        serie = self.serie_catalogue.with_user(self.user).with_context(comic_auto_own=True)
        serie.write({"work_ids": [Command.create({"titre_canonique": "En ligne", "tome": 4})]})
        work = self.serie_catalogue.work_ids.filtered(lambda w: w.tome == 4)
        self.assertTrue(self._owns(self.user, work))
        action = serie.action_view_works()
        self.assertTrue(action["context"].get("comic_auto_own"))
        self.assertNotIn("comic_auto_own", self.serie_catalogue.with_user(self.user).action_view_works()["context"])

    # ── US-088 : suivi automatique ──────────────────────────────────────────

    def test_follow_on_serie_creation(self):
        serie = self.env["comic.serie"].with_user(self.user).create({"name": "Série Créée Privée"})
        self.assertEqual(serie.suivi_user_ids, self.user)
        # Superutilisateur / données : pas de suivi
        self.assertFalse(self.env["comic.serie"].create({"name": "Série Données Privée"}).suivi_user_ids)

    def test_follow_on_first_owned_album(self):
        self.assertIn(self.user, self.serie_owned.suivi_user_ids)
        self.assertNotIn(self.user, self.serie_catalogue.suivi_user_ids)
        Album = self.env["comic.customer.album"]
        entry = Album.create(
            {
                "partner_id": self.user.partner_id.id,
                "edition_id": self.work_catalogue.primary_edition_id.id,
                "dans_collection": False,
                "dans_wishlist": True,
            }
        )
        self.assertNotIn(self.user, self.serie_catalogue.suivi_user_ids)
        entry.write({"dans_collection": True})
        self.assertIn(self.user, self.serie_catalogue.suivi_user_ids)

    def test_exclusion(self):
        serie = self.serie_owned.with_user(self.user)
        serie.a_suivre = False
        self.assertNotIn(self.user, self.serie_owned.suivi_user_ids)
        self.assertIn(self.user, self.serie_owned.suivi_exclu_user_ids)
        new_work = self.env["comic.work"].create(
            {"serie_id": self.serie_owned.id, "titre_canonique": "Nouveau", "tome": 2}
        )
        self.env["comic.customer.album"].create(
            {"partner_id": self.user.partner_id.id, "edition_id": new_work.primary_edition_id.id}
        )
        self.assertNotIn(self.user, self.serie_owned.suivi_user_ids)
        serie.a_suivre = True
        self.assertIn(self.user, self.serie_owned.suivi_user_ids)
        self.assertNotIn(self.user, self.serie_owned.suivi_exclu_user_ids)

    def test_server_actions_apply_exclusion(self):
        ctx = {"active_model": "comic.serie", "active_ids": self.serie_owned.ids, "active_id": self.serie_owned.id}
        unmark = self.env.ref("comics_collections.action_serie_unmark_suivie")
        mark = self.env.ref("comics_collections.action_serie_mark_suivie")
        unmark.with_user(self.user).with_context(**ctx).run()
        self.assertIn(self.user, self.serie_owned.suivi_exclu_user_ids)
        mark.with_user(self.user).with_context(**ctx).run()
        self.assertIn(self.user, self.serie_owned.suivi_user_ids)
        self.assertNotIn(self.user, self.serie_owned.suivi_exclu_user_ids)

    def test_portal_never_follows(self):
        self.env["comic.customer.album"].create(
            {"partner_id": self.portal.partner_id.id, "edition_id": self.work_catalogue.primary_edition_id.id}
        )
        self.assertNotIn(self.portal, self.serie_catalogue.suivi_user_ids)
        self.serie_catalogue._auto_follow(self.portal)
        self.assertNotIn(self.portal, self.serie_catalogue.suivi_user_ids)

    def test_migration_follows_owners(self):
        (self.serie_owned | self.serie_other).write({"suivi_user_ids": [Command.clear()]})
        self.serie_other.write({"suivi_exclu_user_ids": [Command.link(self.other.id)]})
        path = file_path("comics_collections/migrations/19.0.4.0.0/post-migrate.py")
        spec = importlib.util.spec_from_file_location("comics_post_migrate_4", path)
        migration = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(migration)
        migration.migrate(self.env.cr, "19.0.3.1.0")
        self.assertEqual(self.serie_owned.suivi_user_ids, self.user)
        self.assertFalse(self.serie_other.suivi_user_ids)
        self.assertFalse(self.serie_catalogue.suivi_user_ids)
