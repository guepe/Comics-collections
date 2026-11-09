"""Suivi de séries par les clients et email à la mise en vente (US-069).

Lancement :
    docker exec odoo-web odoo -d odoo -u comic_shop --test-tags /comic_shop:TestReleaseNotify
"""

from odoo import Command
from odoo.tests import TransactionCase, new_test_user, tagged


@tagged("post_install", "-at_install", "comic_shop", "release_notify")
class TestReleaseNotify(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.manager = new_test_user(
            cls.env,
            login="release_manager",
            groups="comics_collections.group_comic_manager,comic_shop.group_shop_manager,sales_team.group_sale_manager,"
            "product.group_product_manager",
            email="manager@example.com",
        )
        cls.follower = new_test_user(
            cls.env, login="release_follower", groups="base.group_portal", email="f@example.com"
        )
        cls.wisher = new_test_user(cls.env, login="release_wisher", groups="base.group_portal", email="w@example.com")
        cls.owner = new_test_user(cls.env, login="release_owner", groups="base.group_portal", email="o@example.com")
        cls.no_mail = new_test_user(cls.env, login="release_nomail", groups="base.group_portal")
        cls.no_mail.partner_id.email = False
        cls.internal = new_test_user(
            cls.env, login="release_internal", groups="comics_collections.group_comic_user", email="i@example.com"
        )

        cls.serie = cls.env["comic.serie"].create({"name": "Série Mise en vente"})
        cls.other_serie = cls.env["comic.serie"].create({"name": "Série Autre"})
        cls.work = cls.env["comic.work"].create(
            {"serie_id": cls.serie.id, "titre_canonique": "Nouveau tome", "tome": 5}
        )
        cls.edition = cls.work.primary_edition_id
        cls.other_work = cls.env["comic.work"].create(
            {"serie_id": cls.other_serie.id, "titre_canonique": "Album souhaité", "tome": 1}
        )
        cls.other_edition = cls.other_work.primary_edition_id

        cls.serie.write(
            {"suivi_user_ids": [Command.set([cls.follower.id, cls.owner.id, cls.no_mail.id, cls.internal.id])]}
        )
        Album = cls.env["comic.customer.album"]
        Album.create({"partner_id": cls.owner.partner_id.id, "edition_id": cls.edition.id})
        Album.create(
            {
                "partner_id": cls.wisher.partner_id.id,
                "edition_id": cls.other_edition.id,
                "dans_collection": False,
                "dans_wishlist": True,
            }
        )
        Album.create(
            {
                "partner_id": cls.internal.partner_id.id,
                "edition_id": cls.other_edition.id,
                "dans_collection": False,
                "dans_wishlist": True,
            }
        )

    def _put_on_sale(self, edition, published=True):
        product = self.env["product.template"].create({"name": edition.work_id.display_name})
        edition.product_tmpl_id = product
        product.is_published = published
        return product

    def _release_mails(self, partner):
        return self.env["mail.mail"].search(
            [("recipient_ids", "in", partner.id), ("subject", "ilike", "est disponible")]
        )

    # ── Destinataires ───────────────────────────────────────────────────────

    def test_no_recipient_until_on_sale(self):
        self.assertFalse(self.edition._get_release_recipients())
        self._put_on_sale(self.edition, published=False)
        self.assertFalse(self.edition._get_release_recipients())
        self.assertEqual(self.edition.release_recipient_count, 0)

    def test_recipients_followers_and_wishlist(self):
        self._put_on_sale(self.edition)
        self._put_on_sale(self.other_edition)
        # Abonné portail ; pas le propriétaire, ni le client sans email, ni l'interne
        self.assertEqual(self.edition._get_release_recipients(), self.follower.partner_id)
        # Wishlist d'un client (série non suivie) ; pas la wishlist d'un utilisateur interne
        self.assertEqual(self.other_edition._get_release_recipients(), self.wisher.partner_id)
        self.edition.invalidate_recordset(["release_recipient_count"])
        self.assertEqual(self.edition.release_recipient_count, 1)

    # ── Envoi ───────────────────────────────────────────────────────────────

    def test_send_once_per_album_with_chatter_trace(self):
        self._put_on_sale(self.edition)
        sent = self.edition.with_user(self.manager)._send_release_notification()
        self.assertEqual(sent, 1)
        mails = self._release_mails(self.follower.partner_id)
        self.assertEqual(len(mails), 1)
        self.assertIn("Nouveau tome", mails.subject)
        self.assertIn(self.edition.product_tmpl_id.website_url, mails.body_html)
        self.assertFalse(self._release_mails(self.owner.partner_id))
        self.assertIn(self.follower.partner_id, self.work.release_customer_ids)
        self.assertTrue(self.edition.message_ids.filtered(lambda m: "1 client(s)" in (m.body or "")))
        # Deuxième envoi, ou autre édition du même album : personne n'est reprévenu
        self.assertEqual(self.edition._send_release_notification(), 0)
        second = self.env["comic.edition"].create({"work_id": self.work.id})
        self._put_on_sale(second)
        self.assertFalse(second._get_release_recipients())
        self.assertEqual(len(self._release_mails(self.follower.partner_id)), 1)

    def test_new_follower_is_notified_later(self):
        self._put_on_sale(self.edition)
        self.edition._send_release_notification()
        late = new_test_user(self.env, login="release_late", groups="base.group_portal", email="l@example.com")
        self.serie.with_user(late).sudo().a_suivre = True
        self.assertEqual(self.edition._get_release_recipients(), late.partner_id)

    # ── Assistant (aperçu avant envoi) ──────────────────────────────────────

    def test_wizard_preview_and_send(self):
        self._put_on_sale(self.edition)
        self._put_on_sale(self.other_edition)
        action = (self.edition | self.other_edition).with_user(self.manager).action_release_notify()
        self.assertEqual(action["res_model"], "comic.release.notify.wizard")
        wizard = (
            self.env["comic.release.notify.wizard"].with_user(self.manager).with_context(**action["context"]).create({})
        )
        self.assertEqual(wizard.recipient_count, 2)
        self.assertIn("Nouveau tome", wizard.preview_subject)
        self.assertIn("Voir l", wizard.preview_body)
        self.assertIn("Album souhaité", wizard.summary_html)
        result = wizard.action_send()
        self.assertEqual(result["tag"], "display_notification")
        self.assertTrue(self._release_mails(self.wisher.partner_id))
        self.assertEqual(self.edition.with_user(self.manager).action_release_notify()["tag"], "display_notification")

    def test_publish_series_opens_wizard(self):
        product = self._put_on_sale(self.edition, published=False)
        action = self.serie.with_user(self.manager).action_publish_products()
        self.assertTrue(product.is_published)
        self.assertEqual(action["res_model"], "comic.release.notify.wizard")
        # Sans client à prévenir, la publication n'ouvre rien
        self.edition._send_release_notification()
        self.assertFalse(self.serie.with_user(self.manager).action_publish_products())

    def test_core_release_alert_skips_portal_followers(self):
        """L'alerte nouveauté du cœur (US-068) ne concerne pas les clients du portail."""
        work = self.env["comic.work"].create(
            {"serie_id": self.serie.id, "titre_canonique": "Tome à paraître", "tome": 6}
        )
        work.primary_edition_id.date_parution = "2099-01-01"
        work._notify_new_release()
        message = work.message_ids.filtered(lambda m: "Nouveau tome dans une série" in (m.body or ""))
        self.assertEqual(message.partner_ids, self.internal.partner_id)
