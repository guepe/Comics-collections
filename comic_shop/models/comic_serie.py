from odoo import _, api, fields, models


class ComicSerie(models.Model):
    _inherit = 'comic.serie'

    nb_albums_with_product = fields.Integer(
        string='Produits liés',
        compute='_compute_nb_albums_with_product',
        store=True,
    )
    nb_albums_isbn_sans_produit = fields.Integer(
        string='Éditions à publier',
        compute='_compute_nb_albums_with_product',
        store=True,
    )

    @api.depends('work_ids.edition_ids.product_tmpl_id', 'work_ids.edition_ids.isbn_ids')
    def _compute_nb_albums_with_product(self):
        for serie in self:
            all_editions = serie.work_ids.edition_ids
            serie.nb_albums_with_product = len(all_editions.filtered('product_tmpl_id'))
            serie.nb_albums_isbn_sans_produit = len(
                all_editions.filtered(lambda e: e.isbn_ids and not e.product_tmpl_id)
            )

    def action_create_products_bulk(self):
        """Crée un produit pour chaque édition sans produit, sur plusieurs séries."""
        editions = self.mapped('work_ids.edition_ids').filtered(lambda e: not e.product_tmpl_id)
        category = self.env.ref('comic_shop.product_category_bd', raise_if_not_found=False)
        for edition in editions:
            product = self.env['product.template'].create({
                'name': edition._get_product_name(),
                'type': 'consu',
                'comic_edition_id': edition.id,
                'categ_id': category.id if category else False,
            })
            edition.product_tmpl_id = product
            edition._sync_to_product()
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _("Produits créés"),
                'message': _("%d produit(s) créé(s) sur %d série(s).") % (len(editions), len(self)),
                'type': 'success' if editions else 'warning',
                'sticky': False,
            },
        }

    def action_create_products_from_isbn(self):
        """Creates a product for each edition with an ISBN but no linked product."""
        self.ensure_one()
        editions = self.work_ids.edition_ids.filtered(lambda e: e.isbn_ids and not e.product_tmpl_id)
        if not editions:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _("Rien à faire"),
                    'message': _("Toutes les éditions avec ISBN ont déjà un produit lié."),
                    'type': 'warning',
                    'sticky': False,
                },
            }

        category = self.env.ref('comic_shop.product_category_bd', raise_if_not_found=False)
        for edition in editions:
            product = self.env['product.template'].create({
                'name': edition._get_product_name(),
                'type': 'consu',
                'comic_edition_id': edition.id,
                'categ_id': category.id if category else False,
            })
            edition.product_tmpl_id = product
            edition._sync_to_product()

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _("Produits créés"),
                'message': _("%d produit(s) créé(s) pour « %s ».") % (len(editions), self.name),
                'type': 'success',
                'sticky': False,
            },
        }

    def action_view_products(self):
        """Opens the list of products linked to editions of this series."""
        self.ensure_one()
        product_ids = self.work_ids.edition_ids.filtered('product_tmpl_id').mapped('product_tmpl_id').ids
        return {
            'type': 'ir.actions.act_window',
            'name': _("Produits — %s") % self.name,
            'res_model': 'product.template',
            'view_mode': 'list,form',
            'domain': [('id', 'in', product_ids)],
        }
