import logging

from odoo import _, models

_logger = logging.getLogger(__name__)


class ComicSerie(models.Model):
    _inherit = "comic.serie"

    def action_update_albums_from_datasource(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Mise à jour depuis les sources de données"),
            "res_model": "comic.serie.update.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {"default_serie_id": self.id},
        }

    def action_search_missing_volumes(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Tomes manquants — ") + self.name,
            "res_model": "comic.serie.missing.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {"default_serie_id": self.id},
        }

    def _cron_check_missing_volumes(self):
        """Cron hebdomadaire : détecte et ajoute en wishlist les tomes manquants
        pour toutes les séries marquées «À suivre»."""
        series = self.search([("a_suivre", "=", True)])
        if not series:
            _logger.info("Cron tomes manquants : aucune série à suivre.")
            return

        _logger.info("Cron tomes manquants : %d série(s) à traiter.", len(series))
        Wizard = self.env["comic.serie.missing.wizard"]
        total_added = 0

        for serie in series:
            try:
                wizard = Wizard.create({"serie_id": serie.id})
                wizard.action_search()
                if not wizard.line_ids:
                    _logger.info("  [%s] aucun tome manquant détecté.", serie.name)
                    continue
                # Cron : on n'ajoute que les tomes avec ISBN confirmé par une source.
                # Les lignes sans ISBN (isbn_unverified ou source "expected") sont
                # écartées pour éviter les doublons et les faux positifs.
                wizard.line_ids.filtered(
                    lambda line: not line.isbn or line.isbn_unverified or line.source == "expected"
                ).write({"selected": False})
                nb_lines = len(wizard.line_ids.filtered("selected"))
                if not nb_lines:
                    _logger.info("  [%s] aucun tome avec ISBN confirmé.", serie.name)
                    continue
                wizard.action_add_to_wishlist()
                _logger.info("  [%s] %d tome(s) ajouté(s) à la wishlist.", serie.name, nb_lines)
                total_added += nb_lines
            except Exception:
                _logger.exception('Cron tomes manquants : erreur sur la série "%s".', serie.name)

        _logger.info("Cron tomes manquants terminé : %d tome(s) ajouté(s) au total.", total_added)
