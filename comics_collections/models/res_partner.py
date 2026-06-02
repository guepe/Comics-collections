from odoo import fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    auteur_work_line_ids = fields.One2many(
        "comic.work.auteur.line",
        "partner_id",
        string="Rôles BD",
    )
