from odoo import models


class ComicAlbum(models.Model):
    _inherit = 'comic.album'

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
