import logging

from odoo import models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class ComicAlbumBdgest(models.Model):
    _inherit = 'comic.album'

    def action_enrich_from_bdgest(self):
        """Ouvre le wizard BDGest pour enrichir cet album."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Enrichir depuis BDGest',
            'res_model': 'comic.bdgest.enrich.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_album_id': self.id},
        }

    def action_batch_enrich_from_bdgest(self):
        """Enrichit les albums sélectionnés depuis BDGest par ISBN."""
        from odoo.addons.comic_bdgest.scraper.bdgest_scraper import (
            BdgestError, BdgestScraper)

        albums_with_isbn = self.filtered('isbn')
        if not albums_with_isbn:
            raise UserError(
                "Aucun des albums sélectionnés n'a d'ISBN renseigné."
            )

        scraper = BdgestScraper(request_delay=2.0)
        done, skipped, errors = 0, 0, []

        for album in albums_with_isbn:
            try:
                detail = scraper.search_by_isbn(album.isbn)
                if not detail:
                    skipped += 1
                    continue
                album._bdgest_apply_detail(detail, scraper)
                done += 1
            except BdgestError as exc:
                errors.append(f"{album.name} : {exc}")
                _logger.warning("BDGest erreur album %d : %s", album.id, exc)

        parts = [f"{done} enrichi(s)"]
        if skipped:
            parts.append(f"{skipped} non trouvé(s)")
        if errors:
            parts.append(f"{len(errors)} erreur(s)")

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Enrichissement BDGest terminé',
                'message': ' · '.join(parts),
                'type': 'warning' if errors else 'success',
                'sticky': bool(errors),
            },
        }

    def _bdgest_import_from_id(self, bdgest_album_id,
                                bdgest_serie_id=None, serie_name=None,
                                scraper=None):
        """Récupère la fiche BDGest et l'applique à cet album."""
        from odoo.addons.comic_bdgest.scraper.bdgest_scraper import (
            BdgestError, BdgestScraper)
        if scraper is None:
            scraper = BdgestScraper(request_delay=2.0)
        try:
            detail = scraper.get_album_detail(bdgest_album_id)
        except BdgestError as exc:
            raise UserError(str(exc)) from exc
        detail.setdefault('bdgest_serie_id', bdgest_serie_id)
        detail.setdefault('serie_name', serie_name)
        self._bdgest_apply_detail(detail, scraper)

    def _bdgest_apply_detail(self, detail, scraper):
        """Mappe un dict BDGest sur les champs de l'album et sauvegarde."""
        vals = {}

        for odoo_field, key in [
            ('name', 'titre'),
            ('tome', 'tome'),
            ('isbn', 'isbn'),
            ('date_parution', 'date_parution'),
            ('date_depot_legal', 'date_depot_legal'),
            ('nb_pages', 'nb_pages'),
            ('synopsis', 'synopsis'),
            ('bdgest_album_id', 'bdgest_album_id'),
        ]:
            if detail.get(key):
                vals[odoo_field] = detail[key]

        if detail.get('couverture_url'):
            img = scraper.download_image_b64(detail['couverture_url'])
            if img:
                vals['image_couverture'] = img

        isbn = detail.get('isbn') or self.isbn
        if isbn:
            vals['url_club_be'] = f"https://www.club.be/search?q={isbn}"
            vals['url_amazon_be'] = f"https://www.amazon.com.be/s?k={isbn}"

        if detail.get('editeur'):
            editeur = self.env['comic.editeur'].search(
                [('name', 'ilike', detail['editeur'])], limit=1)
            if not editeur:
                editeur = self.env['comic.editeur'].create(
                    {'name': detail['editeur']})
            vals['editeur_id'] = editeur.id

        bdgest_serie_id = detail.get('bdgest_serie_id')
        serie_name = detail.get('serie_name')
        if bdgest_serie_id:
            serie = self.env['comic.serie'].search(
                [('bdgest_id', '=', bdgest_serie_id)], limit=1)
            if not serie and serie_name:
                serie = self.env['comic.serie'].create({
                    'name': serie_name,
                    'bdgest_id': bdgest_serie_id,
                })
            if serie:
                vals['serie_id'] = serie.id

        self.write(vals)

        if detail.get('auteurs'):
            self.auteur_line_ids.unlink()
            lines = []
            for a in detail['auteurs']:
                partner = self.env['res.partner'].search(
                    [('name', 'ilike', a['nom'])], limit=1)
                if not partner:
                    partner = self.env['res.partner'].create(
                        {'name': a['nom']})
                lines.append({
                    'album_id': self.id,
                    'partner_id': partner.id,
                    'role': a.get('role', 'autre'),
                })
            self.env['comic.album.auteur.line'].create(lines)
