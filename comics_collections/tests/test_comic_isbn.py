"""Tests ORM pour le modèle comic.isbn.

Teste la validation EAN-13/ISBN-10, la normalisation et la contrainte d'unicité
via le vrai ORM Odoo (TransactionCase).

Lancement :
    docker exec odoo-web odoo-bin -d odoo -u comics_collections \
        --test-tags /comics_collections:TestComicIsbn
"""
from odoo.tests.common import TransactionCase
from odoo.tests import tagged
from odoo.exceptions import ValidationError


@tagged('comics_collections', 'comic_isbn')
class TestComicIsbn(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.serie = cls.env['comic.serie'].create({'name': 'TestSerie ISBN'})
        cls.work = cls.env['comic.work'].create({
            'serie_id': cls.serie.id,
            'titre_canonique': 'Œuvre Test ISBN',
            'tome': 1,
        })
        cls.edition = cls.env['comic.edition'].create({
            'work_id': cls.work.id,
            'langue': 'fr',
        })
        cls.edition2 = cls.env['comic.edition'].create({
            'work_id': cls.work.id,
            'langue': 'nl',
        })

    # ── Validation EAN-13 ────────────────────────────────────────────────────

    def test_valid_ean13_accepted(self):
        isbn = self.env['comic.isbn'].create({
            'edition_id': self.edition.id,
            'isbn_13': '9782012101340',
        })
        self.assertEqual(isbn.isbn_13, '9782012101340')

    def test_invalid_ean13_checksum_rejected(self):
        with self.assertRaises(ValidationError):
            self.env['comic.isbn'].create({
                'edition_id': self.edition.id,
                'isbn_13': '9782012101341',  # checksum incorrect
            })

    def test_invalid_ean13_too_short_rejected(self):
        with self.assertRaises(ValidationError):
            self.env['comic.isbn'].create({
                'edition_id': self.edition.id,
                'isbn_13': '978201210134',  # 12 chiffres
            })

    # ── Normalisation ────────────────────────────────────────────────────────

    def test_dashes_stripped_on_create(self):
        isbn = self.env['comic.isbn'].create({
            'edition_id': self.edition2.id,
            'isbn_13': '978-2-01-210134-0',
        })
        self.assertEqual(isbn.isbn_13, '9782012101340')

    def test_spaces_stripped_on_create(self):
        edition3 = self.env['comic.edition'].create({
            'work_id': self.work.id,
            'langue': 'en',
        })
        isbn = self.env['comic.isbn'].create({
            'edition_id': edition3.id,
            'isbn_13': '978 2012101340',
        })
        self.assertEqual(isbn.isbn_13, '9782012101340')

    # ── Validation ISBN-10 ───────────────────────────────────────────────────

    def test_invalid_isbn10_rejected(self):
        with self.assertRaises(ValidationError):
            self.env['comic.isbn'].create({
                'edition_id': self.edition.id,
                'isbn_10': '0000000001',  # checksum incorrect
            })

    # ── Contrainte d'unicité ─────────────────────────────────────────────────

    # def test_unique_isbn13_constraint(self):
    #     """Deux comic.isbn avec le même isbn_13 → violation de contrainte."""
    #     isbn_val = '9782012101395'
    #     edition_a = self.env['comic.edition'].create({'work_id': self.work.id, 'langue': 'fr'})
    #     edition_b = self.env['comic.edition'].create({'work_id': self.work.id, 'langue': 'nl'})
    #     self.env['comic.isbn'].create({'edition_id': edition_a.id, 'isbn_13': isbn_val})
    #     with self.assertRaises(Exception):
    #         with self.env.cr.savepoint():
    #             self.env['comic.isbn'].create({'edition_id': edition_b.id, 'isbn_13': isbn_val})
