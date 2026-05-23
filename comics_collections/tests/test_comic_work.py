"""Tests ORM pour le modèle comic.work.

Teste : contrainte unique (serie_id, tome), génération de slug, display_name,
titre_normalise, auteur_line_ids et nb_editions.

Lancement :
    docker exec odoo-web odoo-bin -d odoo -u comics_collections \
        --test-tags /comics_collections:TestComicWork
"""
from odoo.tests.common import TransactionCase
from odoo.tests import tagged


@tagged('comics_collections', 'comic_work')
class TestComicWork(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.serie = cls.env['comic.serie'].create({'name': 'Thorgal'})

    # ── Génération de slug ───────────────────────────────────────────────────

    def test_slug_generated_on_create(self):
        work = self.env['comic.work'].create({
            'serie_id': self.serie.id,
            'titre_canonique': 'Iles des mers gelées',
            'tome': 99,
        })
        self.assertEqual(work.slug, 'thorgal-t99')

    def test_slug_no_serie_uses_tome_only(self):
        work = self.env['comic.work'].create({
            'titre_canonique': 'One Shot',
            'tome': 3,
        })
        self.assertTrue(work.slug.startswith('t03'))

    def test_slug_conflict_gets_numeric_suffix(self):
        """Deux séries avec noms similaires → slug base identique → suffixe -1."""
        serie_a = self.env['comic.serie'].create({'name': 'Lucky Luke!'})
        serie_b = self.env['comic.serie'].create({'name': 'Lucky Luke'})
        # Les deux normalisent en "lucky-luke"
        w1 = self.env['comic.work'].create({
            'serie_id': serie_a.id,
            'titre_canonique': 'Titre A',
            'tome': 1,
        })
        w2 = self.env['comic.work'].create({
            'serie_id': serie_b.id,
            'titre_canonique': 'Titre B',
            'tome': 1,
        })
        self.assertEqual(w1.slug, 'lucky-luke-t01')
        self.assertEqual(w2.slug, 'lucky-luke-t01-1')

    def test_custom_slug_preserved_on_create(self):
        work = self.env['comic.work'].create({
            'titre_canonique': 'Test',
            'tome': 99,
            'slug': 'mon-slug-custom',
        })
        self.assertEqual(work.slug, 'mon-slug-custom')

    # ── display_name ─────────────────────────────────────────────────────────

    def test_display_name_with_serie_and_tome(self):
        work = self.env['comic.work'].create({
            'serie_id': self.serie.id,
            'titre_canonique': 'La Magicienne trahie',
            'tome': 1,
        })
        self.assertEqual(work.display_name, 'Thorgal T01 — La Magicienne trahie')

    def test_display_name_without_serie_and_tome(self):
        work = self.env['comic.work'].create({
            'titre_canonique': 'One Shot pur',
            'tome': 0,
        })
        self.assertEqual(work.display_name, 'One Shot pur')

    def test_display_name_tome_only(self):
        work = self.env['comic.work'].create({
            'titre_canonique': 'Volume unique',
            'tome': 7,
        })
        self.assertEqual(work.display_name, 'T07 — Volume unique')

    # ── titre_normalise ──────────────────────────────────────────────────────

    def test_titre_normalise_strips_leading_article_fr(self):
        work = self.env['comic.work'].create({
            'titre_canonique': 'Les Landes perdues',
            'tome': 1,
        })
        self.assertEqual(work.titre_normalise, 'landes perdues')

    def test_titre_normalise_strips_le(self):
        work = self.env['comic.work'].create({
            'titre_canonique': 'Le Grand Pouvoir du Chninkel',
            'tome': 1,
        })
        self.assertEqual(work.titre_normalise, 'grand pouvoir du chninkel')

    def test_titre_normalise_strips_accents(self):
        work = self.env['comic.work'].create({
            'titre_canonique': 'Étoiles lointaines',
            'tome': 1,
        })
        self.assertNotIn('É', work.titre_normalise)
        self.assertIn('etoiles', work.titre_normalise)

    # ── Contrainte unique (serie_id, tome) ───────────────────────────────────

    def test_unique_serie_tome_constraint(self):
        """Deux works avec le même (serie_id, tome) → erreur DB."""
        self.env['comic.work'].create({
            'serie_id': self.serie.id,
            'titre_canonique': 'Premier tome',
            'tome': 10,
        })
        with self.assertRaises(Exception):
            with self.env.cr.savepoint():
                self.env['comic.work'].create({
                    'serie_id': self.serie.id,
                    'titre_canonique': 'Doublon interdit',
                    'tome': 10,
                })

    def test_same_tome_different_serie_is_allowed(self):
        """Même numéro de tome pour deux séries différentes : OK."""
        serie2 = self.env['comic.serie'].create({'name': 'Blacksad'})
        w1 = self.env['comic.work'].create({
            'serie_id': self.serie.id,
            'titre_canonique': 'Thorgal T2',
            'tome': 2,
        })
        w2 = self.env['comic.work'].create({
            'serie_id': serie2.id,
            'titre_canonique': 'Blacksad T2',
            'tome': 2,
        })
        self.assertTrue(w1.id != w2.id)

    # ── auteur_line_ids / nb_auteurs ─────────────────────────────────────────

    def test_add_auteur_line(self):
        work = self.env['comic.work'].create({
            'titre_canonique': 'Test Auteurs',
            'tome': 1,
        })
        partner = self.env['res.partner'].create({'name': 'Van Hamme Jean'})
        line = self.env['comic.work.auteur.line'].create({
            'work_id': work.id,
            'partner_id': partner.id,
            'role': 'scenariste',
        })
        self.assertEqual(work.nb_auteurs, 1)
        self.assertEqual(line.role, 'scenariste')
        self.assertEqual(line.partner_id, partner)

    def test_remove_auteur_line(self):
        work = self.env['comic.work'].create({
            'titre_canonique': 'Test Suppression Auteur',
            'tome': 1,
        })
        partner = self.env['res.partner'].create({'name': 'Auteur Test'})
        line = self.env['comic.work.auteur.line'].create({
            'work_id': work.id,
            'partner_id': partner.id,
            'role': 'dessinateur',
        })
        self.assertEqual(work.nb_auteurs, 1)
        line.unlink()
        self.assertEqual(work.nb_auteurs, 0)

    # ── nb_editions ──────────────────────────────────────────────────────────

    def test_nb_editions_computed_on_add(self):
        work = self.env['comic.work'].create({
            'serie_id': self.serie.id,
            'titre_canonique': 'Test Editions',
            'tome': 20,
        })
        # create() auto-creates a default edition (fr/cartonne)
        self.assertEqual(work.nb_editions, 1)
        self.env['comic.edition'].create({'work_id': work.id, 'langue': 'nl'})
        self.env['comic.edition'].create({'work_id': work.id, 'langue': 'en'})
        self.assertEqual(work.nb_editions, 3)
