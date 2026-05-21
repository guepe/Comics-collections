import base64
import json
import logging
import re
import requests
from datetime import date

from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

ISBN_RE = re.compile(r'^[\d\-X]{10,17}$')


def _clean_isbn(term):
    cleaned = re.sub(r'[^0-9X]', '', (term or '').upper())
    return cleaned if len(cleaned) in (10, 13) else None


def _normalize_isbn(isbn):
    raw = re.sub(r'[\-\s]', '', isbn or '')
    if len(raw) == 10 and raw[:9].isdigit():
        base = '978' + raw[:9]
        total = sum(int(d) * (1 if i % 2 == 0 else 3) for i, d in enumerate(base))
        check = (10 - total % 10) % 10
        return base + str(check)
    return raw


class ComicDatasourceSearchWizard(models.TransientModel):
    _name = 'comic.datasource.search.wizard'
    _description = 'Recherche et import BD multi-sources'

    search_term = fields.Char(string='Rechercher', required=True)
    search_type = fields.Selection(
        [('isbn', 'ISBN / EAN-13'), ('title', 'Titre')],
        compute='_compute_search_type', store=True,
    )
    state = fields.Selection(
        [('search', 'Recherche'), ('results', 'Résultats'), ('done', 'Terminé')],
        default='search',
    )
    edition_id = fields.Many2one('comic.edition', string='Édition à enrichir')
    result_ids = fields.One2many('comic.datasource.result.line', 'wizard_id', string='Résultats')
    import_report = fields.Html(string='Rapport', readonly=True)
    bdgest_enabled = fields.Boolean(compute='_compute_bdgest_enabled')
    has_duplicates = fields.Boolean(compute='_compute_has_duplicates')
    has_title_conflicts = fields.Boolean(compute='_compute_has_duplicates')

    def _compute_bdgest_enabled(self):
        enabled = self.env['ir.config_parameter'].sudo().get_param(
            'comic.bdgest_enabled', 'False'
        ) == 'True'
        for rec in self:
            rec.bdgest_enabled = enabled

    @api.depends('result_ids.is_duplicate', 'result_ids.title_conflict')
    def _compute_has_duplicates(self):
        for rec in self:
            rec.has_duplicates = any(rec.result_ids.mapped('is_duplicate'))
            rec.has_title_conflicts = any(rec.result_ids.mapped('title_conflict'))

    @api.depends('search_term')
    def _compute_search_type(self):
        for rec in self:
            rec.search_type = 'isbn' if _clean_isbn(rec.search_term or '') else 'title'

    # ── Search ────────────────────────────────────────────────────────────────

    def action_search(self):
        self.ensure_one()
        self.result_ids.unlink()

        from ..aggregator import ComicDataAggregator
        aggregator = ComicDataAggregator(env=self.env)

        isbn = _clean_isbn(self.search_term)

        try:
            if isbn:
                agg = aggregator.search(isbn=isbn)
                if not agg.data:
                    raise UserError(_('Aucun résultat trouvé pour l\'ISBN %s.') % isbn)
                lines = [self._aggregated_to_line_vals(agg, isbn)]
            else:
                raw_results = aggregator.search_list(title=self.search_term)
                if not raw_results:
                    raise UserError(_('Aucun résultat trouvé pour "%s".') % self.search_term)
                lines = [self._source_result_to_line_vals(r) for r in raw_results[:15]]
        except UserError:
            raise
        except Exception as e:
            raise UserError(_('Erreur lors de la recherche : %s') % str(e))

        for vals in lines:
            if vals.get('isbn'):
                existing = self._find_edition_by_isbn(vals['isbn'])
                if existing:
                    vals['is_duplicate'] = True
                    vals['existing_edition_id'] = existing.id
                    new_t = (vals.get('title') or '').lower().strip()
                    old_t = (existing.work_id.titre_canonique or '').lower().strip()
                    if new_t and old_t and new_t != old_t:
                        vals['title_conflict'] = True
                        vals['existing_title'] = existing.work_id.titre_canonique
                        vals['title_action'] = 'keep'

        self.env['comic.datasource.result.line'].create(
            [dict(v, wizard_id=self.id) for v in lines]
        )
        self.state = 'results'
        return self._reopen()

    def _aggregated_to_line_vals(self, agg, isbn):
        data = agg.data
        auteurs_display = ', '.join(
            f"{a['name']} ({a.get('role', '')})" for a in data.get('auteurs', [])
        )
        return {
            'selected': True,
            'title': data.get('title', ''),
            'serie_name': data.get('serie_name'),
            'tome': data.get('tome') or 0,
            'isbn': data.get('isbn') or isbn,
            'editeur': data.get('editeur'),
            'auteurs_display': auteurs_display,
            'date_parution': str(data.get('date_parution') or ''),
            'source': data.get('field_sources', {}).get('title', 'google'),
            'cover_url': data.get('cover_url') or data.get('cover_url_small'),
            'cover_data': self._fetch_cover(data.get('cover_url_small') or data.get('cover_url')),
            'result_data': json.dumps(data, default=str),
        }

    def _source_result_to_line_vals(self, result):
        auteurs_display = ', '.join(
            f"{a['name']} ({a.get('role', '')})" for a in (result.auteurs or [])
        )
        data = result.to_dict()
        return {
            'selected': False,
            'title': result.title or '',
            'serie_name': result.serie_name,
            'tome': result.tome or 0,
            'isbn': result.isbn,
            'editeur': result.editeur,
            'auteurs_display': auteurs_display,
            'date_parution': str(result.date_parution or ''),
            'source': result.source,
            'cover_url': result.cover_url or result.cover_url_small,
            'cover_data': self._fetch_cover(result.cover_url_small or result.cover_url),
            'result_data': json.dumps(data, default=str),
        }

    def _find_edition_by_isbn(self, isbn):
        """Finds a comic.edition by looking up comic.isbn records."""
        clean = _normalize_isbn(isbn)
        if not clean:
            return self.env['comic.edition'].browse()
        isbn_rec = self.env['comic.isbn'].search(
            ['|', ('isbn_13', '=', isbn), ('isbn_13', '=', clean)], limit=1
        )
        if isbn_rec:
            return isbn_rec.edition_id
        candidates = self.env['comic.isbn'].search([('isbn_13', 'like', clean[:7])])
        match = candidates.filtered(lambda i: _normalize_isbn(i.isbn_13) == clean)[:1]
        return match.edition_id if match else self.env['comic.edition'].browse()

    def _fetch_cover(self, url):
        if not url:
            return False
        try:
            resp = requests.get(url, timeout=5)
            if resp.status_code == 200 and len(resp.content) > 100:
                return base64.b64encode(resp.content).decode()
        except Exception:
            pass
        return False

    # ── Import ────────────────────────────────────────────────────────────────

    def action_import(self):
        self.ensure_one()
        selected = self.result_ids.filtered('selected')
        if not selected:
            raise UserError(_('Sélectionnez au moins un résultat à importer.'))

        created, updated, ignored = [], [], []
        for line in selected:
            try:
                status, record = self._import_line(line)
                if status == 'created':
                    created.append(record)
                elif status == 'updated':
                    updated.append(record)
                else:
                    ignored.append(record)
            except Exception as e:
                _logger.error('Datasource import error on "%s": %s', line.title, e)
                ignored.append(None)

        self.import_report = self._build_report(created, updated, ignored)
        self.state = 'done'
        return self._reopen()

    def _import_line(self, line):
        data = json.loads(line.result_data or '{}')
        raw_isbn = data.get('isbn') or line.isbn
        isbn = _normalize_isbn(raw_isbn) or raw_isbn or False

        existing = self._find_edition_by_isbn(isbn) if isbn else None

        editeur = self._get_or_create_editeur(data.get('editeur') or line.editeur)
        serie = self._get_or_create_serie(data.get('serie_name') or line.serie_name, editeur)
        cover_b64 = self._get_cover_b64(line, data)

        if line.title_conflict:
            if line.title_action == 'skip':
                return 'ignored', existing or self.env['comic.edition'].browse()
            use_title = (
                existing.work_id.titre_canonique
                if line.title_action == 'keep' and existing
                else (data.get('title') or line.title or '')
            )
        else:
            use_title = data.get('title') or line.title or ''
        if not use_title:
            use_title = data.get('serie_name') or line.serie_name or _('Sans titre')

        if existing:
            work_vals = {}
            if use_title:
                work_vals['titre_canonique'] = use_title
            if serie and not existing.work_id.serie_id:
                work_vals['serie_id'] = serie.id
            if work_vals:
                existing.work_id.write(work_vals)

            ed_vals = {}
            if not existing.synopsis and data.get('synopsis'):
                ed_vals['synopsis'] = data['synopsis']
            if not existing.nb_pages and data.get('nb_pages'):
                ed_vals['nb_pages'] = data['nb_pages']
            if editeur and not existing.editeur_id:
                ed_vals['editeur_id'] = editeur.id
            if cover_b64 and not existing.image_couverture:
                ed_vals['image_couverture'] = cover_b64
            if ed_vals:
                existing.write(ed_vals)
            self._sync_work_authors(existing.work_id, data.get('auteurs', []))
            return 'updated', existing

        tome = data.get('tome') or line.tome or 0
        inherited_serie = self.edition_id.work_id.serie_id if self.edition_id else False
        if not serie and inherited_serie:
            serie = inherited_serie
        work = self._find_work(serie, tome, use_title)

        work_vals = {
            'titre_canonique': use_title,
            'serie_id': serie.id if serie else False,
            'tome': tome,
        }
        if not work:
            work = self.env['comic.work'].create(work_vals)
        else:
            missing_work_vals = {}
            if use_title and not work.titre_canonique:
                missing_work_vals['titre_canonique'] = use_title
            if serie and not work.serie_id:
                missing_work_vals['serie_id'] = serie.id
            if tome and not work.tome:
                missing_work_vals['tome'] = tome
            if missing_work_vals:
                work.write(missing_work_vals)

        ed_vals = {
            'work_id': work.id,
            'editeur_id': editeur.id if editeur else False,
            'nb_pages': data.get('nb_pages') or False,
            'synopsis': data.get('synopsis') or False,
        }
        if cover_b64:
            ed_vals['image_couverture'] = cover_b64
        self._parse_date_into_vals(ed_vals, 'date_parution', data.get('date_parution'))
        self._parse_date_into_vals(ed_vals, 'date_depot_legal', data.get('date_depot_legal'))
        edition = self.env['comic.edition'].create(ed_vals)

        if isbn:
            existing_isbn = self.env['comic.isbn'].search([('isbn_13', '=', isbn)], limit=1)
            if not existing_isbn:
                self.env['comic.isbn'].create({'edition_id': edition.id, 'isbn_13': isbn})

        self._sync_work_authors(work, data.get('auteurs', []))

        return 'created', edition

    def _find_work(self, serie, tome, title):
        Work = self.env['comic.work']
        if serie:
            work = Work.search([('serie_id', '=', serie.id), ('tome', '=', tome)], limit=1)
            if work:
                return work
        if serie and title:
            work = Work.search(
                [('serie_id', '=', serie.id), ('titre_canonique', '=', title)],
                limit=1,
            )
            if work:
                return work
        if title:
            return Work.search([('titre_canonique', '=', title)], limit=1)
        return Work.browse()

    def _sync_work_authors(self, work, auteurs):
        for auteur in auteurs:
            name = auteur.get('name', '').strip()
            if not name:
                continue
            partner = self.env['res.partner'].search([('name', 'ilike', name)], limit=1)
            if not partner:
                partner = self.env['res.partner'].create({'name': name})
            role = auteur.get('role', 'autre')
            already = work.auteur_line_ids.filtered(
                lambda l: l.partner_id == partner and l.role == role
            )
            if already:
                continue
            self.env['comic.work.auteur.line'].create({
                'work_id': work.id,
                'partner_id': partner.id,
                'role': role,
            })

    def _get_or_create_editeur(self, name):
        if not name:
            return None
        editeur = self.env['comic.editeur'].search([('name', 'ilike', name)], limit=1)
        return editeur or self.env['comic.editeur'].create({'name': name})

    def _get_or_create_serie(self, name, editeur):
        if not name:
            return None
        serie = self.env['comic.serie'].search([('name', 'ilike', name)], limit=1)
        if not serie:
            serie = self.env['comic.serie'].create({
                'name': name,
                'editeur_id': editeur.id if editeur else False,
            })
        elif editeur and not serie.editeur_id:
            serie.editeur_id = editeur
        return serie

    def _get_cover_b64(self, line, data):
        cover_b64 = False
        if line.cover_data:
            cover_b64 = line.cover_data.decode() if isinstance(line.cover_data, bytes) else line.cover_data
        if not cover_b64:
            cover_url = data.get('cover_url')
            if cover_url:
                try:
                    resp = requests.get(cover_url, timeout=10)
                    if resp.status_code == 200 and len(resp.content) > 100:
                        cover_b64 = base64.b64encode(resp.content).decode()
                except Exception as e:
                    _logger.warning('Datasource: téléchargement couverture échoué: %s', e)
        return cover_b64

    @staticmethod
    def _parse_date_into_vals(vals, field, date_str):
        if not date_str:
            return
        try:
            parts = str(date_str)[:10].split('-')
            vals[field] = date(int(parts[0]), int(parts[1]), int(parts[2]))
        except Exception:
            pass

    def _build_report(self, created, updated, ignored):
        lines = []
        if created:
            lines.append(f'<b>✅ {len(created)} créé(s) :</b>')
            lines += [f'<li>{r.display_name}</li>' for r in created if r]
        if updated:
            lines.append(f'<b>🔄 {len(updated)} mis à jour :</b>')
            lines += [f'<li>{r.display_name}</li>' for r in updated if r]
        if ignored:
            lines.append(f'<b>⏭️ {len(ignored)} ignoré(s) / erreur(s)</b>')
        return '<ul>' + ''.join(lines) + '</ul>'

    def action_back(self):
        self.result_ids.unlink()
        self.state = 'search'
        return self._reopen()

    def action_new_search(self):
        self.result_ids.unlink()
        self.write({'state': 'search', 'search_term': '', 'import_report': False})
        return self._reopen()

    def _reopen(self):
        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }

    def action_close_and_return(self):
        self.ensure_one()
        if self.edition_id:
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'comic.edition',
                'res_id': self.edition_id.id,
                'view_mode': 'form',
                'target': 'current',
            }
        return {'type': 'ir.actions.act_window_close'}

    def action_view_imported(self):
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'comic.edition',
            'view_mode': 'list,form',
            'target': 'current',
        }


