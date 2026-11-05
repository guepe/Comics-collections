import logging

from markupsafe import Markup

from odoo import models

_logger = logging.getLogger(__name__)


class SaleOrder(models.Model):
    _inherit = "sale.order"

    def action_confirm(self):
        res = super().action_confirm()
        try:
            with self.env.cr.savepoint():
                self._add_comics_to_library()
        except Exception:
            # La bibliothèque client ne doit jamais bloquer une confirmation de commande
            _logger.exception("Bibliothèque BD : échec de la mise à jour pour la commande %s", self.ids)
        return res

    def _action_cancel(self):
        res = super()._action_cancel()
        self.env["comic.customer.album"].sudo().search(
            [("sale_order_line_id", "in", self.order_line.ids)]
        )._revert_purchase()
        return res

    def _add_comics_to_library(self):
        """Automatically adds purchased editions to the customer's library."""
        CustomerAlbum = self.env["comic.customer.album"].sudo()
        for order in self:
            partner = order.partner_id
            if not partner.comic_auto_library:
                continue
            added = []
            for line in order.order_line:
                if line.product_uom_qty <= 0 or not line.product_id:
                    continue
                edition = line.product_id.product_tmpl_id._get_comic_edition()
                if not edition:
                    continue
                _record, created = CustomerAlbum._register_purchase(partner, edition, sale_line=line)
                if created:
                    added.append(edition)
            if added:
                self._notify_customer_library_added(order, partner, added)

    def _notify_customer_library_added(self, order, partner, editions):
        """Sends a notification to the customer listing the BD added to their library."""
        items = Markup("").join(
            Markup("<li><strong>{name}</strong></li>").format(name=e.display_name) for e in editions
        )
        body = Markup(
            "<p>Les BD suivantes ont été ajoutées à "
            '<a href="/my/library">votre bibliothèque</a> suite à votre commande :</p>'
            "<ul>{items}</ul>"
            "<p>"
            '<a href="/my/library" '
            'style="background:#875A7B;color:#fff;padding:8px 16px;'
            'border-radius:4px;text-decoration:none;">'
            "Voir ma bibliothèque</a>"
            "</p>"
        ).format(items=items)
        order.message_post(
            body=body,
            partner_ids=partner.ids,
            message_type="comment",
            subtype_xmlid="mail.mt_comment",
        )
