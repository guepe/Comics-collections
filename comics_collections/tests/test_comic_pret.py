"""Tests ORM pour le modèle comic.pret.

Teste : création d'un prêt, retour effectif, champs date.

Lancement :
    docker exec odoo-web odoo-bin -d odoo -u comics_collections \
        --test-tags /comics_collections:TestComicPret
"""

from datetime import date, timedelta

from odoo.exceptions import ValidationError
from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged("comics_collections", "comic_pret")
class TestComicPret(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.env["res.partner"].create({"name": "Lecteur Test"})
        serie = cls.env["comic.serie"].create({"name": "Série Prêt"})
        work = cls.env["comic.work"].create(
            {
                "serie_id": serie.id,
                "titre_canonique": "Album Prêt T1",
                "tome": 1,
            }
        )
        cls.edition = cls.env["comic.edition"].create({"work_id": work.id})
        cls.Pret = cls.env["comic.pret"]

    def test_create_pret(self):
        """Création d'un prêt valide — retourne=False par défaut."""
        pret = self.Pret.create(
            {
                "edition_id": self.edition.id,
                "partner_id": self.partner.id,
                "date_pret": date.today(),
                "date_retour_prevue": date.today() + timedelta(days=14),
            }
        )
        self.assertFalse(pret.retourne)
        self.assertFalse(pret.date_retour_effective)

    def test_retour_effectif(self):
        """Marquer retourne=True et enregistrer la date de retour réelle."""
        pret = self.Pret.create(
            {
                "edition_id": self.edition.id,
                "partner_id": self.partner.id,
                "date_pret": date.today(),
            }
        )
        today = date.today()
        pret.write({"retourne": True, "date_retour_effective": today})
        self.assertTrue(pret.retourne)
        self.assertEqual(pret.date_retour_effective, today)

    def test_pret_sans_date_retour_prevue(self):
        """Un prêt sans date de retour prévue (effacée volontairement) est valide."""
        pret = self.Pret.create(
            {
                "edition_id": self.edition.id,
                "partner_id": self.partner.id,
                "date_pret": date.today(),
                "date_retour_prevue": False,
            }
        )
        self.assertFalse(pret.date_retour_prevue)
        self.assertTrue(pret.id)

    def test_plusieurs_prets_meme_edition(self):
        """Prêts successifs sur la même édition : autorisés une fois le premier rendu."""
        partner2 = self.env["res.partner"].create({"name": "Deuxième Lecteur"})
        first = self.Pret.create({"edition_id": self.edition.id, "partner_id": self.partner.id})
        first.action_retourner()
        second = self.Pret.create({"edition_id": self.edition.id, "partner_id": partner2.id})
        self.assertTrue(second.id)

    def test_double_pret_simultane_refuse(self):
        self.Pret.create({"edition_id": self.edition.id, "partner_id": self.partner.id})
        partner2 = self.env["res.partner"].create({"name": "Deuxième Lecteur"})
        with self.assertRaises(ValidationError):
            self.Pret.create({"edition_id": self.edition.id, "partner_id": partner2.id})

    def test_defaults(self):
        pret = self.Pret.create({"edition_id": self.edition.id, "partner_id": self.partner.id})
        self.assertEqual(pret.date_pret, date.today())
        self.assertEqual(pret.date_retour_prevue, date.today() + timedelta(days=30))

    def test_action_retourner_sets_date(self):
        pret = self.Pret.create({"edition_id": self.edition.id, "partner_id": self.partner.id})
        pret.action_retourner()
        self.assertTrue(pret.retourne)
        self.assertEqual(pret.date_retour_effective, date.today())

    def test_cocher_retourne_remplit_date_et_decocher_l_efface(self):
        pret = self.Pret.create({"edition_id": self.edition.id, "partner_id": self.partner.id})
        pret.retourne = True
        self.assertEqual(pret.date_retour_effective, date.today())
        pret.retourne = False
        self.assertFalse(pret.date_retour_effective)

    def test_dates_incoherentes_refusees(self):
        with self.assertRaises(ValidationError):
            self.Pret.create(
                {
                    "edition_id": self.edition.id,
                    "partner_id": self.partner.id,
                    "date_pret": date.today(),
                    "date_retour_prevue": date.today() - timedelta(days=1),
                }
            )

    def test_en_retard_et_rappel(self):
        pret = self.Pret.create(
            {
                "edition_id": self.edition.id,
                "partner_id": self.partner.id,
                "date_pret": date.today() - timedelta(days=40),
                "date_retour_prevue": date.today() - timedelta(days=10),
            }
        )
        self.assertTrue(pret.en_retard)
        self.assertIn(pret, self.Pret.search([("en_retard", "=", True)]))
        self.Pret._cron_remind_overdue()
        self.assertEqual(len(pret.activity_ids), 1)
        self.Pret._cron_remind_overdue()
        self.assertEqual(len(pret.activity_ids), 1, "Pas de doublon d'activité")
        pret.action_retourner()
        self.assertFalse(pret.en_retard)
