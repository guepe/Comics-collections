import base64
import logging
import re
from datetime import date

import requests

from odoo import models

_logger = logging.getLogger(__name__)


def _normalize_isbn(isbn):
    raw = re.sub(r'[\-\s]', '', isbn or '')
    if len(raw) == 10 and raw[:9].isdigit():
        base = '978' + raw[:9]
        total = sum(int(d) * (1 if i % 2 == 0 else 3) for i, d in enumerate(base))
        check = (10 - total % 10) % 10
        return base + str(check)
    return raw


class ComicEdition(models.Model):
    _inherit = 'comic.edition'

    def _apply_datasource_data(self, data):
        """Updates self (a comic.edition) with a normalized dict from the aggregator."""
        self.ensure_one()
        vals = {}

        if data.get('synopsis'):
            vals['synopsis'] = data['synopsis']
        if data.get('nb_pages'):
            vals['nb_pages'] = data['nb_pages']

        for field, key in [('date_parution', 'date_parution'), ('date_depot_legal', 'date_depot_legal')]:
            if data.get(key) and not getattr(self, field):
                try:
                    parts = str(data[key])[:10].split('-')
                    vals[field] = date(int(parts[0]), int(parts[1]), int(parts[2]))
                except Exception:
                    pass

        isbn_raw = data.get('isbn')
        if isbn_raw:
            isbn_norm = _normalize_isbn(isbn_raw) or isbn_raw
            existing_isbn = self.env['comic.isbn'].search([('isbn_13', '=', isbn_norm)], limit=1)
            if isbn_norm and not existing_isbn:
                self.env['comic.isbn'].create({'edition_id': self.id, 'isbn_13': isbn_norm})

        cover_url = data.get('cover_url') or data.get('cover_url_small')
        if cover_url and not self.image_couverture:
            try:
                resp = requests.get(cover_url, timeout=10)
                if resp.status_code == 200 and len(resp.content) > 100:
                    vals['image_couverture'] = base64.b64encode(resp.content).decode()
            except Exception as e:
                _logger.warning('Cover download failed for "%s": %s', self.display_name, e)

        if vals:
            self.write(vals)

        work = self.work_id
        for auteur in data.get('auteurs', []):
            name = (auteur.get('name') or '').strip()
            if not name:
                continue
            partner = self.env['res.partner'].search([('name', 'ilike', name)], limit=1)
            if not partner:
                partner = self.env['res.partner'].create({'name': name})
            role = auteur.get('role', 'autre')
            if not work.auteur_line_ids.filtered(lambda l: l.partner_id == partner and l.role == role):
                self.env['comic.work.auteur.line'].create({
                    'work_id': work.id,
                    'partner_id': partner.id,
                    'role': role,
                })

    def _cron_update_editions(self, batch_size=30):
        """Cron: enriches incomplete editions (missing synopsis, cover, or isbn)."""
        from ..aggregator import ComicDataAggregator

        domain = [
            '|', '|',
            ('synopsis', 'in', [False, '']),
            ('image_couverture', '=', False),
            ('isbn_ids', '=', False),
        ]
        editions = self.search(domain, limit=batch_size, order='write_date asc')
        if not editions:
            _logger.info('Cron éditions : aucune édition incomplète.')
            return

        _logger.info('Cron éditions : %d édition(s) à enrichir.', len(editions))
        aggregator = ComicDataAggregator(env=self.env)
        updated = 0

        for edition in editions:
            try:
                agg = None
                isbn = edition._get_primary_isbn()
                if isbn:
                    agg = aggregator.search(isbn=isbn)
                elif edition.work_id.titre_canonique:
                    results = aggregator.search_list(title=edition.work_id.titre_canonique)
                    if results:
                        best = next(
                            (r for r in results if r.isbn and r.tome == edition.work_id.tome),
                            next((r for r in results if r.isbn), None),
                        )
                        if best:
                            agg = aggregator.search(isbn=best.isbn)

                if not agg or not agg.data:
                    continue

                edition._apply_datasource_data(agg.data)
                updated += 1
            except Exception:
                _logger.exception('Cron édition : erreur sur "%s"', edition.display_name)

        _logger.info('Cron éditions terminé : %d/%d enrichie(s).', updated, len(editions))

    def _cron_update_albums(self, batch_size=30):
        """Backward-compatible entrypoint for older cron records."""
        return self._cron_update_editions(batch_size=batch_size)

    def action_search_datasource(self):
        """Opens the multi-source search wizard pre-filled with this edition's ISBN or title."""
        self.ensure_one()
        ctx = {'default_edition_id': self.id}
        isbn = self._get_primary_isbn()
        if isbn:
            ctx['default_search_term'] = isbn
        elif self.work_id.titre_canonique:
            ctx['default_search_term'] = self.work_id.titre_canonique
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'comic.datasource.search.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': ctx,
        }
