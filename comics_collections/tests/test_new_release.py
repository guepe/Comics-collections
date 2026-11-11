"""Tests de l'alerte nouveautés sur les séries suivies (US-068).

Lancement :
    docker exec odoo-web odoo -d odoo -u comics_collections \
        --test-tags /comics_collections:TestNewRelease
"""

from datetime import timedelta

from odoo import Command, fields
from odoo.tests import new_test_user, tagged
from odoo.tests.common import TransactionCase


@tagged("post_install", "-at_install", "comics_collections")
class TestNewRelease(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        groups = "comics_collections.group_comic_user"
        cls.user_a = new_test_user(cls.env, login="release_user_a", groups=groups)
        cls.user_b = new_test_user(cls.env, login="release_user_b", groups=groups)
        cls.user_other = new_test_user(cls.env, login="release_user_other", groups=groups)
        cls.serie = cls.env["comic.serie"].create(
            {
                "name": "Série nouveautés test",
                "suivi_user_ids": [Command.set([cls.user_a.id, cls.user_b.id])],
            }
        )
        cls.today = fields.Date.context_today(cls.env["comic.work"])
        cls.env["ir.config_parameter"].sudo().set_param("comic.new_release_days", "90")

    def _work(self, tome, days_ago=None, serie=None):
        vals = {"serie_id": (serie or self.serie).id, "titre_canonique": f"Tome nouveauté {tome}", "tome": tome}
        if days_ago is not None:
            vals["date_parution"] = self.today - timedelta(days=days_ago)
        return self.env["comic.work"].create(vals)

    def _release_messages(self, work):
        return work.message_ids.filtered(lambda m: "New volume in a series you follow" in (m.body or ""))

    # ── Détection d'une nouveauté ────────────────────────────────────────────

    def test_is_new_release(self):
        self.assertTrue(self._work(1, days_ago=10)._is_new_release())
        self.assertTrue(self._work(2, days_ago=-30)._is_new_release(), "Une parution future est une nouveauté")
        self.assertFalse(self._work(3, days_ago=400)._is_new_release())
        self.assertFalse(self._work(4)._is_new_release(), "Sans date : jamais une nouveauté")

    def test_parameter_days_respected(self):
        work = self._work(1, days_ago=60)
        self.assertTrue(work._is_new_release())
        self.env["ir.config_parameter"].sudo().set_param("comic.new_release_days", "30")
        self.assertFalse(work._is_new_release())
        work._notify_new_release()
        self.assertFalse(self._release_messages(work))
        self.env["ir.config_parameter"].sudo().set_param("comic.new_release_days", "pas un nombre")
        self.assertEqual(self.env["comic.work"]._get_new_release_days(), 90)
        self.assertTrue(work._is_new_release())

    # ── Notification ─────────────────────────────────────────────────────────

    def test_recent_tome_notifies_followers_once(self):
        work = self._work(1, days_ago=5)
        work._notify_new_release()
        self.assertTrue(work.release_notified)
        messages = self._release_messages(work)
        self.assertEqual(len(messages), 1)
        expected = self.user_a.partner_id | self.user_b.partner_id
        self.assertEqual(messages.partner_ids, expected)
        self.assertEqual(messages.notification_ids.res_partner_id, expected)
        self.assertIn("Vol. 1", messages.body)
        self.assertIn(work.date_parution.strftime("%d/%m/%Y"), messages.body)

        work._notify_new_release()
        self.assertEqual(len(self._release_messages(work)), 1, "Jamais notifié deux fois")

    def test_non_follower_not_notified(self):
        work = self._work(1, days_ago=5)
        work._notify_new_release()
        message = self._release_messages(work)
        self.assertNotIn(self.user_other.partner_id, message.partner_ids)
        self.assertNotIn(self.user_other.partner_id, message.notification_ids.res_partner_id)

    def test_current_user_excluded_outside_cron(self):
        work = self._work(1, days_ago=5)
        work.with_user(self.user_a)._notify_new_release()
        message = self._release_messages(work)
        self.assertEqual(message.notification_ids.res_partner_id, self.user_b.partner_id)

    def test_old_or_undated_tome_not_notified(self):
        old = self._work(1, days_ago=400)
        undated = self._work(2)
        (old | undated)._notify_new_release()
        self.assertFalse(self._release_messages(old))
        self.assertFalse(self._release_messages(undated))
        self.assertFalse(old.release_notified)
        self.assertFalse(undated.release_notified)

    def test_no_recipient_still_flagged(self):
        serie = self.env["comic.serie"].create({"name": "Série sans abonné"})
        work = self._work(1, days_ago=5, serie=serie)
        work._notify_new_release()
        self.assertTrue(work.release_notified)
        self.assertFalse(self._release_messages(work))

    # ── Wishlist ─────────────────────────────────────────────────────────────

    def test_add_to_my_wishlist_does_not_downgrade_owned(self):
        CustomerAlbum = self.env["comic.customer.album"]
        partner = self.user_a.partner_id
        owned = self._work(1, days_ago=5)
        wanted = self._work(2, days_ago=5)
        CustomerAlbum._upsert(partner, owned.primary_edition_id, {"dans_collection": True})

        result = (owned | wanted).with_user(self.user_a).action_add_to_my_wishlist()
        self.assertEqual(result["tag"], "display_notification")
        self.assertIn("1 album(s)", result["params"]["message"])
        self.assertIn("already in your collection", result["params"]["message"])

        owned_entry = CustomerAlbum.search(
            [("partner_id", "=", partner.id), ("edition_id", "=", owned.primary_edition_id.id)]
        )
        self.assertTrue(owned_entry.dans_collection)
        self.assertFalse(owned_entry.dans_wishlist)
        wanted_entry = CustomerAlbum.search(
            [("partner_id", "=", partner.id), ("edition_id", "=", wanted.primary_edition_id.id)]
        )
        self.assertTrue(wanted_entry.dans_wishlist)
        self.assertFalse(wanted_entry.dans_collection)
