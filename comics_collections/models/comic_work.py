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

    nb_editions = fields.Integer(
        string='Nb éditions', compute='_compute_nb_editions', store=True)
    nb_auteurs = fields.Integer(
        string='Nb auteurs', compute='_compute_nb_auteurs', store=True)

    _unique_serie_tome = models.Constraint(
        'UNIQUE(serie_id, tome)',
        "Un tome de cette série existe déjà. Chaque numéro de tome doit être unique par série.",
    )

    # ── Édition principale — façade "album tout-en-un" ───────────────────────

    primary_edition_id = fields.Many2one(
        'comic.edition',
        string='Édition principale',
        compute='_compute_primary_edition_id',
        store=True,
        index=True,
    )

    # Champs délégués à l'édition principale (écriture transparente)
    image_couverture = fields.Image(
        string='Couverture',
        related='primary_edition_id.image_couverture',
        readonly=False,
    )
    editeur_id = fields.Many2one(
        'comic.editeur',
        string='Éditeur',
        related='primary_edition_id.editeur_id',
        readonly=False,
    )
    langue = fields.Selection(
        related='primary_edition_id.langue',
        string='Langue',
        readonly=False,
    )
    format = fields.Selection(
        related='primary_edition_id.format',
        string='Format',
        readonly=False,
    )
    nb_pages = fields.Integer(
        string='Nombre de pages',
        related='primary_edition_id.nb_pages',
        readonly=False,
    )
    date_parution = fields.Date(
        string='Date de parution',
        related='primary_edition_id.date_parution',
        readonly=False,
    )
    synopsis = fields.Html(
        string='Synopsis',
        related='primary_edition_id.synopsis',
        readonly=False,
    )
    isbn_ids = fields.One2many(
        related='primary_edition_id.isbn_ids',
        string='ISBNs',
        readonly=False,
    )
    url_club_be = fields.Char(
        related='primary_edition_id.url_club_be',
        string='Lien Club.be',
        readonly=False,
    )
    url_amazon_be = fields.Char(
        related='primary_edition_id.url_amazon_be',
        string='Lien Amazon.be',
        readonly=False,
    )
    url_fnac_be = fields.Char(
        related='primary_edition_id.url_fnac_be',
        string='Lien FNAC.be',
        readonly=False,
    )

    # ── Computes ─────────────────────────────────────────────────────────────

    @api.depends('edition_ids')
    def _compute_primary_edition_id(self):
        for rec in self:
            rec.primary_edition_id = rec.edition_ids[:1] if rec.edition_ids else False

    @api.depends('edition_ids')
    def _compute_nb_editions(self):
        for rec in self:
            rec.nb_editions = len(rec.edition_ids)

    @api.depends('auteur_line_ids')
    def _compute_nb_auteurs(self):
        for rec in self:
            rec.nb_auteurs = len(rec.auteur_line_ids)

    @api.depends('titre_canonique')
    def _compute_titre_normalise(self):
        for rec in self:
            rec.titre_normalise = _normalize_title(rec.titre_canonique)

    def _compute_display_name(self):
        for rec in self:
            serie = rec.serie_id.name if rec.serie_id else ''
            tome = f' T{rec.tome:02d}' if rec.tome else ''
            sep = ' — ' if (serie or tome) and rec.titre_canonique else ''
            rec.display_name = f'{serie}{tome}{sep}{rec.titre_canonique}'.strip()

    # ── Création + édition par défaut ────────────────────────────────────────

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('slug'):
                vals['slug'] = self._generate_slug(vals)
        records = super().create(vals_list)
        for record in records:
            if not record.edition_ids:
                self.env['comic.edition'].create({
                    'work_id': record.id,
                    'langue': 'fr',
                    'format': 'cartonne',
                })
        return records

    # ── Actions ───────────────────────────────────────────────────────────────

    def action_view_editions(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': f'Éditions — {self.display_name}',
            'res_model': 'comic.edition',
            'view_mode': 'list,form',
            'domain': [('work_id', '=', self.id)],
            'context': {'default_work_id': self.id},
        }

    def action_generate_purchase_links(self):
        self.ensure_one()
        if self.primary_edition_id:
            self.primary_edition_id.action_generate_purchase_links()

    # ── Slug ──────────────────────────────────────────────────────────────────

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
