"""Wishlist (US-089) : manques des séries suivies + souhaits manuels."""

import json

from odoo import Command
from odoo.exceptions import AccessError
from odoo.tests import new_test_user, tagged
from odoo.tests.common import TransactionCase


@tagged("post_install", "-at_install", "comics_collections")
class TestWishlist(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        groups = "comics_collections.group_comic_user"
        cls.user_a = new_test_user(cls.env, login="wishlist_user_a", groups=groups)
        cls.user_b = new_test_user(cls.env, login="wishlist_user_b", groups=groups)
        cls.serie = cls.env["comic.serie"].create({"name": "Wishlist Série suivie"})
        cls.works = {}
        cls.editions = {}
        for tome in (1, 2, 3):
            work = cls.env["comic.work"].create(
                {"serie_id": cls.serie.id, "titre_canonique": f"Wishlist T{tome}", "tome": tome}
            )
            cls.works[tome] = work
            # La création d'un album crée son édition principale
            cls.editions[tome] = work.primary_edition_id
        # Hors-série (tome 0) et album archivé : jamais des manques
        cls.hors_serie = cls.env["comic.work"].create(
            {"serie_id": cls.serie.id, "titre_canonique": "Wishlist HS", "tome": 0}
        )
        cls.archived = cls.env["comic.work"].create(
            {"serie_id": cls.serie.id, "titre_canonique": "Wishlist archivé", "tome": 9}
        )
        cls.archived.active = False

        cls.other_serie = cls.env["comic.serie"].create({"name": "Wishlist Série non suivie"})
        cls.other_work = cls.env["comic.work"].create(
            {"serie_id": cls.other_serie.id, "titre_canonique": "Wishlist souhait", "tome": 1}
        )
        cls.other_edition = cls.other_work.primary_edition_id

        Album = cls.env["comic.customer.album"]
        Album.create({"partner_id": cls.user_a.partner_id.id, "edition_id": cls.editions[1].id})
        cls.serie.write({"suivi_user_ids": [Command.set([cls.user_a.id])]})
        cls.other_serie.write({"suivi_user_ids": [Command.clear()]})

    # ── Helpers ─────────────────────────────────────────────────────────────

    def _items(self, user):
        self.env.flush_all()
        self.env["comic.wishlist.item"].invalidate_model()
        return self.env["comic.wishlist.item"].with_user(user).search([])

    def _lines(self, user, type_=None):
        items = self._items(user)
        if type_:
            items = items.filtered(lambda i: i.type == type_)
        return {(i.work_id, i.type) for i in items}

    def _entry(self, user, edition):
        return self.env["comic.customer.album"].search(
            [("partner_id", "=", user.partner_id.id), ("edition_id", "=", edition.id)]
        )

    def _add_wish(self, user, edition):
        return self.env["comic.customer.album"].create(
            {
                "partner_id": user.partner_id.id,
                "edition_id": edition.id,
                "dans_collection": False,
                "dans_wishlist": True,
            }
        )

    # ── Contenu de la vue ───────────────────────────────────────────────────

    def test_missing_tomes_of_followed_serie(self):
        self.assertTrue(all(self.editions.values()) and self.other_edition)
        self.assertEqual(
            self._lines(self.user_a),
            {(self.works[2], "manque"), (self.works[3], "manque")},
        )
        item = self._items(self.user_a).filtered(lambda i: i.work_id == self.works[2])
        self.assertEqual(item.serie_id, self.serie)
        self.assertEqual(item.tome, 2)
        self.assertEqual(item.edition_id, self.editions[2])
        self.assertEqual(item.user_id, self.user_a)
        self.assertEqual(item.partner_id, self.user_a.partner_id)

    def test_list_and_kanban_views_can_be_read(self):
        """Ce que lit le client web : chaque champ des vues liste / kanban, plus write_date
        (clé de cache du widget image) — régression « Invalid field 'write_date' »."""
        Item = self.env["comic.wishlist.item"].with_user(self.user_a)
        views = Item.get_views([(False, "list"), (False, "kanban")])
        fields_in_views = set()
        for view in views["views"].values():
            fields_in_views |= set(view.get("fields", {}) or {})
        fields_in_views |= set(views["models"]["comic.wishlist.item"]["fields"])
        spec = {name: {} for name in fields_in_views if name in Item._fields}
        spec["write_date"] = {}
        result = Item.web_search_read([], spec)
        self.assertEqual(result["length"], 2)
        self.assertIn("write_date", result["records"][0])

    def test_tome_numbers_never_summed_in_groups(self):
        """Un n° de tome ne s'additionne pas dans les lignes de groupe (ex. « Thorgal 23 »)."""
        for model in ("comic.wishlist.item", "comic.work", "comic.work.auteur.line"):
            self.assertFalse(self.env[model]._fields["tome"].aggregator, model)
        self.assertFalse(self.env["comic.serie"]._fields["bdgest_id"].aggregator)

    def test_click_opens_album(self):
        line = self._items(self.user_a).filtered(lambda i: i.work_id == self.works[2])
        action = line.action_open_work()
        self.assertEqual((action["res_model"], action["res_id"]), ("comic.work", self.works[2].id))
        # L'album s'ouvre pour l'utilisateur (catalogue partagé en lecture)
        self.works[2].with_user(self.user_a).check_access("read")

    def test_stable_ids(self):
        first = self._items(self.user_a).ids
        self.assertEqual(self._items(self.user_a).ids, first)
        self.assertEqual(len(set(first)), len(first))

    def test_missing_disappears_when_owned_or_unfollowed(self):
        self.env["comic.customer.album"].create(
            {"partner_id": self.user_a.partner_id.id, "edition_id": self.editions[2].id}
        )
        self.assertEqual(self._lines(self.user_a), {(self.works[3], "manque")})
        self.serie.with_user(self.user_a).a_suivre = False
        self.assertFalse(self._items(self.user_a))

    def test_manual_wish_of_unfollowed_serie(self):
        self._add_wish(self.user_a, self.other_edition)
        self.assertIn((self.other_work, "souhait"), self._lines(self.user_a))
        # Un souhait d'une série suivie n'est pas aussi un manque
        self._add_wish(self.user_a, self.editions[3])
        lines = self._lines(self.user_a)
        self.assertIn((self.works[3], "souhait"), lines)
        self.assertNotIn((self.works[3], "manque"), lines)

    def test_isolation_between_users(self):
        self._add_wish(self.user_b, self.other_edition)
        self.assertEqual(self._lines(self.user_b), {(self.other_work, "souhait")})
        self.assertNotIn((self.other_work, "souhait"), self._lines(self.user_a))
        # B suit la série sans rien posséder : manques T1..T3 pour B uniquement
        self.serie.with_user(self.user_b).a_suivre = True
        self.assertEqual(len(self._lines(self.user_b, "manque")), 3)
        self.assertEqual(len(self._lines(self.user_a, "manque")), 2)
        # Une ligne de B est invisible pour A et inutilisable par A
        line_b = self._items(self.user_b)[:1]
        with self.assertRaises(AccessError):
            line_b.with_user(self.user_a).action_mark_owned()

    def test_tome_zero_and_archived_never_missing(self):
        works = {i.work_id for i in self._items(self.user_a)}
        self.assertNotIn(self.hors_serie, works)
        self.assertNotIn(self.archived, works)

    # ── Actions de ligne ────────────────────────────────────────────────────

    def _line(self, user, work):
        return self._items(user).filtered(lambda i: i.work_id == work)

    def test_action_ignore(self):
        action = self._line(self.user_a, self.works[2]).action_ignore()
        self.assertEqual(action["tag"], "soft_reload")
        entry = self._entry(self.user_a, self.editions[2])
        self.assertTrue(entry.ignore_wishlist)
        self.assertFalse(entry.dans_collection)
        self.assertEqual(self._lines(self.user_a), {(self.works[3], "manque")})

    def test_action_mark_owned(self):
        self._line(self.user_a, self.works[3]).action_mark_owned()
        entry = self._entry(self.user_a, self.editions[3])
        self.assertTrue(entry.dans_collection)
        self.assertFalse(entry.dans_wishlist)
        # Un souhait passé en collection sort lui aussi de la wishlist
        self._add_wish(self.user_a, self.other_edition)
        self._line(self.user_a, self.other_work).action_mark_owned()
        self.assertTrue(self._entry(self.user_a, self.other_edition).dans_collection)
        self.assertEqual(self._lines(self.user_a), {(self.works[2], "manque")})
        self.assertFalse(self._entry(self.user_b, self.editions[3]))

    def test_action_remove_wish(self):
        self._add_wish(self.user_a, self.other_edition)
        self._line(self.user_a, self.other_work).action_remove()
        self.assertFalse(self._entry(self.user_a, self.other_edition).dans_wishlist)
        self.assertNotIn((self.other_work, "souhait"), self._lines(self.user_a))

    def test_action_remove_missing_unfollows_serie_for_user_only(self):
        self.serie.with_user(self.user_b).a_suivre = True
        self._line(self.user_a, self.works[2]).action_remove()
        self.assertEqual(self.serie.suivi_user_ids, self.user_b)
        self.assertFalse(self._lines(self.user_a, "manque"))
        self.assertEqual(len(self._lines(self.user_b, "manque")), 3)

    # ── Statistiques et tableau de bord ─────────────────────────────────────

    def test_collection_stats_counters(self):
        self._add_wish(self.user_a, self.other_edition)
        self.env.flush_all()
        stats = self.env["comic.customer.album"]._get_collection_stats(self.user_a.partner_id)
        self.assertEqual(stats["nb_souhaits"], 1)
        self.assertEqual(stats["nb_manques"], 2)
        self.assertEqual(stats["nb_wishlist"], 3)
        stats_b = self.env["comic.customer.album"]._get_collection_stats(self.user_b.partner_id)
        self.assertEqual((stats_b["nb_souhaits"], stats_b["nb_manques"], stats_b["nb_wishlist"]), (0, 0, 0))

    def test_portal_partner_counts_only_wishes(self):
        portal = new_test_user(self.env, login="wishlist_portal", groups="base.group_portal")
        self.serie.write({"suivi_user_ids": [Command.link(portal.id)]})
        self._add_wish(portal, self.other_edition)
        self.env.flush_all()
        stats = self.env["comic.customer.album"]._get_collection_stats(portal.partner_id)
        self.assertEqual((stats["nb_souhaits"], stats["nb_manques"], stats["nb_wishlist"]), (1, 0, 1))

    def test_dashboard_data_serializable(self):
        self._add_wish(self.user_a, self.other_edition)
        data = self.env["comic.customer.album"].with_user(self.user_a).get_dashboard_data()
        json.loads(json.dumps(data))
        self.assertEqual((data["nb_manques"], data["nb_souhaits"], data["nb_wishlist"]), (2, 1, 3))

    # ── Bouton « Ajouter à ma wishlist » de la fiche album (#7) ────────────

    def test_wishlist_button_state_per_user(self):
        work_a = self.works[1].with_user(self.user_a)
        work_b = self.works[1].with_user(self.user_b)
        # T1 possédé par A : bouton masqué pour A, visible pour B
        self.assertTrue(work_a.in_my_collection)
        self.assertFalse(work_b.in_my_collection or work_b.in_my_wishlist)
        # Un souhait de B le masque aussi pour B
        self._add_wish(self.user_b, self.editions[1])
        self.env.invalidate_all()
        self.assertTrue(self.works[1].with_user(self.user_b).in_my_wishlist)
        self.assertFalse(self.works[2].with_user(self.user_a).in_my_collection)
        arch = self.env["comic.work"].get_view(self.env.ref("comics_collections.view_comic_work_form").id)["arch"]
        self.assertIn("in_my_collection or in_my_wishlist", arch)
