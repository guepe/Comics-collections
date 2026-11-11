"""API de l'app mobile (US-093) : scan, collection, série, wishlist, ajout, lecture."""

from odoo.exceptions import UserError
from odoo.tests import new_test_user, tagged
from odoo.tests.common import TransactionCase


@tagged("post_install", "-at_install", "comic_mobile")
class TestMobileApi(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        groups = "comics_collections.group_comic_user"
        cls.user = new_test_user(cls.env, login="mobile_user", groups=groups)
        cls.other = new_test_user(cls.env, login="mobile_other", groups=groups)
        cls.serie = cls.env["comic.serie"].create({"name": "Série Mobile Test"})
        Work = cls.env["comic.work"]
        cls.works = Work.browse()
        isbns = ["9791099000019", "9791099000026", "9791099000033"]
        for tome, isbn in enumerate(isbns, start=1):
            work = Work.create({"serie_id": cls.serie.id, "titre_canonique": f"Tome mobile {tome}", "tome": tome})
            cls.env["comic.isbn"].create({"edition_id": work.primary_edition_id.id, "isbn_13": isbn})
            cls.works |= work
        cls.w1, cls.w2, cls.w3 = cls.works
        Album = cls.env["comic.customer.album"]
        for work in (cls.w1, cls.w2):
            Album.create(
                {
                    "partner_id": cls.user.partner_id.id,
                    "edition_id": work.primary_edition_id.id,
                    "etat_lecture": "lu",
                }
            )
        cls.api = cls.env["comic.mobile.api"].with_user(cls.user)

    def test_scan_missing_next_volume(self):
        res = self.api.mobile_scan("979-10-99000-03-3")
        self.assertEqual(res["status"], "missing")
        self.assertEqual(res["work_id"], self.w3.id)
        self.assertTrue(res["is_next"])
        self.assertEqual((res["serie_owned"], res["serie_total"]), (2, 3))
        self.assertEqual([t["owned"] for t in res["strip"]], [True, True, False])

    def test_scan_owned_unknown_invalid(self):
        self.assertEqual(self.api.mobile_scan("9791099000019")["status"], "owned")
        self.assertEqual(self.api.mobile_scan("9780000000002")["status"], "unknown")
        with self.assertRaises(UserError):
            self.api.mobile_scan("12345")

    def test_add_wishlist_then_collection(self):
        res = self.api.mobile_add(self.w3.id, "wishlist")
        self.assertEqual(res["status"], "wished")
        res = self.api.mobile_add(self.w3.id, "collection")
        self.assertEqual(res["status"], "owned")
        # Un album possédé n'est jamais déclassé en wishlist
        self.assertEqual(self.api.mobile_add(self.w3.id, "wishlist")["status"], "owned")

    def test_collection_filters_and_privacy(self):
        res = self.api.mobile_get_collection()
        self.assertEqual(res["total"], 2)
        self.assertEqual([a["tome"] for a in res["albums"]], [1, 2])
        self.assertEqual(self.api.mobile_get_collection(reading="non_lu")["total"], 0)
        self.assertEqual(self.api.mobile_get_collection(search="Tome mobile 2")["total"], 1)
        other = self.env["comic.mobile.api"].with_user(self.other)
        self.assertEqual(other.mobile_get_collection()["total"], 0)
        self.assertEqual(other.mobile_scan("9791099000019")["status"], "missing")

    def test_reading_status(self):
        res = self.api.mobile_set_reading(self.w1.id, "en_cours")
        self.assertEqual(res["reading"], "en_cours")
        with self.assertRaises(UserError):
            self.api.mobile_set_reading(self.w3.id, "lu")
        with self.assertRaises(UserError):
            self.api.mobile_set_reading(self.w1.id, "bidon")

    def test_serie_and_follow(self):
        res = self.api.mobile_get_serie(self.serie.id)
        self.assertEqual((res["owned"], res["total"], res["read"]), (2, 3, 2))
        self.assertEqual([a["missing"] for a in res["albums"]], [False, False, True])
        # Série commencée : suivie automatiquement (US-088)
        self.assertTrue(res["followed"])
        self.assertFalse(self.api.mobile_set_follow(self.serie.id, False)["followed"])
        self.assertTrue(self.api.mobile_set_follow(self.serie.id, True)["followed"])

    def test_wishlist_and_summary(self):
        self.api.mobile_set_follow(self.serie.id, True)
        res = self.api.mobile_get_wishlist()
        self.assertEqual(res["missing"], 1)
        group = res["groups"][0]
        self.assertEqual(group["serie_id"], self.serie.id)
        self.assertEqual([i["work_id"] for i in group["items"]], [self.w3.id])
        self.assertEqual((group["owned"], group["total"]), (2, 3))
        summary = self.api.mobile_get_summary()
        self.assertEqual((summary["albums"], summary["series"], summary["missing"]), (2, 1, 1))

    def test_collection_keys_unique_with_two_editions(self):
        """Un album possédé en deux éditions donne deux cartes de clés distinctes (pas de page blanche)."""
        second = self.env["comic.edition"].create({"work_id": self.w1.id})
        self.env["comic.customer.album"].create({"partner_id": self.user.partner_id.id, "edition_id": second.id})
        albums = self.api.mobile_get_collection()["albums"]
        keys = [a["key"] for a in albums]
        self.assertEqual(len(keys), 3)
        self.assertEqual(len(set(keys)), 3)
