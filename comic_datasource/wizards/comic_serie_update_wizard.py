import base64
import logging
import re

import requests

from odoo import _, api, fields, models

_logger = logging.getLogger(__name__)


def _normalize_isbn(isbn):
    raw = re.sub(r'[\-\s]', '', isbn or '')
    if len(raw) == 10 and raw[:9].isdigit():
        base = '978' + raw[:9]
        total = sum(int(d) * (1 if i % 2 == 0 else 3) for i, d in enumerate(base))
        check = (10 - total % 10) % 10
        return base + str(check)
    return raw


class ComicSerieUpdateWizard(models.TransientModel):
    _name = 'comic.serie.update.wizard'
    _description = "Mise à jour en lot des albums d'une série depuis les sources de données"

    serie_id = fields.Many2one('comic.serie', required=True, readonly=True)
    nb_albums = fields.Integer(compute='_compute_nb_albums', string='Albums à traiter')
    state = fields.Selection(
        [('confirm', 'Confirmation'), ('done', 'Terminé')],
        default='confirm',
    )
    import_report = fields.Html(string='Rapport', readonly=True)

    @api.depends('serie_id.album_ids')
    def _compute_nb_albums(self):
        for rec in self:
            rec.nb_albums = len(rec.serie_id.album_ids)

    def action_run(self):
        self.ensure_one()
        from ..aggregator import ComicDataAggregator

        aggregator = ComicDataAggregator(env=self.env)
        updated, skipped, errors = [], [], []

        for album in self.serie_id.album_ids.sorted('tome'):
            try:
                agg = None

                if album.isbn:
                    clean = _normalize_isbn(album.isbn)
                    agg = aggregator.search(isbn=clean or album.isbn)
                elif album.name:
                    results = aggregator.search_list(title=album.name)
                    if results:
                        best = self._best_match(results, album)
                        if best and best.isbn:
                            agg = aggregator.search(isbn=best.isbn)
                        elif best:
                            # Utilise les données du résultat titre directement
                            agg = _FakeAgg(best.to_dict())

                if not agg or not agg.data:
                    skipped.append(album)
                    continue

                self._apply_data(album, agg.data)
                updated.append(album)

            except Exception as e:
                _logger.error('Serie update error on "%s": %s', album.name, e)
                errors.append(album)

        self.import_report = self._build_report(updated, skipped, errors)
        self.state = 'done'
        return self._reopen()

    def _best_match(self, results, album):
        """Retourne le résultat le plus pertinent pour cet album (par numéro de tome)."""
        if album.tome:
            for r in results:
                if r.tome == album.tome:
                    return r
        return results[0] if results else None

    def _apply_data(self, album, data):
        """Met à jour un album avec les données de l'aggregator."""
        vals = {}

        if data.get('synopsis'):
            vals['synopsis'] = data['synopsis']
        if data.get('nb_pages'):
            vals['nb_pages'] = data['nb_pages']

        if data.get('isbn') and not album.isbn:
            vals['isbn'] = _normalize_isbn(data['isbn']) or data['isbn']

        if data.get('date_parution') and not album.date_parution:
            try:
                from datetime import date
                parts = str(data['date_parution'])[:10].split('-')
                vals['date_parution'] = date(int(parts[0]), int(parts[1]), int(parts[2]))
            except Exception:
                pass

        if data.get('date_depot_legal') and not album.date_depot_legal:
            try:
                from datetime import date
                parts = str(data['date_depot_legal'])[:10].split('-')
                vals['date_depot_legal'] = date(int(parts[0]), int(parts[1]), int(parts[2]))
            except Exception:
                pass

        # Couverture : télécharge la version HD (cover_url), ou miniature en fallback
        cover_url = data.get('cover_url') or data.get('cover_url_small')
        if cover_url:
            try:
                resp = requests.get(cover_url, timeout=10)
                if resp.status_code == 200 and len(resp.content) > 100:
                    vals['image_couverture'] = base64.b64encode(resp.content).decode()
            except Exception as e:
                _logger.warning('Cover download failed for "%s": %s', album.name, e)

        if vals:
            album.write(vals)

        # Auteurs : ajoute ceux qui manquent
        for auteur in data.get('auteurs', []):
            name = (auteur.get('name') or '').strip()
            if not name:
                continue
            partner = self.env['res.partner'].search([('name', 'ilike', name)], limit=1)
            if not partner:
                partner = self.env['res.partner'].create({'name': name})
            already = album.auteur_line_ids.filtered(lambda l: l.partner_id == partner)
            if not already:
                self.env['comic.album.auteur.line'].create({
                    'album_id': album.id,
                    'partner_id': partner.id,
                    'role': auteur.get('role', 'autre'),
                })

    def _build_report(self, updated, skipped, errors):
        lines = []
        if updated:
            lines.append(f'<b>✅ {len(updated)} mis à jour :</b><ul>')
            lines += [f'<li>{a.name}</li>' for a in updated]
            lines.append('</ul>')
        if skipped:
            lines.append(f'<b>⏭️ {len(skipped)} ignoré(s) (non trouvé ou déjà à jour) :</b><ul>')
            lines += [f'<li>{a.name}</li>' for a in skipped]
            lines.append('</ul>')
        if errors:
            lines.append(f'<b>❌ {len(errors)} erreur(s) :</b><ul>')
            lines += [f'<li>{a.name}</li>' for a in errors]
            lines.append('</ul>')
        return ''.join(lines) or '<p>Aucun album à traiter.</p>'

    def action_close_and_return(self):
        """Ferme le wizard et retourne à la fiche série."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'comic.serie',
            'res_id': self.serie_id.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def _reopen(self):
        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }


class _FakeAgg:
    """Wrapper minimal pour uniformiser le résultat d'une recherche titre."""
    def __init__(self, data):
        self.data = data
