"""
Tests des correctifs mineurs des sources : ISBN, échappement CQL BnF,
couvertures Open Library sans HEAD, dates partielles, requête Google Books.
Les appels HTTP sont mockés — aucun accès réseau requis.
"""

# pylint: disable=odoo-addons-relative-import

from unittest.mock import MagicMock, patch

from odoo.tests import tagged
from odoo.tests.common import BaseCase

from odoo.addons.comic_datasource.sources.base import (
    cql_quote,
    normalize_isbn,
    parse_full_date,
)
from odoo.addons.comic_datasource.sources.bnf import BNF_SRU_URL, BnfSource
from odoo.addons.comic_datasource.sources.google_books import GoogleBooksSource
from odoo.addons.comic_datasource.sources.open_library import OpenLibrarySource

EMPTY_SRU = """<?xml version="1.0"?>
<srw:searchRetrieveResponse xmlns:srw="http://www.loc.gov/zing/srw/">
  <srw:numberOfRecords>0</srw:numberOfRecords>
  <srw:records/>
</srw:searchRetrieveResponse>"""


@tagged("comic_datasource")
class TestNormalizeIsbn(BaseCase):

    def test_valid_isbn10_converted(self):
        self.assertEqual(normalize_isbn("0306406152"), "9780306406157")

    def test_valid_isbn10_with_x_and_dashes(self):
        self.assertEqual(normalize_isbn("0-8044-2957-X"), "9780804429573")
        self.assertEqual(normalize_isbn("0-8044-2957-x"), "9780804429573")

    def test_invalid_isbn10_not_converted(self):
        # Clé de contrôle fausse : renvoyé nettoyé, sans conversion
        self.assertEqual(normalize_isbn("0306406153"), "0306406153")
        self.assertEqual(normalize_isbn("030640615Y"), "030640615Y")

    def test_isbn13_with_dashes_and_spaces(self):
        self.assertEqual(normalize_isbn("978-2-01-210134-0"), "9782012101340")
        self.assertEqual(normalize_isbn(" 978 2012101340 "), "9782012101340")

    def test_empty(self):
        self.assertEqual(normalize_isbn(None), "")
        self.assertEqual(normalize_isbn(""), "")


@tagged("comic_datasource")
class TestBnfQuoting(BaseCase):

    def test_cql_quote(self):
        self.assertEqual(cql_quote('Le "Grand" Duc'), 'Le \\"Grand\\" Duc')
        self.assertEqual(cql_quote("a\\b"), "a\\\\b")
        self.assertEqual(cql_quote(None), "")

    @patch("odoo.addons.comic_datasource.sources.bnf.requests.get")
    def test_title_query_escapes_quotes(self, mock_get):
        mock_get.return_value = MagicMock(status_code=200, text=EMPTY_SRU)
        BnfSource().search_by_title('Le "Grand" Duc', author='Yann "X"')
        query = mock_get.call_args.kwargs["params"]["query"]
        self.assertEqual(
            query,
            'bib.title adj "Le \\"Grand\\" Duc" and bib.author adj "Yann \\"X\\""',
        )

    @patch("odoo.addons.comic_datasource.sources.bnf.requests.get")
    def test_serie_query_escapes_quotes_over_https(self, mock_get):
        mock_get.return_value = MagicMock(status_code=200, text=EMPTY_SRU)
        BnfSource().search_by_serie('Les "Tuniques"')
        self.assertTrue(BNF_SRU_URL.startswith("https://"))
        self.assertEqual(mock_get.call_args.args[0], BNF_SRU_URL)
        queries = [c.kwargs["params"]["query"] for c in mock_get.call_args_list]
        self.assertIn('bib.serie adj "Les \\"Tuniques\\""', queries)


@tagged("comic_datasource")
class TestOpenLibraryCovers(BaseCase):

    @patch("odoo.addons.comic_datasource.sources.open_library.requests.head")
    @patch("odoo.addons.comic_datasource.sources.open_library.requests.get")
    def test_search_cover_from_cover_i_without_head(self, mock_get, mock_head):
        docs = {
            "docs": [
                {
                    "title": "Avec couverture",
                    "isbn": ["9782012101340"],
                    "cover_i": 12345,
                    "first_publish_year": 1961,
                },
                {"title": "Sans couverture", "isbn": ["9782205049657"]},
            ]
        }
        mock_get.return_value = MagicMock(status_code=200, json=lambda: docs)
        results = OpenLibrarySource().search_by_title("Astérix")
        mock_head.assert_not_called()
        self.assertEqual(results[0].cover_url, "https://covers.openlibrary.org/b/id/12345-L.jpg")
        self.assertEqual(results[0].cover_url_small, "https://covers.openlibrary.org/b/id/12345-M.jpg")
        self.assertIsNone(results[1].cover_url)
        self.assertIsNone(results[1].cover_url_small)
        # first_publish_year = date de l'œuvre, pas de l'édition
        self.assertIsNone(results[0].date_parution)

    @patch("odoo.addons.comic_datasource.sources.open_library.requests.head")
    @patch("odoo.addons.comic_datasource.sources.open_library.requests.get")
    def test_isbn_publish_date(self, mock_get, mock_head):
        def response(publish_date):
            data = {"ISBN:9782012101340": {"title": "T", "details": {"publish_date": publish_date}}}
            return MagicMock(status_code=200, json=lambda: data)

        source = OpenLibrarySource()
        mock_get.return_value = response("1961")
        self.assertIsNone(source.search_by_isbn("9782012101340").date_parution)
        mock_get.return_value = response("October 1961")
        self.assertIsNone(source.search_by_isbn("9782012101340").date_parution)
        mock_get.return_value = response("October 29, 1961")
        self.assertEqual(source.search_by_isbn("9782012101340").date_parution, "1961-10-29")
        mock_head.assert_not_called()


@tagged("comic_datasource")
class TestPartialDates(BaseCase):

    def test_parse_full_date(self):
        self.assertIsNone(parse_full_date("1961"))
        self.assertIsNone(parse_full_date("DL 2005"))
        self.assertIsNone(parse_full_date("2005-02-30"))
        self.assertEqual(parse_full_date("2005-03-14"), "2005-03-14")
        self.assertEqual(parse_full_date("14/03/2005"), "2005-03-14")
        self.assertEqual(parse_full_date("14 mars 2005"), "2005-03-14")

    def test_bnf_year_only_gives_no_date(self):
        record = {
            "srw:recordData": {
                "mxc:collection": {
                    "mxc:record": {
                        "mxc:datafield": [
                            {"@tag": "200", "mxc:subfield": {"@code": "a", "#text": "Titre"}},
                            {"@tag": "210", "mxc:subfield": {"@code": "d", "#text": "1961"}},
                        ]
                    }
                }
            }
        }
        result = BnfSource()._parse_unimarc(record)
        self.assertEqual(result.title, "Titre")
        self.assertIsNone(result.date_parution)


@tagged("comic_datasource")
class TestGoogleQuery(BaseCase):

    @patch("odoo.addons.comic_datasource.sources.google_books.requests.get")
    def test_title_author_query_uses_space(self, mock_get):
        mock_get.return_value = MagicMock(status_code=200, json=lambda: {"items": []})
        GoogleBooksSource().search_by_title("Blacksad", author="Canales")
        query = mock_get.call_args.kwargs["params"]["q"]
        self.assertNotIn("+", query)
        self.assertEqual(query, "intitle:Blacksad inauthor:Canales")
