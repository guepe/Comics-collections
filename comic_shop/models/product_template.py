from odoo import models, fields


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    comic_album_id = fields.Many2one(
        'comic.album',
        string='Album BD',
        ondelete='set null',
        copy=False,
        help="Album BD lié à ce produit. Géré via la fiche album.",
    )
