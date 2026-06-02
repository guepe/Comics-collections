import logging
import re
import requests
import xmltodict
from .base import BaseComicSource, ComicSourceResult

_logger = logging.getLogger(__name__)

BNF_SRU_URL = "http://catalogue.bnf.fr/api/SRU"


class BnfSource(BaseComicSource):
    SOURCE_NAME = "bnf"

    def is_available(self) -> bool:
        # Activée par défaut ; désactivable via paramètre
        val = self._get_config("comic.bnf_enabled", "True")
        return val != "False"

    def _sru_query(self, query: str, max_records: int = 10, start_record: int = 1):
        params = {
            "version": "1.2",
            "operation": "searchRetrieve",
            "query": query,
            "maximumRecords": str(max_records),
            "startRecord": str(start_record),
            "recordSchema": "unimarcxchange",
        }
        try:
            resp = requests.get(BNF_SRU_URL, params=params, timeout=15)
            resp.raise_for_status()
            return xmltodict.parse(resp.text)
        except Exception as e:
            _logger.warning("BnF SRU: requête échouée: %s", e)
            return None

    def _extract_records(self, data):
        """Extrait la liste de records depuis la réponse SRU."""
        try:
            root = data.get("srw:searchRetrieveResponse", data)
            records = root.get("srw:records", {}).get("srw:record", [])
            if isinstance(records, dict):
                records = [records]
            return records
        except Exception:
            return []

    def _extract_total(self, data) -> int:
        """Retourne le nombre total de résultats déclaré par le SRU."""
        try:
            root = data.get("srw:searchRetrieveResponse", data)
            return int(root.get("srw:numberOfRecords", 0))
        except Exception:
            return 0

    def _parse_unimarc(self, record) -> ComicSourceResult:
        """Parse un enregistrement UNIMARC BnF."""
        try:
            xml_data = record.get("srw:recordData", {})
            collection = xml_data.get("mxc:collection", xml_data.get("collection", {}))
            unimarc = collection.get("mxc:record", collection.get("record", {}))
        except Exception:
            return None

        fields = unimarc.get("mxc:datafield", unimarc.get("datafield", []))
        if isinstance(fields, dict):
            fields = [fields]

        def get_subfield(tag_code, subfield_code):
            for f in fields:
                if f.get("@tag") == tag_code:
                    subs = f.get("mxc:subfield", f.get("subfield", []))
                    if isinstance(subs, dict):
                        subs = [subs]
                    for s in subs:
                        if s.get("@code") == subfield_code:
                            return s.get("#text", "")
            return None

        def get_all_subfields(tag_code, subfield_code):
            results = []
            for f in fields:
                if f.get("@tag") == tag_code:
                    subs = f.get("mxc:subfield", f.get("subfield", []))
                    if isinstance(subs, dict):
                        subs = [subs]
                    for s in subs:
                        if s.get("@code") == subfield_code:
                            val = s.get("#text", "")
                            if val:
                                results.append(val)
            return results

        title = get_subfield("200", "a") or ""
        isbn = get_subfield("010", "a")
        if isbn:
            isbn = re.sub(r"[^0-9X]", "", isbn)

        editeur = get_subfield("210", "c") or get_subfield("214", "c")
        date_str = get_subfield("210", "d") or get_subfield("214", "d") or ""
        year_match = re.search(r"(\d{4})", date_str)
        date_parution = f"{year_match.group(1)}-01-01" if year_match else None

        depot_str = get_subfield("099", "b") or ""
        year_depot = re.search(r"(\d{4})", depot_str)
        date_depot = f"{year_depot.group(1)}-01-01" if year_depot else None

        pages_str = get_subfield("215", "a") or ""
        pages_match = re.search(r"(\d+)", pages_str)
        nb_pages = int(pages_match.group(1)) if pages_match else None

        auteurs = []
        for name in get_all_subfields("700", "a"):
            auteurs.append({"name": name, "role": "scenariste"})
        for name in get_all_subfields("701", "a"):
            auteurs.append({"name": name, "role": "dessinateur"})

        # Numéro de tome : field 225v (volume dans la série) ou 200h (désignation volume)
        tome = None
        for tag, sub in [("225", "v"), ("200", "h"), ("463", "v")]:
            val = get_subfield(tag, sub)
            if val:
                m = re.search(r"(\d+)", val)
                if m:
                    tome = int(m.group(1))
                    break
        # Fallback : cherche un numéro dans le titre lui-même
        if not tome and title:
            m = re.search(
                r"(?:tome|t\.?|vol\.?|volume|n°)\s*\.?\s*(\d+)",
                title,
                re.IGNORECASE,
            )
            if m:
                tome = int(m.group(1))

        return ComicSourceResult(
            source=self.SOURCE_NAME,
            title=title,
            tome=tome,
            isbn=isbn,
            date_parution=date_parution,
            date_depot_legal=date_depot,
            nb_pages=nb_pages,
            editeur=editeur,
            auteurs=auteurs,
            raw=record,
        )

    def search_by_isbn(self, isbn: str):
        data = self._sru_query(f'bib.isbn adj "{isbn}"')
        if not data:
            return None
        records = self._extract_records(data)
        if not records:
            return None
        return self._parse_unimarc(records[0])

    def search_by_serie(self, serie_name: str, page_size: int = 50, max_results: int = 200) -> list:
        """Recherche tous les albums d'une série via BnF SRU, avec pagination complète.
        Essaie bib.serie adj d'abord, puis bib.title adj si peu de résultats."""
        # Essai 1 : champ série UNIMARC 225 — le plus précis
        results = self._paginate_query(
            f'bib.serie adj "{serie_name}"',
            page_size,
            max_results,
        )
        # Essai 2 : phrase exacte dans le titre — rattrape les albums non taggués en série
        # On cumule uniquement si le premier essai a retourné peu de résultats
        if len(results) < 5:
            title_results = self._paginate_query(
                f'bib.title adj "{serie_name}"',
                page_size,
                max_results,
            )
            # Déduplique par ISBN, puis par titre
            seen_isbns = {r.isbn for r in results if r.isbn}
            seen_titles = {r.title.lower() for r in results if r.title}
            for r in title_results:
                if r.isbn and r.isbn in seen_isbns:
                    continue
                if r.title and r.title.lower() in seen_titles:
                    continue
                results.append(r)
                if r.isbn:
                    seen_isbns.add(r.isbn)
                if r.title:
                    seen_titles.add(r.title.lower())
        return results

    def _paginate_query(self, query: str, page_size: int, max_results: int = 200) -> list:
        """Exécute une requête SRU avec pagination, capée à max_results enregistrements."""
        results = []
        start = 1
        total = None

        while True:
            batch_size = min(page_size, max_results - len(results))
            data = self._sru_query(query, max_records=batch_size, start_record=start)
            if not data:
                break

            if total is None:
                total = self._extract_total(data)
                if total == 0:
                    break
                _logger.info('BnF "%s" : %d résultats (cap %d)', query[:60], total, max_results)

            records = self._extract_records(data)
            if not records:
                break

            for record in records:
                parsed = self._parse_unimarc(record)
                if parsed:
                    results.append(parsed)

            start += len(records)
            if start > total or len(records) < batch_size or len(results) >= max_results:
                break

        return results

    def search_by_title(self, title: str, author: str = None) -> list:
        query = f'bib.title adj "{title}"'
        if author:
            query += f' and bib.author adj "{author}"'
        data = self._sru_query(query)
        if not data:
            return []
        records = self._extract_records(data)
        results = []
        for record in records:
            parsed = self._parse_unimarc(record)
            if parsed:
                results.append(parsed)
        return results
