"""Tests unitaires pour la validation ISBN et la génération des liens d'achat.

Ces méthodes sont des @staticmethod — aucun ORM Odoo requis.
Compatible Odoo SH : utilise unittest.TestCase + @tagged pour être découvert
par le runner Odoo sans nécessiter de base de données.

Lancement direct :
    docker exec odoo-web odoo-bin -d odoo -u comics_collections \
        --test-tags /comics_collections:TestValidateEan13,TestBuildPurchaseLinks
"""

import unittest

from odoo.tests import tagged


def _validate_ean13(isbn):
    """Copie locale de ComicAlbum._validate_ean13 pour tests hors ORM."""
    isbn = isbn.replace("-", "").replace(" ", "")
    if len(isbn) != 13 or not isbn.isdigit():
        return False
    total = sum(int(d) * (1 if i % 2 == 0 else 3) for i, d in enumerate(isbn[:12]))
    check = (10 - total % 10) % 10
    return check == int(isbn[12])


def _build_purchase_links(isbn):
    """Copie locale de ComicAlbum._build_purchase_links."""
    if not isbn:
        return {}
    templates = {
        "url_club_be": "https://www.librairieclub.be/c/search?filter=search({isbn})&page=1&page_size=24&sort=RelevanceClub&sort_type=desc",  # noqa: E501
        "url_amazon_be": "https://www.amazon.com.be/s?k={isbn}",
        "url_fnac_be": "https://www.fnac.be/SearchResult/ResultList.aspx?Search={isbn}&sft=2",
    }
    return {field: tpl.format(isbn=isbn) for field, tpl in templates.items()}


@tagged("comics_collections", "comic_isbn", "post_install", "-at_install")
class TestValidateEan13(unittest.TestCase):

    def test_valid_isbn(self):
        self.assertTrue(_validate_ean13("9782012101340"))

    def test_valid_isbn_asterix(self):
        self.assertTrue(_validate_ean13("9782012101395"))

    def test_invalid_checksum(self):
        self.assertFalse(_validate_ean13("9782012101341"))

    def test_too_short(self):
        self.assertFalse(_validate_ean13("978201210134"))

    def test_too_long(self):
        self.assertFalse(_validate_ean13("97820121013400"))

    def test_non_digits(self):
        self.assertFalse(_validate_ean13("978201210134X"))

    def test_dashes_stripped(self):
        self.assertTrue(_validate_ean13("978-2-01-210134-0"))

    def test_spaces_stripped(self):
        self.assertTrue(_validate_ean13("978 2012101340"))

    def test_all_zeros_invalid_checksum(self):
        self.assertFalse(_validate_ean13("0000000000001"))

    def test_all_zeros_valid_checksum(self):
        self.assertTrue(_validate_ean13("0000000000000"))

    def test_empty_string(self):
        self.assertFalse(_validate_ean13(""))


@tagged("comics_collections", "comic_isbn", "post_install", "-at_install")
class TestBuildPurchaseLinks(unittest.TestCase):

    ISBN = "9782012101340"

    def test_returns_three_links(self):
        links = _build_purchase_links(self.ISBN)
        self.assertIn("url_club_be", links)
        self.assertIn("url_amazon_be", links)
        self.assertIn("url_fnac_be", links)

    def test_isbn_injected_in_urls(self):
        links = _build_purchase_links(self.ISBN)
        for url in links.values():
            self.assertIn(self.ISBN, url)

    def test_empty_isbn_returns_empty_dict(self):
        self.assertEqual(_build_purchase_links(""), {})

    def test_false_isbn_returns_empty_dict(self):
        self.assertEqual(_build_purchase_links(False), {})

    def test_club_be_url_format(self):
        links = _build_purchase_links(self.ISBN)
        self.assertTrue(links["url_club_be"].startswith("https://www.librairieclub.be"))

    def test_amazon_be_url_format(self):
        links = _build_purchase_links(self.ISBN)
        self.assertTrue(links["url_amazon_be"].startswith("https://www.amazon.com.be"))


if __name__ == "__main__":
    unittest.main()
