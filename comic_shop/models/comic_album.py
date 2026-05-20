from odoo import models, fields, _
from odoo.exceptions import UserError
from odoo.tools import html2plaintext


class ComicAlbum(models.Model):
    _inherit = 'comic.album'

    product_tmpl_id = fields.Many2one(
        'product.template',
        string='Produit',
        ondelete='set null',
        copy=False,
        help="Produit Odoo associé à cet album pour la vente en ligne et en caisse.",
    )
    sync_product = fields.Boolean(
        string='Synchro auto',
        default=True,
        help="Si activé, les modifications de l'album (ISBN, ...) se répercutent "
             "automatiquement sur le produit lié.",
    )

    # --- Actions boutons ----------------------------------------------------

    def action_create_product(self):
        self.ensure_one()
        if self.product_tmpl_id:
            raise UserError(_("Cet album est déjà lié à un produit."))

        category = self.env.ref('comic_shop.product_category_bd', raise_if_not_found=False)
        product = self.env['product.template'].create({
            'name': self._get_product_name(),
            'type': 'consu',
            'comic_album_id': self.id,
            'categ_id': category.id if category else False,
        })
        self.product_tmpl_id = product
        self._sync_to_product()

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'product.template',
            'res_id': product.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_view_product(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'product.template',
            'res_id': self.product_tmpl_id.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_unlink_product(self):
        self.ensure_one()
        if self.product_tmpl_id:
            self.product_tmpl_id.comic_album_id = False
        self.product_tmpl_id = False

    def action_resync_product(self):
        """Force la resynchronisation album → produit, quel que soit sync_product."""
        self.ensure_one()
        if not self.product_tmpl_id:
            raise UserError(_("Aucun produit lié à cet album."))
        self._sync_to_product()

    # --- Synchro auto sur write ---------------------------------------------

    _SYNC_TRIGGER_FIELDS = {'isbn', 'image_couverture', 'name', 'tome', 'serie_id', 'synopsis'}

    def write(self, vals):
        res = super().write(vals)
        if self._SYNC_TRIGGER_FIELDS & set(vals):
            for album in self.filtered(lambda a: a.product_tmpl_id and a.sync_product):
                album._sync_to_product()
        return res

    # --- Helpers ------------------------------------------------------------

    def _sync_to_product(self):
        """Synchronise les champs de l'album vers le product.template lié."""
        self.ensure_one()
        if not self.product_tmpl_id:
            return
        self.product_tmpl_id.write({
            'name': self._get_product_name(),
            'image_1920': self.image_couverture or False,
            'barcode': self.isbn or False,
            'description_sale': html2plaintext(self.synopsis) if self.synopsis else False,
        })

    def _get_product_name(self):
        parts = []
        if self.serie_id:
            parts.append(self.serie_id.name)
        if self.name:
            parts.append(self.name)
        name = ' — '.join(parts) if parts else _('Album BD')
        if self.tome:
            name = f"{name} (T{self.tome})"
        return name
