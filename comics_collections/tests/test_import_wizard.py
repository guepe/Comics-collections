"""Tests unitaires pour les méthodes statiques/de classe du wizard d'import.

Toutes ces méthodes sont pures (pas d'ORM) — testables sans Odoo.
Lancement : python -m pytest comics_collections/tests/test_import_wizard.py -v
"""
import io
import unittest

# ── Import direct du module wizard ────────────────────────────────────────────
# On charge le fichier wizard avec importlib pour contourner comics_collections/__init__.py
# (qui importe les modèles Odoo). Dans l'env odoo-bin, l'import standard fonctionne.

import sys
import os
import importlib.util
import types

_WIZARD_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    'wizards', 'comic_import_wizard.py',
)

# Stub odoo minimal pour que le wizard puisse être importé sans Odoo installé
if 'odoo' not in sys.modules:
    _odoo = types.ModuleType('odoo')
    _fields = types.ModuleType('odoo.fields')
    _models = types.ModuleType('odoo.models')
    _exceptions = types.ModuleType('odoo.exceptions')

    class _TransientModel:
        pass

    class _UserError(Exception):
        pass

    _models.TransientModel = _TransientModel
    _exceptions.UserError = _UserError
    _odoo.fields = _fields
    _odoo.models = _models
    _odoo.exceptions = _exceptions

    _field_stub = lambda *a, **kw: None  # noqa: E731
    for _attr in (
        'Char', 'Binary', 'Boolean', 'Html', 'Selection',
        'One2many', 'Integer', 'Float', 'Text', 'Date',
        'Image', 'Many2one', 'Many2many',
    ):
        setattr(_fields, _attr, _field_stub)

    sys.modules['odoo'] = _odoo
    sys.modules['odoo.fields'] = _fields
    sys.modules['odoo.models'] = _models
    sys.modules['odoo.exceptions'] = _exceptions

# Chargement direct du module pour contourner le __init__.py du package
_spec = importlib.util.spec_from_file_location('comic_import_wizard', _WIZARD_PATH)
_wizard_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_wizard_mod)
ComicImportWizard = _wizard_mod.ComicImportWizard


# ── Helpers ───────────────────────────────────────────────────────────────────

_parse_date = ComicImportWizard._parse_date
_parse_integer = ComicImportWizard._parse_integer
_parse_float = ComicImportWizard._parse_float
_parse_reading_state = ComicImportWizard._parse_reading_state
_normalise_header = ComicImportWizard._normalise_header
_read_csv_rows = ComicImportWizard._read_csv_rows
_split_series_title = ComicImportWizard._split_series_title
_parse_collection_content = ComicImportWizard._parse_collection_content
_clean_isbn = ComicImportWizard._clean_isbn
_normalise_import_rows = ComicImportWizard._normalise_import_rows
_xlsx_column_index = ComicImportWizard._xlsx_column_index
_xlsx_column_name = ComicImportWizard._xlsx_column_name
_split_names = ComicImportWizard._split_names
_normalize_author_name = ComicImportWizard._normalize_author_name


# ── Tests _parse_date ─────────────────────────────────────────────────────────

class TestParseDate(unittest.TestCase):

    def test_iso_format(self):
        self.assertEqual(_parse_date('1985-05-01'), '1985-05-01')

    def test_slash_dd_mm_yyyy(self):
        self.assertEqual(_parse_date('01/05/1985'), '1985-05-01')

    def test_slash_mm_yyyy(self):
        self.assertEqual(_parse_date('05/1985'), '1985-05-01')

    def test_empty_returns_false(self):
        self.assertFalse(_parse_date(''))

    def test_none_returns_false(self):
        self.assertFalse(_parse_date(None))

    def test_garbage_returns_false(self):
        self.assertFalse(_parse_date('not a date'))

    def test_year_only_returns_false(self):
        self.assertFalse(_parse_date('1985'))


# ── Tests _parse_integer ──────────────────────────────────────────────────────

class TestParseInteger(unittest.TestCase):

    def test_plain_number(self):
        self.assertEqual(_parse_integer('5'), 5)

    def test_number_with_text(self):
        self.assertEqual(_parse_integer('tome 12'), 12)

    def test_float_string(self):
        self.assertEqual(_parse_integer('3.0'), 3)

    def test_empty(self):
        self.assertEqual(_parse_integer(''), 0)

    def test_none(self):
        self.assertEqual(_parse_integer(None), 0)

    def test_negative(self):
        self.assertEqual(_parse_integer('-5'), 5)


# ── Tests _parse_float ────────────────────────────────────────────────────────

class TestParseFloat(unittest.TestCase):

    def test_integer_string(self):
        self.assertAlmostEqual(_parse_float('4'), 4.0)

    def test_float_dot(self):
        self.assertAlmostEqual(_parse_float('3.5'), 3.5)

    def test_float_comma(self):
        self.assertAlmostEqual(_parse_float('3,5'), 3.5)

    def test_empty(self):
        self.assertAlmostEqual(_parse_float(''), 0.0)

    def test_none(self):
        self.assertAlmostEqual(_parse_float(None), 0.0)

    def test_garbage(self):
        self.assertAlmostEqual(_parse_float('abc'), 0.0)


