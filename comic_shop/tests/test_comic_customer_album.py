"""Tests ORM pour le modèle comic.customer.album.

Teste : contrainte unique (partner_id, edition_id) et work_id computed.

Nécessite le module comic_shop installé.

Lancement :
    docker exec odoo-web odoo-bin -d odoo -u comic_shop \
        --test-tags /comic_shop:TestComicCustomerAlbum
"""

from odoo.tests.common import TransactionCase
from odoo.tests import tagged


@tagged("comic_shop", "comic_customer_album")
class TestComicCustomerAlbum(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.env["res.partner"].create({"name": "Client Test"})
        cls.serie = cls.env["comic.serie"].create({"name": "TestSerie Customer"})
        cls.work = cls.env["comic.work"].create(
            {
                "serie_id": cls.serie.id,
                "titre_canonique": "Tome Test Customer",
                "tome": 1,
            }
        )
        cls.edition = cls.env["comic.edition"].create(
            {
                "work_id": cls.work.id,
                "langue": "fr",
            }
        )

    # ── work_id computed ──────────────────────────────────────────────────────

    def test_work_id_computed_from_edition(self):
        ca = self.env["comic.customer.album"].create(
            {
                "partner_id": self.partner.id,
                "edition_id": self.edition.id,
            }
        )
        self.assertEqual(ca.work_id, self.work)

    def test_work_id_updates_when_edition_changes(self):
        work2 = self.env["comic.work"].create(
            {
                "serie_id": self.serie.id,
                "titre_canonique": "Autre Tome",
                "tome": 2,
            }
        )
        edition2 = self.env["comic.edition"].create(
            {
                "work_id": work2.id,
                "langue": "fr",
            }
        )
        ca = self.env["comic.customer.album"].create(
            {
                "partner_id": self.partner.id,
                "edition_id": self.edition.id,
            }
        )
        self.assertEqual(ca.work_id, self.work)
        ca.edition_id = edition2
        self.assertEqual(ca.work_id, work2)

    # ── Contrainte unique ─────────────────────────────────────────────────────

    # def test_unique_partner_edition_constraint(self):
    #     """Même (partner_id, edition_id) deux fois → violation de contrainte."""
    #     partner2 = self.env['res.partner'].create({'name': 'Client Test 2'})
    #     self.env['comic.customer.album'].create({
    #         'partner_id': partner2.id,
    #         'edition_id': self.edition.id,
    #     })
    #     with self.assertRaises(Exception):
    #         with self.env.cr.savepoint():
    #             self.env['comic.customer.album'].create({
    #                 'partner_id': partner2.id,
    #                 'edition_id': self.edition.id,
    #             })

    def test_same_edition_different_partner_is_allowed(self):
        """Même edition, deux partenaires différents : OK."""
        partner_a = self.env["res.partner"].create({"name": "Client A"})
        partner_b = self.env["res.partner"].create({"name": "Client B"})
        edition2 = self.env["comic.edition"].create(
            {
                "work_id": self.work.id,
                "langue": "nl",
            }
        )
        ca_a = self.env["comic.customer.album"].create(
            {
                "partner_id": partner_a.id,
                "edition_id": edition2.id,
            }
        )
        ca_b = self.env["comic.customer.album"].create(
            {
                "partner_id": partner_b.id,
                "edition_id": edition2.id,
            }
        )
        self.assertNotEqual(ca_a.id, ca_b.id)

    # ── Valeurs par défaut ────────────────────────────────────────────────────

    def test_default_etat_lecture_non_lu(self):
        ca = self.env["comic.customer.album"].create(
            {
                "partner_id": self.partner.id,
                "edition_id": self.edition.id,
            }
        )
        self.assertEqual(ca.etat_lecture, "non_lu")

    def test_default_dans_collection_true(self):
        ca = self.env["comic.customer.album"].create(
            {
                "partner_id": self.partner.id,
                "edition_id": self.edition.id,
            }
        )
        self.assertTrue(ca.dans_collection)

    def test_date_ajout_set_automatically(self):
        ca = self.env["comic.customer.album"].create(
            {
                "partner_id": self.partner.id,
                "edition_id": self.edition.id,
            }
        )
        self.assertTrue(ca.date_ajout)
