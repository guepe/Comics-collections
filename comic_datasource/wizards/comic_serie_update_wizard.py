import logging

from odoo import api, fields, models

from ..models.comic_edition import _best_title_match
from ..sources.base import normalize_isbn as _normalize_isbn


_logger = logging.getLogger(__name__)


class ComicSerieUpdateWizard(models.TransientModel):
    _name = "comic.serie.update.wizard"
    _description = "Batch update of a series' albums from data sources"

    serie_id = fields.Many2one("comic.serie", string="Series", required=True, readonly=True)
    nb_albums = fields.Integer(compute="_compute_nb_albums", string="Albums to process")
    state = fields.Selection(
        [("confirm", "Confirmation"), ("done", "Done")],
        default="confirm",
    )
    import_report = fields.Html(string="Report", readonly=True)

    @api.depends("serie_id.work_ids")
    def _compute_nb_albums(self):
        for rec in self:
            rec.nb_albums = len(rec.serie_id.work_ids)

    def action_run(self):
        self.ensure_one()
        from ..aggregator import ComicDataAggregator

        from ..sources.google_books import GoogleBooksQuotaError

        aggregator = ComicDataAggregator(env=self.env)
        updated, skipped, errors = [], [], []
        quota_hit = False

        for work in self.serie_id.work_ids.sorted("tome"):
            try:
                agg = None
                edition = work.edition_ids[:1]
                isbn = edition._get_primary_isbn() if edition else False

                if isbn:
                    clean = _normalize_isbn(isbn)
                    agg = aggregator.search(isbn=clean or isbn)
                elif work.titre_canonique:
                    results = aggregator.search_list(title=work.titre_canonique)
                    best = _best_title_match(results or [], work)
                    if best:
                        agg = aggregator.search(isbn=best.isbn)

                if not agg or not agg.data:
                    skipped.append(work)
                    continue

                if not edition:
                    skipped.append(work)
                    continue
                edition._apply_datasource_data(agg.data)
                updated.append(work)

            except GoogleBooksQuotaError:
                quota_hit = True
                break
            except Exception as e:
                _logger.error('Serie update error on "%s": %s', work.titre_canonique, e)
                errors.append(work)

        report = self._build_report(updated, skipped, errors)
        if quota_hit:
            report = (
                "<p><b>%s</b> %s</p>"
                % (
                    self.env._("⚠️ Google Books quota reached: update interrupted."),
                    self.env._("Try again later or add an API key in the settings."),
                )
                + report
            )
        self.import_report = report
        self.state = "done"
        return self._reopen()

    def _build_report(self, updated, skipped, errors):
        _ = self.env._
        lines = []
        if updated:
            lines.append("<b>%s</b><ul>" % _("✅ %(n)s updated:", n=len(updated)))
            lines += [f"<li>{w.titre_canonique}</li>" for w in updated]
            lines.append("</ul>")
        if skipped:
            lines.append("<b>%s</b><ul>" % _("⏭️ %(n)s skipped (not found or already up to date):", n=len(skipped)))
            lines += [f"<li>{w.titre_canonique}</li>" for w in skipped]
            lines.append("</ul>")
        if errors:
            lines.append("<b>%s</b><ul>" % _("❌ %(n)s error(s):", n=len(errors)))
            lines += [f"<li>{w.titre_canonique}</li>" for w in errors]
            lines.append("</ul>")
        return "".join(lines) or "<p>%s</p>" % _("No album to process.")

    def action_close_and_return(self):
        """Ferme le wizard et retourne à la fiche série."""
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "res_model": "comic.serie",
            "res_id": self.serie_id.id,
            "view_mode": "form",
            "target": "current",
        }

    def _reopen(self):
        return {
            "type": "ir.actions.act_window",
            "res_model": self._name,
            "res_id": self.id,
            "view_mode": "form",
            "target": "new",
        }
