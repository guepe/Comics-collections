from odoo import fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    auteur_album_line_ids = fields.One2many(
        'comic.album.auteur.line', 'partner_id',
        string='Rôles BD',
    )
