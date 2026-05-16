import base64
import logging
import re

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


class ComicAlbum(models.Model):
    _inherit = 'comic.album'

    # ── Mise à jour depuis les sources de données ──────────────────────────────

    def _apply_datasource_data(self, data):
        """Met à jour self (un album) avec un dict normalisé venant de l'aggregator."""
        self.ensure_one()
        vals = {}

        if data.get('synopsis'):
            vals['synopsis'] = data['synopsis']
        if data.get('nb_pages'):
            vals['nb_pages'] = data['nb_pages']
        if data.get('isbn') and not self.isbn:
            vals['isbn'] = _normalize_isbn(data['isbn']) or data['isbn']

        for field, key in [('date_parution', 'date_parution'), ('date_depot_legal', 'date_depot_legal')]:
            if data.get(key) and not getattr(self, field):
                try:
                    from datetime import date
                    parts = str(data[key])[:10].split('-')
                    vals[field] = date(int(parts[0]), int(parts[1]), int(parts[2]))
                except Exception:
                    pass

        cover_url = data.get('cover_url') or data.get('cover_url_small')
        if cover_url and not self.image_couverture:
            try:
                resp = requests.get(cover_url, timeout=10)
                if resp.status_code == 200 and len(resp.content) > 100:
                    vals['image_couverture'] = base64.b64encode(resp.content).decode()
            except Exception as e:
                _logger.warning('Cover download failed for "%s": %s', self.name, e)

        if vals:
            self.write(vals)

        for auteur in data.get('auteurs', []):
            name = (auteur.get('name') or '').strip()
            if not name:
                continue
            partner = self.env['res.partner'].search([('name', 'ilike', name)], limit=1)
            if not partner:
                partner = self.env['res.partner'].create({'name': name})
            if not self.auteur_line_ids.filtered(lambda l: l.partner_id == partner):
                self.env['comic.album.auteur.line'].create({
                    'album_id': self.id,
                    'partner_id': partner.id,
                    'role': auteur.get('role', 'autre'),
                })

    def _cron_update_albums(self, batch_size=30):
        """Cron : enrichit les albums incomplets (sans synopsis, couverture ou ISBN).

        Règle : on ne traite un album que si une source externe retourne un résultat
        avec un ISBN. Sans ISBN confirmé, on passe — cela évite d'appliquer des
        données ambiguës issues d'une simple correspondance de titre.
        """
        from ..aggregator import ComicDataAggregator

        domain = [
            '|', '|',
            ('synopsis', 'in', [False, '']),
            ('image_couverture', '=', False),
            ('isbn', 'in', [False, '']),
        ]
        albums = self.search(domain, limit=batch_size, order='dans_collection desc, write_date asc')
        if not albums:
            _logger.info('Cron mise à jour albums : aucun album incomplet.')
            return

        _logger.info('Cron mise à jour albums : %d album(s) à traiter.', len(albums))
        aggregator = ComicDataAggregator(env=self.env)
        updated = 0

        for album in albums:
            try:
                agg = None
                if album.isbn:
                    agg = aggregator.search(isbn=album.isbn)
                elif album.name:
                    results = aggregator.search_list(title=album.name)
                    if results:
                        # Prend le premier résultat avec ISBN (tome exact en priorité,
                        # puis n'importe quel résultat avec ISBN toutes sources confondues).
                        # Sans ISBN confirmé, on ignore cet album.
                        best = next(
                            (r for r in results if r.isbn and r.tome == album.tome),
                            next((r for r in results if r.isbn), None),
                        )
                        if best:
                            agg = aggregator.search(isbn=best.isbn)

                if not agg or not agg.data:
                    continue

                album._apply_datasource_data(agg.data)
                updated += 1
            except Exception:
                _logger.exception('Cron album update: erreur sur "%s"', album.name)

        _logger.info(
            'Cron mise à jour albums terminé : %d/%d album(s) enrichi(s).',
            updated, len(albums),
        )

    def action_search_datasource(self):
        """Ouvre le wizard de recherche multi-sources pré-rempli avec l'ISBN ou le titre."""
        self.ensure_one()
        ctx = {'default_album_id': self.id}
        if self.isbn:
            ctx['default_search_term'] = self.isbn
        elif self.name:
            ctx['default_search_term'] = self.name
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'comic.datasource.search.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': ctx,
        }
