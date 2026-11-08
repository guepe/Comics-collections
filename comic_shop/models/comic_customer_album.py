"""Extension commerciale de la bibliothèque personnelle (modèle défini dans comics_collections).

Ajoute la source « Acheté ici », le lien vers la vente d'origine (shop ou caisse) et
l'enregistrement / l'annulation automatiques des achats.
"""

from odoo import api, fields, models


class ComicCustomerAlbum(models.Model):
    _inherit = "comic.customer.album"

    source = fields.Selection(
        selection_add=[("achete_ici", "Acheté ici")],
        ondelete={"achete_ici": "set default"},
    )
    sale_order_line_id = fields.Many2one(
        "sale.order.line",
        string="Ligne de commande",
        ondelete="set null",
        copy=False,
        help="Ligne de commande à l'origine de l'ajout automatique.",
    )
    pos_order_line_id = fields.Many2one(
        "pos.order.line",
        string="Ligne de caisse",
        ondelete="set null",
        copy=False,
        help="Ligne de vente en caisse à l'origine de l'ajout automatique.",
    )
    auto_created = fields.Boolean(
        string="Créé par un achat",
        copy=False,
        help="Entrée créée automatiquement par une vente (shop ou caisse). "
        "Sert à la retirer proprement en cas d'annulation ou de remboursement.",
    )
    has_product = fields.Boolean(
        string="Produit disponible",
        compute="_compute_has_product",
        store=True,
        index=True,
        help="True si l'édition est liée à un produit vendable dans le shop.",
    )

    @api.depends("edition_id.product_tmpl_id")
    def _compute_has_product(self):
        for rec in self:
            rec.has_product = bool(rec.edition_id.product_tmpl_id)

    # ── Enregistrement / annulation d'achats ────────────────────────────────

    @api.model
    def _register_purchase(self, partner, edition, sale_line=None, pos_line=None):
        vals = {
            "source": "achete_ici",
            "dans_collection": True,
            "dans_wishlist": False,  # acheté → sort de la wishlist
        }
        if sale_line:
            vals["sale_order_line_id"] = sale_line.id
        if pos_line:
            vals["pos_order_line_id"] = pos_line.id
        record, created = self._upsert(partner, edition, vals)
        if created:
            record.auto_created = True
        return record, created

    def _revert_purchase(self):
        """Undo an automatic purchase registration (cancelled order / refund).

        Entrée créée par l'achat et jamais touchée par le client → supprimée.
        Sinon (le client l'a lue, notée, commentée, ou elle existait avant) → conservée,
        mais la source « acheté ici » n'est plus vraie : elle repasse à « inconnu ».
        """
        for rec in self:
            untouched = rec.etat_lecture == "non_lu" and not rec.note and not rec.commentaire
            if rec.auto_created and untouched:
                rec.unlink()
            else:
                rec.write(
                    {
                        "source": "inconnu" if rec.source == "achete_ici" else rec.source,
                        "sale_order_line_id": False,
                        "pos_order_line_id": False,
                        "auto_created": False,
                    }
                )
