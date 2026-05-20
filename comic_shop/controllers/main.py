from odoo import http
from odoo.http import request
from odoo.addons.website_sale.controllers.main import WebsiteSale


class ComicShopController(WebsiteSale):
    """Étend website_sale : page produit BD, filtres sidebar, pages séries."""

    # ── Page produit ──────────────────────────────────────────────────────────

    @http.route()
    def product(self, product, category='', search='', **kwargs):
        response = super().product(product, category=category, search=search, **kwargs)
        if not hasattr(response, 'qcontext'):
            return response
        response.qcontext.update({
            'comic_album': False,
            'comic_other_tomes': [],
            'comic_in_library': False,
        })
        album = product.sudo().comic_album_id
        if not album:
            return response
        other_tomes = request.env['comic.album'].sudo().search([
            ('serie_id', '=', album.serie_id.id),
            ('product_tmpl_id', '!=', False),
            ('id', '!=', album.id),
        ], order='tome') if album.serie_id else []
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

    # ── Shop : injection des filtres BD dans le contexte ─────────────────────

    @http.route()
    def shop(self, **kwargs):
        response = super().shop(**kwargs)
        if not hasattr(response, 'qcontext'):
            return response

        env = request.env
        params = request.params

        bd_serie_id = params.get('bd_serie_id', '')
        bd_genre_id = params.get('bd_genre', '')
        bd_auteur_id = params.get('bd_auteur', '')
        bd_type = params.get('bd_type', '')

        # Listes pour les selects de la sidebar
        bd_series = env['comic.serie'].sudo().search([
            ('album_ids.product_tmpl_id', '!=', False),
        ])
        bd_genres = env['comic.genre'].sudo().search([])
        bd_auteur_lines = env['comic.album.auteur.line'].sudo().search([
            ('album_id.product_tmpl_id', '!=', False),
            ('role', 'in', ['scenariste', 'dessinateur']),
        ])
        bd_auteurs = bd_auteur_lines.mapped('partner_id')

        response.qcontext.update({
            'bd_series': bd_series,
            'bd_genres': bd_genres,
            'bd_auteurs': bd_auteurs,
            'bd_types': [
                ('bd', 'BD'),
                ('manga', 'Manga'),
                ('comics', 'Comics'),
                ('one_shot', 'One-shot'),
            ],
            'bd_selected_serie': int(bd_serie_id) if bd_serie_id else False,
            'bd_selected_genre': int(bd_genre_id) if bd_genre_id else False,
            'bd_selected_auteur': int(bd_auteur_id) if bd_auteur_id else False,
            'bd_selected_type': bd_type,
        })

        # Post-filtrage du résultat quand un filtre BD est actif
        if any([bd_serie_id, bd_genre_id, bd_auteur_id, bd_type]):
            album_domain = [('product_tmpl_id', '!=', False)]
            if bd_serie_id:
                album_domain.append(('serie_id', '=', int(bd_serie_id)))
            if bd_genre_id:
                album_domain.append(('serie_id.genre_id', '=', int(bd_genre_id)))
            if bd_auteur_id:
                album_domain.append(('auteur_line_ids.partner_id', '=', int(bd_auteur_id)))
            if bd_type:
                album_domain.append(('serie_id.type', '=', bd_type))
            albums = env['comic.album'].sudo().search(album_domain)
            allowed_ids = set(albums.mapped('product_tmpl_id.id'))
            ctx = response.qcontext
            if 'products' in ctx:
                ctx['products'] = ctx['products'].filtered(
                    lambda p: p.id in allowed_ids
                )

        return response

    # ── Page /shop/series ─────────────────────────────────────────────────────

    @http.route('/shop/series', type='http', auth='public', website=True)
    def shop_series(self, **kwargs):
        series = request.env['comic.serie'].sudo().search([
            ('album_ids.product_tmpl_id', '!=', False),
        ])
        return request.render('comic_shop.shop_series_page', {'series': series})

    # ── Page /shop/series/<id> ────────────────────────────────────────────────

    @http.route('/shop/series/<int:serie_id>', type='http', auth='public', website=True)
    def shop_serie_detail(self, serie_id, **kwargs):
        serie = request.env['comic.serie'].sudo().browse(serie_id)
        if not serie.exists():
            return request.not_found()
        albums = request.env['comic.album'].sudo().search([
            ('serie_id', '=', serie.id),
            ('product_tmpl_id', '!=', False),
        ], order='tome')
        return request.render('comic_shop.shop_serie_detail_page', {
            'serie': serie,
            'albums': albums,
        })
