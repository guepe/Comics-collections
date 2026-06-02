from odoo import fields, models


class ComicPret(models.Model):
    _name = "comic.pret"
    _description = "Prêt d'un album BD"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "date_pret desc"

    edition_id = fields.Many2one("comic.edition", string="Édition", required=True, ondelete="restrict", tracking=True)
    partner_id = fields.Many2one("res.partner", string="Prêté à", required=True, tracking=True)
    date_pret = fields.Date(string="Date de prêt", tracking=True)
    date_retour_prevue = fields.Date(string="Date retour prévue")
    date_retour_effective = fields.Date(string="Date retour réelle")
    retourne = fields.Boolean(string="Retourné", tracking=True)
    notes = fields.Text()
