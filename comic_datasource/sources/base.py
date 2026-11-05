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
    'source': str,                  # 'google'|'openlibrary'|'bnf'
    'source_id': str | None,        # ID dans la source (ex: Google Books volume ID)
    'raw': dict,                    # Réponse brute pour debugging
}
"""

import logging
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import date
from typing import Optional


def _isbn10_is_valid(isbn10: str) -> bool:
    """Vérifie la clé de contrôle d'un ISBN-10 (9 chiffres + chiffre ou X)."""
    if len(isbn10) != 10 or not isbn10[:9].isdigit():
        return False
    last = isbn10[9].upper()
    if not (last.isdigit() or last == "X"):
        return False
    values = [int(d) for d in isbn10[:9]] + [10 if last == "X" else int(last)]
    return sum((10 - i) * v for i, v in enumerate(values)) % 11 == 0


def normalize_isbn(isbn):
    """Normalise un ISBN : supprime espaces/tirets et convertit un ISBN-10
    valide (clé de contrôle vérifiée, X accepté) en ISBN-13.

    Retourne l'ISBN-13 ou, si la conversion est impossible, la chaîne nettoyée.
    """
    raw = re.sub(r"[\-\s]", "", isbn or "")
    if len(raw) == 10 and _isbn10_is_valid(raw):
        base = "978" + raw[:9]
        total = sum(int(d) * (1 if i % 2 == 0 else 3) for i, d in enumerate(base))
        check = (10 - total % 10) % 10
        return base + str(check)
    return raw


def cql_quote(value) -> str:
    """Échappe une valeur pour l'insérer entre guillemets dans une requête CQL
    (SRU) : antislash et guillemets doubles sont précédés d'un antislash."""
    return (value or "").replace("\\", "\\\\").replace('"', '\\"')


_MONTHS = {
    # Anglais (Open Library) et français (BnF)
    "january": 1,
    "jan": 1,
    "janvier": 1,
    "janv": 1,
    "february": 2,
    "feb": 2,
    "fevrier": 2,
    "février": 2,
    "fevr": 2,
    "févr": 2,
    "march": 3,
    "mar": 3,
    "mars": 3,
    "april": 4,
    "apr": 4,
    "avril": 4,
    "avr": 4,
    "may": 5,
    "mai": 5,
    "june": 6,
    "jun": 6,
    "juin": 6,
    "july": 7,
    "jul": 7,
    "juillet": 7,
    "juil": 7,
    "august": 8,
    "aug": 8,
    "aout": 8,
    "août": 8,
    "september": 9,
    "sep": 9,
    "sept": 9,
    "septembre": 9,
    "october": 10,
    "oct": 10,
    "octobre": 10,
    "november": 11,
    "nov": 11,
    "novembre": 11,
    "december": 12,
    "dec": 12,
    "decembre": 12,
    "décembre": 12,
    "déc": 12,
}


def parse_full_date(value):
    """Convertit une date complète (jour, mois, année) en 'YYYY-MM-DD'.

    Une valeur partielle (année seule, mois + année) retourne None : on ne
    fabrique pas de date fictive du type 'YYYY-01-01'.
    Formats acceptés : 2005-03-14, 2005/03/14, 14/03/2005, 14.03.2005,
    'March 14, 2005', '14 March 2005', '14 mars 2005'.
    """
    text = (value or "").strip().lower()
    if not text:
        return None
    year = month = day = None
    m = re.search(r"\b(\d{4})[-/.](\d{1,2})[-/.](\d{1,2})\b", text)
    if m:
        year, month, day = (int(g) for g in m.groups())
    else:
        m = re.search(r"\b(\d{1,2})[-/.](\d{1,2})[-/.](\d{4})\b", text)
        if m:
            day, month, year = (int(g) for g in m.groups())
        else:
            m = re.search(r"\b([^\W\d_]+)\.?\s+(\d{1,2})(?:st|nd|rd|th)?,?\s+(\d{4})\b", text)
            if m and m.group(1) in _MONTHS:
                month, day, year = _MONTHS[m.group(1)], int(m.group(2)), int(m.group(3))
            else:
                m = re.search(r"\b(\d{1,2})(?:er)?\s+([^\W\d_]+)\.?\s+(\d{4})\b", text)
                if m and m.group(2) in _MONTHS:
                    day, month, year = int(m.group(1)), _MONTHS[m.group(2)], int(m.group(3))
    if not year:
        return None
    try:
        return date(year, month, day).isoformat()
    except ValueError:
        return None


