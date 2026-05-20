from odoo import http
from odoo.http import request
from odoo.addons.website_sale.controllers.main import WebsiteSale

_ROLE_LABELS = {
    'scenariste': 'Scénariste',
    'dessinateur': 'Dessinateur',
    'coloriste': 'Coloriste',
    'encreur': 'Encreur',
    'traducteur': 'Traducteur',
    'autre': 'Autre',
}

_BD_FILTER_PARAMS = ('bd_serie_id', 'bd_genre', 'bd_auteur', 'bd_type')


def _bd_params(params):
    """Retourne (serie_id, genre_id, auteur_id, type) depuis les GET params."""
    return (
        params.get('bd_serie_id', ''),
        params.get('bd_genre', ''),
        params.get('bd_auteur', ''),
        params.get('bd_type', ''),
    )


class ComicShopController(WebsiteSale):
    """Étend website_sale : page produit BD, filtres sidebar, pages séries/auteurs/éditeurs."""

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

    # ── Filtrage BD : intercepté au bon niveau (avant calcul de bins) ─────────

    def _shop_lookup_products(self, options, post, search, website):
        """Override pour filtrer par série / genre / auteur / type BD."""
        fuzzy_term, product_count, search_result = super()._shop_lookup_products(
            options, post, search, website
        )
        bd_serie_id, bd_genre_id, bd_auteur_id, bd_type = _bd_params(request.params)
        if not any([bd_serie_id, bd_genre_id, bd_auteur_id, bd_type]):
            return fuzzy_term, product_count, search_result

        album_domain = [('product_tmpl_id', '!=', False)]
        if bd_serie_id:
            album_domain.append(('serie_id', '=', int(bd_serie_id)))
        if bd_genre_id:
            album_domain.append(('serie_id.genre_id', '=', int(bd_genre_id)))
        if bd_auteur_id:
            album_domain.append(('auteur_line_ids.partner_id', '=', int(bd_auteur_id)))
        if bd_type:
            album_domain.append(('serie_id.type', '=', bd_type))

        allowed_ids = set(
            request.env['comic.album'].sudo().search(album_domain).mapped('product_tmpl_id.id')
        )
        search_result = search_result.filtered(lambda p: p.id in allowed_ids)
        return fuzzy_term, len(search_result), search_result

    def _shop_get_query_url_kwargs(self, search, min_price, max_price, order=None, tags=None, **kwargs):
        """Inclure les params BD dans keep() pour que pagination/tri les préserve."""
        result = super()._shop_get_query_url_kwargs(
            search, min_price, max_price, order=order, tags=tags, **kwargs
        )
        for key in _BD_FILTER_PARAMS:
            val = request.params.get(key, '')
            if val:
                result[key] = val
        return result

    # ── Shop : injection des données de filtres BD dans le contexte ───────────

    @http.route()
    def shop(self, **kwargs):
        response = super().shop(**kwargs)
        if not hasattr(response, 'qcontext'):
            return response

        env = request.env
        params = request.params
        bd_serie_id, bd_genre_id, bd_auteur_id, bd_type = _bd_params(params)

        bd_series = env['comic.serie'].sudo().search([
            ('album_ids.product_tmpl_id', '!=', False),
        ])
        bd_genres = env['comic.genre'].sudo().search([])
        bd_auteurs = env['comic.album.auteur.line'].sudo().search([
            ('album_id.product_tmpl_id', '!=', False),
            ('role', 'in', ['scenariste', 'dessinateur']),
        ]).mapped('partner_id')

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
        return response

    # ── Pages séries ──────────────────────────────────────────────────────────

    @http.route('/shop/series', type='http', auth='public', website=True)
    def shop_series(self, **kwargs):
        series = request.env['comic.serie'].sudo().search([
            ('album_ids.product_tmpl_id', '!=', False),
        ])
        return request.render('comic_shop.shop_series_page', {'series': series})

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

    # ── Pages auteurs ─────────────────────────────────────────────────────────

    @http.route('/shop/auteurs', type='http', auth='public', website=True)
    def shop_auteurs(self, **kwargs):
        lines = request.env['comic.album.auteur.line'].sudo().search([
            ('album_id.product_tmpl_id', '!=', False),
        ])
        auteur_map = {}
        for line in lines:
            pid = line.partner_id.id
            if pid not in auteur_map:
                auteur_map[pid] = {
                    'partner': line.partner_id,
                    'roles': set(),
                    'nb_albums': 0,
                }
            auteur_map[pid]['roles'].add(line.role)
            auteur_map[pid]['nb_albums'] += 1
        auteurs = []
        for data in sorted(auteur_map.values(), key=lambda d: (d['partner'].name or '').lower()):
            data['role_labels'] = ', '.join(
                _ROLE_LABELS.get(r, r) for r in sorted(data['roles'])
            )
            auteurs.append(data)
        return request.render('comic_shop.shop_auteurs_page', {'auteurs': auteurs})

    @http.route('/shop/auteurs/<int:auteur_id>', type='http', auth='public', website=True)
    def shop_auteur_detail(self, auteur_id, **kwargs):
        auteur = request.env['res.partner'].sudo().browse(auteur_id)
        if not auteur.exists():
            return request.not_found()
        lines = request.env['comic.album.auteur.line'].sudo().search([
            ('partner_id', '=', auteur_id),
            ('album_id.product_tmpl_id', '!=', False),
        ])
        lines = lines.sorted(key=lambda l: (l.album_id.serie_id.name or '', l.album_id.tome or 0))
        by_role = {}
        for line in lines:
            label = _ROLE_LABELS.get(line.role, line.role)
            if label not in by_role:
                by_role[label] = []
            by_role[label].append(line.album_id)
        return request.render('comic_shop.shop_auteur_detail_page', {
            'auteur': auteur,
            'by_role': by_role,
            'nb_albums': sum(len(v) for v in by_role.values()),
        })

    # ── Pages éditeurs ────────────────────────────────────────────────────────

    @http.route('/shop/editeurs', type='http', auth='public', website=True)
    def shop_editeurs(self, **kwargs):
        series_with_products = request.env['comic.serie'].sudo().search([
            ('album_ids.product_tmpl_id', '!=', False),
            ('editeur_id', '!=', False),
        ])
        editeur_map = {}
        for serie in series_with_products:
            eid = serie.editeur_id.id
            if eid not in editeur_map:
                editeur_map[eid] = {
                    'editeur': serie.editeur_id,
                    'nb_series': 0,
                    'nb_albums': 0,
                }
            editeur_map[eid]['nb_series'] += 1
            editeur_map[eid]['nb_albums'] += len(
                serie.album_ids.filtered(lambda a: a.product_tmpl_id)
            )
        editeurs = sorted(
            editeur_map.values(),
            key=lambda d: (d['editeur'].name or '').lower()
        )
        return request.render('comic_shop.shop_editeurs_page', {'editeurs': editeurs})

    @http.route('/shop/editeurs/<int:editeur_id>', type='http', auth='public', website=True)
    def shop_editeur_detail(self, editeur_id, **kwargs):
        editeur = request.env['comic.editeur'].sudo().browse(editeur_id)
        if not editeur.exists():
            return request.not_found()
        series = request.env['comic.serie'].sudo().search([
            ('editeur_id', '=', editeur_id),
            ('album_ids.product_tmpl_id', '!=', False),
        ])
        return request.render('comic_shop.shop_editeur_detail_page', {
            'editeur': editeur,
            'series': series,
        })
