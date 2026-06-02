import logging

from odoo import _, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class ComicEdition(models.Model):
    _inherit = "comic.edition"

    def action_enrich_from_bdgest(self):
        """Opens the BDGest wizard to enrich this edition."""
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "Enrichir depuis BDGest",
            "res_model": "comic.bdgest.enrich.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {"default_edition_id": self.id},
        }

    def action_batch_enrich_from_bdgest(self):
        """Enriches selected editions from BDGest by ISBN."""
        from ..scraper.bdgest_scraper import BdgestError, BdgestScraper

        editions_with_isbn = self.filtered(lambda e: e._get_primary_isbn())
        if not editions_with_isbn:
            raise UserError(_("Aucune des éditions sélectionnées n'a d'ISBN renseigné."))

        scraper = BdgestScraper(request_delay=2.0)
        done, skipped, errors = 0, 0, []

        for edition in editions_with_isbn:
            try:
                isbn = edition._get_primary_isbn()
                detail = scraper.search_by_isbn(isbn)
                if not detail:
                    skipped += 1
                    continue
                edition._bdgest_apply_detail(detail, scraper)
                done += 1
            except BdgestError as exc:
                errors.append(f"{edition.display_name} : {exc}")
                _logger.warning("BDGest erreur édition %d : %s", edition.id, exc)

        parts = [f"{done} enrichi(s)"]
        if skipped:
            parts.append(f"{skipped} non trouvé(s)")
        if errors:
            parts.append(f"{len(errors)} erreur(s)")

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": "Enrichissement BDGest terminé",
                "message": " · ".join(parts),
                "type": "warning" if errors else "success",
                "sticky": bool(errors),
            },
        }

    def _bdgest_import_from_id(self, bdgest_album_id, bdgest_serie_id=None, serie_name=None, scraper=None):
        """Fetches a BDGest album and applies it to this edition."""
        from ..scraper.bdgest_scraper import BdgestError, BdgestScraper

        if scraper is None:
            scraper = BdgestScraper(request_delay=2.0)
        try:
            detail = scraper.get_album_detail(bdgest_album_id)
        except BdgestError as exc:
            raise UserError(str(exc)) from exc
        detail.setdefault("bdgest_serie_id", bdgest_serie_id)
        detail.setdefault("serie_name", serie_name)
        self._bdgest_apply_detail(detail, scraper)

    def _bdgest_apply_detail(self, detail, scraper):
        """Maps a BDGest dict onto comic.edition (and its work) and saves."""
        work = self.work_id
        work_vals = {}
        ed_vals = {}

        if detail.get("titre"):
            work_vals["titre_canonique"] = detail["titre"]
        if detail.get("tome"):
            work_vals["tome"] = detail["tome"]

        for field in ("date_parution", "date_depot_legal", "nb_pages", "synopsis"):
            if detail.get(field):
                ed_vals[field] = detail[field]

        if detail.get("couverture_url"):
            img = scraper.download_image_b64(detail["couverture_url"])
            if img:
                ed_vals["image_couverture"] = img

        isbn = detail.get("isbn") or self._get_primary_isbn()
        if isbn:
            from re import sub

            isbn_clean = sub(r"[\-\s]", "", isbn)
            if isbn_clean and not self.isbn_ids.filtered(lambda i: i.isbn_13 == isbn_clean):
                self.env["comic.isbn"].create({"edition_id": self.id, "isbn_13": isbn_clean})
            ed_vals["url_club_be"] = (
                f"https://www.librairieclub.be/c/search?filter=search({isbn_clean})&page=1&page_size=24&sort=RelevanceClub&sort_type=desc"  # noqa: E501
            )
            ed_vals["url_amazon_be"] = f"https://www.amazon.com.be/s?k={isbn_clean}"

        if detail.get("editeur"):
            editeur = self.env["comic.editeur"].search([("name", "ilike", detail["editeur"])], limit=1)
            if not editeur:
                editeur = self.env["comic.editeur"].create({"name": detail["editeur"]})
            ed_vals["editeur_id"] = editeur.id

        bdgest_serie_id = detail.get("bdgest_serie_id")
        serie_name = detail.get("serie_name")
        if bdgest_serie_id:
            serie = self.env["comic.serie"].search([("bdgest_id", "=", bdgest_serie_id)], limit=1)
            if not serie and serie_name:
                serie = self.env["comic.serie"].create(
                    {
                        "name": serie_name,
                        "bdgest_id": bdgest_serie_id,
                    }
                )
            if serie:
                work_vals["serie_id"] = serie.id

        if work_vals:
            work.write(work_vals)
        if ed_vals:
            self.write(ed_vals)

        if detail.get("auteurs"):
            work.auteur_line_ids.unlink()
            lines = []
            for a in detail["auteurs"]:
                partner = self.env["res.partner"].search([("name", "ilike", a["nom"])], limit=1)
                if not partner:
                    partner = self.env["res.partner"].create({"name": a["nom"]})
                lines.append(
                    {
                        "work_id": work.id,
                        "partner_id": partner.id,
                        "role": a.get("role", "autre"),
                    }
                )
            self.env["comic.work.auteur.line"].create(lines)
