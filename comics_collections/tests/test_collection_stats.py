"""Bibliothèque personnelle dans le cœur : statistiques, droits, état de lecture, migration."""

import datetime
import importlib.util

from odoo.tests import new_test_user, tagged
from odoo.tests.common import TransactionCase
from odoo.tools.misc import file_path


@tagged("post_install", "-at_install", "comics_collections", "comic_collection_stats")
class TestCollectionStats(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = new_test_user(cls.env, login="stats_user", groups="comics_collections.group_comic_user")
        cls.other = new_test_user(cls.env, login="stats_other", groups="comics_collections.group_comic_user")
        cls.genre = cls.env["comic.genre"].create({"name": "Genre Stats"})
        cls.serie_full = cls.env["comic.serie"].create({"name": "Série Complète Stats", "genre_id": cls.genre.id})
        cls.serie_part = cls.env["comic.serie"].create({"name": "Série Partielle Stats"})
        cls.editions = {}
        for serie, tomes in ((cls.serie_full, (1, 2)), (cls.serie_part, (1, 2, 3))):
            for tome in tomes:
                work = cls.env["comic.work"].create(
                    {"serie_id": serie.id, "titre_canonique": f"{serie.name} T{tome}", "tome": tome}
                )
                cls.editions[(serie.id, tome)] = cls.env["comic.edition"].create({"work_id": work.id})
        Album = cls.env["comic.customer.album"]
        partner = cls.user.partner_id

        def add(serie, tome, **vals):
            return Album.create({"partner_id": partner.id, "edition_id": cls.editions[(serie.id, tome)].id, **vals})

        add(cls.serie_full, 1, etat_lecture="lu", note=5, date_ajout=datetime.date(2026, 1, 1))
        add(cls.serie_full, 2, etat_lecture="en_cours", note=4, date_ajout=datetime.date(2026, 2, 1))
        add(cls.serie_part, 1, note=2, date_ajout=datetime.date(2026, 3, 1))
        add(cls.serie_part, 3, dans_collection=False, dans_wishlist=True)
        # Bruit : bibliothèque d'un autre utilisateur
        Album.create({"partner_id": cls.other.partner_id.id, "edition_id": cls.editions[(cls.serie_part.id, 2)].id})

    def _stats(self, **kw):
        return self.env["comic.customer.album"]._get_collection_stats(self.user.partner_id, **kw)

    def test_counts(self):
        stats = self._stats()
        self.assertEqual(stats["nb_albums"], 3)
        # Suivi automatique (US-088) : posséder un album fait suivre sa série, donc le
        # tome 2 de la série partielle (possédé par un autre) devient un manque (US-089).
        self.assertEqual(stats["nb_souhaits"], 1)
        self.assertEqual(stats["nb_manques"], 1)
        self.assertEqual(stats["nb_wishlist"], 2)
        self.assertEqual(stats["nb_series"], 2)
        self.assertEqual(stats["series_completes"], 1)
        self.assertEqual(stats["series_en_cours"], 1)

    def test_breakdowns(self):
        stats = self._stats()
        self.assertEqual(dict(stats["by_genre"]), {"Genre Stats": 2, "No genre": 1})
        reading = {key: count for key, _label, count in stats["by_reading"]}
        self.assertEqual(reading, {"non_lu": 1, "en_cours": 1, "lu": 1})

    def test_top_series_and_recent(self):
        stats = self._stats()
        self.assertEqual(
            [row["name"] for row in stats["top_series"]], ["Série Complète Stats", "Série Partielle Stats"]
        )
        self.assertEqual(stats["top_series"][0]["note"], 4.5)
        self.assertEqual(stats["recent"][0]["date"], datetime.date(2026, 3, 1))
        self.assertEqual(len(stats["recent"]), 3)

    def test_loans_only_on_request(self):
        self.assertNotIn("loans_late", self._stats())
        self.assertEqual(self._stats(include_loans=True)["loans_late"], 0)

    def test_user_sees_only_own_entries(self):
        Album = self.env["comic.customer.album"].with_user(self.user)
        self.assertEqual(Album.search_count([]), 4)
        self.assertFalse(Album.search([("partner_id", "=", self.other.partner_id.id)]))

    def test_mark_read_adds_to_library(self):
        work = self.editions[(self.serie_part.id, 2)].work_id
        work.with_user(self.user).action_mark_lu()
        entry = self.env["comic.customer.album"].search(
            [("partner_id", "=", self.user.partner_id.id), ("work_id", "=", work.id)]
        )
        self.assertEqual(entry.etat_lecture, "lu")
        self.assertTrue(entry.dans_collection)

    def test_migration_moves_xmlids(self):
        """The pre-migrate script reassigns comic_shop xmlids of the model to the core."""
        path = file_path("comics_collections/migrations/19.0.3.0.0/pre-migrate.py")
        spec = importlib.util.spec_from_file_location("comics_pre_migrate_3", path)
        migration = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(migration)
        names = migration._xmlids_to_move()
        self.assertIn("model_comic_customer_album", names)
        self.assertIn("field_comic_customer_album__note", names)
        self.assertNotIn("field_comic_customer_album__sale_order_line_id", names)
        self.assertNotIn("selection__comic_customer_album__source__achete_ici", names)
        model_xmlid = self.env["ir.model.data"].search(
            [("model", "=", "ir.model"), ("name", "=", "model_comic_customer_album")]
        )
        self.assertIn("comics_collections", model_xmlid.mapped("module"))
