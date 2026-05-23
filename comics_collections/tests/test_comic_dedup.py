"""Tests pour le moteur de déduplication (US-056).

Lancement :
    docker exec odoo-web odoo-bin -d odoo -u comics_collections \
        --test-tags /comics_collections:TestNormalize,TestDedupEngine,TestMerge
"""
from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase
from odoo.tests import tagged

from ..utils.normalize import normalize_title


@tagged('comics_collections', 'normalize')
class TestNormalize(TransactionCase):

    def test_strips_leading_les(self):
        self.assertEqual(normalize_title('Les Landes perdues'), 'landes perdues')

    def test_strips_trailing_les_parentheses(self):
        self.assertEqual(normalize_title('Landes perdues (Les)'), 'landes perdues')

    def test_both_forms_are_identical(self):
        self.assertEqual(
            normalize_title('Les Landes perdues'),
            normalize_title('Landes perdues (Les)'),
        )

    def test_strips_accents(self):
        result = normalize_title("l'Enfant des étoiles")
        self.assertNotIn('é', result)
        self.assertIn('etoiles', result)

    def test_case_insensitive(self):
        self.assertEqual(normalize_title('Thorgal'), normalize_title('THORGAL'))

    def test_strips_leading_le(self):
        self.assertEqual(normalize_title('Le Grand Pouvoir'), 'grand pouvoir')

    def test_strips_leading_la(self):
        self.assertEqual(normalize_title("La Marque des Démons"), 'marque des demons')

    def test_strips_leading_l_apostrophe(self):
        self.assertEqual(normalize_title("l'Île mystérieuse"), 'ile mysterieuse')

    def test_empty_string(self):
        self.assertEqual(normalize_title(''), '')

    def test_none_returns_empty(self):
        self.assertEqual(normalize_title(None), '')

    def test_strips_punctuation(self):
        result = normalize_title("Tintin, l'aventurier!")
        self.assertNotIn(',', result)
        self.assertNotIn('!', result)


