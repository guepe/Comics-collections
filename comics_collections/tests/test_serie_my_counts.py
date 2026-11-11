"""« Mes séries » à la Bubble : compteurs de l'utilisateur connecté, initiale, onglets."""

from datetime import timedelta

from odoo import Command, fields
from odoo.tests import new_test_user, tagged
from odoo.tests.common import TransactionCase
from odoo.tools.safe_eval import safe_eval


@tagged("post_install", "-at_install", "comics_collections")
class TestSerieMyCounts(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        groups = "comics_collections.group_comic_user"
        cls.user_a = new_test_user(cls.env, login="mycounts_user_a", groups=groups)
        cls.user_b = new_test_user(cls.env, login="mycounts_user_b", groups=groups)
        Serie = cls.env["comic.serie"]
        Work = cls.env["comic.work"]
        cls.serie = Serie.create({"name": "Les Mycounts", "type": "bd"})
        cls.works = {
            tome: Work.create({"serie_id": cls.serie.id, "titre_canonique": f"Mycounts T{tome}", "tome": tome})
            for tome in (1, 2, 3, 4)
        }
        cls.editions = {tome: work.primary_edition_id for tome, work in cls.works.items()}
        # Série complète pour A (un seul tome, possédé et lu)
        cls.serie_full = Serie.create({"name": "2000 Mycounts", "type": "manga"})
        cls.work_full = Work.create({"serie_id": cls.serie_full.id, "titre_canonique": "Full T1", "tome": 1})
        # Série jamais commencée, suivie par A
        cls.serie_empty = Serie.create({"name": "Zorglub Mycounts", "type": "comics"})
        cls.work_empty = Work.create({"serie_id": cls.serie_empty.id, "titre_canonique": "Empty T1", "tome": 1})

        Album = cls.env["comic.customer.album"]
        pa = cls.user_a.partner_id.id
        Album.create({"partner_id": pa, "edition_id": cls.editions[1].id, "etat_lecture": "lu", "note": 4})
        Album.create({"partner_id": pa, "edition_id": cls.editions[2].id, "note": 3})
        # Tome 3 ignoré (« ne pas acheter ») : pas un manque
        Album.create(
            {
                "partner_id": pa,
                "edition_id": cls.editions[3].id,
                "dans_collection": False,
                "ignore_wishlist": True,
            }
        )
        Album.create({"partner_id": pa, "edition_id": cls.work_full.primary_edition_id.id, "etat_lecture": "lu"})
        # B possède seulement le tome 4 de la première série
        Album.create({"partner_id": cls.user_b.partner_id.id, "edition_id": cls.editions[4].id})

        cls.env["comic.pret"].with_user(cls.user_a).create(
            {"edition_id": cls.editions[1].id, "partner_id": cls.user_b.partner_id.id}
        )
        cls.env["comic.pret"].with_user(cls.user_a).create(
            {"edition_id": cls.editions[2].id, "partner_id": cls.user_b.partner_id.id, "retourne": True}
        )
        (cls.serie | cls.serie_full | cls.serie_empty).write({"suivi_user_ids": [Command.link(cls.user_a.id)]})

    def _serie_as(self, user, serie):
        return serie.with_user(user)

    # ── Compteurs ────────────────────────────────────────────────────────────

    def test_counts_user_a(self):
        serie = self._serie_as(self.user_a, self.serie)
        self.assertEqual(serie.my_owned_count, 2)
        self.assertEqual(serie.my_read_count, 1)
        self.assertEqual(serie.my_unread_count, 1)
        self.assertEqual(serie.my_lent_count, 1, "Only the loan not returned counts")
        self.assertEqual(serie.my_missing_count, 1, "Volume 4 only: 1-2 owned, 3 ignored")
        self.assertAlmostEqual(serie.my_rating, 3.5)

    def test_counts_isolated_per_user(self):
        serie = self._serie_as(self.user_b, self.serie)
        self.assertEqual(serie.my_owned_count, 1)
        self.assertEqual(serie.my_read_count, 0)
        self.assertEqual(serie.my_lent_count, 0, "A's loans are not B's")
        self.assertEqual(serie.my_missing_count, 3)
        self.assertEqual(serie.my_rating, 0.0)

    def test_counts_batch(self):
        series = (self.serie | self.serie_full | self.serie_empty).with_user(self.user_a)
        self.assertEqual(series.mapped("my_owned_count"), [2, 1, 0])
        self.assertEqual(series.mapped("my_missing_count"), [1, 0, 1])

    # ── Initiale ─────────────────────────────────────────────────────────────

    def test_name_initial(self):
        self.assertEqual(self.serie.name_initial, "M", "Leading article is ignored")
        self.assertEqual(self.serie_full.name_initial, "#")
        self.assertEqual(self.serie_empty.name_initial, "Z")
        self.serie_empty.name = "éléphant"
        self.assertEqual(self.serie_empty.name_initial, "E")

    # ── Filtres de recherche ─────────────────────────────────────────────────

    def _search(self, user, domain):
        mine = [("id", "in", (self.serie | self.serie_full | self.serie_empty).ids)]
        return self.env["comic.serie"].with_user(user).search(mine + domain)

    def test_search_started(self):
        self.assertEqual(self._search(self.user_a, [("my_owned_count", ">", 0)]), self.serie | self.serie_full)
        self.assertEqual(self._search(self.user_a, [("my_owned_count", "=", 0)]), self.serie_empty)
        self.assertEqual(self._search(self.user_b, [("my_owned_count", ">", 0)]), self.serie)

    def test_search_complete_incomplete(self):
        complete = [("my_owned_count", ">", 0), ("my_missing_count", "=", 0)]
        self.assertEqual(self._search(self.user_a, complete), self.serie_full)
        self.assertEqual(self._search(self.user_a, [("my_missing_count", ">", 0)]), self.serie | self.serie_empty)
        self.assertFalse(self._search(self.user_b, complete))

    def test_search_read_unread_lent(self):
        self.assertEqual(self._search(self.user_a, [("my_unread_count", ">", 0)]), self.serie)
        read = [("my_owned_count", ">", 0), ("my_unread_count", "=", 0)]
        self.assertEqual(self._search(self.user_a, read), self.serie_full)
        self.assertEqual(self._search(self.user_a, [("my_lent_count", ">", 0)]), self.serie)
        self.assertFalse(self._search(self.user_b, [("my_lent_count", ">", 0)]))

    # ── Suivi ────────────────────────────────────────────────────────────────

    def test_toggle_and_stop_following(self):
        serie = self._serie_as(self.user_a, self.serie_empty)
        serie.action_toggle_follow()
        self.assertNotIn(self.user_a, self.serie_empty.suivi_user_ids)
        self.assertIn(self.user_a, self.serie_empty.suivi_exclu_user_ids)
        serie.action_toggle_follow()
        self.assertIn(self.user_a, self.serie_empty.suivi_user_ids)
        serie.action_stop_following()
        self.assertNotIn(self.user_a, self.serie_empty.suivi_user_ids)

    def test_view_my_missing_action(self):
        action = self._serie_as(self.user_a, self.serie).action_view_my_missing()
        self.assertEqual(action["res_model"], "comic.wishlist.item")
        self.assertEqual(action["context"]["search_default_serie_id"], self.serie.id)

    # ── Actions des nouveaux onglets ─────────────────────────────────────────

    def _action_records(self, xmlid, user):
        action = self.env["ir.actions.act_window"]._for_xml_id(xmlid)
        domain = safe_eval(action["domain"], {"uid": user.id})
        self.env.flush_all()
        return self.env[action["res_model"]].with_user(user).search(domain)

    def test_action_missing_volumes(self):
        series = self._action_records("comics_collections.action_comic_serie_missing", self.user_a)
        self.assertIn(self.serie, series)
        self.assertIn(self.serie_empty, series)
        self.assertNotIn(self.serie_full, series)
        # B ne suit pas la série : rien chez lui
        self.serie.write({"suivi_user_ids": [Command.unlink(self.user_b.id)]})
        series_b = self._action_records("comics_collections.action_comic_serie_missing", self.user_b)
        self.assertNotIn(self.serie, series_b)

    def test_action_to_read(self):
        entries = self._action_records("comics_collections.action_comic_to_read", self.user_a)
        self.assertEqual(entries.edition_id, self.editions[2])

    def test_action_upcoming_and_wishes(self):
        today = fields.Date.today()
        self.editions[4].date_parution = today + timedelta(days=10)
        self.work_empty.primary_edition_id.date_parution = today - timedelta(days=10)
        wish_work = self.env["comic.work"].create({"titre_canonique": "Mycounts wish", "tome": 0})
        wish_work.primary_edition_id.date_parution = today
        self.env["comic.customer.album"].create(
            {
                "partner_id": self.user_a.partner_id.id,
                "edition_id": wish_work.primary_edition_id.id,
                "dans_collection": False,
                "dans_wishlist": True,
            }
        )
        upcoming = self._action_records("comics_collections.action_comic_upcoming", self.user_a)
        self.assertEqual(set(upcoming.mapped("work_id").ids), {self.works[4].id, wish_work.id})
        wishes = self._action_records("comics_collections.action_comic_wishlist", self.user_a).filtered(
            lambda line: line.type == "souhait"
        )
        self.assertEqual(wishes.work_id, wish_work)
        self.assertFalse(self._action_records("comics_collections.action_comic_upcoming", self.user_b))
