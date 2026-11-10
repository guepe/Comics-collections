from odoo import _, fields, models

from .comic_ai_service import (
    DEFAULT_CLAUDE_MODEL,
    DEFAULT_LANG,
    DEFAULT_OPENAI_MODEL,
    DEFAULT_PROVIDER,
    LANGS,
    PROVIDERS,
    ComicAiError,
)


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    comic_ai_provider = fields.Selection(
        PROVIDERS,
        string="Fournisseur IA",
        default=DEFAULT_PROVIDER,
        config_parameter="comic_ai.provider",
    )
    comic_ai_claude_api_key = fields.Char(
        string="Clé API Claude",
        config_parameter="comic_ai.claude_api_key",
        help="Clé à créer sur platform.claude.com. Stockée dans les paramètres système.",
    )
    comic_ai_claude_model = fields.Char(
        string="Modèle Claude",
        default=DEFAULT_CLAUDE_MODEL,
        config_parameter="comic_ai.claude_model",
    )
    comic_ai_openai_api_key = fields.Char(
        string="Clé API OpenAI",
        config_parameter="comic_ai.openai_api_key",
    )
    comic_ai_openai_model = fields.Char(
        string="Modèle OpenAI",
        default=DEFAULT_OPENAI_MODEL,
        config_parameter="comic_ai.openai_model",
    )
    comic_ai_lang = fields.Selection(
        [code for code in LANGS if code[0] != "de"],
        string="Langue de génération",
        default=DEFAULT_LANG,
        config_parameter="comic_ai.lang",
    )

    # US-090 : synopsis vides remplis en tâche de fond (cron désactivé par défaut)
    comic_ai_auto_synopsis = fields.Boolean(
        string="Remplir automatiquement les synopsis vides",
        compute="_compute_comic_ai_auto_synopsis",
        inverse="_inverse_comic_ai_auto_synopsis",
    )
    comic_ai_auto_synopsis_batch = fields.Integer(
        string="Synopsis par passage",
        default=20,
        config_parameter="comic_ai.auto_synopsis_batch",
        help="Nombre maximal de synopsis générés à chaque passage (toutes les heures).",
    )

    # Biographies d'auteurs et histoires d'éditeurs dans la même tâche de fond (US-091).
    # Stocké explicitement "True" / "False" : un config_parameter booléen décoché est
    # supprimé, et la valeur par défaut (activé) reviendrait.
    comic_ai_auto_bio = fields.Boolean(
        string="Inclure les biographies d'auteurs et les histoires des éditeurs",
        compute="_compute_comic_ai_auto_bio",
        inverse="_inverse_comic_ai_auto_bio",
    )

    def _compute_comic_ai_auto_bio(self):
        enabled = self.env["comic.ai.service"]._auto_bio_enabled()
        for settings in self:
            settings.comic_ai_auto_bio = enabled

    def _inverse_comic_ai_auto_bio(self):
        self.env["ir.config_parameter"].sudo().set_param(
            "comic_ai.auto_bio", "True" if self[:1].comic_ai_auto_bio else "False"
        )

    def _auto_synopsis_cron(self):
        return self.env.ref("comic_ai.ir_cron_fill_empty_synopses", raise_if_not_found=False)

    def _compute_comic_ai_auto_synopsis(self):
        cron = self._auto_synopsis_cron()
        for settings in self:
            settings.comic_ai_auto_synopsis = bool(cron and cron.sudo().active)

    def _inverse_comic_ai_auto_synopsis(self):
        cron = self._auto_synopsis_cron()
        if cron:
            cron.sudo().active = self[:1].comic_ai_auto_synopsis

    def action_run_auto_synopsis_now(self):
        """Enregistre puis planifie un passage immédiat du cron (exécuté en arrière-plan)."""
        self.ensure_one()
        self.execute()
        cron = self._auto_synopsis_cron()
        if not cron:
            return False
        cron.sudo()._trigger()
        return self._ai_notification(
            _("Synopsis automatiques"),
            _("Un passage est planifié : les synopsis vides seront remplis en arrière-plan."),
            "info",
        )

    def action_test_ai_connection(self):
        """Enregistre les paramètres puis fait un petit appel au fournisseur actif."""
        self.ensure_one()
        self.execute()
        try:
            result = self.env["comic.ai.service"]._test_connection()
        except ComicAiError as exc:
            return self._ai_notification(_("Connexion IA en échec"), str(exc), "danger")
        return self._ai_notification(
            _("Connexion IA réussie"),
            _(
                "%(provider)s répond (modèle %(model)s).",
                provider=dict(PROVIDERS)[result["provider"]],
                model=result["model"],
            ),
            "success",
        )

    @staticmethod
    def _ai_notification(title, message, kind):
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {"title": title, "message": message, "type": kind, "sticky": kind == "danger"},
        }
