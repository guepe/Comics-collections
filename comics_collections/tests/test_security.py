"""Tests des règles d'accès — catalogue partagé.

Séries / albums / éditions : visibles et modifiables par tout utilisateur BD,
suppression limitée au créateur (ou au gestionnaire). Prêts : privés.

Lancement :
    docker exec odoo-web odoo-bin -d odoo -u comics_collections \
        --test-tags /comics_collections:TestCatalogSecurity
"""

from odoo.exceptions import AccessError
from odoo.tests import new_test_user, tagged
from odoo.tests.common import TransactionCase
from odoo.tools import mute_logger


@tagged("post_install", "-at_install", "comics_collections", "comic_security")
class TestCatalogSecurity(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        groups = "comics_collections.group_comic_user"
        cls.user_a = new_test_user(cls.env, login="comic_user_a", groups=groups)
        cls.user_b = new_test_user(cls.env, login="comic_user_b", groups=groups)
        cls.manager = new_test_user(cls.env, login="comic_manager", groups="comics_collections.group_comic_manager")

        env_a = cls.env(user=cls.user_a)
        cls.serie = env_a["comic.serie"].create({"name": "Série partagée"})
        cls.work = env_a["comic.work"].create({"serie_id": cls.serie.id, "titre_canonique": "Album A", "tome": 1})
        cls.edition = cls.work.edition_ids[:1] or env_a["comic.edition"].create({"work_id": cls.work.id})
        cls.isbn = env_a["comic.isbn"].create({"edition_id": cls.edition.id, "isbn_13": "9782800152851"})
        borrower = cls.env["res.partner"].create({"name": "Emprunteur"})
        cls.pret = env_a["comic.pret"].create({"edition_id": cls.edition.id, "partner_id": borrower.id})

    def test_other_user_reads_shared_catalog(self):
        env_b = self.env(user=self.user_b)
        self.assertIn(self.serie, env_b["comic.serie"].search([]))
        self.assertIn(self.work, env_b["comic.work"].search([]))
        self.assertIn(self.edition, env_b["comic.edition"].search([]))
        isbn = env_b["comic.isbn"].search([("isbn_13", "=", "9782800152851")])
        self.assertEqual(isbn.edition_id.work_id, self.work.with_user(self.user_b))

    def test_other_user_can_edit_shared_catalog(self):
        self.work.with_user(self.user_b).write({"titre_canonique": "Album A corrigé"})
        self.assertEqual(self.work.titre_canonique, "Album A corrigé")

    def test_other_user_cannot_delete(self):
        with self.assertRaises(AccessError), mute_logger("odoo.models"):
            self.serie.with_user(self.user_b).unlink()

    def test_creator_can_delete_own_serie(self):
        serie = self.env(user=self.user_b)["comic.serie"].create({"name": "Série de B"})
        serie.unlink()
        self.assertFalse(serie.exists())

    def test_manager_can_delete_any(self):
        serie = self.env(user=self.user_a)["comic.serie"].create({"name": "Série à supprimer"})
        serie.with_user(self.manager).unlink()
        self.assertFalse(serie.exists())

    def test_prets_are_private(self):
        self.assertNotIn(self.pret, self.env(user=self.user_b)["comic.pret"].search([]))
        self.assertIn(self.pret, self.env(user=self.user_a)["comic.pret"].search([]))
        self.assertIn(self.pret, self.env(user=self.manager)["comic.pret"].search([]))
