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
