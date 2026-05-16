import logging
import re
import requests
import xmltodict
from .base import BaseComicSource, ComicSourceResult

_logger = logging.getLogger(__name__)

BNF_SRU_URL = 'http://catalogue.bnf.fr/api/SRU'


class BnfSource(BaseComicSource):
    SOURCE_NAME = 'bnf'

    def _sru_query(self, query: str):
        params = {
            'version': '1.2',
            'operation': 'searchRetrieve',
            'query': query,
            'maximumRecords': '10',
            'recordSchema': 'unimarcxchange',
        }
        try:
            resp = requests.get(BNF_SRU_URL, params=params, timeout=15)
            resp.raise_for_status()
            return xmltodict.parse(resp.text)
        except Exception as e:
            _logger.warning('BnF SRU: requête échouée: %s', e)
            return None

    def _extract_records(self, data):
        """Extrait la liste de records depuis la réponse SRU."""
        try:
            root = data.get('srw:searchRetrieveResponse', data)
            records = root.get('srw:records', {}).get('srw:record', [])
            if isinstance(records, dict):
                records = [records]
            return records
        except Exception:
            return []

    def _parse_unimarc(self, record) -> ComicSourceResult:
        """Parse un enregistrement UNIMARC BnF."""
        try:
            xml_data = record.get('srw:recordData', {})
            collection = xml_data.get('mxc:collection', xml_data.get('collection', {}))
            unimarc = collection.get('mxc:record', collection.get('record', {}))
        except Exception:
            return None

        fields = unimarc.get('mxc:datafield', unimarc.get('datafield', []))
        if isinstance(fields, dict):
            fields = [fields]

        def get_subfield(tag_code, subfield_code):
            for f in fields:
                if f.get('@tag') == tag_code:
                    subs = f.get('mxc:subfield', f.get('subfield', []))
                    if isinstance(subs, dict):
                        subs = [subs]
                    for s in subs:
                        if s.get('@code') == subfield_code:
                            return s.get('#text', '')
            return None

        def get_all_subfields(tag_code, subfield_code):
            results = []
            for f in fields:
                if f.get('@tag') == tag_code:
                    subs = f.get('mxc:subfield', f.get('subfield', []))
                    if isinstance(subs, dict):
                        subs = [subs]
                    for s in subs:
                        if s.get('@code') == subfield_code:
                            val = s.get('#text', '')
                            if val:
                                results.append(val)
            return results

        title = get_subfield('200', 'a') or ''
        isbn = get_subfield('010', 'a')
        if isbn:
            isbn = re.sub(r'[^0-9X]', '', isbn)

        editeur = get_subfield('210', 'c') or get_subfield('214', 'c')
        date_str = get_subfield('210', 'd') or get_subfield('214', 'd') or ''
        year_match = re.search(r'(\d{4})', date_str)
        date_parution = f'{year_match.group(1)}-01-01' if year_match else None

        depot_str = get_subfield('099', 'b') or ''
        year_depot = re.search(r'(\d{4})', depot_str)
        date_depot = f'{year_depot.group(1)}-01-01' if year_depot else None

        pages_str = get_subfield('215', 'a') or ''
        pages_match = re.search(r'(\d+)', pages_str)
        nb_pages = int(pages_match.group(1)) if pages_match else None

        auteurs = []
        for name in get_all_subfields('700', 'a'):
            auteurs.append({'name': name, 'role': 'scenariste'})
        for name in get_all_subfields('701', 'a'):
            auteurs.append({'name': name, 'role': 'dessinateur'})

        return ComicSourceResult(
            source=self.SOURCE_NAME,
            title=title,
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
