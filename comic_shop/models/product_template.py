from odoo import _, models, fields
from odoo.exceptions import UserError


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    comic_album_id = fields.Many2one(
        'comic.album',
        string='Album BD',
        ondelete='set null',
        copy=False,
        help="Album BD lié à ce produit. Géré via la fiche album.",
    )

    def action_view_comic_album(self):
        self.ensure_one()
        if not self.comic_album_id:
            raise UserError(_("Aucun album BD lié à ce produit."))
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'comic.album',
            'res_id': self.comic_album_id.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_sync_from_album(self):
        self.ensure_one()
        if not self.comic_album_id:
            raise UserError(_("Aucun album BD lié à ce produit."))
        self.comic_album_id._sync_to_product()
