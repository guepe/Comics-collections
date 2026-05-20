from odoo import _, api, fields, models


class ComicSerie(models.Model):
    _inherit = 'comic.serie'

    nb_albums_with_product = fields.Integer(
        string='Produits liés',
        compute='_compute_nb_albums_with_product',
        store=True,
    )
    nb_albums_isbn_sans_produit = fields.Integer(
        string='Albums à publier',
        compute='_compute_nb_albums_with_product',
        store=True,
    )

    @api.depends('album_ids.product_tmpl_id', 'album_ids.isbn')
    def _compute_nb_albums_with_product(self):
        for serie in self:
            serie.nb_albums_with_product = len(
                serie.album_ids.filtered('product_tmpl_id')
            )
            serie.nb_albums_isbn_sans_produit = len(
                serie.album_ids.filtered(lambda a: a.isbn and not a.product_tmpl_id)
            )

    def action_create_products_from_isbn(self):
        """Crée un produit pour chaque album de la série qui a un ISBN mais pas encore de produit."""
        self.ensure_one()
        albums = self.album_ids.filtered(lambda a: a.isbn and not a.product_tmpl_id)
        if not albums:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _("Rien à faire"),
                    'message': _("Tous les albums avec ISBN ont déjà un produit lié."),
                    'type': 'warning',
                    'sticky': False,
                },
            }

        category = self.env.ref('comic_shop.product_category_bd', raise_if_not_found=False)
        for album in albums:
            product = self.env['product.template'].create({
                'name': album._get_product_name(),
                'type': 'consu',
                'comic_album_id': album.id,
                'categ_id': category.id if category else False,
            })
            album.product_tmpl_id = product
            album._sync_to_product()

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _("Produits créés"),
                'message': _("%d produit(s) créé(s) pour « %s ».") % (len(albums), self.name),
                'type': 'success',
                'sticky': False,
            },
        }

    def action_view_products(self):
        """Ouvre la liste des produits liés aux albums de cette série."""
        self.ensure_one()
        product_ids = self.album_ids.filtered('product_tmpl_id').mapped('product_tmpl_id').ids
        return {
            'type': 'ir.actions.act_window',
            'name': _("Produits — %s") % self.name,
            'res_model': 'product.template',
            'view_mode': 'list,form',
            'domain': [('id', 'in', product_ids)],
        }
