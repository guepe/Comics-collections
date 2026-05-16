import base64
import json
import logging
import re
import requests

from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

ISBN_RE = re.compile(r'^[\d\-X]{10,17}$')


def _clean_isbn(term):
    """Retourne l'ISBN sans tirets/espaces si c'est un ISBN valide, sinon None."""
    cleaned = re.sub(r'[^0-9X]', '', (term or '').upper())
    return cleaned if len(cleaned) in (10, 13) else None


def _normalize_isbn(isbn):
    """
    Normalise un ISBN : supprime tirets/espaces et convertit ISBN-10 → EAN-13.
    Retourne une chaîne de 13 chiffres ou chaîne vide.
    """
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
    album_id = fields.Many2one('comic.album', string='Album à enrichir')
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

    # ── Recherche ─────────────────────────────────────────────────────────────

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

        # Marque les doublons et détecte les conflits de titre
        for vals in lines:
            if vals.get('isbn'):
                existing = self._find_album_by_isbn(vals['isbn'])
                if existing:
                    vals['is_duplicate'] = True
                    vals['existing_album_id'] = existing.id
                    # Conflit de titre : titres différents (ignore casse et espaces)
                    new_t = (vals.get('title') or '').lower().strip()
                    old_t = (existing.name or '').lower().strip()
                    if new_t and old_t and new_t != old_t:
                        vals['title_conflict'] = True
                        vals['existing_title'] = existing.name
                        vals['title_action'] = 'keep'  # par défaut : conserver le titre existant

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

    def _find_album_by_isbn(self, isbn):
        """Cherche un album par ISBN en ignorant tirets et espaces."""
        clean = _normalize_isbn(isbn)
        if not clean:
            return self.env['comic.album'].browse()
        # Tente d'abord une correspondance exacte (avec ou sans tirets)
        existing = self.env['comic.album'].search(
            ['|', ('isbn', '=', isbn), ('isbn', '=', clean)], limit=1
        )
        if existing:
            return existing
        # Fallback : normalise tous les albums ayant un ISBN proche
        candidates = self.env['comic.album'].search([
            ('isbn', 'like', clean[:7])
        ])
        return candidates.filtered(
            lambda a: _normalize_isbn(a.isbn) == clean
        )[:1]

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
                status, album = self._import_line(line)
                if status == 'created':
                    created.append(album)
                elif status == 'updated':
                    updated.append(album)
                else:
                    ignored.append(album)
            except Exception as e:
                _logger.error('Datasource import error on "%s": %s', line.title, e)
                ignored.append(None)

        report = self._build_report(created, updated, ignored)
        self.import_report = report
        self.state = 'done'
        return self._reopen()

    def _import_line(self, line):
        data = json.loads(line.result_data or '{}')
        # ISBN normalisé (sans tirets) pour stockage cohérent
        raw_isbn = data.get('isbn') or line.isbn
        isbn = _normalize_isbn(raw_isbn) or raw_isbn or False

        # Doublon : mise à jour ou abandon
        existing = None
        if isbn:
            existing = self._find_album_by_isbn(isbn)

        # Éditeur
        editeur = None
        editeur_name = data.get('editeur') or line.editeur
        if editeur_name:
            editeur = self.env['comic.editeur'].search(
                [('name', 'ilike', editeur_name)], limit=1
            )
            if not editeur:
                editeur = self.env['comic.editeur'].create({'name': editeur_name})

        # Série
        serie = None
        serie_name = data.get('serie_name') or line.serie_name
        if serie_name:
            serie = self.env['comic.serie'].search(
                [('name', 'ilike', serie_name)], limit=1
            )
            if not serie:
                serie = self.env['comic.serie'].create({
                    'name': serie_name,
                    'editeur_id': editeur.id if editeur else False,
                })
            elif editeur and not serie.editeur_id:
                serie.editeur_id = editeur

        # Couverture : utilise la miniature déjà téléchargée sur la ligne,
        # sinon télécharge la version HD depuis cover_url
        cover_b64 = False
        if line.cover_data:
            # cover_data est déjà en base64 (fields.Image le stocke ainsi)
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

        # Conflit de titre : applique le choix de l'utilisateur
        if line.title_conflict:
            if line.title_action == 'skip':
                return 'ignored', existing or self.env['comic.album'].browse()
            use_title = (
                existing.name if line.title_action == 'keep'
                else (data.get('title') or line.title or '')
            )
        else:
            use_title = data.get('title') or line.title or ''

        vals = {
            'name': use_title,
            'serie_id': serie.id if serie else False,
            'tome': data.get('tome') or line.tome or 0,
            'isbn': isbn or False,
            'nb_pages': data.get('nb_pages') or False,
            'synopsis': data.get('synopsis') or False,
        }
        # Si l'album est lié à un album existant dans le wizard, hérite de sa série
        if not vals['serie_id'] and self.album_id and self.album_id.serie_id:
            vals['serie_id'] = self.album_id.serie_id.id
        if cover_b64:
            vals['image_couverture'] = cover_b64
        if data.get('date_parution'):
            # Convertit str YYYY-MM-DD en date
            try:
                from datetime import date
                parts = data['date_parution'][:10].split('-')
                vals['date_parution'] = date(int(parts[0]), int(parts[1]), int(parts[2]))
            except Exception:
                pass
        if data.get('date_depot_legal'):
            try:
                from datetime import date
                parts = data['date_depot_legal'][:10].split('-')
                vals['date_depot_legal'] = date(int(parts[0]), int(parts[1]), int(parts[2]))
            except Exception:
                pass

        if existing:
            existing.write(vals)
            album = existing
            status = 'updated'
        else:
            album = self.env['comic.album'].create(vals)
            status = 'created'

        # Auteurs
        for auteur in data.get('auteurs', []):
            name = auteur.get('name', '').strip()
            if not name:
                continue
            partner = self.env['res.partner'].search([('name', 'ilike', name)], limit=1)
            if not partner:
                partner = self.env['res.partner'].create({'name': name})
            already = album.auteur_line_ids.filtered(lambda l: l.partner_id == partner)
            if not already:
                self.env['comic.album.auteur.line'].create({
                    'album_id': album.id,
                    'partner_id': partner.id,
                    'role': auteur.get('role', 'autre'),
                })

        return status, album

    def _build_report(self, created, updated, ignored):
        lines = []
        if created:
            lines.append(f'<b>✅ {len(created)} créé(s) :</b>')
            lines += [f'<li>{a.name}</li>' for a in created if a]
        if updated:
            lines.append(f'<b>🔄 {len(updated)} mis à jour :</b>')
            lines += [f'<li>{a.name}</li>' for a in updated if a]
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
        """Ferme le wizard et retourne à l'album source si disponible."""
        self.ensure_one()
        if self.album_id:
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'comic.album',
                'res_id': self.album_id.id,
                'view_mode': 'form',
                'target': 'current',
            }
        return {'type': 'ir.actions.act_window_close'}

    def action_view_imported(self):
        """Ouvre la liste des albums après import."""
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'comic.album',
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
    existing_album_id = fields.Many2one('comic.album', string='Album existant')
    title_conflict = fields.Boolean(string='Conflit de titre')
    existing_title = fields.Char(string='Titre existant en base')
    title_action = fields.Selection([
        ('keep', 'Garder le titre existant'),
        ('use_new', 'Utiliser le titre de la source'),
        ('skip', 'Ne pas importer'),
    ], string='Action sur le titre', default='keep')
    result_data = fields.Text()
