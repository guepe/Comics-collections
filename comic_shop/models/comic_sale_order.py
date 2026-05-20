from odoo import models
from markupsafe import Markup


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def action_confirm(self):
        res = super().action_confirm()
        self._add_comics_to_library()
        return res

    def _add_comics_to_library(self):
        """Ajoute automatiquement les albums achetés à la bibliothèque du client."""
        CustomerAlbum = self.env['comic.customer.album'].sudo()
        Album = self.env['comic.album'].sudo()
        for order in self:
            partner = order.partner_id
            if not partner.comic_auto_library:
                continue
            added = []
            for line in order.order_line:
                tmpl_id = line.product_id.product_tmpl_id.id
                album = Album.search([('product_tmpl_id', '=', tmpl_id)], limit=1)
                if not album:
                    continue
                existing = CustomerAlbum.search([
                    ('partner_id', '=', partner.id),
                    ('album_id', '=', album.id),
                ], limit=1)
                if existing:
                    existing.write({
                        'source': 'achete_ici',
                        'dans_collection': True,
                        'sale_order_line_id': line.id,
                    })
                else:
                    CustomerAlbum.create({
                        'partner_id': partner.id,
                        'album_id': album.id,
                        'source': 'achete_ici',
                        'dans_collection': True,
                        'sale_order_line_id': line.id,
                    })
                    added.append(album)
            if added:
                self._notify_customer_library_added(order, partner, added)

    def _notify_customer_library_added(self, order, partner, albums):
        """Envoie une notification au client listant les BD ajoutées à sa bibliothèque."""
        items = Markup('').join(
            Markup('<li><strong>{name}</strong></li>').format(name=a.name)
            for a in albums
        )
        body = Markup(
            '<p>Les BD suivantes ont été ajoutées à '
            '<a href="/my/library">votre bibliothèque</a> suite à votre commande :</p>'
            '<ul>{items}</ul>'
            '<p>'
            '<a href="/my/library" '
            'style="background:#875A7B;color:#fff;padding:8px 16px;'
            'border-radius:4px;text-decoration:none;">'
            'Voir ma bibliothèque</a>'
            '</p>'
        ).format(items=items)
        order.message_post(
            body=body,
            partner_ids=partner.ids,
            message_type='comment',
            subtype_xmlid='mail.mt_comment',
        )
