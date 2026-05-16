"""
Source BDGest (scraping Bedetheque.com) — FALLBACK UNIQUEMENT.

⚠️  Cette source utilise du scraping et est désactivée par défaut.
    L'utilisateur doit explicitement accepter les CGU de BDGest avant activation.
    Un délai de 2 secondes entre requêtes est obligatoire.
"""
import logging
import time
import requests
from bs4 import BeautifulSoup
from .base import BaseComicSource, ComicSourceResult

_logger = logging.getLogger(__name__)

BASE_URL = 'https://www.bedetheque.com'
SEARCH_URL = f'{BASE_URL}/search/albums'
REQUEST_DELAY = 2  # secondes entre requêtes (obligatoire CGU)

LEGAL_DISCLAIMER = (
    "BDGest (bedetheque.com) est un service privé. "
    "Son utilisation via scraping est soumise à l'acceptation de leurs CGU. "
    "Cette source est un fallback de dernier recours, "
    "utilisée uniquement si aucune API officielle n'a trouvé l'album. "
    "Un délai de 2 secondes entre requêtes est appliqué automatiquement."
)


class BdgestSource(BaseComicSource):
    SOURCE_NAME = 'bdgest'

    def __init__(self, env=None):
        super().__init__(env)
        self._session = requests.Session()
        self._session.headers.update({'User-Agent': 'Mozilla/5.0 (compatible; OdooComicCollection/1.0)'})
        self._csrf_token = None
        self._last_request_time = 0

    def is_available(self) -> bool:
        return self._get_config('comic.bdgest_enabled', 'False') == 'True'

    def _rate_limit(self):
        elapsed = time.time() - self._last_request_time
        if elapsed < REQUEST_DELAY:
            time.sleep(REQUEST_DELAY - elapsed)
        self._last_request_time = time.time()

    def _get_csrf_token(self):
        if self._csrf_token:
            return self._csrf_token
        self._rate_limit()
        try:
            resp = self._session.get(SEARCH_URL, timeout=10)
            soup = BeautifulSoup(resp.text, 'lxml')
            token_input = soup.find('input', {'name': 'csrf_token_bel'})
            if token_input:
                self._csrf_token = token_input.get('value', '')
        except Exception as e:
            _logger.warning('BDGest: impossible de récupérer le CSRF token: %s', e)
        return self._csrf_token or ''

    def _search_params(self, **criteria):
        params = {
            'RechIdSerie': '', 'RechIdEditeur': '', 'RechCollection': '',
            'RechSerie': '', 'RechTitre': '', 'RechAuteur': '',
            'RechISBN': '', 'RechParution': '', 'RechOrigine': '',
            'RechLangue': '', 'RechNomPropre': '', 'RechGenre': '',
            'csrf_token_bel': self._get_csrf_token(),
        }
        params.update(criteria)
        return params

    def _parse_search_results(self, html: str) -> list:
        soup = BeautifulSoup(html, 'lxml')
        results = []
        for li in soup.select('ul.search-list li'):
            try:
                link = li.find('a', href=True)
                if not link:
                    continue
                href = link['href']
                title = li.find('h3') or li.find('h2')
                serie = li.find('span', class_='serie')
                cover = li.find('img')

                bdgest_id = None
                import re
                match = re.search(r'/album/(\d+)', href)
                if match:
                    bdgest_id = match.group(1)

                results.append({
                    'title': title.get_text(strip=True) if title else '',
                    'serie_name': serie.get_text(strip=True) if serie else None,
                    'cover_url': cover.get('src') if cover else None,
                    'bdgest_id': bdgest_id,
                    'url': href if href.startswith('http') else BASE_URL + href,
                })
            except Exception:
                continue
        return results

    def _parse_album_detail(self, html: str, isbn: str = None) -> ComicSourceResult:
        soup = BeautifulSoup(html, 'lxml')

        def text(selector):
            el = soup.select_one(selector)
            return el.get_text(strip=True) if el else None

        title = text('h1.titre') or text('h1') or ''
        serie_name = text('h2 a') or text('.serie-name')
        cover_img = soup.select_one('img.couverture') or soup.select_one('.album-cover img')
        cover_url = cover_img.get('src') if cover_img else None

        auteurs = []
        for a_tag in soup.select('.auteurs a, .author a'):
            role_el = a_tag.find_previous_sibling(string=True) or ''
            role_text = str(role_el).lower()
            if 'dessin' in role_text:
                role = 'dessinateur'
            elif 'couleur' in role_text:
                role = 'coloriste'
            elif 'trad' in role_text:
                role = 'traducteur'
            else:
                role = 'scenariste'
            auteurs.append({'name': a_tag.get_text(strip=True), 'role': role})

        editeur = text('.editeur a') or text('.publisher a')
        parution = text('.parution') or text('.date-parution') or ''
        import re
        year_match = re.search(r'(\d{4})', parution)
        date_parution = f'{year_match.group(1)}-01-01' if year_match else None

        pages_text = text('.pages') or ''
        pages_match = re.search(r'(\d+)', pages_text)
        nb_pages = int(pages_match.group(1)) if pages_match else None

        isbn_found = text('.isbn') or isbn

        synopsis_el = soup.select_one('.synopsis') or soup.select_one('.description')
        synopsis = str(synopsis_el) if synopsis_el else None

        return ComicSourceResult(
            source=self.SOURCE_NAME,
            title=title,
            serie_name=serie_name,
            isbn=isbn_found,
            date_parution=date_parution,
            nb_pages=nb_pages,
            editeur=editeur,
            auteurs=auteurs,
            synopsis=synopsis,
            cover_url=cover_url,
            raw={'html_length': len(html)},
        )

    def search_by_isbn(self, isbn: str):
        if not self.is_available():
            return None
        self._rate_limit()
        try:
            resp = self._session.get(SEARCH_URL, params=self._search_params(RechISBN=isbn), timeout=10)
            results = self._parse_search_results(resp.text)
            if not results:
                return None
            first = results[0]
            return self._get_album_detail(first['url'], isbn)
        except Exception as e:
            _logger.warning('BDGest search_by_isbn: %s', e)
            return None

    def search_by_title(self, title: str, author: str = None) -> list:
        if not self.is_available():
            return []
        params = self._search_params(RechTitre=title)
        if author:
            params['RechAuteur'] = author
        self._rate_limit()
        try:
            resp = self._session.get(SEARCH_URL, params=params, timeout=10)
            raw_results = self._parse_search_results(resp.text)
            return [
                ComicSourceResult(
                    source=self.SOURCE_NAME,
                    title=r['title'],
                    serie_name=r.get('serie_name'),
                    cover_url=r.get('cover_url'),
                    source_id=r.get('bdgest_id'),
                    raw=r,
                )
                for r in raw_results
            ]
        except Exception as e:
            _logger.warning('BDGest search_by_title: %s', e)
            return []

    def _get_album_detail(self, url: str, isbn: str = None) -> ComicSourceResult:
        self._rate_limit()
        try:
            resp = self._session.get(url, timeout=10)
            return self._parse_album_detail(resp.text, isbn)
        except Exception as e:
            _logger.warning('BDGest get_album_detail: %s', e)
            return None

    def get_serie_albums(self, bdgest_serie_id: str) -> list:
        """Récupère la liste complète des albums d'une série BDGest."""
        if not self.is_available():
            return []
        url = f'{BASE_URL}/serie-{bdgest_serie_id}.html'
        self._rate_limit()
        try:
            resp = self._session.get(url, timeout=10)
            soup = BeautifulSoup(resp.text, 'lxml')
            albums = []
            for li in soup.select('ul.albums li'):
                link = li.find('a', href=True)
                if link:
                    albums.append({
                        'url': link['href'] if link['href'].startswith('http') else BASE_URL + link['href'],
                        'title': link.get_text(strip=True),
                    })
            return albums
        except Exception as e:
            _logger.warning('BDGest get_serie_albums: %s', e)
            return []
