from odoo import fields, models


class ComicEditeur(models.Model):
    _name = "comic.editeur"
    _description = "Éditeur de bandes dessinées"
    _order = "name"

    name = fields.Char(string="Nom", required=True)
    partner_id = fields.Many2one("res.partner", string="Contact")
    pays_id = fields.Many2one("res.country", string="Pays")
    site_web = fields.Char(string="Site web")
    bdgest_editeur_id = fields.Integer(string="ID BDGest")
