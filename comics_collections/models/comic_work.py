import re
import unicodedata

from odoo import api, fields, models


def _normalize_title(title):
    """Normalize a comic title for deduplication (strips articles, accents, punctuation)."""
    if not title:
        return ''
    nfd = unicodedata.normalize('NFD', title)
    no_accents = ''.join(c for c in nfd if unicodedata.category(c) != 'Mn')
    s = no_accents.lower().strip()
    for article in ("l'", 'les ', 'le ', 'la ', 'de ', 'het ', 'een ', 'the ', 'an ', 'a '):
        if s.startswith(article):
            s = s[len(article):]
            break
    s = re.sub(r'\s*\((les|de|the|het|een|an|a)\)\s*$', '', s)
    s = re.sub(r"[,.\-'\"!?;:]", ' ', s)
    return ' '.join(s.split())


class ComicWork(models.Model):
    _name = 'comic.work'
    _description = "Œuvre BD (titre canonique)"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'titre_canonique'
    _order = 'serie_id, tome'

    serie_id = fields.Many2one(
        'comic.serie', string='Série', ondelete='restrict', index=True, tracking=True)
    titre_canonique = fields.Char(string='Titre canonique', required=True, tracking=True)
    tome = fields.Integer(string='Tome', tracking=True)
    slug = fields.Char(string='Slug URL', index=True, copy=False)
    titre_normalise = fields.Char(
        string='Titre normalisé',
        compute='_compute_titre_normalise',
        store=True,
        index=True,
    )

    # Références externes
    wikidata_id = fields.Char(string='Wikidata ID')
    openlibrary_id = fields.Char(string='Open Library ID')
    bedetheque_id = fields.Char(string='Bedetheque ID')
    comicvine_id = fields.Char(string='Comicvine ID')

    auteur_line_ids = fields.One2many('comic.work.auteur.line', 'work_id', string='Auteurs')
    edition_ids = fields.One2many('comic.edition', 'work_id', string='Éditions')
    active = fields.Boolean(default=True)

    _unique_serie_tome = models.Constraint(
        'UNIQUE(serie_id, tome)',
        "Un tome de cette série existe déjà. Chaque numéro de tome doit être unique par série.",
    )

    @api.depends('titre_canonique')
    def _compute_titre_normalise(self):
        for rec in self:
            rec.titre_normalise = _normalize_title(rec.titre_canonique)

    def _compute_display_name(self):
        for rec in self:
            serie = rec.serie_id.name if rec.serie_id else ''
            tome = f' T{rec.tome:02d}' if rec.tome else ''
            sep = ' — ' if (serie or tome) and rec.titre_canonique else ''
            rec.display_name = f'{serie}{tome}{sep}{rec.titre_canonique}'

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('slug'):
                vals['slug'] = self._generate_slug(vals)
        return super().create(vals_list)

    def _generate_slug(self, vals):
        serie_slug = ''
        if vals.get('serie_id'):
            serie = self.env['comic.serie'].browse(vals['serie_id'])
            serie_slug = re.sub(r'[^a-z0-9]+', '-', serie.name.lower()).strip('-')
        tome = vals.get('tome', 0)
        base = f'{serie_slug}-t{tome:02d}' if serie_slug else f't{tome:02d}'
        slug = base
        n = 1
        while self.search_count([('slug', '=', slug)]):
            slug = f'{base}-{n}'
            n += 1
        return slug


class ComicWorkAuteurLine(models.Model):
    _name = 'comic.work.auteur.line'
    _description = "Auteur d'une œuvre BD"

    work_id = fields.Many2one(
        'comic.work', string='Œuvre', required=True, ondelete='cascade', index=True)
    partner_id = fields.Many2one('res.partner', string='Auteur', required=True)
    role = fields.Selection([
        ('scenariste', 'Scénariste'),
        ('dessinateur', 'Dessinateur'),
        ('coloriste', 'Coloriste'),
        ('encreur', 'Encreur'),
        ('traducteur', 'Traducteur'),
        ('autre', 'Autre'),
    ], string='Rôle', required=True, default='dessinateur')