# ── Tests _parse_reading_state ────────────────────────────────────────────────

class TestParseReadingState(unittest.TestCase):

    def test_non_lu(self):
        self.assertEqual(_parse_reading_state('non_lu'), 'non_lu')

    def test_lu(self):
        self.assertEqual(_parse_reading_state('lu'), 'lu')

    def test_lue(self):
        self.assertEqual(_parse_reading_state('lue'), 'lu')

    def test_en_cours(self):
        self.assertEqual(_parse_reading_state('en_cours'), 'en_cours')

    def test_a_lire_alias(self):
        self.assertEqual(_parse_reading_state('a_lire'), 'non_lu')

    def test_empty_defaults_to_non_lu(self):
        self.assertEqual(_parse_reading_state(''), 'non_lu')

    def test_unknown_defaults_to_non_lu(self):
        self.assertEqual(_parse_reading_state('inconnu'), 'non_lu')

    def test_case_insensitive(self):
        self.assertEqual(_parse_reading_state('LU'), 'lu')


# ── Tests _normalise_header ───────────────────────────────────────────────────

class TestNormaliseHeader(unittest.TestCase):

    def test_serie_alias(self):
        self.assertEqual(_normalise_header('serie'), 'serie_name')

    def test_serie_accent_alias(self):
        self.assertEqual(_normalise_header('série'), 'serie_name')

    def test_titre_alias(self):
        self.assertEqual(_normalise_header('titre'), 'titre_album')

    def test_lowercase(self):
        self.assertEqual(_normalise_header('ISBN'), 'isbn')

    def test_spaces_to_underscores(self):
        self.assertEqual(_normalise_header('serie name'), 'serie_name')

    def test_dashes_to_underscores(self):
        self.assertEqual(_normalise_header('serie-name'), 'serie_name')

    def test_degree_sign_removed(self):
        self.assertEqual(_normalise_header('n°'), 'n')


# ── Tests _read_csv_rows ──────────────────────────────────────────────────────

class TestReadCsvRows(unittest.TestCase):

    def _csv(self, text):
        return _read_csv_rows(text.encode('utf-8'))

    def test_semicolon_delimiter(self):
        rows = self._csv('serie_name;tome;titre_album\nAstérix;1;Le Gaulois')
        self.assertEqual(rows[0], ['serie_name', 'tome', 'titre_album'])
        self.assertEqual(rows[1], ['Astérix', '1', 'Le Gaulois'])

    def test_comma_delimiter(self):
        rows = self._csv('serie_name,tome\nAstérix,1')
        self.assertEqual(rows[0], ['serie_name', 'tome'])
        self.assertEqual(rows[1], ['Astérix', '1'])

    def test_bom_utf8(self):
        # Simule un fichier Excel sauvegardé en UTF-8 avec BOM
        rows = _read_csv_rows('col1;col2\nval1;val2'.encode('utf-8-sig'))
        self.assertEqual(rows[0], ['col1', 'col2'])

    def test_cells_stripped(self):
        rows = self._csv('  a  ;  b  \n  1  ;  2  ')
        self.assertEqual(rows[0], ['a', 'b'])
        self.assertEqual(rows[1], ['1', '2'])

    def test_empty_file(self):
        rows = self._csv('')
        self.assertEqual(rows, [])


# ── Tests _split_series_title ─────────────────────────────────────────────────

class TestSplitSeriesTitle(unittest.TestCase):

    def test_serie_tome_title_pattern(self):
        serie, tome, title = _split_series_title("Agent 212 (L') -5- Poulet aux amendes")
        self.assertEqual(serie, "Agent 212 (L')")
        self.assertEqual(tome, '5')
        self.assertEqual(title, 'Poulet aux amendes')

    def test_serie_dash_title(self):
        serie, tome, title = _split_series_title('Astérix - Le Gaulois')
        self.assertEqual(serie, 'Astérix')
        self.assertEqual(tome, '')
        self.assertEqual(title, 'Le Gaulois')

    def test_no_separator(self):
        serie, tome, title = _split_series_title('Tintin')
        self.assertEqual(serie, 'Tintin')
        self.assertEqual(tome, '')
        self.assertEqual(title, 'Tintin')

    def test_multi_digit_tome(self):
        serie, tome, title = _split_series_title('Largo Winch -12- Le Prix de lArgent')
        self.assertEqual(tome, '12')


# ── Tests _parse_collection_content ──────────────────────────────────────────

