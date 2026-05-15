"""
Classe de base abstraite pour toutes les sources de données BD.

Modèle normalisé retourné par chaque source (ComicSourceResult) :
{
    'title': str,                   # Titre de l'album
    'serie_name': str | None,       # Nom de la série
    'tome': int | None,             # Numéro de tome
    'isbn': str | None,             # ISBN EAN-13
    'date_parution': str | None,    # Format YYYY-MM-DD
    'date_depot_legal': str | None, # Format YYYY-MM-DD (BnF uniquement)
    'nb_pages': int | None,
    'editeur': str | None,
    'auteurs': [
        {'name': str, 'role': 'scenariste'|'dessinateur'|'coloriste'|'traducteur'|'autre'}
    ],
    'synopsis': str | None,         # HTML ou texte brut
    'cover_url': str | None,        # URL couverture haute résolution
    'cover_url_small': str | None,  # URL couverture miniature
    'source': str,                  # 'google'|'openlibrary'|'bnf'|'bdgest'
    'source_id': str | None,        # ID dans la source (ex: Google Books volume ID)
    'raw': dict,                    # Réponse brute pour debugging
}
"""
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional

_logger = logging.getLogger(__name__)


@dataclass
class ComicSourceResult:
    """Modèle normalisé pour les résultats de toutes les sources."""
    source: str
    title: str = ''
    serie_name: Optional[str] = None
    tome: Optional[int] = None
    isbn: Optional[str] = None
    date_parution: Optional[str] = None
    date_depot_legal: Optional[str] = None
    nb_pages: Optional[int] = None
    editeur: Optional[str] = None
    auteurs: list = field(default_factory=list)
    synopsis: Optional[str] = None
    cover_url: Optional[str] = None
    cover_url_small: Optional[str] = None
    source_id: Optional[str] = None
    raw: dict = field(default_factory=dict)

    def to_dict(self):
        return {
            'title': self.title,
            'serie_name': self.serie_name,
            'tome': self.tome,
            'isbn': self.isbn,
            'date_parution': self.date_parution,
            'date_depot_legal': self.date_depot_legal,
            'nb_pages': self.nb_pages,
            'editeur': self.editeur,
            'auteurs': self.auteurs,
            'synopsis': self.synopsis,
            'cover_url': self.cover_url,
            'cover_url_small': self.cover_url_small,
            'source': self.source,
            'source_id': self.source_id,
            'raw': self.raw,
        }


class BaseComicSource(ABC):
    """Interface commune pour toutes les sources de données BD."""

    SOURCE_NAME = ''  # à définir dans chaque sous-classe

    def __init__(self, env=None):
        self._env = env  # environnement Odoo (accès ir.config_parameter)

    def _get_config(self, key, default=None):
        if self._env:
            return self._env['ir.config_parameter'].sudo().get_param(key, default)
        return default

    @abstractmethod
    def search_by_isbn(self, isbn: str) -> Optional[ComicSourceResult]:
        """Recherche un album par ISBN. Retourne None si non trouvé."""

    @abstractmethod
    def search_by_title(self, title: str, author: str = None) -> list:
        """
        Recherche des albums par titre (+ auteur optionnel).
        Retourne une liste de ComicSourceResult (peut être vide).
        """

    def is_available(self) -> bool:
        """Indique si la source est configurée et utilisable."""
        return True

    def _safe_request(self, func, *args, **kwargs):
        """Wrapper pour capturer les erreurs réseau sans crasher."""
        try:
            return func(*args, **kwargs)
        except Exception as e:
            _logger.warning('%s: request failed: %s', self.SOURCE_NAME, e)
            return None
