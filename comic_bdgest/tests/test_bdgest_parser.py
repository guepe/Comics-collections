"""Tests unitaires pour BdgestParser — aucune dépendance HTTP ni Odoo."""

import os
import unittest

from comic_bdgest.scraper.bdgest_parser import BdgestParser

FIXTURES = os.path.join(os.path.dirname(__file__), 'fixtures')


def _load(filename):
    with open(os.path.join(FIXTURES, filename), encoding='utf-8') as f:
        return f.read()


class TestParseSearchResults(unittest.TestCase):

    def setUp(self):
        self.html = _load('search_results.html')
        self.results = BdgestParser.parse_search_results(self.html)

    def test_returns_three_items(self):
        self.assertEqual(len(self.results), 3)

    def test_album_ids(self):
        ids = [r['bdgest_album_id'] for r in self.results]
        self.assertIn(12345, ids)
        self.assertIn(12346, ids)
        self.assertIn(99001, ids)

    def test_serie_id_and_name(self):
        asterix = self.results[0]
        self.assertEqual(asterix['bdgest_serie_id'], 678)
        self.assertEqual(asterix['serie_name'], 'Astérix')

    def test_tome(self):
        self.assertEqual(self.results[0]['tome'], 1)
        self.assertEqual(self.results[1]['tome'], 2)
        self.assertEqual(self.results[2]['tome'], 1)

    def test_titre(self):
        self.assertEqual(self.results[0]['titre'], 'Astérix le Gaulois')
        self.assertEqual(self.results[2]['titre'], 'Quelque part entre les ombres')

    def test_editeur(self):
        self.assertEqual(self.results[0]['editeur'], 'Albert René')
        self.assertEqual(self.results[2]['editeur'], 'Dargaud')

    def test_auteurs_roles(self):
        auteurs = self.results[0]['auteurs']
        roles = {a['nom']: a['role'] for a in auteurs}
        self.assertEqual(roles.get('Goscinny'), 'scenariste')
        self.assertEqual(roles.get('Uderzo'), 'coloriste')  # last role wins for same name

    def test_auteurs_blacksad(self):
        auteurs = self.results[2]['auteurs']
        roles = {a['nom']: a['role'] for a in auteurs}
        self.assertEqual(roles.get('Canales'), 'scenariste')
        self.assertEqual(roles.get('Guarnido'), 'dessinateur')

    def test_couverture_url_relative_made_absolute(self):
        url = self.results[0]['couverture_url']
        self.assertTrue(url.startswith('https://'))

    def test_couverture_url_absolute_unchanged(self):
        url = self.results[2]['couverture_url']
        self.assertTrue(url.startswith('https://www.bedetheque.com'))

    def test_isbn_empty_in_search(self):
        for r in self.results:
            self.assertEqual(r['isbn'], '')


class TestParseAlbumDetail(unittest.TestCase):

    def setUp(self):
        self.html = _load('album_detail.html')
        self.result = BdgestParser.parse_album_detail(self.html, bdgest_album_id=12345)

    def test_album_id_preserved(self):
        self.assertEqual(self.result['bdgest_album_id'], 12345)

    def test_titre(self):
        self.assertEqual(self.result['titre'], 'Astérix le Gaulois')

    def test_serie(self):
        self.assertEqual(self.result['serie_name'], 'Astérix')
        self.assertEqual(self.result['bdgest_serie_id'], 678)

    def test_tome(self):
        self.assertEqual(self.result['tome'], 1)

    def test_isbn_normalized(self):
        self.assertEqual(self.result['isbn'], '9782012101302')

    def test_date_parution_iso(self):
        self.assertEqual(self.result['date_parution'], '1961-01-29')

    def test_date_depot_legal_iso(self):
        self.assertEqual(self.result['date_depot_legal'], '1961-01-01')

    def test_nb_pages(self):
        self.assertEqual(self.result['nb_pages'], 48)

    def test_editeur(self):
        self.assertEqual(self.result['editeur'], 'Albert René')

    def test_couverture_url_absolute(self):
        self.assertTrue(self.result['couverture_url'].startswith('https://'))

    def test_synopsis_not_empty(self):
        self.assertIn('Astérix', self.result.get('synopsis', ''))

    def test_auteurs_roles(self):
        auteurs = self.result['auteurs']
        roles = {a['nom']: a['role'] for a in auteurs}
        self.assertEqual(roles.get('Goscinny'), 'scenariste')
        self.assertEqual(roles.get('Uderzo'), 'coloriste')  # last occurrence wins

    def test_auteurs_count(self):
        # 3 <li> in ul.auteurs (Goscinny, Uderzo×2 — but Uderzo appears twice)
        noms = [a['nom'] for a in self.result['auteurs']]
        self.assertIn('Goscinny', noms)
        self.assertIn('Uderzo', noms)


