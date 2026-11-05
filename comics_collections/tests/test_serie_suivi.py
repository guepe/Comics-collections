"""Tests du suivi de série par utilisateur (catalogue partagé).

Lancement :
    docker exec odoo-web odoo-bin -d odoo -u comics_collections \
        --test-tags /comics_collections:TestSerieSuivi
"""

from odoo.tests import new_test_user, tagged
from odoo.tests.common import TransactionCase


@tagged("post_install", "-at_install", "comics_collections")
class TestSerieSuivi(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        groups = "comics_collections.group_comic_user"
        cls.user_a = new_test_user(cls.env, login="suivi_user_a", groups=groups)
        cls.user_b = new_test_user(cls.env, login="suivi_user_b", groups=groups)
        cls.serie = cls.env["comic.serie"].create({"name": "Série suivie test"})
        cls.serie_2 = cls.env["comic.serie"].create({"name": "Série non suivie test"})

    def _serie_as(self, user, serie=None):
        return (serie or self.serie).with_user(user)

    def test_follow_is_per_user(self):
        self._serie_as(self.user_a).a_suivre = True
        self.assertTrue(self._serie_as(self.user_a).a_suivre)
        self.assertFalse(self._serie_as(self.user_b).a_suivre)
        self.assertEqual(self.serie.suivi_user_ids, self.user_a)

    def test_search_followed_per_user(self):
        self._serie_as(self.user_a).write({"a_suivre": True})
        self._serie_as(self.user_b, self.serie_2).write({"a_suivre": True})

        Serie_a = self.env["comic.serie"].with_user(self.user_a)
        Serie_b = self.env["comic.serie"].with_user(self.user_b)

        followed_a = Serie_a.search([("a_suivre", "=", True)])
        self.assertIn(self.serie, followed_a)
        self.assertNotIn(self.serie_2, followed_a)

        followed_b = Serie_b.search([("a_suivre", "=", True)])
        self.assertIn(self.serie_2, followed_b)
        self.assertNotIn(self.serie, followed_b)

        not_followed_a = Serie_a.search([("a_suivre", "=", False)])
        self.assertIn(self.serie_2, not_followed_a)
        self.assertNotIn(self.serie, not_followed_a)

        self.assertIn(self.serie, Serie_a.search([("a_suivre", "!=", False)]))

    def test_unfollow_removes_only_current_user(self):
        self._serie_as(self.user_a).write({"a_suivre": True})
        self._serie_as(self.user_b).write({"a_suivre": True})
        self.assertEqual(self.serie.suivi_user_ids, self.user_a | self.user_b)

        self._serie_as(self.user_a).write({"a_suivre": False})
        self.assertEqual(self.serie.suivi_user_ids, self.user_b)
        self.assertFalse(self._serie_as(self.user_a).a_suivre)
        self.assertTrue(self._serie_as(self.user_b).a_suivre)

    def test_server_actions_toggle_current_user(self):
        mark = self.env.ref("comics_collections.action_serie_mark_suivie")
        unmark = self.env.ref("comics_collections.action_serie_unmark_suivie")
        series = self.serie | self.serie_2
        ctx = {"active_model": "comic.serie", "active_ids": series.ids, "active_id": series[0].id}

        mark.with_user(self.user_a).with_context(**ctx).run()
        self.assertEqual(self.serie.suivi_user_ids, self.user_a)
        self.assertEqual(self.serie_2.suivi_user_ids, self.user_a)

        mark.with_user(self.user_b).with_context(**ctx).run()
        unmark.with_user(self.user_a).with_context(**ctx).run()
        self.assertEqual(self.serie.suivi_user_ids, self.user_b)
        self.assertEqual(self.serie_2.suivi_user_ids, self.user_b)

    def test_cron_domain_selects_series_followed_by_anyone(self):
        self._serie_as(self.user_b).write({"a_suivre": True})
        followed = self.env["comic.serie"].search([("suivi_user_ids", "!=", False)])
        self.assertIn(self.serie, followed)
        self.assertNotIn(self.serie_2, followed)
