"""Modération des fiches catalogue proposées par les clients du portail.

Lancement :
    docker exec odoo-web odoo-bin -d odoo -u comic_shop \
        --test-tags /comic_shop:TestPortalModeration
"""

from odoo import Command
from odoo.exceptions import UserError
from odoo.tests import tagged
from odoo.tests.common import TransactionCase

SUMMARY = "Album proposé par un client à valider"
TEST_ISBN = "9791098765438"


@tagged("post_install", "-at_install", "comic_shop")
class TestPortalModeration(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.portal_partner = cls.env["res.partner"].create({"name": "Client Portail"})
        cls.manager = cls.env["res.users"].create(
            {
                "name": "Gestionnaire Modération",
                "login": "comic_shop_moderation_manager",
                "group_ids": [
                    Command.link(cls.env.ref("base.group_user").id),
                    Command.link(cls.env.ref("comic_shop.group_shop_manager").id),
                ],
            }
        )
        cls.Edition = cls.env["comic.edition"].sudo()

    def _portal_create(self, **data):
        vals = {
            "title": "Album Portail",
            "serie_name": "Série Portail Inédite",
            "editeur_name": "Éditeur Portail Inédit",
            "isbn": "",
            "tome": 1,
            "cover_url": "",
        }
        vals.update(data)
        return self.Edition._create_from_portal_data(vals, self.portal_partner)

    def _portal_activities(self, work):
        return work.activity_ids.filtered(lambda a: a.summary == SUMMARY)

    def test_created_records_are_flagged(self):
        edition = self._portal_create()
        work = edition.work_id
        self.assertTrue(work.a_valider)
        self.assertEqual(work.portal_partner_id, self.portal_partner)
        self.assertTrue(work.serie_id.a_valider)
        self.assertEqual(work.serie_id.portal_partner_id, self.portal_partner)
        self.assertTrue(edition.editeur_id.a_valider)
        self.assertEqual(edition.editeur_id.portal_partner_id, self.portal_partner)

    def test_reused_records_are_not_flagged(self):
        editeur = self.env["comic.editeur"].create({"name": "Éditeur Existant"})
        serie = self.env["comic.serie"].create({"name": "Série Existante"})
        work = self.env["comic.work"].create({"serie_id": serie.id, "titre_canonique": "Album Existant", "tome": 3})
        edition = self._portal_create(
            title="Album Existant", serie_name="Série Existante", editeur_name="Éditeur Existant", tome=3
        )
        self.assertEqual(edition.work_id, work)
        self.assertFalse(work.a_valider)
        self.assertFalse(work.portal_partner_id)
        self.assertFalse(serie.a_valider)
        self.assertFalse(editeur.a_valider)
        self.assertFalse(self._portal_activities(work))

    def test_new_album_in_existing_serie_only_flags_album(self):
        serie = self.env["comic.serie"].create({"name": "Série Connue"})
        edition = self._portal_create(serie_name="Série Connue", tome=7)
        self.assertEqual(edition.work_id.serie_id, serie)
        self.assertFalse(serie.a_valider)
        self.assertTrue(edition.work_id.a_valider)

    def test_activity_created_once_for_manager(self):
        edition = self._portal_create()
        work = edition.work_id
        activities = self._portal_activities(work)
        self.assertEqual(len(activities), 1)
        self.assertIn(activities.user_id, work._get_shop_manager_users())
        # Un second appel ne crée pas de doublon d'activité
        work._schedule_portal_validation_activity()
        self.assertEqual(len(self._portal_activities(work)), 1)
        # Réutilisation de l'album existant : pas de nouvelle activité
        self._portal_create()
        self.assertEqual(len(self._portal_activities(work)), 1)

    def test_no_manager_skips_activity(self):
        Work = self.env["comic.work"]
        self.patch(type(Work), "_get_shop_manager_users", lambda self: self.env["res.users"])
        edition = self._portal_create(title="Album Sans Gestionnaire", serie_name="Série Sans Gestionnaire")
        self.assertTrue(edition.work_id.a_valider)
        self.assertFalse(self._portal_activities(edition.work_id))

    def test_validation_clears_flag(self):
        edition = self._portal_create()
        work = edition.work_id
        work.action_valider_portail()
        work.serie_id.action_valider_portail()
        edition.editeur_id.action_valider_portail()
        self.assertFalse(work.a_valider)
        self.assertFalse(work.serie_id.a_valider)
        self.assertFalse(edition.editeur_id.a_valider)

    def test_product_creation_refused_while_a_valider(self):
        edition = self._portal_create(isbn=TEST_ISBN)
        with self.assertRaises(UserError):
            edition.action_create_product()
        self.assertFalse(edition.product_tmpl_id)

        serie = edition.work_id.serie_id
        self.assertEqual(serie.nb_albums_isbn_sans_produit, 0)
        serie.action_create_products_bulk()
        serie.action_create_products_from_isbn()
        self.assertFalse(edition.product_tmpl_id)

        edition.work_id.action_valider_portail()
        edition.action_create_product()
        self.assertTrue(edition.product_tmpl_id)
