from odoo import api, fields, models

_PURCHASE_LINK_TEMPLATES = {
    'url_club_be': 'https://www.librairieclub.be/c/search?filter=search({isbn})&page=1&page_size=24&sort=RelevanceClub&sort_type=desc',
    'url_amazon_be': 'https://www.amazon.com.be/s?k={isbn}',
    'url_fnac_be': 'https://www.fnac.be/SearchResult/ResultList.aspx?Search={isbn}&sft=2',
}


class ComicEdition(models.Model):
    _name = 'comic.edition'
    _description = "Édition d'une œuvre BD"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'work_id, date_parution'

    work_id = fields.Many2one(
        'comic.work', string='Œuvre', required=True, ondelete='restrict', index=True, tracking=True)
    editeur_id = fields.Many2one('comic.editeur', string='Éditeur', tracking=True)
    date_parution = fields.Date(string='Date de parution', tracking=True)
    date_depot_legal = fields.Date(string='Dépôt légal')
    langue = fields.Selection([
        ('fr', 'Français'),
        ('nl', 'Néerlandais'),
        ('en', 'Anglais'),
        ('de', 'Allemand'),
        ('autre', 'Autre'),
    ], string='Langue', default='fr', tracking=True)
    format = fields.Selection([
        ('broche', 'Broché'),
        ('cartonne', 'Cartonné'),
        ('integrale', 'Intégrale'),
        ('collector', 'Collector'),
        ('numerique', 'Numérique'),
        ('autre', 'Autre'),
    ], string='Format', default='cartonne', tracking=True)
    image_couverture = fields.Image(string='Couverture')
    synopsis = fields.Html(string='Synopsis')
    nb_pages = fields.Integer(string='Nombre de pages')
    url_club_be = fields.Char(string='Lien Club.be')
    url_amazon_be = fields.Char(string='Lien Amazon.be')
    url_fnac_be = fields.Char(string='Lien FNAC.be')
    isbn_ids = fields.One2many('comic.isbn', 'edition_id', string='ISBNs')
    active = fields.Boolean(default=True)

    nb_isbn = fields.Integer(string='Nb ISBN', compute='_compute_nb_isbn', store=True)

    @api.depends('isbn_ids')
    def _compute_nb_isbn(self):
        for rec in self:
            rec.nb_isbn = len(rec.isbn_ids)

    def _compute_display_name(self):
        langue_labels = dict(self._fields['langue'].selection)
        for rec in self:
            work_name = rec.work_id.display_name if rec.work_id else '?'
            parts = []
            if rec.langue:
                parts.append(langue_labels.get(rec.langue, rec.langue))
            if rec.editeur_id:
                parts.append(rec.editeur_id.name)
            if rec.date_parution:
                parts.append(str(rec.date_parution.year))
            suffix = f" ({' — '.join(parts)})" if parts else ''
            rec.display_name = f'{work_name}{suffix}'

    @staticmethod
    def _build_purchase_links(isbn):
        if not isbn:
            return {}
        return {field: tpl.format(isbn=isbn) for field, tpl in _PURCHASE_LINK_TEMPLATES.items()}

    def _get_primary_isbn(self):
        self.ensure_one()
        return self.isbn_ids[:1].isbn_13 if self.isbn_ids else False

    def action_generate_purchase_links(self):
        for edition in self:
            isbn = edition._get_primary_isbn()
            links = self._build_purchase_links(isbn)
            if links:
                edition.write(links)

    @api.model
    def _cron_fill_missing_purchase_links(self):
        link_fields = list(_PURCHASE_LINK_TEMPLATES)
        missing_domain = ['|', '|',
            ('url_club_be', 'in', [False, '']),
            ('url_amazon_be', 'in', [False, '']),
            ('url_fnac_be', 'in', [False, '']),
        ]
        for edition in self.search(missing_domain):
            isbn = edition._get_primary_isbn()
            if not isbn:
                continue
            links = self._build_purchase_links(isbn)
            to_write = {f: u for f, u in links.items() if not getattr(edition, f)}
            if to_write:
                edition.write(to_write)
