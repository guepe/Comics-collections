import logging
import requests
from .base import BaseComicSource, ComicSourceResult

_logger = logging.getLogger(__name__)

GOOGLE_BOOKS_URL = 'https://www.googleapis.com/books/v1/volumes'

ROLE_MAP = {
    'scenarist': 'scenariste',
    'illustrator': 'dessinateur',
    'colorist': 'coloriste',
    'translator': 'traducteur',
}


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
            if resp.status_code == 429:
                _logger.warning('Google Books: quota dépassé (HTTP 429)')
                return None
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            _logger.warning('Google Books: requête échouée: %s', e)
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

        published = info.get('publishedDate', '')
        # Normalise vers YYYY-MM-DD
        if published and len(published) == 4:
            published = published + '-01-01'
        elif published and len(published) == 7:
            published = published + '-01'

        return ComicSourceResult(
            source=self.SOURCE_NAME,
            title=info.get('title', ''),
            isbn=isbn,
            date_parution=published or None,
            nb_pages=info.get('pageCount') or None,
            editeur=info.get('publisher') or None,
            auteurs=auteurs,
            synopsis=info.get('description') or None,
            cover_url=images.get('extraLarge') or images.get('large') or images.get('medium') or None,
            cover_url_small=images.get('thumbnail') or images.get('smallThumbnail') or None,
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
