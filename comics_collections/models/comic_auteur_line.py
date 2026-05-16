from odoo import fields, models


class ComicAlbumAuteurLine(models.Model):
    _name = 'comic.album.auteur.line'
    _description = "Auteur d'un album"

    album_id = fields.Many2one('comic.album', string='Album', required=True, ondelete='cascade')
    partner_id = fields.Many2one('res.partner', string='Auteur', required=True)
    role = fields.Selection([
        ('scenariste', 'Scénariste'),
        ('dessinateur', 'Dessinateur'),
        ('coloriste', 'Coloriste'),
        ('encreur', 'Encreur'),
        ('traducteur', 'Traducteur'),
        ('autre', 'Autre'),
    ], string='Rôle', required=True, default='dessinateur')
