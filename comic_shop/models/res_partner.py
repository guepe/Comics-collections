from odoo import models, fields


class ResPartner(models.Model):
    _inherit = 'res.partner'

    comic_auto_library = fields.Boolean(
        string='Ajout automatique à la bibliothèque',
        default=True,
        help="Si activé, les BD achetées dans le shop sont automatiquement ajoutées à la bibliothèque.",
    )
