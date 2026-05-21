from odoo import _, models, fields
from odoo.exceptions import UserError


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    comic_edition_id = fields.Many2one(
        'comic.edition',
        string='Édition BD',
        ondelete='set null',
        copy=False,
        help="Édition BD liée à ce produit. Gérée via la fiche édition.",
    )

    def action_view_comic_edition(self):
        self.ensure_one()
        if not self.comic_edition_id:
            raise UserError(_("Aucune édition BD liée à ce produit."))
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'comic.edition',
            'res_id': self.comic_edition_id.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_sync_from_edition(self):
        self.ensure_one()
        if not self.comic_edition_id:
            raise UserError(_("Aucune édition BD liée à ce produit."))
        self.comic_edition_id._sync_to_product()
