from odoo import fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    auteur_work_line_ids = fields.One2many(
        "comic.work.auteur.line",
        "partner_id",
        string="Rôles BD",
    )
    is_comic_author = fields.Boolean(
        string="Auteur BD",
        default=False,
        index=True,
        help="Coché automatiquement dès que le contact est crédité sur un album, "
        "ou à la création depuis le menu Auteurs.",
    )
