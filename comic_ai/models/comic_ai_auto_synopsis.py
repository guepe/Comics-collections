"""Remplissage automatique des synopsis vides en tâche de fond (US-090).

Le cron « BD — IA : synopsis vides » (désactivé par défaut : chaque synopsis coûte
un appel IA) traite par lots les séries puis les albums actifs (édition principale)
dont le synopsis est vide. Il réutilise le prompt de l'assistant (US-027), n'écrit
que si le synopsis est toujours vide, ajoute la mention « Généré automatiquement par
IA » et coche ``synopsis_auto`` (filtre « à relire »). Une erreur du fournisseur
(clé, quota, délai) interrompt le lot : inutile d'enchaîner des appels en échec.
"""

import logging

from markupsafe import Markup

from odoo import _, api, models
from odoo.tools import is_html_empty

from ..wizards.comic_ai_wizard import TEXT_FIELDS, text_to_html
from .comic_ai_service import LANGS, ComicAiError

_logger = logging.getLogger(__name__)

DEFAULT_AUTO_BATCH = 20
# Case « généré automatiquement » de chaque champ texte
AUTO_FLAGS = {"synopsis": "synopsis_auto", "comic_bio": "comic_bio_auto", "comic_histoire": "comic_histoire_auto"}
# Contexte qui préserve la case lors de l'écriture par la tâche de fond
AUTO_CONTEXT = "comic_ai_auto_text"
AUTO_MENTION = Markup("<p><em>%s</em></p>")


class ComicAiService(models.AbstractModel):
    _inherit = "comic.ai.service"

    @api.model
    def _auto_synopsis_batch_size(self):
        try:
            return max(1, int(self._get_param("auto_synopsis_batch", DEFAULT_AUTO_BATCH)))
        except (TypeError, ValueError):
            return DEFAULT_AUTO_BATCH

    @api.model
    def _auto_bio_enabled(self):
        return self._get_param("auto_bio", "True") != "False"

    @api.model
    def _empty_synopsis_targets(self, limit):
        """Fiches au texte vide, au plus ``limit`` : séries, albums (édition principale), puis
        (option « biographies ») auteurs crédités et éditeurs ayant au moins une édition."""
        targets = []
        series = self.env["comic.serie"].search([("active", "=", True)], order="id")
        for serie in series:
            if len(targets) >= limit:
                return targets
            if is_html_empty(serie.synopsis):
                targets.append(serie)
        works = self.env["comic.work"].search([("active", "=", True), ("primary_edition_id", "!=", False)], order="id")
        for work in works:
            if len(targets) >= limit:
                break
            if is_html_empty(work.primary_edition_id.synopsis):
                targets.append(work.primary_edition_id)
        if len(targets) >= limit or not self._auto_bio_enabled():
            return targets
        authors = self.env["res.partner"].search([("auteur_work_line_ids", "!=", False)], order="id")
        for partner in authors:
            if len(targets) >= limit:
                return targets
            if is_html_empty(partner.comic_bio):
                targets.append(partner)
        editeurs = self.env["comic.editeur"].search([("edition_ids", "!=", False)], order="id")
        for editeur in editeurs:
            if len(targets) >= limit:
                break
            if is_html_empty(editeur.comic_histoire):
                targets.append(editeur)
        return targets

    _AUTO_WIZARD_FIELDS = {
        "comic.serie": "serie_id",
        "comic.edition": "edition_id",
        "res.partner": "partner_id",
        "comic.editeur": "editeur_id",
    }

    @api.model
    def _auto_fill_synopsis(self, record):
        """Génère et écrit le texte de ``record`` (série, édition, auteur, éditeur) s'il est toujours vide."""
        lang = self._get_default_lang()
        if record._name == "comic.edition" and record.langue in dict(LANGS):
            lang = record.langue
        wizard = self.env["comic.ai.wizard"].create(
            {self._AUTO_WIZARD_FIELDS[record._name]: record.id, "lang": lang, "mode": "synopsis"}
        )
        result = self._generate(wizard._build_prompt(), max_tokens=1024, effort="low")
        field_name = TEXT_FIELDS[record._name]
        record.invalidate_recordset([field_name])
        if not is_html_empty(record[field_name]):
            return False  # rempli entre-temps : on ne touche à rien
        mention = AUTO_MENTION % _("(Généré automatiquement par IA)")
        record.sudo().with_context(**{AUTO_CONTEXT: True}).write(
            {field_name: text_to_html(result["text"]) + mention, AUTO_FLAGS[field_name]: True}
        )
        label = {
            "res.partner": _("Biographie générée automatiquement (tâche de fond) — à relire"),
            "comic.editeur": _("Histoire de la maison générée automatiquement (tâche de fond) — à relire"),
        }.get(record._name, _("Synopsis généré automatiquement (tâche de fond)"))
        self._post_trace(record.sudo(), label, result)
        return True

    @api.model
    def _cron_fill_empty_synopses(self, limit=None):
        """Point d'entrée du cron. Retourne le nombre de synopsis écrits."""
        limit = limit or self._auto_synopsis_batch_size()
        targets = self._empty_synopsis_targets(limit)
        in_cron = bool(self.env.context.get("cron_id"))
        if in_cron:
            self.env["ir.cron"]._commit_progress(remaining=len(targets))
        written = 0
        for record in targets:
            try:
                written += int(self._auto_fill_synopsis(record))
            except ComicAiError as exc:
                _logger.warning("Synopsis IA automatiques interrompus (%s) : %s", record.display_name, exc)
                break
            if in_cron and not self.env["ir.cron"]._commit_progress(1):
                break  # temps alloué au cron écoulé : la suite au prochain passage
        _logger.info("Synopsis IA automatiques : %d écrit(s) sur %d candidat(s).", written, len(targets))
        return written
