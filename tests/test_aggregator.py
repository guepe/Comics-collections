"""Tests unitaires pour ComicDataAggregator."""
import unittest
from unittest.mock import patch, MagicMock
from comic_datasource.sources.base import ComicSourceResult


def _make_result(source, **kwargs):
    return ComicSourceResult(source=source, **kwargs)


class TestComicDataAggregator(unittest.TestCase):

    def setUp(self):
        from comic_datasource.aggregator import ComicDataAggregator
        self.aggregator = ComicDataAggregator(env=None)

    def _mock_sources(self, google=None, openlibrary=None, bnf=None, bdgest=None):
        """Patche toutes les sources avec des résultats prédéfinis."""
        self.aggregator._sources['google'].search_by_isbn = MagicMock(return_value=google)
        self.aggregator._sources['openlibrary'].search_by_isbn = MagicMock(return_value=openlibrary)
        self.aggregator._sources['bnf'].search_by_isbn = MagicMock(return_value=bnf)
        self.aggregator._sources['bdgest'].search_by_isbn = MagicMock(return_value=bdgest)
        # BDGest désactivé par défaut
        self.aggregator._sources['bdgest'].is_available = MagicMock(return_value=False)

    def test_google_wins_for_synopsis(self):
        google_result = _make_result('google', title='Astérix', synopsis='Synopsis Google', cover_url='http://google/large.jpg')
        bnf_result = _make_result('bnf', title='Astérix', synopsis='Synopsis BnF')
        self._mock_sources(google=google_result, bnf=bnf_result)
        result = self.aggregator.search(isbn='9782012101340')
        self.assertEqual(result.data.get('synopsis'), 'Synopsis Google')
        self.assertEqual(result.field_sources.get('synopsis'), 'google')

    def test_bnf_wins_for_synopsis_when_google_absent(self):
        bnf_result = _make_result('bnf', title='BD FR', synopsis='Synopsis BnF officiel')
        self._mock_sources(bnf=bnf_result)
        result = self.aggregator.search(isbn='9782012101340')
        self.assertEqual(result.data.get('synopsis'), 'Synopsis BnF officiel')
        self.assertEqual(result.field_sources.get('synopsis'), 'bnf')

    def test_bnf_wins_for_date_depot_legal(self):
        google_result = _make_result('google', title='Astérix', date_parution='1961-01-01')
        bnf_result = _make_result('bnf', title='Astérix', date_depot_legal='1961-10-29')
        self._mock_sources(google=google_result, bnf=bnf_result)
        result = self.aggregator.search(isbn='9782012101340')
        self.assertEqual(result.data.get('date_depot_legal'), '1961-10-29')
        self.assertEqual(result.field_sources.get('date_depot_legal'), 'bnf')

    def test_google_cover_preferred_over_openlibrary(self):
        google_result = _make_result('google', title='Astérix', cover_url='http://google/extralarge.jpg')
        ol_result = _make_result('openlibrary', title='Astérix', cover_url='http://openlibrary/L.jpg')
        self._mock_sources(google=google_result, openlibrary=ol_result)
        result = self.aggregator.search(isbn='9782012101340')
        self.assertEqual(result.data.get('cover_url'), 'http://google/extralarge.jpg')
        self.assertEqual(result.field_sources.get('cover_url'), 'google')

    def test_openlibrary_cover_used_when_google_absent(self):
        ol_result = _make_result('openlibrary', title='Astérix', cover_url='http://openlibrary/L.jpg')
        self._mock_sources(openlibrary=ol_result)
        result = self.aggregator.search(isbn='9782012101340')
        self.assertEqual(result.data.get('cover_url'), 'http://openlibrary/L.jpg')

    def test_auteurs_most_complete_source_wins(self):
        google_result = _make_result('google', title='Astérix', auteurs=[
            {'name': 'Goscinny', 'role': 'scenariste'},
        ])
        bnf_result = _make_result('bnf', title='Astérix', auteurs=[
            {'name': 'Goscinny', 'role': 'scenariste'},
            {'name': 'Uderzo', 'role': 'dessinateur'},
        ])
        self._mock_sources(google=google_result, bnf=bnf_result)
        result = self.aggregator.search(isbn='9782012101340')
        self.assertEqual(len(result.data.get('auteurs', [])), 2)

    def test_empty_result_when_no_source_found(self):
        self._mock_sources()
        result = self.aggregator.search(isbn='0000000000000')
        self.assertEqual(result.data, {})

    def test_cache_prevents_double_call(self):
        google_result = _make_result('google', title='Astérix', isbn='9782012101340')
        self._mock_sources(google=google_result)
        self.aggregator.search(isbn='9782012101340')
        self.aggregator.search(isbn='9782012101340')
        # search_by_isbn ne doit être appelé qu'une seule fois
        self.assertEqual(self.aggregator._sources['google'].search_by_isbn.call_count, 1)

    def test_sources_queried_tracked(self):
        google_result = _make_result('google', title='Astérix')
        bnf_result = _make_result('bnf', title='Astérix')
        self._mock_sources(google=google_result, bnf=bnf_result)
        result = self.aggregator.search(isbn='9782012101340')
        queried = result.data.get('sources_queried', [])
        self.assertIn('google', queried)
        self.assertIn('bnf', queried)

    def test_source_error_does_not_crash_aggregator(self):
        self.aggregator._sources['google'].search_by_isbn = MagicMock(side_effect=Exception('network'))
        bnf_result = _make_result('bnf', title='Fallback BnF')
        self.aggregator._sources['bnf'].search_by_isbn = MagicMock(return_value=bnf_result)
        self.aggregator._sources['openlibrary'].search_by_isbn = MagicMock(return_value=None)
        self.aggregator._sources['bdgest'].is_available = MagicMock(return_value=False)
        result = self.aggregator.search(isbn='9782012101340')
        self.assertEqual(result.data.get('title'), 'Fallback BnF')


if __name__ == '__main__':
    unittest.main()
