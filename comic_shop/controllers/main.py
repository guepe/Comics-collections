from odoo import http
from odoo.http import request
from odoo.addons.website_sale.controllers.main import WebsiteSale


class ComicShopController(WebsiteSale):
    """Étend la page produit website_sale pour afficher les données BD."""

    @http.route()
    def product(self, product, category='', search='', **kwargs):
        response = super().product(product, category=category, search=search, **kwargs)

        album = product.sudo().comic_album_id
        if not album or not hasattr(response, 'qcontext'):
            return response

        # Autres tomes de la même série ayant un produit (hors tome courant)
        other_tomes = request.env['comic.album'].sudo().search([
            ('serie_id', '=', album.serie_id.id),
            ('product_tmpl_id', '!=', False),
            ('id', '!=', album.id),
        ], order='tome') if album.serie_id else []

        # Cet album est-il dans la bibliothèque du visiteur connecté ?
        in_library = False
        if not request.website.is_public_user():
            in_library = bool(request.env['comic.customer.album'].search_count([
                ('album_id', '=', album.id),
                ('partner_id', '=', request.env.user.partner_id.id),
            ]))

        response.qcontext.update({
            'comic_album': album,
            'comic_other_tomes': other_tomes,
            'comic_in_library': in_library,
        })
        return response
