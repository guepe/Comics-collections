from odoo import fields, models


class ComicGenre(models.Model):
    _name = "comic.genre"
    _description = "Comic genre"
    _order = "name"

    name = fields.Char(required=True, translate=True)
    description = fields.Text()
    color = fields.Integer()
