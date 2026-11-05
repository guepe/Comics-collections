import logging
import requests
from .base import BaseComicSource, ComicSourceResult, parse_full_date

_logger = logging.getLogger(__name__)

OL_BOOKS_URL = "https://openlibrary.org/api/books"
# `?default=false` : Open Library renvoie un 404 au lieu d'une image vide quand
# la couverture n'existe pas — le téléchargeur l'écarte (status != 200).
OL_COVERS_URL = "https://covers.openlibrary.org/b/isbn/{isbn}-{size}.jpg?default=false"
OL_COVERS_ID_URL = "https://covers.openlibrary.org/b/id/{cover_id}-{size}.jpg"
OL_SEARCH_URL = "https://openlibrary.org/search.json"


class OpenLibrarySource(BaseComicSource):
    SOURCE_NAME = "openlibrary"

    def is_available(self) -> bool:
        # Activée par défaut ; désactivable via paramètre
        val = self._get_config("comic.openlibrary_enabled", "True")
        return val != "False"

    def _cover_url(self, isbn, size="L"):
        return OL_COVERS_URL.format(isbn=isbn, size=size)

    def _cover_id_url(self, cover_id, size="L"):
        return OL_COVERS_ID_URL.format(cover_id=cover_id, size=size) if cover_id else None

    def _parse_book_data(self, isbn, data) -> ComicSourceResult:
        key = f"ISBN:{isbn}"
        book = data.get(key, {})
        if not book:
            return None

        details = book.get("details", {})
        authors = []
        for a in book.get("authors", []):
            authors.append({"name": a.get("name", ""), "role": "scenariste"})

        # Uniquement une date complète : une année seule ne devient pas YYYY-01-01.
        date_parution = parse_full_date(details.get("publish_date"))

        publishers = book.get("publishers", [])
        editeur = publishers[0].get("name") if publishers else None

        # Pas de requête HEAD : l'URL `?default=false` renvoie 404 si la
        # couverture est absente, ce que le téléchargeur gère.
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
            # Couverture construite depuis `cover_i` (aucune requête HEAD).
            cover_id = doc.get("cover_i")
            results.append(
                ComicSourceResult(
                    source=self.SOURCE_NAME,
                    title=doc.get("title", ""),
                    isbn=isbn,
                    # `first_publish_year` = 1re publication de l'œuvre, pas de cette
                    # édition : non repris comme date de parution.
                    date_parution=None,
                    nb_pages=doc.get("number_of_pages_median") or None,
                    editeur=doc.get("publisher", [None])[0],
                    auteurs=authors,
                    cover_url=self._cover_id_url(cover_id, "L"),
                    cover_url_small=self._cover_id_url(cover_id, "M"),
                    source_id=doc.get("key"),
                    raw=doc,
                )
            )
        return results
