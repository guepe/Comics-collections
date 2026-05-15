from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


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
    url_club_be = fields.Char(string='Lien Club.be')
    url_amazon_be = fields.Char(string='Lien Amazon.be')
    bdgest_album_id = fields.Integer(string='ID BDGest')
    auteur_line_ids = fields.One2many('comic.album.auteur.line', 'album_id', string='Auteurs')
    active = fields.Boolean(default=True)

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
