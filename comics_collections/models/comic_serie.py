from odoo import api, fields, models

from ..utils.normalize import normalize_title


class ComicSerie(models.Model):
    _name = 'comic.serie'
    _description = 'Série de bandes dessinées'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name'

    name = fields.Char(string='Titre', required=True, tracking=True)
    name_normalise = fields.Char(
        string='Titre normalisé',
        compute='_compute_name_normalise',
        store=True,
        index=True,
    )
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
    work_ids = fields.One2many('comic.work', 'serie_id', string='Œuvres')
    nb_works_total = fields.Integer(
        string='Tomes au total', compute='_compute_works', store=True)
    a_suivre = fields.Boolean(string='À suivre', default=False, tracking=True)
    first_edition_cover_id = fields.Many2one(
        'comic.edition',
        compute='_compute_first_edition_cover',
        store=True,
    )
    active = fields.Boolean(default=True)
    has_cover = fields.Boolean(compute='_compute_has_cover', store=True)

    @api.depends('name')
    def _compute_name_normalise(self):
        for rec in self:
            rec.name_normalise = normalize_title(rec.name)

    @api.depends('image_couverture')
    def _compute_has_cover(self):
        for rec in self:
            rec.has_cover = bool(rec.image_couverture)

    @api.depends('work_ids.edition_ids.image_couverture', 'work_ids.tome')
    def _compute_first_edition_cover(self):
        for serie in self:
            edition = False
            for work in serie.work_ids.sorted('tome'):
                ed = work.edition_ids.filtered('image_couverture')
                if ed:
                    edition = ed[0]
                    break
            serie.first_edition_cover_id = edition

    @api.depends('work_ids')
    def _compute_works(self):
        for serie in self:
            serie.nb_works_total = len(serie.work_ids)

    def action_view_works(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': f'Œuvres — {self.name}',
            'res_model': 'comic.work',
            'view_mode': 'list,form',
            'domain': [('serie_id', '=', self.id)],
            'context': {'default_serie_id': self.id},
        }
