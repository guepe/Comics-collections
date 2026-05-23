from odoo import _, fields, models
from odoo.exceptions import UserError


class ComicWorkMergeWizard(models.TransientModel):
    _name = 'comic.work.merge.wizard'
    _description = 'Fusion de deux albums BD'

    source_work_id = fields.Many2one(
        'comic.work', required=True, string='Album source (sera archivé)',
        domain=[('active', '=', True)],
    )
    target_work_id = fields.Many2one(
        'comic.work', required=True, string='Album cible (sera conservé)',
        domain=[('active', '=', True)],
    )
    pair_id = fields.Many2one('comic.dedup.pair', string='Paire de doublons')

    nb_editions_source = fields.Integer(
        related='source_work_id.nb_editions', string='Éditions à transférer')
    nb_auteurs_source = fields.Integer(
        related='source_work_id.nb_auteurs', string='Auteurs à transférer')

    def action_confirm_merge(self):
        self.ensure_one()
        if self.source_work_id == self.target_work_id:
            raise UserError(_("Source et cible doivent être deux albums différents."))

        self.source_work_id._merge_into(self.target_work_id)

        if self.pair_id:
            self.pair_id.unlink()

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'comic.work',
            'res_id': self.target_work_id.id,
            'view_mode': 'form',
            'target': 'current',
        }
