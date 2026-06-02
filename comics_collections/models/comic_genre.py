from odoo import fields, models


class ComicGenre(models.Model):
    _name = "comic.genre"
    _description = "Genre de bande dessinée"
    _order = "name"

    name = fields.Char(string="Nom", required=True)
    description = fields.Text()
    color = fields.Integer(string="Couleur")