class TestParseCollectionContent(unittest.TestCase):

    def test_full_line(self):
        result = _parse_collection_content(
            "Agent 212 (L') -5- Poulet aux amendes 05/1985 Dupuis 11/03/2017"
        )
        self.assertEqual(result['serie_name'], "Agent 212 (L')")
        self.assertEqual(result['tome'], '5')
        self.assertEqual(result['titre_album'], 'Poulet aux amendes')
        self.assertEqual(result['date_parution'], '1985-05-01')
        self.assertEqual(result['editeur'], 'Dupuis')
        self.assertEqual(result['etat_lecture'], 'non_lu')

    def test_no_date(self):
        result = _parse_collection_content('Astérix - Le Gaulois Dargaud')
        self.assertFalse(result['date_parution'])

    def test_empty_content(self):
        result = _parse_collection_content('')
        self.assertEqual(result['serie_name'], '')


# ── Tests _clean_isbn ─────────────────────────────────────────────────────────

class TestCleanIsbn(unittest.TestCase):

    def test_ean13_unchanged(self):
        self.assertEqual(_clean_isbn('9782012101340'), '9782012101340')

    def test_dashes_removed(self):
        self.assertEqual(_clean_isbn('978-2-01-210134-0'), '9782012101340')

    def test_isbn10_converted_to_ean13(self):
        # ISBN-10 : 2010005500  → EAN-13 : 9782010005503
        result = _clean_isbn('2010005500')
        self.assertEqual(len(result), 13)
        self.assertTrue(result.startswith('978'))

    def test_empty_returns_false(self):
        self.assertFalse(_clean_isbn(''))

    def test_none_returns_false(self):
        self.assertFalse(_clean_isbn(None))

    def test_ean13_checksum_correct_after_conversion(self):
        """Vérifie que le checksum EAN-13 est correct après conversion ISBN-10."""
        isbn10 = '2010005500'
        ean13 = _clean_isbn(isbn10)
        digits = ean13[:12]
        total = sum(int(d) * (1 if i % 2 == 0 else 3) for i, d in enumerate(digits))
        expected_check = (10 - total % 10) % 10
        self.assertEqual(int(ean13[12]), expected_check)


# ── Tests _normalise_import_rows ──────────────────────────────────────────────

class TestNormaliseImportRows(unittest.TestCase):

    def test_standard_headers(self):
        rows = [
            ['serie_name', 'tome', 'titre_album'],
            ['Astérix', '1', 'Le Gaulois'],
            ['Astérix', '2', 'La Serpe d\'Or'],
        ]
        result = _normalise_import_rows(rows)
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]['serie_name'], 'Astérix')
        self.assertEqual(result[0]['tome'], '1')
        self.assertEqual(result[1]['titre_album'], "La Serpe d'Or")

    def test_header_aliases_resolved(self):
        rows = [
            ['série', 'titre'],
            ['Blacksad', 'Quelque part entre les ombres'],
        ]
        result = _normalise_import_rows(rows)
        self.assertIn('serie_name', result[0])
        self.assertIn('titre_album', result[0])

    def test_empty_rows_skipped(self):
        rows = [
            ['serie_name', 'titre_album'],
            ['', ''],
            ['Astérix', 'Le Gaulois'],
        ]
        result = _normalise_import_rows(rows)
        self.assertEqual(len(result), 1)


# ── Tests _split_names ────────────────────────────────────────────────────────

class TestSplitNames(unittest.TestCase):

    def test_single_name(self):
        self.assertEqual(_split_names('Goscinny'), ['Goscinny'])

    def test_semicolon_separator(self):
        self.assertEqual(_split_names('Goscinny;Uderzo'), ['Goscinny', 'Uderzo'])

    def test_pipe_separator(self):
        self.assertEqual(_split_names('Goscinny|Uderzo'), ['Goscinny', 'Uderzo'])

    def test_newline_separator(self):
        self.assertEqual(_split_names('Goscinny\nUderzo'), ['Goscinny', 'Uderzo'])

    def test_empty_returns_empty(self):
        self.assertEqual(_split_names(''), [])

    def test_inverted_name_normalised(self):
        result = _split_names('Goscinny, René')
        self.assertEqual(result, ['René Goscinny'])


# ── Tests _xlsx_column_index / _xlsx_column_name ──────────────────────────────

class TestXlsxColumnHelpers(unittest.TestCase):

    def test_column_A_is_1(self):
        self.assertEqual(_xlsx_column_index('A1'), 1)

    def test_column_Z_is_26(self):
        self.assertEqual(_xlsx_column_index('Z1'), 26)

    def test_column_AA_is_27(self):
        self.assertEqual(_xlsx_column_index('AA1'), 27)

    def test_column_name_1_is_A(self):
        self.assertEqual(_xlsx_column_name(1), 'A')

    def test_column_name_26_is_Z(self):
        self.assertEqual(_xlsx_column_name(26), 'Z')

    def test_column_name_27_is_AA(self):
        self.assertEqual(_xlsx_column_name(27), 'AA')

    def test_roundtrip(self):
        for i in range(1, 30):
            self.assertEqual(_xlsx_column_index(_xlsx_column_name(i) + '1'), i)


if __name__ == '__main__':
    unittest.main()
