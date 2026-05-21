import logging

from odoo import api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class ComicBdgestEnrichWizard(models.TransientModel):
    _name = 'comic.bdgest.enrich.wizard'
    _description = 'Enrichissement depuis BDGest'

    edition_id = fields.Many2one('comic.edition', readonly=True)
    edition_display = fields.Char(compute='_compute_edition_display')
    search_type = fields.Selection([
        ('isbn', 'Par ISBN'),
        ('titre', 'Par titre'),
    ], default='isbn', required=True)
    search_term = fields.Char(string='Terme de recherche', required=True)
    state = fields.Selection([
        ('search', 'Recherche'),
        ('results', 'Résultats'),
    ], default='search')
    result_ids = fields.One2many(
        'comic.bdgest.result.line', 'wizard_id', string='Résultats')

    @api.depends('edition_id')
    def _compute_edition_display(self):
        for rec in self:
            e = rec.edition_id
            if not e:
                rec.edition_display = ''
                continue
            parts = []
            if e.work_id.serie_id:
                parts.append(e.work_id.serie_id.name)
            if e.work_id.tome:
                parts.append(f'T{e.work_id.tome}')
            if e.work_id.titre_canonique:
                parts.append(e.work_id.titre_canonique)
            rec.edition_display = ' – '.join(parts)

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        edition_id = self.env.context.get('default_edition_id')
        if edition_id:
            edition = self.env['comic.edition'].browse(edition_id)
            isbn = edition._get_primary_isbn()
            if isbn:
                res.update({'search_type': 'isbn', 'search_term': isbn})
            elif edition.work_id.titre_canonique:
                res.update({'search_type': 'titre', 'search_term': edition.work_id.titre_canonique})
        return res

    def action_search(self):
        self.ensure_one()
        from odoo.addons.comic_bdgest.scraper.bdgest_scraper import (
            BdgestError, BdgestScraper)
        try:
            scraper = BdgestScraper(request_delay=2.0)
            if self.search_type == 'isbn':
                detail = scraper.search_by_isbn(self.search_term)
                if not detail:
                    raise UserError("Aucun album trouvé pour cet ISBN sur BDGest.")
                self.edition_id._bdgest_apply_detail(detail, scraper)
                return {'type': 'ir.actions.act_window_close'}
            else:
                raw = scraper.search_by_title(self.search_term)[:20]
        except BdgestError as exc:
            raise UserError(str(exc)) from exc

        if not raw:
            raise UserError("Aucun résultat trouvé. Essayez une autre recherche.")

        self.result_ids.unlink()
        self.env['comic.bdgest.result.line'].create([{
            'wizard_id': self.id,
            'bdgest_album_id': r.get('bdgest_album_id') or 0,
            'bdgest_serie_id': r.get('bdgest_serie_id') or 0,
            'serie_name': r.get('serie_name', ''),
            'tome': r.get('tome') or 0,
            'titre': r.get('titre', ''),
            'auteur': ', '.join(a['nom'] for a in r.get('auteurs', [])),
            'editeur': r.get('editeur', ''),
            'couverture_url': r.get('couverture_url', ''),
        } for r in raw])
        self.state = 'results'
        return self._reopen()

    def action_import(self):
        self.ensure_one()
        selected = self.result_ids.filtered('selected')
        if not selected:
            raise UserError("Sélectionnez un résultat à importer.")
        if len(selected) > 1:
            raise UserError("Sélectionnez un seul résultat.")
        line = selected[0]
        self.edition_id._bdgest_import_from_id(
            line.bdgest_album_id,
            bdgest_serie_id=line.bdgest_serie_id,
            serie_name=line.serie_name,
        )
        return {'type': 'ir.actions.act_window_close'}

    def action_back(self):
        self.ensure_one()
        self.state = 'search'
        return self._reopen()

    def _reopen(self):
        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
            'context': self.env.context,
        }


class ComicBdgestResultLine(models.TransientModel):
    _name = 'comic.bdgest.result.line'
    _description = 'Résultat de recherche BDGest'

    wizard_id = fields.Many2one(
        'comic.bdgest.enrich.wizard', ondelete='cascade', required=True)
    selected = fields.Boolean(default=False)
    bdgest_album_id = fields.Integer(string='ID BDGest')
    bdgest_serie_id = fields.Integer()
    serie_name = fields.Char(string='Série')
    tome = fields.Integer(string='T.')
    titre = fields.Char(string='Titre')
    auteur = fields.Char(string='Auteur(s)')
    editeur = fields.Char(string='Éditeur')
    couverture_url = fields.Char()
