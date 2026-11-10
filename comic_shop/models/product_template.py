from odoo import _, api, models, fields
from odoo.exceptions import UserError


class ProductTemplate(models.Model):
    _inherit = "product.template"

    comic_edition_id = fields.Many2one(
        "comic.edition",
        string="Édition BD",
        ondelete="set null",
        copy=False,
        help="Édition BD liée à ce produit. Gérée via la fiche édition.",
    )
    comic_work_id = fields.Many2one(
        "comic.work",
        string="Titre BD",
        compute="_compute_comic_work_id",
        store=True,
    )

    @api.depends("comic_edition_id.work_id")
    def _compute_comic_work_id(self):
        for rec in self:
            rec.comic_work_id = rec.comic_edition_id.work_id if rec.comic_edition_id else False

    def action_view_comic_edition(self):
        self.ensure_one()
        if not self.comic_edition_id:
            raise UserError(_("Aucune édition BD liée à ce produit."))
        return {
            "type": "ir.actions.act_window",
            "res_model": "comic.edition",
            "res_id": self.comic_edition_id.id,
            "view_mode": "form",
            "target": "current",
        }

    def action_sync_from_edition(self):
        self.ensure_one()
        if not self.comic_edition_id:
            raise UserError(_("Aucune édition BD liée à ce produit."))
        self.comic_edition_id._sync_to_product()

    def _get_comic_edition(self):
        """Edition linked to this product — both link directions are checked
        (product.comic_edition_id and comic.edition.product_tmpl_id)."""
        self.ensure_one()
        return self.comic_edition_id or self.env["comic.edition"].sudo().search(
            [("product_tmpl_id", "=", self.id)], limit=1
        )

    # ── Relier produits et éditions (après réinstallation de comic_shop) ─────

    @api.model
    def _comic_relink_editions(self):
        """Recrée les liens produit ↔ édition perdus (désinstallation de comic_shop).

        Seuls les produits et éditions encore sans lien sont considérés. Correspondance,
        par ordre de fiabilité :
        1. code-barres du produit = ISBN-13 (ou ISBN-10, converti) d'une édition ;
        2. nom du produit (dans n'importe quelle langue) = nom généré pour l'édition
           (``_get_product_name``), seulement si ce nom désigne une seule édition.
        Une édition n'est jamais reliée à deux produits. Retourne le nombre de liens créés.
        """
        Isbn = self.env["comic.isbn"].sudo()
        Edition = self.env["comic.edition"].sudo()
        products = self.sudo().with_context(active_test=False).search([("comic_edition_id", "=", False)])
        free_editions = Edition.search([("product_tmpl_id", "=", False)])
        taken = set()
        links = []

        def _isbn_edition(barcode):
            code = (barcode or "").replace("-", "").replace(" ", "").upper()
            if len(code) == 10:
                code = Isbn._isbn10_to_isbn13(code) or code
            if not code:
                return Edition
            isbn = Isbn.search(["|", ("isbn_13", "=", code), ("isbn_10", "=", code)], limit=1)
            return isbn.edition_id

        by_name = {}
        for edition in free_editions:
            by_name.setdefault(edition._get_product_name().strip().casefold(), []).append(edition)

        for product in products:
            edition = Edition
            for barcode in product.product_variant_ids.mapped("barcode") + [product.barcode]:
                edition = _isbn_edition(barcode)
                if edition:
                    break
            if not edition:
                names = {
                    (product.with_context(lang=code).name or "").strip().casefold()
                    for code, _l in self.env["res.lang"].get_installed()
                }
                candidates = {e for name in names for e in by_name.get(name, [])}
                if len(candidates) == 1:
                    edition = candidates.pop()
            if not edition or edition.product_tmpl_id or edition.id in taken:
                continue
            taken.add(edition.id)
            links.append((product, edition))

        for product, edition in links:
            edition.product_tmpl_id = product
            product.comic_edition_id = edition
        return len(links)

    @api.model
    def action_comic_relink_editions(self):
        count = self._comic_relink_editions()
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "message": _("%s produit(s) relié(s) à leur édition BD.", count),
                "type": "success" if count else "info",
                "sticky": False,
            },
        }
