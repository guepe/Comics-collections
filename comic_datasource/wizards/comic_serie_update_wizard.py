import logging
import re

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

                album._apply_datasource_data(agg.data)
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
