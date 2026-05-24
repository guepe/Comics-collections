import base64
import logging
import re

import requests as http_requests

from odoo import http, _
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal
from odoo.addons.comic_datasource.aggregator import ComicDataAggregator

_logger = logging.getLogger(__name__)


def _clean_isbn(raw):
    """Strip spaces/dashes, return digits only (13 or 10 chars), or empty string."""
    digits = re.sub(r'[\s\-]', '', raw or '')
    return digits if len(digits) in (10, 13) else ''


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

        records = request.env['comic.customer.album'].sudo().search(domain)

        if sort == 'serie':
            records = records.sorted(
                key=lambda r: (r.edition_id.work_id.serie_id.name or '', r.edition_id.work_id.tome or 0)
            )
        elif sort == 'title':
            records = records.sorted(key=lambda r: r.edition_id.work_id.titre_canonique or '')
        else:
            records = records.sorted(key=lambda r: r.date_ajout or '', reverse=True)

        all_records = request.env['comic.customer.album'].sudo().search([
            ('partner_id', '=', partner.id),
        ])
        nb_series = len(all_records.mapped('edition_id.work_id.serie_id').filtered('id'))

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
        record = request.env['comic.customer.album'].sudo().browse(cust_album_id)
        if not record.exists() or record.partner_id.id != request.env.user.partner_id.id:
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
        record = request.env['comic.customer.album'].sudo().browse(cust_album_id)
        if not record.exists() or record.partner_id.id != request.env.user.partner_id.id:
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
        record = request.env['comic.customer.album'].sudo().browse(cust_album_id)
        if record.exists() and record.partner_id.id == request.env.user.partner_id.id:
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

    # ── /my/library/add — formulaire de recherche (étape 1) ────────────────

    @http.route('/my/library/add', type='http', auth='user', website=True)
    def my_library_add(self, **kw):
        flash = request.session.pop('comic_library_flash', None)
        return request.render('comic_shop.portal_library_add', {
            'step': 'search',
            'page_name': 'library',
            'flash': flash,
        })

    # ── /my/library/add/search — résultats de recherche (étape 1→2) ────────

    @http.route(
        '/my/library/add/search',
        type='http', auth='user', methods=['POST'], website=True, csrf=True,
    )
    def my_library_add_search(self, **post):
        isbn_raw = (post.get('isbn') or '').strip()
        title_raw = (post.get('title') or '').strip()

        if not isbn_raw and not title_raw:
            return request.redirect('/my/library/add')

        isbn = _clean_isbn(isbn_raw)
        results = []
        error = None

        # Local DB — ISBN exact
        if isbn:
            isbn_rec = request.env['comic.isbn'].sudo().search(
                [('isbn_13', '=', isbn)], limit=1
            )
            if isbn_rec:
                results.append(self._edition_to_result(isbn_rec.edition_id, is_local=True))

        # Local DB — titre (si pas trouvé par ISBN)
        if not results and title_raw:
            works = request.env['comic.work'].sudo().search(
                [('titre_canonique', 'ilike', title_raw)], limit=5, order='id desc'
            )
            for work in works:
                if work.edition_ids:
                    results.append(self._edition_to_result(work.edition_ids[0], is_local=True))

        # Sources externes via ComicDataAggregator
        if not results:
            try:
                agg = ComicDataAggregator(env=request.env)
                if isbn:
                    agg_result = agg.search(isbn=isbn)
                    if agg_result.data:
                        results.append(self._agg_to_result(agg_result.data, isbn))
                elif title_raw:
                    for r in agg.search_list(title=title_raw)[:6]:
                        d = self._source_result_to_result(r)
                        if d:
                            results.append(d)
            except Exception as exc:
                _logger.warning('Library add search error: %s', exc)
                error = _("La recherche externe est temporairement indisponible.")

        return request.render('comic_shop.portal_library_add', {
            'step': 'results',
            'results': results,
            'search_isbn': isbn_raw,
            'search_title': title_raw,
            'error': error,
            'page_name': 'library',
        })

    # ── /my/library/add/confirm — création / mise à jour (étape 2) ─────────

    @http.route(
        '/my/library/add/confirm',
        type='http', auth='user', methods=['POST'], website=True, csrf=True,
    )
    def my_library_add_confirm(self, **post):
        partner = request.env.user.partner_id
        isbn = _clean_isbn(post.get('isbn', ''))
        edition_id = int(post.get('edition_id') or 0)
        source = post.get('source', 'inconnu')
        etat_lecture = post.get('etat_lecture', 'non_lu')
        force_update = bool(post.get('force_update'))

        try:
            note = max(0.0, min(5.0, float(post.get('note') or 0)))
        except (ValueError, TypeError):
            note = 0.0

        # Resolve edition
        edition = None
        if edition_id:
            rec = request.env['comic.edition'].sudo().browse(edition_id)
            if rec.exists():
                edition = rec
        if not edition and isbn:
            isbn_rec = request.env['comic.isbn'].sudo().search(
                [('isbn_13', '=', isbn)], limit=1
            )
            if isbn_rec:
                edition = isbn_rec.edition_id
        if not edition:
            edition = self._create_edition_from_post(post)

        if not edition:
            return request.redirect('/my/library/add')

        existing = request.env['comic.customer.album'].sudo().search([
            ('partner_id', '=', partner.id),
            ('edition_id', '=', edition.id),
        ], limit=1)

        update_vals = {
            'source': source,
            'etat_lecture': etat_lecture,
            'dans_collection': True,
            'note': note,
        }

        if existing and not force_update:
            return request.render('comic_shop.portal_library_add', {
                'step': 'warning',
                'existing': existing,
                'edition': edition,
                'post': post,
                'page_name': 'library',
            })

        title = edition.work_id.titre_canonique or _('cet album')
        if existing:
            existing.sudo().write(update_vals)
            request.session['comic_library_flash'] = {
                'type': 'success',
                'message': _('« %s » a été mis à jour dans votre bibliothèque.') % title,
            }
        else:
            update_vals.update({'partner_id': partner.id, 'edition_id': edition.id})
            request.env['comic.customer.album'].sudo().create(update_vals)
            request.session['comic_library_flash'] = {
                'type': 'success',
                'message': _('« %s » a été ajouté à votre bibliothèque.') % title,
            }

        return request.redirect('/my/library')

    # ── Helpers ────────────────────────────────────────────────────────────

    def _edition_to_result(self, edition, is_local=True):
        work = edition.work_id
        auteurs = ', '.join(
            line.partner_id.name for line in work.auteur_line_ids if line.partner_id
        )
        isbn = edition._get_primary_isbn() or ''
        return {
            'edition_id': edition.id,
            'isbn': isbn,
            'title': work.titre_canonique or '',
            'serie_name': work.serie_id.name or '',
            'tome': work.tome or 0,
            'auteurs': auteurs,
            'editeur_name': edition.editeur_id.name or '',
            'cover_url': '',
            'is_local': is_local,
        }

    def _agg_to_result(self, data, isbn_fallback=''):
        auteurs_list = data.get('auteurs') or []
        auteurs = ', '.join(a.get('name', '') for a in auteurs_list if a.get('name'))
        return {
            'edition_id': 0,
            'isbn': data.get('isbn') or isbn_fallback,
            'title': data.get('title') or '',
            'serie_name': data.get('serie_name') or '',
            'tome': data.get('tome') or 0,
            'auteurs': auteurs,
            'editeur_name': data.get('editeur') or '',
            'cover_url': data.get('cover_url_small') or data.get('cover_url') or '',
            'is_local': False,
        }

    def _source_result_to_result(self, result):
        if not result:
            return None
        auteurs_list = result.auteurs or []
        auteurs = ', '.join(a.get('name', '') for a in auteurs_list if a.get('name'))
        return {
            'edition_id': 0,
            'isbn': result.isbn or '',
            'title': result.title or '',
            'serie_name': result.serie_name or '',
            'tome': result.tome or 0,
            'auteurs': auteurs,
            'editeur_name': result.editeur or '',
            'cover_url': getattr(result, 'cover_url_small', '') or getattr(result, 'cover_url', '') or '',
            'is_local': False,
        }

    def _create_edition_from_post(self, post):
        """Creates comic.work + comic.edition + comic.isbn from POST data (external result)."""
        isbn = _clean_isbn(post.get('isbn', ''))
        title = (post.get('title') or '').strip()
        serie_name = (post.get('serie_name') or '').strip()
        editeur_name = (post.get('editeur_name') or '').strip()
        cover_url = (post.get('cover_url') or '').strip()

        try:
            tome = int(post.get('tome') or 0)
        except (ValueError, TypeError):
            tome = 0

        if not title:
            return None

        env = request.env

        # Editeur
        editeur = None
        if editeur_name:
            editeur = env['comic.editeur'].sudo().search(
                [('name', '=', editeur_name)], limit=1
            )
            if not editeur:
                editeur = env['comic.editeur'].sudo().create({'name': editeur_name})

        # Série
        serie = None
        if serie_name:
            serie = env['comic.serie'].sudo().search(
                [('name', '=', serie_name)], limit=1
            )
            if not serie:
                serie = env['comic.serie'].sudo().create({'name': serie_name})

        # Work
        work = None
        if serie and tome:
            work = env['comic.work'].sudo().search(
                [('serie_id', '=', serie.id), ('tome', '=', tome)], limit=1
            )
        if not work and serie:
            work = env['comic.work'].sudo().search(
                [('serie_id', '=', serie.id), ('titre_canonique', '=', title)], limit=1
            )
        if not work:
            work_vals = {'titre_canonique': title}
            if serie:
                work_vals['serie_id'] = serie.id
            if tome:
                work_vals['tome'] = tome
            work = env['comic.work'].sudo().create(work_vals)

        # Edition
        edition = env['comic.edition'].sudo().search(
            [('work_id', '=', work.id)], limit=1
        )
        if not edition:
            edition_vals = {'work_id': work.id}
            if editeur:
                edition_vals['editeur_id'] = editeur.id
            if cover_url:
                try:
                    resp = http_requests.get(cover_url, timeout=10)
                    if resp.status_code == 200 and len(resp.content) > 100:
                        edition_vals['image_couverture'] = base64.b64encode(resp.content).decode()
                except Exception as exc:
                    _logger.warning('Cover download failed: %s', exc)
            edition = env['comic.edition'].sudo().create(edition_vals)

        # ISBN
        if isbn:
            if not env['comic.isbn'].sudo().search([('isbn_13', '=', isbn)], limit=1):
                env['comic.isbn'].sudo().create({'edition_id': edition.id, 'isbn_13': isbn})

        return edition