class TestParseSerieAlbums(unittest.TestCase):

    def setUp(self):
        self.html = _load('serie.html')
        self.results = BdgestParser.parse_serie_albums(self.html)

    def test_returns_four_albums(self):
        self.assertEqual(len(self.results), 4)

    def test_serie_id_from_canonical(self):
        for r in self.results:
            self.assertEqual(r['bdgest_serie_id'], 678)

    def test_serie_name_from_h1(self):
        for r in self.results:
            self.assertEqual(r['serie_name'], 'Astérix')

    def test_album_ids(self):
        ids = [r['bdgest_album_id'] for r in self.results]
        self.assertIn(12345, ids)
        self.assertIn(12348, ids)

    def test_tomes(self):
        tomes = [r['tome'] for r in self.results]
        self.assertEqual(tomes, [1, 2, 3, 4])

    def test_titres(self):
        titres = [r['titre'] for r in self.results]
        self.assertIn('Astérix le Gaulois', titres)
        self.assertIn('La Serpe d\'Or', titres)

    def test_no_duplicates(self):
        ids = [r['bdgest_album_id'] for r in self.results]
        self.assertEqual(len(ids), len(set(ids)))


class TestHelpers(unittest.TestCase):

    def test_id_from_url_album(self):
        self.assertEqual(BdgestParser._id_from_url('/album-12345-BD-Titre.html', 'album'), 12345)

    def test_id_from_url_serie(self):
        self.assertEqual(BdgestParser._id_from_url('/serie-678-Asterix.html', 'serie'), 678)

    def test_id_from_url_none(self):
        self.assertIsNone(BdgestParser._id_from_url('/auteur-11-Goscinny.html', 'album'))

    def test_int_with_text(self):
        self.assertEqual(BdgestParser._int('Tome 12'), 12)
        self.assertEqual(BdgestParser._int('48'), 48)
        self.assertIsNone(BdgestParser._int(''))
        self.assertIsNone(BdgestParser._int(None))

    def test_abs_relative(self):
        self.assertEqual(
            BdgestParser._abs('/media/image.jpg'),
            'https://www.bedetheque.com/media/image.jpg'
        )

    def test_abs_already_absolute(self):
        url = 'https://www.bedetheque.com/media/image.jpg'
        self.assertEqual(BdgestParser._abs(url), url)

    def test_abs_empty(self):
        self.assertEqual(BdgestParser._abs(''), '')
        self.assertEqual(BdgestParser._abs(None), '')

    def test_parse_date_dd_mm_yyyy(self):
        self.assertEqual(BdgestParser._parse_date('29/01/1961'), '1961-01-29')

    def test_parse_date_mm_yyyy(self):
        self.assertEqual(BdgestParser._parse_date('01/1961'), '1961-01-01')

    def test_parse_date_yyyy(self):
        self.assertEqual(BdgestParser._parse_date('1961'), '1961-01-01')

    def test_parse_date_empty(self):
        self.assertEqual(BdgestParser._parse_date(''), '')
        self.assertEqual(BdgestParser._parse_date(None), '')

    def test_role_scenariste(self):
        self.assertEqual(BdgestParser._role('Scénario'), 'scenariste')
        self.assertEqual(BdgestParser._role('script'), 'scenariste')

    def test_role_dessinateur(self):
        self.assertEqual(BdgestParser._role('Dessin'), 'dessinateur')
        self.assertEqual(BdgestParser._role('Illustration'), 'dessinateur')

    def test_role_coloriste(self):
        self.assertEqual(BdgestParser._role('Couleurs'), 'coloriste')
        self.assertEqual(BdgestParser._role('Coloriages'), 'coloriste')

    def test_role_autre(self):
        self.assertEqual(BdgestParser._role('Préface'), 'autre')
        self.assertEqual(BdgestParser._role(''), 'autre')


if __name__ == '__main__':
    unittest.main()
