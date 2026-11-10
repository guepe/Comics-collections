import logging

from odoo import fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class ComicSerie(models.Model):
    _inherit = "comic.serie"

    nb_tomes_parus = fields.Integer(
        string="Number of volumes released",
        tracking=True,
        help="Number of volumes published by the publisher (manual entry). Used as the reference for "
        "missing volumes detection. Leave at 0 to rely on the highest known volume number "
        "(albums in the database and data source results).",
    )
    missing_last_check = fields.Datetime(
        string="Last missing volumes detection",
        readonly=True,
        copy=False,
        help="Date of the last search for missing volumes (manual or scheduled).",
    )

    def action_update_albums_from_datasource(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": self.env._("Update from data sources"),
            "res_model": "comic.serie.update.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {"default_serie_id": self.id},
        }

    def action_search_missing_volumes(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": self.env._("Missing volumes — %(serie)s", serie=self.name),
            "res_model": "comic.serie.missing.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {"default_serie_id": self.id},
        }

    def _cron_check_missing_volumes(self, batch_size=20):
        """Cron hebdomadaire : détecte et ajoute au catalogue les tomes manquants
        des séries marquées «À suivre».

        Traite au plus ``batch_size`` séries par passage, en commençant par celles
        dont la dernière vérification (``missing_last_check``) est la plus ancienne
        (jamais vérifiées en premier).
        """
        series = self.search(
            [("suivi_user_ids", "!=", False)],  # suivie par au moins un utilisateur
            order="missing_last_check asc nulls first, id asc",
            limit=batch_size,
        )
        if not series:
            _logger.info("Cron tomes manquants : aucune série à suivre.")
            return

        _logger.info("Cron tomes manquants : %d série(s) à traiter.", len(series))
        Wizard = self.env["comic.serie.missing.wizard"]
        total_added = 0

        for serie in series:
            try:
                with self.env.cr.savepoint():
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
                    # Pas de wishlist en tâche planifiée : l'utilisateur du cron n'est pas
                    # un lecteur, on complète seulement le catalogue.
                    wizard._add_selected_lines(to_wishlist=False)
                    _logger.info("  [%s] %d tome(s) ajouté(s) au catalogue.", serie.name, nb_lines)
                    total_added += nb_lines
            except UserError as e:
                # Quota Google Books atteint : inutile de poursuivre, les séries
                # restantes seront reprises au prochain passage.
                _logger.warning("Cron tomes manquants interrompu sur « %s » : %s", serie.name, e)
                break
            except Exception:
                _logger.exception('Cron tomes manquants : erreur sur la série "%s".', serie.name)
                serie.missing_last_check = fields.Datetime.now()

        _logger.info("Cron tomes manquants terminé : %d tome(s) ajouté(s) au total.", total_added)
