"""Refus d'un album proposé depuis le portail.

Lancement :
    docker exec odoo-web odoo -d odoo -u comic_shop --test-tags /comic_shop:TestPortalRefuse
"""

from odoo.exceptions import UserError
from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged("post_install", "-at_install", "comic_shop", "portal_refuse")
class TestPortalRefuse(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.env["res.partner"].create({"name": "Client Proposant"})
        cls.Album = cls.env["comic.customer.album"]
        cls.Wizard = cls.env["comic.portal.refuse.wizard"]
        # Album existant (validé) qui servira de cible
        cls.target = cls.env["comic.work"].create({"titre_canonique": "Album Officiel", "tome": 1})

    def _propose(self, isbn="", serie="Série Proposée Unique", editeur="Éditeur Proposé Unique"):
        edition = self.env["comic.edition"].sudo()._create_from_portal_data(
            {"title": "Album Proposé", "serie_name": serie, "editeur_name": editeur, "isbn": isbn, "tome": 2},
            self.partner,
        )
        self.Album.create({"partner_id": self.partner.id, "edition_id": edition.id, "source": "achete_ailleurs"})
        return edition.work_id

    def test_refuse_incorrect_removes_everything(self):
        work = self._propose()
        serie, editeur = work.serie_id, work.edition_ids.editeur_id
        self.assertTrue(serie.a_valider and editeur.a_valider)
        self.Wizard.create({"work_id": work.id, "motif": "incorrect"}).action_refuse()
        self.assertFalse(work.exists())
        self.assertFalse(self.Album.search([("partner_id", "=", self.partner.id)]))
        self.assertFalse(serie.exists(), "Série créée par le client et devenue vide : supprimée")
        self.assertFalse(editeur.exists())

    def test_refuse_doublon_moves_library_and_isbn(self):
        work = self._propose(isbn="9782800152851")
        self.Wizard.create({"work_id": work.id, "motif": "doublon", "target_work_id": self.target.id}).action_refuse()
        self.assertFalse(work.exists())
        entry = self.Album.search([("partner_id", "=", self.partner.id)])
        self.assertEqual(entry.edition_id, self.target.primary_edition_id)
        self.assertEqual(entry.source, "achete_ailleurs")
        self.assertEqual(self.target.isbn_ids.isbn_13, "9782800152851")

    def test_refuse_doublon_when_customer_already_owns_target(self):
        work = self._propose()
        self.Album.create({"partner_id": self.partner.id, "edition_id": self.target.primary_edition_id.id})
        self.Wizard.create({"work_id": work.id, "motif": "doublon", "target_work_id": self.target.id}).action_refuse()
        self.assertEqual(len(self.Album.search([("partner_id", "=", self.partner.id)])), 1)

    def test_existing_serie_is_kept(self):
        serie = self.env["comic.serie"].create({"name": "Série Déjà Là"})
        self.env["comic.work"].create({"serie_id": serie.id, "titre_canonique": "Autre", "tome": 9})
        work = self._propose(serie="Série Déjà Là")
        self.Wizard.create({"work_id": work.id, "motif": "incorrect"}).action_refuse()
        self.assertTrue(serie.exists())

    def test_customer_is_notified(self):
        work = self._propose()
        before = self.env["mail.message"].search_count([("model", "=", "res.partner"), ("res_id", "=", self.partner.id)])
        self.Wizard.create({"work_id": work.id, "motif": "incorrect", "message": "Titre illisible"}).action_refuse()
        msgs = self.env["mail.message"].search([("model", "=", "res.partner"), ("res_id", "=", self.partner.id)])
        self.assertEqual(len(msgs), before + 1)
        self.assertIn("Titre illisible", msgs[0].body)

    def test_doublon_requires_target(self):
        work = self._propose()
        with self.assertRaises(UserError):
            self.Wizard.create({"work_id": work.id, "motif": "doublon"}).action_refuse()
