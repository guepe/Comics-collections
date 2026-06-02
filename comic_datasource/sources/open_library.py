import logging
import requests
from .base import BaseComicSource, ComicSourceResult

_logger = logging.getLogger(__name__)

OL_BOOKS_URL = "https://openlibrary.org/api/books"
OL_COVERS_URL = "https://covers.openlibrary.org/b/isbn/{isbn}-{size}.jpg"
OL_SEARCH_URL = "https://openlibrary.org/search.json"


class OpenLibrarySource(BaseComicSource):
    SOURCE_NAME = "openlibrary"

    def is_available(self) -> bool:
        # Activée par défaut ; désactivable via paramètre
        val = self._get_config("comic.openlibrary_enabled", "True")
        return val != "False"

    def _cover_url(self, isbn, size="L"):
        return OL_COVERS_URL.format(isbn=isbn, size=size)

    def _cover_exists(self, isbn, size="L"):
        """Vérifie l'existence de la couverture avant de la retourner."""
        url = self._cover_url(isbn, size)
        try:
            resp = requests.head(url, timeout=5, allow_redirects=True)
            # Open Library retourne une image placeholder de 1 octet si absente
            content_length = int(resp.headers.get("Content-Length", 999))
            return resp.status_code == 200 and content_length > 100
        except Exception:
            return False

    def _parse_book_data(self, isbn, data) -> ComicSourceResult:
        key = f"ISBN:{isbn}"
        book = data.get(key, {})
        if not book:
            return None

        details = book.get("details", {})
        authors = []
        for a in book.get("authors", []):
            authors.append({"name": a.get("name", ""), "role": "scenariste"})

        published = details.get("publish_date", "") or ""
        # Tente d'extraire une année à 4 chiffres
        import re

        year_match = re.search(r"(\d{4})", published)
        date_parution = f"{year_match.group(1)}-01-01" if year_match else None

        publishers = book.get("publishers", [])
        editeur = publishers[0].get("name") if publishers else None

        cover_url = None
        cover_url_small = None
        if self._cover_exists(isbn, "L"):
            cover_url = self._cover_url(isbn, "L")
            cover_url_small = self._cover_url(isbn, "S")

        return ComicSourceResult(
            source=self.SOURCE_NAME,
            title=book.get("title", ""),
            isbn=isbn,
            date_parution=date_parution,
            nb_pages=details.get("number_of_pages") or None,
            editeur=editeur,
            auteurs=authors,
            synopsis=book.get("notes") or None,
            cover_url=cover_url,
            cover_url_small=cover_url_small,
            source_id=details.get("key"),
            raw=book,
        )

    def search_by_isbn(self, isbn: str):
        try:
            resp = requests.get(
                OL_BOOKS_URL,
                params={"bibkeys": f"ISBN:{isbn}", "format": "json", "jscmd": "data"},
                timeout=10,
            )
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            _logger.warning("Open Library: requête échouée: %s", e)
            return None

        return self._parse_book_data(isbn, data)

    def search_by_title(self, title: str, author: str = None) -> list:
        params = {"q": title, "limit": 10}
        if author:
            params["author"] = author
        try:
            resp = requests.get(OL_SEARCH_URL, params=params, timeout=10)
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            _logger.warning("Open Library search: requête échouée: %s", e)
            return []

        results = []
        for doc in data.get("docs", []):
            isbn_list = doc.get("isbn", [])
            isbn = next((i for i in isbn_list if len(i) == 13), isbn_list[0] if isbn_list else None)
            authors = [{"name": a, "role": "scenariste"} for a in doc.get("author_name", [])]
            cover_url = None
            if isbn and self._cover_exists(isbn, "L"):
                cover_url = self._cover_url(isbn, "L")
            results.append(
                ComicSourceResult(
                    source=self.SOURCE_NAME,
                    title=doc.get("title", ""),
                    isbn=isbn,
                    date_parution=f"{doc['first_publish_year']}-01-01" if doc.get("first_publish_year") else None,
                    nb_pages=doc.get("number_of_pages_median") or None,
                    editeur=doc.get("publisher", [None])[0],
                    auteurs=authors,
                    cover_url=cover_url,
                    source_id=doc.get("key"),
                    raw=doc,
                )
            )
        return results
