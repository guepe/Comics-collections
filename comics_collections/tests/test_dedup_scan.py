"""Tests du scan de doublons par blocking et du nettoyage des paires après fusion.

Lancement :
    docker exec odoo-web odoo-bin -d odoo -u comics_collections \
        --test-tags /comics_collections:TestDedupScan
"""

from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged("post_install", "-at_install", "comics_collections")
class TestDedupScan(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Pair = cls.env["comic.dedup.pair"]
        cls.Work = cls.env["comic.work"].with_context(skip_dedup_check=True)
        cls.serie = cls.env["comic.serie"].create({"name": "Xyzzorgal Dedupscan"})
        cls.serie_typo = cls.env["comic.serie"].create({"name": "Xyzzorgal Dedupscann"})
        cls.serie_other = cls.env["comic.serie"].create({"name": "Qwvblacksad Dedupscan"})

    def _work(self, titre, serie, tome):
        return self.Work.create({"titre_canonique": titre, "serie_id": serie.id, "tome": tome})

    def _pair_between(self, wa, wb):
        return self.Pair.search(
            [
                "|",
                "&",
                ("work_a_id", "=", wa.id),
                ("work_b_id", "=", wb.id),
                "&",
                ("work_a_id", "=", wb.id),
                ("work_b_id", "=", wa.id),
            ]
        )

    # ── Blocking ─────────────────────────────────────────────────────────────

    def test_scan_finds_probable_duplicate_same_serie(self):
        w1 = self._work("Les Zorbules perdues", self.serie, 501)
        w2 = self._work("Zorbules perdues (Les)", self.serie, 502)
        self.Pair.action_scan_all()
        pair = self._pair_between(w1, w2)
        self.assertEqual(len(pair), 1)
        self.assertEqual(pair.reason, "doublon_probable")
        self.assertAlmostEqual(pair.score, 0.9)

    def test_scan_finds_possible_duplicate_across_similar_series(self):
        w1 = self._work("La Magiquenne trahie", self.serie, 511)
        w2 = self._work("La Magiquenne trahie", self.serie_typo, 511)
        self.Pair.action_scan_all()
        pair = self._pair_between(w1, w2)
        self.assertEqual(len(pair), 1)
        self.assertEqual(pair.reason, "doublon_possible")
        self.assertGreaterEqual(pair.score, 0.7)

    def test_scan_ignores_unrelated_albums(self):
        w1 = self._work("Kwazimodo du soir", self.serie, 521)
        w2 = self._work("Kwazimodo du soir", self.serie_other, 521)
        self.Pair.action_scan_all()
        self.assertFalse(self._pair_between(w1, w2))

    def test_blocking_does_not_compare_unrelated_buckets(self):
        rows = [
            {"id": 1, "tome": 1, "titre": "magicienne trahie", "serie_id": 10, "serie_norm": "thorgal"},
            {"id": 2, "tome": 2, "titre": "ile des mers gelees", "serie_id": 10, "serie_norm": "thorgal"},
            {"id": 3, "tome": 1, "titre": "magicienne trahie", "serie_id": 11, "serie_norm": "thorgall"},
            {"id": 4, "tome": 1, "titre": "quelque part", "serie_id": 12, "serie_norm": "blacksad"},
            {"id": 5, "tome": 1, "titre": "magicienne trahie", "serie_id": 13, "serie_norm": "blacksad"},
        ]
        compared = {tuple(sorted((a["id"], b["id"]))) for a, b in self.Pair._iter_blocked_pairs(rows)}
        # Same serie (1, 2) and same title/serie prefixes (1, 3)
        self.assertIn((1, 2), compared)
        self.assertIn((1, 3), compared)
        # Different title prefix within blacksad-like series: never compared
        self.assertNotIn((4, 5), compared)
        # Same title but serie prefixes differ: never compared
        self.assertNotIn((1, 5), compared)
        self.assertNotIn((3, 5), compared)
        self.assertNotIn((2, 4), compared)
        # Each pair is yielded once even when it shares several buckets
        pairs = [tuple(sorted((a["id"], b["id"]))) for a, b in self.Pair._iter_blocked_pairs(rows)]
        self.assertEqual(len(pairs), len(set(pairs)))

    def test_score_rows_matches_score_pair_semantics(self):
        ra = {"id": 1, "tome": 3, "titre": "abc", "serie_id": 10, "serie_norm": "serie"}
        rb = {"id": 2, "tome": 3, "titre": "zzzzzz", "serie_id": 10, "serie_norm": "serie"}
        # Same serie + same tome: conflit_certain even with unrelated titles
        self.assertEqual(self.Pair._score_rows(ra, rb), (1.0, "conflit_certain"))
        rb = dict(rb, tome=4)
        self.assertEqual(self.Pair._score_rows(ra, rb), (0.0, ""))

    # ── Nettoyage après fusion ───────────────────────────────────────────────

    def test_pairs_cleaned_after_merge(self):
        wa = self._work("Album source nettoyage", self.serie, 531)
        wb = self._work("Album cible nettoyage", self.serie, 532)
        wc = self._work("Album tiers nettoyage", self.serie, 533)
        pair_ab = self.Pair.create({"work_a_id": wa.id, "work_b_id": wb.id, "score": 0.9})
        pair_ca = self.Pair.create({"work_a_id": wc.id, "work_b_id": wa.id, "score": 0.9})
        pair_bc = self.Pair.create({"work_a_id": wb.id, "work_b_id": wc.id, "score": 0.9})

        action = pair_ab.action_open_merge_wizard()
        wizard = self.env["comic.work.merge.wizard"].with_context(**action["context"]).create({})
        wizard.action_confirm_merge()

        self.assertFalse(wa.active)
        self.assertFalse(pair_ab.exists())
        self.assertFalse(pair_ca.exists(), "Les paires de l'album archivé doivent être supprimées")
        self.assertTrue(pair_bc.exists())

    def test_merge_into_cleans_pairs_directly(self):
        wa = self._work("Source directe", self.serie, 541)
        wb = self._work("Cible directe", self.serie, 542)
        pair = self.Pair.create({"work_a_id": wa.id, "work_b_id": wb.id, "score": 0.9, "ignored": True})
        wa._merge_into(wb)
        self.assertFalse(pair.exists())

    def test_scan_drops_pairs_on_archived_albums(self):
        wa = self._work("Archivé hors fusion", self.serie, 551)
        wb = self._work("Actif hors fusion", self.serie, 552)
        pair = self.Pair.create({"work_a_id": wa.id, "work_b_id": wb.id, "score": 0.9, "ignored": True})
        wa.with_context(skip_dedup_check=True).write({"active": False})
        self.Pair.action_scan_all()
        self.assertFalse(pair.exists())

    # ── Fusion B → A ─────────────────────────────────────────────────────────

    def test_merge_b_into_a(self):
        wa = self._work("Album A inverse", self.serie, 561)
        wb = self._work("Album B inverse", self.serie, 562)
        nb_editions_b = len(wb.edition_ids)
        nb_editions_a = len(wa.edition_ids)
        pair = self.Pair.create({"work_a_id": wa.id, "work_b_id": wb.id, "score": 0.9})

        action = pair.action_open_merge_wizard_reverse()
        self.assertEqual(action["context"]["default_source_work_id"], wb.id)
        self.assertEqual(action["context"]["default_target_work_id"], wa.id)
        wizard = self.env["comic.work.merge.wizard"].with_context(**action["context"]).create({})
        wizard.action_confirm_merge()

        self.assertTrue(wa.active)
        self.assertFalse(wb.active)
        self.assertEqual(len(wa.edition_ids), nb_editions_a + nb_editions_b)
        self.assertFalse(pair.exists())
