"""
Scraper pour BDGest / Bedetheque (bedetheque.com).

Usage depuis Odoo :
    from odoo.addons.comic_bdgest.scraper import BdgestScraper
    scraper = BdgestScraper(request_delay=2)
    results = scraper.search_by_title("Blacksad")
    detail  = scraper.get_album_detail(12345)

Toutes les méthodes publiques lèvent BdgestError (ou une sous-classe)
en cas d'erreur réseau, 404, blocage IP ou timeout.
Le parsing HTML est délégué à BdgestParser (sans dépendance HTTP).
"""

import base64
import logging
import re
import time

import requests

from .bdgest_parser import BdgestParser

_logger = logging.getLogger(__name__)

BASE_URL = "https://www.bedetheque.com"
SEARCH_ALBUMS_URL = f"{BASE_URL}/recherche-albums.html"
LOGIN_URL = f"{BASE_URL}/log_in.php"

DEFAULT_HEADERS = {
    'User-Agent': (
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
        'AppleWebKit/537.36 (KHTML, like Gecko) '
        'Chrome/120.0.0.0 Safari/537.36'
    ),
    'Accept-Language': 'fr-FR,fr;q=0.9,en;q=0.8',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Referer': BASE_URL,
}

# ──────────────────────────────────────────────────────────────
# Exceptions
# ──────────────────────────────────────────────────────────────


class BdgestError(Exception):
    """Erreur générique BDGest."""


class BdgestTimeoutError(BdgestError):
    """Timeout de la requête HTTP."""


class BdgestNotFoundError(BdgestError):
    """Ressource introuvable (404)."""


class BdgestBlockedError(BdgestError):
    """BDGest bloque l'accès (captcha, rate-limit, ban IP)."""


# ──────────────────────────────────────────────────────────────
# Scraper
# ──────────────────────────────────────────────────────────────


class BdgestScraper:
    """
    Scraper HTTP pour bedetheque.com.

    Paramètres
    ----------
    request_delay : float
        Délai minimum en secondes entre deux requêtes (défaut 2 s).
    login / password : str | None
        Identifiants BDGest pour accéder aux informations membres.
    """

    def __init__(self, request_delay=2.0, login=None, password=None):
        self.request_delay = request_delay
        self._last_request_time = 0.0
        self._session = requests.Session()
        self._session.headers.update(DEFAULT_HEADERS)
        if login and password:
            self._authenticate(login, password)

    # ──────────────────────────────────────────────────────────
    # API publique
    # ──────────────────────────────────────────────────────────

    def search_by_title(self, term):
        """
        Recherche des albums par titre.

        Retourne : list[dict] — données partielles (sans ISBN ni détail complet).
        """
        response = self._get(SEARCH_ALBUMS_URL, params={'RechAlbumTitre': term})
        return BdgestParser.parse_search_results(response.text)

    def search_by_isbn(self, isbn):
        """
        Recherche un album par EAN-13 / ISBN.

        Retourne : dict | None
        """
        isbn_clean = re.sub(r'[\s\-]', '', isbn)
        response = self._get(SEARCH_ALBUMS_URL, params={'RechAlbumEan': isbn_clean})
        results = BdgestParser.parse_search_results(response.text)
        return results[0] if results else None

    def search_by_author(self, term):
        """
        Recherche des albums par nom d'auteur.

        Retourne : list[dict]
        """
        response = self._get(SEARCH_ALBUMS_URL, params={'RechAlbumAuteur': term})
        return BdgestParser.parse_search_results(response.text)

    def get_album_detail(self, bdgest_album_id):
        """
        Récupère la fiche complète d'un album depuis son ID BDGest.

        Retourne : dict avec tous les champs disponibles.
        """
        url = f"{BASE_URL}/album-{bdgest_album_id}-.html"
        response = self._get(url)
        return BdgestParser.parse_album_detail(response.text, bdgest_album_id)

    def get_serie_albums(self, serie_id):
        """
        Récupère la liste de tous les albums d'une série depuis son ID BDGest.

        Retourne : list[dict] — données partielles, sans téléchargement d'images.
        """
        url = f"{BASE_URL}/serie-{serie_id}-.html"
        response = self._get(url)
        return BdgestParser.parse_serie_albums(response.text)

    def download_image_b64(self, image_url):
        """
        Télécharge une image de couverture et la retourne en base64.

        Retourne : str (base64 brut, sans préfixe data:) | None
        """
        if not image_url:
            return None
        try:
            resp = self._get(image_url)
            return base64.b64encode(resp.content).decode('utf-8')
        except BdgestError:
            _logger.warning("Impossible de télécharger l'image : %s", image_url)
            return None

    # ──────────────────────────────────────────────────────────
    # HTTP
    # ──────────────────────────────────────────────────────────

    def _get(self, url, params=None):
        self._rate_limit()
        try:
            response = self._session.get(url, params=params, timeout=15)
            self._last_request_time = time.time()
        except requests.exceptions.Timeout as exc:
            raise BdgestTimeoutError(f"Timeout : {url}") from exc
        except requests.exceptions.ConnectionError as exc:
            raise BdgestError(f"Erreur de connexion : {url}") from exc

        if self._is_blocked(response):
            raise BdgestBlockedError(
                "BDGest a bloqué la requête (captcha ou limitation IP). "
                "Attendez quelques minutes avant de réessayer."
            )
        try:
            response.raise_for_status()
        except requests.exceptions.HTTPError as exc:
            if response.status_code == 404:
                raise BdgestNotFoundError(f"Page introuvable : {url}") from exc
            raise BdgestError(
                f"Erreur HTTP {response.status_code} : {url}"
            ) from exc

        return response

    def _rate_limit(self):
        elapsed = time.time() - self._last_request_time
        if elapsed < self.request_delay:
            time.sleep(self.request_delay - elapsed)

    @staticmethod
    def _is_blocked(response):
        if response.status_code in (403, 429, 503):
            return True
        if b'captcha' in response.content[:1000].lower():
            return True
        return False

    def _authenticate(self, login, password):
        """Connexion BDGest pour accéder aux fonctionnalités membres."""
        try:
            self._get(LOGIN_URL)  # récupère les cookies de session
            self._session.post(
                LOGIN_URL,
                data={'login': login, 'password': password, 'redirect': '/'},
                timeout=15,
            )
            _logger.info("Authentification BDGest réussie pour %s", login)
        except BdgestError as exc:
            _logger.warning("Échec authentification BDGest : %s", exc)