# Patterns pour extraire la série et le tome depuis un titre Google Books
# Ex: "Astérix - Tome 1 : Astérix le Gaulois"  → serie="Astérix", tome=1, title="Astérix le Gaulois"
#     "Blacksad T. 1 : Quelque part entre les ombres" → serie="Blacksad", tome=1
#     "Largo Winch, tome 1"                            → serie="Largo Winch", tome=1
#     "Lucky Luke - Tome 12"                          → serie="Lucky Luke", tome=12
_BD_TITLE_PATTERNS = [
    # "Serie - Tome N : Titre" ou "Serie - T.N : Titre"
    re.compile(
        r"^(?P<serie>.+?)\s*[-,]\s*(?:tome|t\.?|vol\.?)\s*(?P<tome>\d+)\s*(?::\s*(?P<title>.+))?$",
        re.IGNORECASE,
    ),
    # "Serie T.N" ou "Serie Tome N" sans titre séparé
    re.compile(
        r"^(?P<serie>.+?)\s+(?:tome|t\.)\s*(?P<tome>\d+)$",
        re.IGNORECASE,
    ),
]


def parse_bd_title(full_title: str, subtitle: str = None):
    """
    Tente d'extraire (serie_name, tome, clean_title) d'un titre Google Books.
    Retourne (serie_name, tome, clean_title) — chacun peut être None si non détecté.
    """
    if not full_title:
        return None, None, full_title

    for pattern in _BD_TITLE_PATTERNS:
        m = pattern.match(full_title.strip())
        if m:
            serie = m.group("serie").strip()
            tome = int(m.group("tome"))
            title = m.group("title").strip() if m.lastindex >= 3 and m.group("title") else full_title
            return serie, tome, title

    # Cherche le numéro de tome dans le subtitle si dispo
    if subtitle:
        m = re.search(r"(?:tome|t\.?|vol\.?)\s*(\d+)", subtitle, re.IGNORECASE)
        if m:
            return None, int(m.group(1)), full_title

    return None, None, full_title


_logger = logging.getLogger(__name__)


@dataclass
class ComicSourceResult:
    """Modèle normalisé pour les résultats de toutes les sources."""

    source: str
    title: str = ""
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
            "title": self.title,
            "serie_name": self.serie_name,
            "tome": self.tome,
            "isbn": self.isbn,
            "date_parution": self.date_parution,
            "date_depot_legal": self.date_depot_legal,
            "nb_pages": self.nb_pages,
            "editeur": self.editeur,
            "auteurs": self.auteurs,
            "synopsis": self.synopsis,
            "cover_url": self.cover_url,
            "cover_url_small": self.cover_url_small,
            "source": self.source,
            "source_id": self.source_id,
            "raw": self.raw,
        }


class BaseComicSource(ABC):
    """Interface commune pour toutes les sources de données BD."""

    SOURCE_NAME = ""  # à définir dans chaque sous-classe

    def __init__(self, env=None):
        self._env = env  # environnement Odoo (accès ir.config_parameter)

    def _get_config(self, key, default=None):
        if self._env:
            return self._env["ir.config_parameter"].sudo().get_param(key, default)
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
            _logger.warning("%s: request failed: %s", self.SOURCE_NAME, e)
            return None
