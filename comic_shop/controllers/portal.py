from odoo import http, _
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal


class ComicLibraryPortal(CustomerPortal):

    def _prepare_home_portal_values(self, counters):
        values = super()._prepare_home_portal_values(counters)
        if 'library_count' in counters:
            values['library_count'] = request.env['comic.customer.album'].search_count([
                ('partner_id', '=', request.env.user.partner_id.id),
            ])
        return values

    # ── /my/library — index ─────────────────────────────────────────────────

    @http.route('/my/library', type='http', auth='user', website=True)
    def my_library(self, filter='all', sort='date', view='kanban', **kw):
        partner = request.env.user.partner_id

        domain = [('partner_id', '=', partner.id)]
        if filter == 'collection':
            domain.append(('dans_collection', '=', True))
        elif filter == 'wishlist':
            domain.append(('dans_wishlist', '=', True))
        elif filter == 'reading':
            domain.append(('etat_lecture', '=', 'en_cours'))

        records = request.env['comic.customer.album'].search(domain)

        if sort == 'serie':
            records = records.sorted(
                key=lambda r: (r.album_id.serie_id.name or '', r.album_id.tome or 0)
            )
        elif sort == 'title':
            records = records.sorted(key=lambda r: r.album_id.name or '')
        else:
            records = records.sorted(key=lambda r: r.date_ajout or '', reverse=True)

        all_records = request.env['comic.customer.album'].search([
            ('partner_id', '=', partner.id),
        ])
        nb_series = len(all_records.mapped('album_id.serie_id').filtered('id'))

        return request.render('comic_shop.portal_library_index', {
            'records': records,
            'filter': filter,
            'sort': sort,
            'view_mode': view,
            'nb_albums': len(all_records),
            'nb_series': nb_series,
            'nb_reading': len(all_records.filtered(lambda r: r.etat_lecture == 'en_cours')),
            'page_name': 'library',
        })

    # ── /my/library/<id> — détail ───────────────────────────────────────────

    @http.route('/my/library/<int:cust_album_id>', type='http', auth='user', website=True)
    def my_library_detail(self, cust_album_id, **kw):
        record = request.env['comic.customer.album'].browse(cust_album_id)
        if not record.exists() or record.partner_id != request.env.user.partner_id:
            return request.not_found()
        return request.render('comic_shop.portal_library_detail', {
            'record': record,
            'page_name': 'library',
        })

    # ── /my/library/<id>/update — POST ─────────────────────────────────────

    @http.route(
        '/my/library/<int:cust_album_id>/update',
        type='http', auth='user', methods=['POST'], website=True, csrf=True,
    )
    def my_library_update(self, cust_album_id, **post):
        record = request.env['comic.customer.album'].browse(cust_album_id)
        if not record.exists() or record.partner_id != request.env.user.partner_id:
            return request.not_found()

        vals = {
            'etat_lecture': post.get('etat_lecture', record.etat_lecture),
            'dans_collection': bool(post.get('dans_collection')),
            'dans_wishlist': bool(post.get('dans_wishlist')),
            'commentaire': post.get('commentaire', ''),
        }
        try:
            vals['note'] = max(0.0, min(5.0, float(post.get('note', 0))))
        except (ValueError, TypeError):
            pass

        record.sudo().write(vals)
        return request.redirect(f'/my/library/{cust_album_id}')

    # ── /my/library/<id>/remove — POST ─────────────────────────────────────

    @http.route(
        '/my/library/<int:cust_album_id>/remove',
        type='http', auth='user', methods=['POST'], website=True, csrf=True,
    )
    def my_library_remove(self, cust_album_id, **post):
        record = request.env['comic.customer.album'].browse(cust_album_id)
        if record.exists() and record.partner_id == request.env.user.partner_id:
            record.sudo().unlink()
        return request.redirect('/my/library')

    # ── /my/library/preferences — POST ─────────────────────────────────────

    @http.route(
        '/my/library/preferences',
        type='http', auth='user', methods=['POST'], website=True, csrf=True,
    )
    def my_library_preferences(self, **post):
        auto_library = bool(post.get('comic_auto_library'))
        request.env.user.partner_id.sudo().write({'comic_auto_library': auto_library})
        return request.redirect('/my/library')
