"""Tests pour la synchronisation comic.edition → product.template.

Teste : action_create_product, idempotence, _sync_to_product.

Lancement :
    docker exec odoo-web odoo-bin -d odoo -u comic_shop \
        --test-tags /comic_shop:TestSyncProduct
"""

from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged("comic_shop", "sync_product")
class TestSyncProduct(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        serie = cls.env["comic.serie"].create({"name": "Série Shop"})
        cls.work = cls.env["comic.work"].create(
            {
                "serie_id": serie.id,
                "titre_canonique": "Album Shop T1",
                "tome": 1,
            }
        )
        cls.edition = cls.env["comic.edition"].create({"work_id": cls.work.id})

    def test_action_create_product_creates_product_template(self):
        """action_create_product() crée un product.template lié à l'édition."""
        self.assertFalse(self.edition.product_tmpl_id)
        self.edition.action_create_product()
        self.assertTrue(self.edition.product_tmpl_id)

    def test_action_create_product_raises_if_already_linked(self):
        """Appeler action_create_product() sur une édition déjà liée lève UserError."""
        from odoo.exceptions import UserError

        self.edition.action_create_product()
        with self.assertRaises(UserError):
            self.edition.action_create_product()

    def test_sync_to_product_updates_product_name(self):
        """_sync_to_product() répercute le titre de l'album sur le produit."""
        self.edition.action_create_product()
        self.work.write({"titre_canonique": "Titre Modifié T1"})
        self.edition._sync_to_product()
        self.assertIn("Modifié", self.edition.product_tmpl_id.name)

    def test_edition_without_product_sync_does_nothing(self):
        """_sync_to_product() sur une édition sans produit ne lève pas d'erreur."""
        edition2 = self.env["comic.edition"].create({"work_id": self.work.id})
        self.assertFalse(edition2.product_tmpl_id)
        edition2._sync_to_product()  # ne doit pas lever d'exception