@tagged('comics_collections', 'dedup_engine')
class TestDedupEngine(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.serie_a = cls.env['comic.serie'].create({'name': 'Thorgal'})
        cls.serie_b = cls.env['comic.serie'].create({'name': 'Blacksad'})

    def _make_work(self, titre, serie=None, tome=1):
        vals = {'titre_canonique': titre, 'tome': tome}
        if serie:
            vals['serie_id'] = serie.id
        return self.env['comic.work'].create(vals)

    # ── _find_duplicate_candidates ───────────────────────────────────────────

    def test_conflit_certain_same_serie_tome(self):
        # _find_duplicate_candidates simulates searching BEFORE creating a new record.
        # Call on an empty recordset so exclude_self doesn't filter out the existing work.
        w1 = self._make_work('La Magicienne trahie', self.serie_a, 1)
        candidates = self.env['comic.work']._find_duplicate_candidates(
            self.serie_a.id, 1, 'Autre titre')
        certain = [c for c in candidates if c['reason'] == 'conflit_certain']
        self.assertTrue(certain, "Doit détecter un conflit certain sur (serie, tome)")
        self.assertEqual(certain[0]['work'], w1)
        self.assertAlmostEqual(certain[0]['score'], 1.0)

    def test_doublon_probable_same_serie_similar_title(self):
        w1 = self._make_work('Les Landes perdues', self.serie_a, 5)
        # Same serie, different tome, title normalized identically → doublon_probable
        candidates = self.env['comic.work']._find_duplicate_candidates(
            self.serie_a.id, 99, 'Landes perdues (Les)')
        probable = [c for c in candidates if c['reason'] == 'doublon_probable']
        self.assertTrue(probable, "Doit détecter un doublon probable (même série, titre ~= )")
        found = next(c for c in probable if c['work'] == w1)
        self.assertAlmostEqual(found['score'], 0.9)

    def test_doublon_possible_similar_serie_and_title(self):
        serie_c = self.env['comic.serie'].create({'name': 'Thorgall'})  # typo vs Thorgal
        w1 = self._make_work('La Magicienne trahie', self.serie_a, 1)
        # Different serie (similar name), same title → doublon_possible
        candidates = self.env['comic.work']._find_duplicate_candidates(
            serie_c.id, 1, 'La Magicienne trahie')
        possible = [c for c in candidates if c['reason'] in ('doublon_possible', 'doublon_probable')]
        self.assertTrue(possible, "Doit détecter un doublon possible (séries similaires)")

    def test_no_candidate_different_serie_different_title(self):
        self._make_work('Quelque chose complètement différent', self.serie_b, 1)
        w2 = self._make_work('Album sans rapport', self.serie_a, 50)
        candidates = w2._find_duplicate_candidates(self.serie_a.id, 50, 'Album sans rapport')
        # w2 itself is excluded (exclude_self=True)
        # The Blacksad album has a completely different title → no candidate
        self.assertFalse(
            any(c['work'].serie_id == self.serie_b for c in candidates),
            "Ne doit pas détecter de doublon entre deux albums sans rapport",
        )

    def test_exclude_self_is_true_by_default(self):
        w = self._make_work('L\'éternité', self.serie_a, 10)
        candidates = w._find_duplicate_candidates(self.serie_a.id, 10, "L'éternité")
        ids = [c['work'].id for c in candidates]
        self.assertNotIn(w.id, ids, "L'album lui-même ne doit pas apparaître dans les candidats")

    # ── @api.constrains ──────────────────────────────────────────────────────

    def test_constrains_blocks_same_normalized_title_same_serie(self):
        self._make_work('Les Landes perdues', self.serie_a, 3)
        with self.assertRaises(UserError):
            # "Landes perdues (Les)" normalise identiquement
            self._make_work('Landes perdues (Les)', self.serie_a, 4)

    def test_constrains_allows_same_title_different_serie(self):
        self._make_work('Le Roi des rois', self.serie_a, 6)
        # Same title, different serie → should not raise
        w2 = self._make_work('Le Roi des rois', self.serie_b, 6)
        self.assertTrue(w2.id > 0)

    def test_constrains_skip_with_context(self):
        self._make_work('Les Landes perdues', self.serie_a, 7)
        # With skip_dedup_check context, the constrains should not fire
        w = self.env['comic.work'].with_context(skip_dedup_check=True).create({
            'serie_id': self.serie_a.id,
            'titre_canonique': 'Landes perdues (Les)',
            'tome': 8,
        })
        self.assertTrue(w.id > 0)


@tagged('comics_collections', 'merge')
class TestMerge(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.serie = cls.env['comic.serie'].create({'name': 'Thorgal'})
        cls.editeur = cls.env['comic.editeur'].create({'name': 'Le Lombard'})

    def _make_work(self, titre, tome):
        return self.env['comic.work'].with_context(skip_dedup_check=True).create({
            'serie_id': self.serie.id,
            'titre_canonique': titre,
            'tome': tome,
        })

    def test_merge_transfers_editions(self):
        source = self._make_work('Source', 100)
        target = self._make_work('Target', 101)

        # Source auto-created 1 edition; add a 2nd
        self.env['comic.edition'].create({
            'work_id': source.id,
            'langue': 'nl',
            'editeur_id': self.editeur.id,
        })
        source_edition_ids = set(source.edition_ids.ids)
        self.assertEqual(len(source_edition_ids), 2)
        target_edition_count_before = len(target.edition_ids)  # 1 auto-created

        source._merge_into(target)

        self.assertFalse(source.active, "La source doit être archivée")
        # target keeps its own edition + receives source's editions
        self.assertEqual(
            len(target.edition_ids),
            target_edition_count_before + len(source_edition_ids),
        )
        # All source editions are now on target
        for eid in source_edition_ids:
            self.assertIn(eid, target.edition_ids.ids)

    def test_merge_transfers_auteur_lines_without_duplicates(self):
        source = self._make_work('Source auteurs', 110)
        target = self._make_work('Target auteurs', 111)
        partner_shared = self.env['res.partner'].create({'name': 'Auteur partagé'})
        partner_only_source = self.env['res.partner'].create({'name': 'Auteur source seul'})

        self.env['comic.work.auteur.line'].create([
            {'work_id': source.id, 'partner_id': partner_shared.id, 'role': 'dessinateur'},
            {'work_id': source.id, 'partner_id': partner_only_source.id, 'role': 'scenariste'},
            {'work_id': target.id, 'partner_id': partner_shared.id, 'role': 'dessinateur'},
        ])

        source._merge_into(target)

        partners_on_target = target.auteur_line_ids.mapped('partner_id')
        self.assertIn(partner_shared, partners_on_target)
        self.assertIn(partner_only_source, partners_on_target)
        # partner_shared appears exactly once (no duplicate)
        shared_lines = target.auteur_line_ids.filtered(
            lambda l: l.partner_id == partner_shared)
        self.assertEqual(len(shared_lines), 1)

    def test_merge_archives_source(self):
        source = self._make_work('Source archive', 120)
        target = self._make_work('Target archive', 121)
        source._merge_into(target)
        self.assertFalse(source.active)

    def test_merge_raises_on_same_record(self):
        w = self._make_work('Self merge', 130)
        with self.assertRaises(UserError):
            w._merge_into(w)

    def test_merge_logs_in_chatter(self):
        source = self._make_work('Source chatter', 140)
        target = self._make_work('Target chatter', 141)
        source._merge_into(target)
        messages = target.message_ids.mapped('body')
        self.assertTrue(
            any('Fusion' in (m or '') for m in messages),
            "Le chatter de la cible doit contenir un message de fusion",
        )
