from odoo import models, fields, api
import datetime


class ComicCustomerAlbum(models.Model):
    _name = 'comic.customer.album'
    _description = 'Bibliothèque client — album'
    _order = 'partner_id, album_id'
    _rec_name = 'album_id'

    partner_id = fields.Many2one(
        'res.partner',
        string='Client',
        required=True,
        ondelete='cascade',
        index=True,
    )
    album_id = fields.Many2one(
        'comic.album',
        string='Album',
        required=True,
        ondelete='restrict',
        index=True,
    )
    source = fields.Selection([
        ('achete_ici', 'Acheté ici'),
        ('achete_ailleurs', 'Acheté ailleurs'),
        ('cadeau', 'Cadeau'),
        ('inconnu', 'Inconnu'),
    ], string='Source', default='inconnu')
    etat_lecture = fields.Selection([
        ('non_lu', 'Non lu'),
        ('en_cours', 'En cours'),
        ('lu', 'Lu'),
    ], string='État de lecture', default='non_lu')
    dans_collection = fields.Boolean(string='Dans la collection', default=True)
    dans_wishlist = fields.Boolean(string='En wishlist', default=False)
    note = fields.Float(string='Note', digits=(2, 1))
    commentaire = fields.Text(string='Commentaire')
    date_ajout = fields.Date(
        string='Date d\'ajout',
        default=lambda self: datetime.date.today(),
    )
    sale_order_line_id = fields.Many2one(
        'sale.order.line',
        string='Ligne de commande',
        ondelete='set null',
        copy=False,
        help="Ligne de commande à l'origine de l'ajout automatique.",
    )

    # Champ calculé
    has_product = fields.Boolean(
        string='Produit disponible',
        compute='_compute_has_product',
        help="True si l'album est lié à un produit vendable dans le shop.",
    )

    _sql_constraints = [
        ('unique_partner_album', 'UNIQUE(partner_id, album_id)',
         "Ce client possède déjà une entrée pour cet album dans sa bibliothèque."),
    ]

    @api.depends('album_id.product_tmpl_id')
    def _compute_has_product(self):
        for rec in self:
            rec.has_product = bool(rec.album_id.product_tmpl_id)
