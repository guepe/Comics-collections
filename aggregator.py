"""
ComicDataAggregator — fusionne les données de toutes les sources disponibles.

Cascade par défaut : Google Books → Open Library → BnF → BDGest
Règles de fusion :
- Premier champ non-vide trouvé est retenu (sauf exceptions ci-dessous)
- synopsis : Google > BnF > BDGest (Open Library rarement utile)
- date_depot_legal : BnF prioritaire (seule source officielle)
- cover_url : Google extraLarge > Open Library L > BDGest
"""
import logging
from .sources import GoogleBooksSource, OpenLibrarySource, BnfSource, BdgestSource
from .sources.base import ComicSourceResult

_logger = logging.getLogger(__name__)

DEFAULT_SOURCE_ORDER = ['google', 'openlibrary', 'bnf', 'bdgest']

# Pour chaque champ : ordre de priorité des sources (différent de l'ordre de cascade)
FIELD_PRIORITY = {
    'synopsis': ['google', 'bnf', 'bdgest', 'openlibrary'],
    'date_depot_legal': ['bnf'],
    'cover_url': ['google', 'openlibrary', 'bdgest'],
    'cover_url_small': ['google', 'openlibrary', 'bdgest'],
}


class AggregatedResult:
    """
    Résultat fusionné avec traçabilité de la source de chaque champ.
    """
    def __init__(self):
        self.data = {}
        self.field_sources = {}  # field_name → source_name

    def set_field(self, field, value, source):
        if value is not None and value != '' and field not in self.data:
            self.data[field] = value
            self.field_sources[field] = source

    def set_field_force(self, field, value, source):
        """Écrase même si déjà rempli (pour les champs à priorité explicite)."""
        if value is not None and value != '':
            self.data[field] = value
            self.field_sources[field] = source

    def to_dict(self):
        return {**self.data, 'field_sources': self.field_sources}


class ComicDataAggregator:
    """
    Agrège les données de plusieurs sources BD.
    Instancier avec l'env Odoo pour accéder à la configuration.
    """

    def __init__(self, env=None):
        self._env = env
        self._sources = {
            'google': GoogleBooksSource(env),
            'openlibrary': OpenLibrarySource(env),
            'bnf': BnfSource(env),
            'bdgest': BdgestSource(env),
        }
        self._cache = {}  # clé: "isbn:XXX" ou "title:XXX" → résultat

    def _source_order(self):
        config = None
        if self._env:
            import json
            raw = self._env['ir.config_parameter'].sudo().get_param('comic.datasource_order', '')
            if raw:
                try:
                    config = json.loads(raw)
                except Exception:
                    pass
        return config or DEFAULT_SOURCE_ORDER

    def search(self, isbn=None, title=None, author=None) -> AggregatedResult:
        cache_key = f'isbn:{isbn}' if isbn else f'title:{title}:{author}'
        if cache_key in self._cache:
            return self._cache[cache_key]

        order = self._source_order()
        results_by_source = {}

        # 1. Collecte — chaque source disponible est interrogée
        for source_name in order:
            source = self._sources.get(source_name)
            if not source or not source.is_available():
                continue
            result = None
            if isbn:
                result = self._safe_search(source.search_by_isbn, isbn)
            elif title:
                results_list = self._safe_search(source.search_by_title, title, author)
                result = results_list[0] if results_list else None

            if result:
                _logger.info('Datasource: %s a trouvé "%s"', source_name, result.title)
                results_by_source[source_name] = result

        if not results_by_source:
            return AggregatedResult()

        # 2. Fusion — champ par champ selon les règles de priorité
        aggregated = AggregatedResult()
        scalar_fields = ['title', 'serie_name', 'tome', 'isbn', 'date_parution',
                         'date_depot_legal', 'nb_pages', 'editeur', 'synopsis',
                         'cover_url', 'cover_url_small']

        for field in scalar_fields:
            priority = FIELD_PRIORITY.get(field, order)
            for source_name in priority:
                result = results_by_source.get(source_name)
                if result:
                    value = getattr(result, field, None)
                    if value:
                        aggregated.set_field_force(field, value, source_name)
                        break

        # auteurs : prend la liste la plus complète disponible
        best_auteurs = []
        for source_name in order:
            result = results_by_source.get(source_name)
            if result and result.auteurs and len(result.auteurs) > len(best_auteurs):
                best_auteurs = result.auteurs
                auteurs_source = source_name
        if best_auteurs:
            aggregated.set_field('auteurs', best_auteurs, auteurs_source)

        aggregated.set_field('sources_queried', list(results_by_source.keys()), 'aggregator')

        self._cache[cache_key] = aggregated
        return aggregated

    def search_list(self, title: str, author: str = None) -> list:
        """Retourne la liste brute de tous les résultats (non fusionnés), toutes sources."""
        order = self._source_order()
        all_results = []
        for source_name in order:
            source = self._sources.get(source_name)
            if not source or not source.is_available():
                continue
            results = self._safe_search(source.search_by_title, title, author) or []
            all_results.extend(results)
        return all_results

    def _safe_search(self, method, *args):
        try:
            return method(*args)
        except Exception as e:
            _logger.warning('Aggregator: source error: %s', e)
            return None
