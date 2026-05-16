import logging
import requests
from .base import BaseComicSource, ComicSourceResult, parse_bd_title

_logger = logging.getLogger(__name__)

GOOGLE_BOOKS_URL = 'https://www.googleapis.com/books/v1/volumes'


class GoogleBooksQuotaError(Exception):
    """Levée quand Google Books retourne HTTP 429 (quota dépassé)."""


class GoogleBooksSource(BaseComicSource):
    SOURCE_NAME = 'google'

    def is_available(self) -> bool:
        # Fonctionne sans clé (quota réduit) — toujours disponible
        return True

    def _api_key(self):
        return self._get_config('comic.google_books_api_key', '')

    def _fetch(self, params):
        key = self._api_key()
        if key:
            params['key'] = key
        try:
            resp = requests.get(GOOGLE_BOOKS_URL, params=params, timeout=10)
        except Exception as e:
            _logger.warning('Google Books: requête échouée: %s', e)
            return None

        if resp.status_code == 429:
            _logger.error(
                'Google Books: quota dépassé (HTTP 429). '
                'Ajoutez une clé API dans Paramètres > Bandes Dessinées '
                'pour augmenter la limite (1000 req/jour).'
            )
            raise GoogleBooksQuotaError(
                'Quota Google Books dépassé. '
                'Ajoutez une clé API dans Paramètres > Sources de données BD.'
            )
        if resp.status_code == 403:
            _logger.error('Google Books: accès refusé (HTTP 403) — clé API invalide ou API non activée.')
            return None

        try:
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            _logger.warning('Google Books: erreur HTTP %s: %s', resp.status_code, e)
            return None

    def _parse_volume(self, item) -> ComicSourceResult:
        info = item.get('volumeInfo', {})
        images = info.get('imageLinks', {})

        auteurs = []
        for author in info.get('authors', []):
            auteurs.append({'name': author, 'role': 'scenariste'})

        isbn = None
        for identifier in info.get('industryIdentifiers', []):
            if identifier.get('type') in ('ISBN_13', 'ISBN_10'):
                isbn = identifier['identifier']
                if identifier['type'] == 'ISBN_13':
                    break
        # Normalise l'ISBN : supprime tirets et espaces
        if isbn:
            import re as _re
            isbn = _re.sub(r'[\-\s]', '', isbn)

        published = info.get('publishedDate', '')
        if published and len(published) == 4:
            published = published + '-01-01'
        elif published and len(published) == 7:
            published = published + '-01'

        # Extraction série + tome depuis le titre Google Books
        raw_title = info.get('title', '')
        subtitle = info.get('subtitle', '')
        serie_name, tome, clean_title = parse_bd_title(raw_title, subtitle)

        # Google Books a parfois seriesInfo (champ expérimental)
        series_info = info.get('seriesInfo', {})
        if series_info:
            book_series = series_info.get('bookSeries', [{}])
            if book_series:
                serie_name = serie_name or book_series[0].get('seriesId')
            volume_series = series_info.get('volumeSeries', [{}])
            if volume_series and not tome:
                tome = volume_series[0].get('orderNumber')

        # Couverture : préférer la grande, zoom=1 donne la version non-tronquée
        cover_large = (
            images.get('extraLarge')
            or images.get('large')
            or (images.get('thumbnail', '').replace('zoom=1', 'zoom=3') if images.get('thumbnail') else None)
            or images.get('medium')
            or None
        )
        cover_small = images.get('thumbnail') or images.get('smallThumbnail') or None

        return ComicSourceResult(
            source=self.SOURCE_NAME,
            title=clean_title or raw_title,
            serie_name=serie_name,
            tome=tome,
            isbn=isbn,
            date_parution=published or None,
            nb_pages=info.get('pageCount') or None,
            editeur=info.get('publisher') or None,
            auteurs=auteurs,
            synopsis=info.get('description') or None,
            cover_url=cover_large,
            cover_url_small=cover_small,
            source_id=item.get('id'),
            raw=item,
        )

    def search_by_isbn(self, isbn: str):
        data = self._fetch({'q': f'isbn:{isbn}'})
        if not data or not data.get('items'):
            return None
        return self._parse_volume(data['items'][0])

    def search_by_title(self, title: str, author: str = None) -> list:
        query = f'intitle:{title}'
        if author:
            query += f'+inauthor:{author}'
        data = self._fetch({'q': query, 'maxResults': 10})
        if not data or not data.get('items'):
            return []
        return [self._parse_volume(item) for item in data['items']]
