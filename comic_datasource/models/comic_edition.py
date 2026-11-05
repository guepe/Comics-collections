import base64
import logging
import re
from datetime import date

import requests

from odoo import fields, models
from odoo.addons.comics_collections.utils.normalize import normalize_title

_logger = logging.getLogger(__name__)


def _normalize_isbn(isbn):
    raw = re.sub(r"[\-\s]", "", isbn or "")
    if len(raw) == 10 and raw[:9].isdigit():
        base = "978" + raw[:9]
        total = sum(int(d) * (1 if i % 2 == 0 else 3) for i, d in enumerate(base))
        check = (10 - total % 10) % 10
        return base + str(check)
    return raw


def _find_or_create_author(env, name):
    """Exact (case-insensitive) name match, preferring partners already credited as
    comic authors — avoids "Morris" matching "Morrison" or a customer homonym."""
    Partner = env["res.partner"]
    partner = Partner.search([("name", "=ilike", name), ("auteur_work_line_ids", "!=", False)], limit=1)
    if not partner:
        partner = Partner.search([("name", "=ilike", name), ("is_company", "=", False)], limit=1)
    return partner or Partner.create({"name": name})


def _best_title_match(results, work):
    """Strict title fallback: return the first result with an ISBN whose normalized
    title equals the work's, and whose serie / tome (when both sides know them) match.
    Returns None rather than guessing — a wrong match would attach a foreign ISBN."""
    work_title = normalize_title(work.titre_canonique)
    work_serie = normalize_title(work.serie_id.name) if work.serie_id else ""
    if not work_title:
        return None
    for r in results:
        if not r.isbn or normalize_title(r.title) != work_title:
            continue
        if work.tome and r.tome and int(r.tome) != work.tome:
            continue
        if work_serie and r.serie_name and normalize_title(r.serie_name) != work_serie:
            continue
        return r
    return None


class ComicEdition(models.Model):
    _inherit = "comic.edition"

    datasource_last_try = fields.Datetime(
        string="Dernier enrichissement tenté",
        readonly=True,
        copy=False,
        help="Date de la dernière tentative d'enrichissement automatique (cron). "
        "Sert à faire tourner le lot : les éditions jamais tentées passent en premier.",
    )

    def _apply_datasource_data(self, data):
        """Updates self (a comic.edition) with a normalized dict from the aggregator."""
        self.ensure_one()
        vals = {}

        # Ne remplit que les champs vides : ne jamais écraser une saisie utilisateur
        if data.get("synopsis") and not self.synopsis:
            vals["synopsis"] = data["synopsis"]
        if data.get("nb_pages") and not self.nb_pages:
            vals["nb_pages"] = data["nb_pages"]

        for field, key in [("date_parution", "date_parution"), ("date_depot_legal", "date_depot_legal")]:
            if data.get(key) and not getattr(self, field):
                try:
                    parts = str(data[key])[:10].split("-")
                    vals[field] = date(int(parts[0]), int(parts[1]), int(parts[2]))
                except Exception:
                    _logger.debug("Invalid date format for field %s: %s", field, data.get(key))

        isbn_raw = data.get("isbn")
        if isbn_raw:
            isbn_norm = _normalize_isbn(isbn_raw) or isbn_raw
            existing_isbn = self.env["comic.isbn"].search([("isbn_13", "=", isbn_norm)], limit=1)
            if isbn_norm and not existing_isbn:
                self.env["comic.isbn"].create({"edition_id": self.id, "isbn_13": isbn_norm})

        cover_url = data.get("cover_url") or data.get("cover_url_small")
        if cover_url and not self.image_couverture:
            try:
                resp = requests.get(cover_url, timeout=10)
                if resp.status_code == 200 and len(resp.content) > 100:
                    vals["image_couverture"] = base64.b64encode(resp.content).decode()
            except Exception as e:
                _logger.warning('Cover download failed for "%s": %s', self.display_name, e)

        if vals:
            self.write(vals)

        work = self.work_id
        for auteur in data.get("auteurs", []):
            name = (auteur.get("name") or "").strip()
            if not name:
                continue
            partner = _find_or_create_author(self.env, name)
            role = auteur.get("role", "autre")
            if not work.auteur_line_ids.filtered(
                lambda line, p=partner, r=role: line.partner_id == p and line.role == r
            ):
                self.env["comic.work.auteur.line"].create(
                    {
                        "work_id": work.id,
                        "partner_id": partner.id,
                        "role": role,
                    }
                )

    def _cron_update_editions(self, batch_size=30):
        """Cron: enriches incomplete editions (missing synopsis, cover, or isbn)."""
        from ..aggregator import ComicDataAggregator

        domain = [
            "|",
            "|",
            ("synopsis", "in", [False, ""]),
            ("image_couverture", "=", False),
            ("isbn_ids", "=", False),
        ]
        editions = self.search(domain, limit=batch_size, order="datasource_last_try asc nulls first, id asc")
        if not editions:
            _logger.info("Cron éditions : aucune édition incomplète.")
            return

        _logger.info("Cron éditions : %d édition(s) à enrichir.", len(editions))
        aggregator = ComicDataAggregator(env=self.env)
        updated = 0

        from ..sources.google_books import GoogleBooksQuotaError

        for edition in editions:
            # Marque la tentative avant l'appel : une édition introuvable laisse
            # sa place aux suivantes au prochain passage.
            edition.datasource_last_try = fields.Datetime.now()
            try:
                agg = None
                isbn = edition._get_primary_isbn()
                if isbn:
                    agg = aggregator.search(isbn=isbn)
                elif edition.work_id.titre_canonique:
                    results = aggregator.search_list(title=edition.work_id.titre_canonique)
                    best = _best_title_match(results or [], edition.work_id)
                    if best:
                        agg = aggregator.search(isbn=best.isbn)

                if not agg or not agg.data:
                    continue

                edition._apply_datasource_data(agg.data)
                updated += 1
            except GoogleBooksQuotaError:
                # Coupe-circuit : inutile de continuer à solliciter Google
                _logger.warning("Cron éditions : quota Google Books atteint — arrêt du lot.")
                break
            except Exception:
                _logger.exception('Cron édition : erreur sur "%s"', edition.display_name)

        _logger.info("Cron éditions terminé : %d/%d enrichie(s).", updated, len(editions))

    def _cron_update_albums(self, batch_size=30):
        """Backward-compatible entrypoint for older cron records."""
        return self._cron_update_editions(batch_size=batch_size)

    def action_search_datasource(self):
        """Opens the multi-source search wizard pre-filled with this edition's ISBN or title."""
        self.ensure_one()
        ctx = {"default_edition_id": self.id}
        isbn = self._get_primary_isbn()
        if isbn:
            ctx["default_search_term"] = isbn
        elif self.work_id.titre_canonique:
            ctx["default_search_term"] = self.work_id.titre_canonique
        return {
            "type": "ir.actions.act_window",
            "res_model": "comic.datasource.search.wizard",
            "view_mode": "form",
            "target": "new",
            "context": ctx,
        }
