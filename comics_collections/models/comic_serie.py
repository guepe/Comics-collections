from odoo import api, fields, models


class ComicSerie(models.Model):
    _name = 'comic.serie'
    _description = 'Série de bandes dessinées'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name'

    name = fields.Char(string='Titre', required=True, tracking=True)
    type = fields.Selection([
        ('bd', 'Bande dessinée'),
        ('manga', 'Manga'),
        ('comics', 'Comics'),
        ('one_shot', 'One-shot'),
    ], string='Type', default='bd', tracking=True)
    statut = fields.Selection([
        ('en_cours', 'En cours'),
        ('terminee', 'Terminée'),
        ('abandonnee', 'Abandonnée'),
    ], string='Statut', default='en_cours', tracking=True)
    genre_id = fields.Many2one('comic.genre', string='Genre')
    editeur_id = fields.Many2one('comic.editeur', string='Éditeur')
    image_couverture = fields.Image(string='Couverture')
    synopsis = fields.Html(string='Synopsis')
    bdgest_id = fields.Integer(string='ID BDGest')
    bedetheque_url = fields.Char(string='URL Bedetheque')
    album_ids = fields.One2many('comic.album', 'serie_id', string='Albums')
    nb_albums_total = fields.Integer(
        string='Tomes au total', compute='_compute_albums', store=True)
    nb_albums_possedes = fields.Integer(
        string='Tomes possédés', compute='_compute_albums', store=True)
    a_suivre = fields.Boolean(string='À suivre', default=False, tracking=True)
    first_album_cover_id = fields.Many2one(
        'comic.album',
        compute='_compute_first_album_cover',
        store=True,
    )
    active = fields.Boolean(default=True)
    has_cover = fields.Boolean(compute='_compute_has_cover', store=True)

    @api.depends('image_couverture')
    def _compute_has_cover(self):
        for rec in self:
            rec.has_cover = bool(rec.image_couverture)

    @api.depends('album_ids.image_couverture', 'album_ids.tome')
    def _compute_first_album_cover(self):
        for serie in self:
            album = serie.album_ids.filtered('image_couverture').sorted('tome')
            serie.first_album_cover_id = album[0] if album else False

    @api.depends('album_ids', 'album_ids.dans_collection')
    def _compute_albums(self):
        for serie in self:
            serie.nb_albums_total = len(serie.album_ids)
            serie.nb_albums_possedes = len(serie.album_ids.filtered('dans_collection'))