class ComicDatasourceResultLine(models.TransientModel):
    _name = 'comic.datasource.result.line'
    _description = "Ligne de résultat de recherche BD"

    wizard_id = fields.Many2one(
        'comic.datasource.search.wizard', required=True, ondelete='cascade'
    )
    selected = fields.Boolean(string='Sélectionner', default=False)
    title = fields.Char(string='Titre')
    serie_name = fields.Char(string='Série')
    tome = fields.Integer(string='T.')
    isbn = fields.Char(string='ISBN')
    editeur = fields.Char(string='Éditeur')
    auteurs_display = fields.Char(string='Auteurs')
    date_parution = fields.Char(string='Parution')
    source = fields.Selection([
        ('google', 'Google Books'),
        ('openlibrary', 'Open Library'),
        ('bnf', 'BnF'),
        ('bdgest', 'BDGest'),
    ], string='Source')
    cover_url = fields.Char(string='URL couverture')
    cover_data = fields.Image(string='Couverture', max_width=120, max_height=160)
    is_duplicate = fields.Boolean(string='Doublon')
    existing_edition_id = fields.Many2one('comic.edition', string='Édition existante')
    title_conflict = fields.Boolean(string='Conflit de titre')
    existing_title = fields.Char(string='Titre existant en base')
    title_action = fields.Selection([
        ('keep', 'Garder le titre existant'),
        ('use_new', 'Utiliser le titre de la source'),
        ('skip', 'Ne pas importer'),
    ], string='Action sur le titre', default='keep')
    result_data = fields.Text()
