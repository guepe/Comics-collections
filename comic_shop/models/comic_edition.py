from odoo import models, fields, _
from odoo.exceptions import UserError
from odoo.tools import html2plaintext


class ComicEdition(models.Model):
    _inherit = 'comic.edition'

    product_tmpl_id = fields.Many2one(
        'product.template',
        string='Produit',
        ondelete='set null',
        copy=False,
        help="Produit Odoo associé à cette édition pour la vente en ligne et en caisse.",
    )
    sync_product = fields.Boolean(
        string='Synchro auto',
        default=True,
        help="Si activé, les modifications de l'édition (couverture, synopsis, ...) se répercutent "
             "automatiquement sur le produit lié.",
    )

    # --- Actions boutons ----------------------------------------------------

    def action_create_product(self):
        self.ensure_one()
        if self.product_tmpl_id:
            raise UserError(_("Cette édition est déjà liée à un produit."))

        category = self.env.ref('comic_shop.product_category_bd', raise_if_not_found=False)
        product = self.env['product.template'].create({
            'name': self._get_product_name(),
            'type': 'consu',
            'comic_edition_id': self.id,
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
            self.product_tmpl_id.comic_edition_id = False
        self.product_tmpl_id = False

    def action_resync_product(self):
        self.ensure_one()
        if not self.product_tmpl_id:
            raise UserError(_("Aucun produit lié à cette édition."))
        self._sync_to_product()

    # --- Auto-sync on write -------------------------------------------------

    _SYNC_TRIGGER_FIELDS = {'image_couverture', 'synopsis', 'editeur_id', 'isbn_ids', 'work_id'}

    def write(self, vals):
        res = super().write(vals)
        if self._SYNC_TRIGGER_FIELDS & set(vals):
            for edition in self.filtered(lambda e: e.product_tmpl_id and e.sync_product):
                edition._sync_to_product()
        return res

    # --- Helpers ------------------------------------------------------------

    def _sync_to_product(self):
        self.ensure_one()
        if not self.product_tmpl_id:
            return
        self.product_tmpl_id.write({
            'name': self._get_product_name(),
            'image_1920': self.image_couverture or False,
            'barcode': self._get_primary_isbn() or False,
            'description_sale': html2plaintext(self.synopsis) if self.synopsis else False,
        })

    def _get_product_name(self):
        work = self.work_id
        parts = []
        if work.serie_id:
            parts.append(work.serie_id.name)
        if work.titre_canonique:
            parts.append(work.titre_canonique)
        name = ' — '.join(parts) if parts else _('Édition BD')
        if work.tome:
            name = f"{name} (T{work.tome})"
        return name
