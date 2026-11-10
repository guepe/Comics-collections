import base64
import logging
from datetime import date

import requests

from odoo import _, fields, models
from odoo.exceptions import UserError
from odoo.addons.comics_collections.utils.normalize import normalize_title
from ..sources.base import normalize_isbn as _normalize_isbn


_logger = logging.getLogger(__name__)


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
                agg = edition._fetch_datasource(aggregator)
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

    def _fetch_datasource(self, aggregator):
        """Résultat agrégé pour l'édition : par ISBN, sinon par titre strict (``_best_title_match``)."""
        self.ensure_one()
        isbn = self._get_primary_isbn()
        if isbn:
            return aggregator.search(isbn=isbn)
        if self.work_id.titre_canonique:
            results = aggregator.search_list(title=self.work_id.titre_canonique)
            best = _best_title_match(results or [], self.work_id)
            if best:
                return aggregator.search(isbn=best.isbn)
        return None

    # Champs dont on signale le remplissage après « Compléter les infos »
    _COMPLETE_FIELDS = {
        "image_couverture": "couverture",
        "synopsis": "synopsis",
        "nb_pages": "nombre de pages",
        "date_parution": "date de parution",
        "date_depot_legal": "dépôt légal",
        "isbn_ids": "ISBN",
    }

    def action_complete_from_sources(self):
        """Va chercher sur les sources les infos manquantes (champs vides seulement) et dit ce qui a été ajouté."""
        self.ensure_one()
        from ..aggregator import ComicDataAggregator
        from ..sources.google_books import GoogleBooksQuotaError

        before = {f: bool(self[f]) for f in self._COMPLETE_FIELDS}
        nb_auteurs = len(self.work_id.auteur_line_ids)
        try:
            agg = self._fetch_datasource(ComicDataAggregator(env=self.env))
        except GoogleBooksQuotaError as exc:
            raise UserError(_("Quota Google Books atteint : réessayez demain ou ajoutez une clé API.")) from exc
        if agg and agg.data:
            self._apply_datasource_data(agg.data)
        self.datasource_last_try = fields.Datetime.now()
        added = [label for f, label in self._COMPLETE_FIELDS.items() if self[f] and not before[f]]
        if len(self.work_id.auteur_line_ids) > nb_auteurs:
            added.append(_("auteurs"))
        if added:
            message, kind = _("Infos ajoutées : %s.", ", ".join(added)), "success"
        elif agg and agg.data:
            message, kind = _("Album trouvé sur les sources, mais rien de nouveau à ajouter."), "info"
        else:
            message, kind = _("Album introuvable sur les sources (ISBN ou titre)."), "warning"
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "message": message,
                "type": kind,
                "sticky": False,
                "next": {"type": "ir.actions.client", "tag": "soft_reload"},
            },
        }

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
