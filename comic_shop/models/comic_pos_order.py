import logging

from odoo import models

_logger = logging.getLogger(__name__)


class PosOrder(models.Model):
    _inherit = "pos.order"

    def action_pos_order_paid(self):
        res = super().action_pos_order_paid()
        try:
            with self.env.cr.savepoint():
                self._add_comics_to_library()
        except Exception:
            # La bibliothèque client ne doit jamais bloquer un encaissement
            _logger.exception("Bibliothèque BD : échec de la mise à jour après paiement POS %s", self.ids)
        return res

    def _add_comics_to_library(self):
        """Registers BD sold at the POS in the customer's library; reverts refunded ones."""
        CustomerAlbum = self.env["comic.customer.album"].sudo()
        for order in self:
            for line in order.lines:
                if line.qty < 0:
                    self._revert_refunded_line(line)
                    continue
                partner = order.partner_id
                if not line.qty or not partner or not partner.comic_auto_library:
                    continue
                edition = line.product_id.product_tmpl_id._get_comic_edition()
                if edition:
                    CustomerAlbum._register_purchase(partner, edition, pos_line=line)

    def _revert_refunded_line(self, refund_line):
        """Refund line: if the original sale line is fully refunded, undo the library entry."""
        origin = refund_line.refunded_orderline_id
        if not origin or origin.refunded_qty < origin.qty:
            return
        albums = self.env["comic.customer.album"].sudo().search([("pos_order_line_id", "=", origin.id)])
        albums._revert_purchase()
