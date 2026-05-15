from odoo import _, models


class ComicSerie(models.Model):
    _inherit = 'comic.serie'

    def action_update_albums_from_datasource(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Mise à jour depuis les sources de données'),
            'res_model': 'comic.serie.update.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_serie_id': self.id},
        }
