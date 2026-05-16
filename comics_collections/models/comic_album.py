from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

# URL templates pour les liens d'achat (paramètre : ISBN EAN-13)
_PURCHASE_LINK_TEMPLATES = {
    'url_club_be': 'https://www.librairieclub.be/c/search?filter=search({isbn})&page=1&page_size=24&sort=RelevanceClub&sort_type=desc',
    'url_amazon_be': 'https://www.amazon.com.be/s?k={isbn}',
    'url_fnac_be': 'https://www.fnac.be/SearchResult/ResultList.aspx?Search={isbn}&sft=2',
}


class ComicAlbum(models.Model):
    _name = 'comic.album'
    _description = 'Album de bandes dessinées'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'serie_id, tome, name'

    name = fields.Char(string='Titre', required=True, tracking=True)
    serie_id = fields.Many2one('comic.serie', string='Série', tracking=True, ondelete='restrict')
    tome = fields.Integer(string='Tome')
    isbn = fields.Char(string='ISBN')
    date_depot_legal = fields.Date(string='Dépôt légal')
    date_parution = fields.Date(string='Date de parution')
    nb_pages = fields.Integer(string='Nombre de pages')
    image_couverture = fields.Image(string='Couverture')
    synopsis = fields.Html(string='Synopsis')
    note = fields.Float(string='Note', digits=(2, 1))
    etat_lecture = fields.Selection([
        ('non_lu', 'Non lu'),
        ('en_cours', 'En cours'),
        ('lu', 'Lu'),
    ], string='État de lecture', default='non_lu', tracking=True)
    dans_collection = fields.Boolean(string='Dans ma collection', tracking=True)
    dans_wishlist = fields.Boolean(string='Wishlist')
    has_cover = fields.Boolean(compute='_compute_has_cover', store=True)
    url_club_be = fields.Char(string='Lien Club.be')
    url_amazon_be = fields.Char(string='Lien Amazon.be')
    url_fnac_be = fields.Char(string='Lien FNAC.be')
    bdgest_album_id = fields.Integer(string='ID BDGest')
    auteur_line_ids = fields.One2many('comic.album.auteur.line', 'album_id', string='Auteurs')
    active = fields.Boolean(default=True)

    @api.depends('image_couverture')
    def _compute_has_cover(self):
        for rec in self:
            rec.has_cover = bool(rec.image_couverture)

    # ── Validation ISBN ────────────────────────────────────────────────────────

    @api.constrains('isbn')
    def _check_isbn(self):
        for album in self:
            if album.isbn and not self._validate_ean13(album.isbn):
                raise ValidationError(
                    _('L\'ISBN "%s" n\'est pas un EAN-13 valide.') % album.isbn
                )

    @staticmethod
    def _validate_ean13(isbn):
        isbn = isbn.replace('-', '').replace(' ', '')
        if len(isbn) != 13 or not isbn.isdigit():
            return False
        total = sum(int(d) * (1 if i % 2 == 0 else 3) for i, d in enumerate(isbn[:12]))
        check = (10 - total % 10) % 10
        return check == int(isbn[12])

    # ── Liens d'achat automatiques ─────────────────────────────────────────────

    @staticmethod
    def _build_purchase_links(isbn):
        """Retourne un dict {field: url} pour un ISBN donné."""
        if not isbn:
            return {}
        return {field: tpl.format(isbn=isbn) for field, tpl in _PURCHASE_LINK_TEMPLATES.items()}

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('isbn'):
                for field, url in self._build_purchase_links(vals['isbn']).items():
                    vals.setdefault(field, url)
        return super().create(vals_list)

    @api.onchange('isbn')
    def _onchange_isbn_purchase_links(self):
        if self.isbn:
            for field, url in self._build_purchase_links(self.isbn).items():
                if not getattr(self, field):
                    setattr(self, field, url)

    def action_generate_purchase_links(self):
        """Régénère les liens d'achat depuis l'ISBN (écrase les valeurs existantes)."""
        for album in self:
            links = self._build_purchase_links(album.isbn)
            if links:
                album.write(links)

    def action_toggle_collection(self):
        self.ensure_one()
        self.dans_collection = not self.dans_collection

    def action_toggle_wishlist(self):
        self.ensure_one()
        self.dans_wishlist = not self.dans_wishlist

    def action_mark_acquired(self):
        """Marque l'album comme acquis : l'ajoute à la collection et le retire de la wishlist."""
        self.write({'dans_collection': True, 'dans_wishlist': False})

    def action_cycle_etat_lecture(self):
        self.ensure_one()
        cycle = {'non_lu': 'en_cours', 'en_cours': 'lu', 'lu': 'non_lu'}
        self.etat_lecture = cycle.get(self.etat_lecture, 'non_lu')
