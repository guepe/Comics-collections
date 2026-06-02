from odoo import models


class PosOrder(models.Model):
    _inherit = "pos.order"

    def action_pos_order_paid(self):
        res = super().action_pos_order_paid()
        self._add_comics_to_library()
        return res

    def _add_comics_to_library(self):
        """Creates/updates comic.customer.album entries for BD sold at the POS."""
        CustomerAlbum = self.env["comic.customer.album"].sudo()
        for order in self:
            partner = order.partner_id
            if not partner or not partner.comic_auto_library:
                continue
            for line in order.lines:
                edition = line.product_id.product_tmpl_id.comic_edition_id
                if not edition:
                    continue
                existing = CustomerAlbum.search(
                    [
                        ("partner_id", "=", partner.id),
                        ("edition_id", "=", edition.id),
                    ],
                    limit=1,
                )
                if existing:
                    existing.write({"source": "achete_ici", "dans_collection": True})
                else:
                    CustomerAlbum.create(
                        {
                            "partner_id": partner.id,
                            "edition_id": edition.id,
                            "source": "achete_ici",
                            "dans_collection": True,
                        }
                    )
