"""
Tests unitaires pour chaque source de données.
Les appels HTTP sont mockés — aucun accès réseau requis.
"""
import unittest
from unittest.mock import patch, MagicMock


# ── Google Books ──────────────────────────────────────────────────────────────

GOOGLE_BOOKS_RESPONSE = {
    'items': [{
        'id': 'abc123',
        'volumeInfo': {
            'title': 'Astérix le Gaulois',
            'authors': ['René Goscinny'],
            'publisher': 'Dargaud',
            'publishedDate': '1961-10-29',
            'pageCount': 48,
            'description': 'Le premier album d\'Astérix.',
            'imageLinks': {
                'thumbnail': 'http://books.google.com/small.jpg',
                'large': 'http://books.google.com/large.jpg',
            },
            'industryIdentifiers': [
                {'type': 'ISBN_13', 'identifier': '9782012101340'},
            ],
        }
    }]
}


class TestGoogleBooksSource(unittest.TestCase):

    @patch('comic_datasource.sources.google_books.requests.get')
    def test_search_by_isbn_found(self, mock_get):
        mock_get.return_value = MagicMock(
            status_code=200,
            json=lambda: GOOGLE_BOOKS_RESPONSE,
        )
        from comic_datasource.sources.google_books import GoogleBooksSource
        source = GoogleBooksSource()
        result = source.search_by_isbn('9782012101340')
        self.assertIsNotNone(result)
        self.assertEqual(result.title, 'Astérix le Gaulois')
        self.assertEqual(result.isbn, '9782012101340')
        self.assertEqual(result.editeur, 'Dargaud')
        self.assertEqual(result.nb_pages, 48)
        self.assertEqual(result.source, 'google')
        self.assertEqual(len(result.auteurs), 1)
        self.assertEqual(result.auteurs[0]['name'], 'René Goscinny')

    @patch('comic_datasource.sources.google_books.requests.get')
    def test_search_by_isbn_not_found(self, mock_get):
        mock_get.return_value = MagicMock(status_code=200, json=lambda: {})
        from comic_datasource.sources.google_books import GoogleBooksSource
        source = GoogleBooksSource()
        result = source.search_by_isbn('0000000000000')
        self.assertIsNone(result)

    @patch('comic_datasource.sources.google_books.requests.get')
    def test_search_by_isbn_quota_exceeded(self, mock_get):
        mock_get.return_value = MagicMock(status_code=429)
        from comic_datasource.sources.google_books import GoogleBooksSource
        source = GoogleBooksSource()
        result = source.search_by_isbn('9782012101340')
        self.assertIsNone(result)

    @patch('comic_datasource.sources.google_books.requests.get')
    def test_search_by_title(self, mock_get):
        mock_get.return_value = MagicMock(
            status_code=200,
            json=lambda: GOOGLE_BOOKS_RESPONSE,
        )
        from comic_datasource.sources.google_books import GoogleBooksSource
        source = GoogleBooksSource()
        results = source.search_by_title('Astérix')
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].title, 'Astérix le Gaulois')

    @patch('comic_datasource.sources.google_books.requests.get')
    def test_network_error_returns_none(self, mock_get):
        mock_get.side_effect = Exception('network error')
        from comic_datasource.sources.google_books import GoogleBooksSource
        source = GoogleBooksSource()
        result = source.search_by_isbn('9782012101340')
        self.assertIsNone(result)

    def test_date_normalization_year_only(self):
        from comic_datasource.sources.google_books import GoogleBooksSource
        source = GoogleBooksSource()
        item = {
            'id': 'x',
            'volumeInfo': {
                'title': 'Test',
                'publishedDate': '1995',
                'industryIdentifiers': [],
                'authors': [],
                'imageLinks': {},
            }
        }
        result = source._parse_volume(item)
        self.assertEqual(result.date_parution, '1995-01-01')


# ── Open Library ──────────────────────────────────────────────────────────────

OL_RESPONSE = {
    'ISBN:9782012101340': {
        'title': 'Astérix le Gaulois',
        'authors': [{'name': 'René Goscinny'}],
        'publishers': [{'name': 'Dargaud'}],
        'details': {
            'publish_date': 'October 1961',
            'number_of_pages': 48,
            'key': '/books/OL123M',
        },
    }
}


class TestOpenLibrarySource(unittest.TestCase):

    @patch('comic_datasource.sources.open_library.requests.head')
    @patch('comic_datasource.sources.open_library.requests.get')
    def test_search_by_isbn_found(self, mock_get, mock_head):
        mock_get.return_value = MagicMock(status_code=200, json=lambda: OL_RESPONSE)
        mock_head.return_value = MagicMock(
            status_code=200, headers={'Content-Length': '50000'}
        )
        from comic_datasource.sources.open_library import OpenLibrarySource
        source = OpenLibrarySource()
        result = source.search_by_isbn('9782012101340')
        self.assertIsNotNone(result)
        self.assertEqual(result.title, 'Astérix le Gaulois')
        self.assertEqual(result.editeur, 'Dargaud')
        self.assertEqual(result.source, 'openlibrary')

    @patch('comic_datasource.sources.open_library.requests.head')
    @patch('comic_datasource.sources.open_library.requests.get')
    def test_cover_absent_returns_none(self, mock_get, mock_head):
        mock_get.return_value = MagicMock(status_code=200, json=lambda: OL_RESPONSE)
        # Couverture absente (Content-Length = 1)
        mock_head.return_value = MagicMock(
            status_code=200, headers={'Content-Length': '1'}
        )
        from comic_datasource.sources.open_library import OpenLibrarySource
        source = OpenLibrarySource()
        result = source.search_by_isbn('9782012101340')
        self.assertIsNone(result.cover_url)

    @patch('comic_datasource.sources.open_library.requests.get')
    def test_search_by_isbn_empty(self, mock_get):
        mock_get.return_value = MagicMock(status_code=200, json=lambda: {})
        from comic_datasource.sources.open_library import OpenLibrarySource
        source = OpenLibrarySource()
        result = source.search_by_isbn('0000000000000')
        self.assertIsNone(result)


# ── BnF SRU ───────────────────────────────────────────────────────────────────

BNF_XML_RESPONSE = """<?xml version="1.0" encoding="UTF-8"?>
<srw:searchRetrieveResponse xmlns:srw="http://www.loc.gov/zing/srw/">
  <srw:numberOfRecords>1</srw:numberOfRecords>
  <srw:records>
    <srw:record>
      <srw:recordData>
        <mxc:collection xmlns:mxc="info:lc/xmlns/marcxchange-v2">
          <mxc:record>
            <mxc:datafield tag="010">
              <mxc:subfield code="a">9782012101340</mxc:subfield>
            </mxc:datafield>
            <mxc:datafield tag="200">
              <mxc:subfield code="a">Astérix le Gaulois</mxc:subfield>
            </mxc:datafield>
            <mxc:datafield tag="210">
              <mxc:subfield code="c">Dargaud</mxc:subfield>
              <mxc:subfield code="d">1961</mxc:subfield>
            </mxc:datafield>
            <mxc:datafield tag="215">
              <mxc:subfield code="a">48 p.</mxc:subfield>
            </mxc:datafield>
            <mxc:datafield tag="700">
              <mxc:subfield code="a">Goscinny, René</mxc:subfield>
            </mxc:datafield>
            <mxc:datafield tag="701">
              <mxc:subfield code="a">Uderzo, Albert</mxc:subfield>
            </mxc:datafield>
          </mxc:record>
        </mxc:collection>
      </srw:recordData>
    </srw:record>
  </srw:records>
</srw:searchRetrieveResponse>"""


class TestBnfSource(unittest.TestCase):

    @patch('comic_datasource.sources.bnf.requests.get')
    def test_search_by_isbn_found(self, mock_get):
        mock_get.return_value = MagicMock(status_code=200, text=BNF_XML_RESPONSE)
        from comic_datasource.sources.bnf import BnfSource
        source = BnfSource()
        result = source.search_by_isbn('9782012101340')
        self.assertIsNotNone(result)
        self.assertEqual(result.title, 'Astérix le Gaulois')
        self.assertEqual(result.isbn, '9782012101340')
        self.assertEqual(result.editeur, 'Dargaud')
        self.assertEqual(result.nb_pages, 48)
        self.assertEqual(result.source, 'bnf')
        self.assertEqual(len(result.auteurs), 2)
        roles = {a['role'] for a in result.auteurs}
        self.assertIn('scenariste', roles)
        self.assertIn('dessinateur', roles)

    @patch('comic_datasource.sources.bnf.requests.get')
    def test_search_by_isbn_empty(self, mock_get):
        empty_xml = """<?xml version="1.0"?>
        <srw:searchRetrieveResponse xmlns:srw="http://www.loc.gov/zing/srw/">
          <srw:numberOfRecords>0</srw:numberOfRecords>
          <srw:records/>
        </srw:searchRetrieveResponse>"""
        mock_get.return_value = MagicMock(status_code=200, text=empty_xml)
        from comic_datasource.sources.bnf import BnfSource
        source = BnfSource()
        result = source.search_by_isbn('0000000000000')
        self.assertIsNone(result)

    @patch('comic_datasource.sources.bnf.requests.get')
    def test_timeout_returns_none(self, mock_get):
        mock_get.side_effect = Exception('timeout')
        from comic_datasource.sources.bnf import BnfSource
        source = BnfSource()
        result = source.search_by_isbn('9782012101340')
        self.assertIsNone(result)


# ── BDGest ────────────────────────────────────────────────────────────────────

class TestBdgestSource(unittest.TestCase):

    def test_disabled_by_default(self):
        from comic_datasource.sources.bdgest import BdgestSource
        source = BdgestSource(env=None)
        # Sans env Odoo, is_available() retourne False (pas de config)
        self.assertFalse(source.is_available())

    def test_search_by_isbn_returns_none_when_disabled(self):
        from comic_datasource.sources.bdgest import BdgestSource
        source = BdgestSource(env=None)
        result = source.search_by_isbn('9782012101340')
        self.assertIsNone(result)

    def test_search_by_title_returns_empty_when_disabled(self):
        from comic_datasource.sources.bdgest import BdgestSource
        source = BdgestSource(env=None)
        results = source.search_by_title('Astérix')
        self.assertEqual(results, [])


if __name__ == '__main__':
    unittest.main()
