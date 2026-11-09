"""Couche d'appel aux fournisseurs IA (US-026) : Claude (Anthropic) ou OpenAI.

Point d'entrée unique : ``self.env["comic.ai.service"]._generate(prompt, ...)``.
Les clés API vivent dans ``ir.config_parameter`` (jamais en dur) et les SDK
officiels (``anthropic``, ``openai``) sont importés à la demande : leur absence
donne une erreur claire au lieu d'empêcher l'installation du module.

Toutes les erreurs remontent en ``ComicAiError`` (``UserError``) avec un message
lisible : clé invalide, délai dépassé, quota, modèle inconnu, réseau, refus.
"""

import importlib
import logging
from string import Template

from markupsafe import Markup

from odoo import _, api, models
from odoo.exceptions import UserError
from odoo.tools import file_open

_logger = logging.getLogger(__name__)

PROVIDERS = [("claude", "Claude (Anthropic)"), ("openai", "OpenAI")]
DEFAULT_PROVIDER = "claude"
DEFAULT_CLAUDE_MODEL = "claude-sonnet-5-5"
DEFAULT_OPENAI_MODEL = "gpt-5-mini"
DEFAULT_LANG = "fr"
DEFAULT_TIMEOUT = 60  # secondes
# Les modèles « à raisonnement » (OpenAI gpt-5 / o-series) décomptent leur réflexion
# de max_completion_tokens : sans réserve, ils l'épuisent et ne renvoient aucun texte.
OPENAI_REASONING_HEADROOM = 4096

# Langues de génération / traduction (code → libellé utilisé dans les prompts)
LANGS = [("fr", "Français"), ("nl", "Néerlandais"), ("en", "Anglais"), ("de", "Allemand")]
LANG_PROMPT_NAMES = {"fr": "français", "nl": "néerlandais", "en": "anglais", "de": "allemand"}

# Modèles Claude qui acceptent le repli serveur « default » en cas de refus
# (beta server-side-fallback-2026-07-01, API Claude uniquement).
_CLAUDE_FALLBACK_MODELS = {"claude-fable-5-1", "claude-opus-5-5", "claude-opus-5", "claude-sonnet-5-5"}
_CLAUDE_FALLBACK_BETA = "server-side-fallback-2026-07-01"

PARAM_PREFIX = "comic_ai."


class ComicAiError(UserError):
    """Erreur IA présentée telle quelle à l'utilisateur."""


class ComicAiService(models.AbstractModel):
    _name = "comic.ai.service"
    _description = "Service IA (Claude / OpenAI)"

    # ── Configuration ────────────────────────────────────────────────────────

    @api.model
    def _get_param(self, key, default=""):
        return self.env["ir.config_parameter"].sudo().get_param(PARAM_PREFIX + key) or default

    @api.model
    def _get_config(self):
        provider = self._get_param("provider", DEFAULT_PROVIDER)
        if provider not in dict(PROVIDERS):
            provider = DEFAULT_PROVIDER
        try:
            timeout = max(5, int(self._get_param("timeout", DEFAULT_TIMEOUT)))
        except (TypeError, ValueError):
            timeout = DEFAULT_TIMEOUT
        if provider == "claude":
            api_key = self._get_param("claude_api_key")
            model = self._get_param("claude_model", DEFAULT_CLAUDE_MODEL)
        else:
            api_key = self._get_param("openai_api_key")
            model = self._get_param("openai_model", DEFAULT_OPENAI_MODEL)
        return {"provider": provider, "api_key": api_key.strip(), "model": model.strip(), "timeout": timeout}

    @api.model
    def _get_default_lang(self):
        lang = self._get_param("lang", DEFAULT_LANG)
        return lang if lang in dict(LANGS) else DEFAULT_LANG

    @api.model
    def _lang_name(self, code):
        """Nom de langue à insérer dans un prompt (« français », « néerlandais »…)."""
        return LANG_PROMPT_NAMES.get(code, LANG_PROMPT_NAMES[DEFAULT_LANG])

    # ── Prompts (fichiers comic_ai/prompts/<nom>.txt) ────────────────────────

    @api.model
    def _render_prompt(self, name, **values):
        """Charge ``prompts/<name>.txt`` et substitue les ``$variables`` (string.Template).

        ``safe_substitute`` : une variable absente reste telle quelle plutôt que de
        lever ; les accolades (JSON d'exemple dans un prompt) ne posent pas problème.
        """
        with file_open(f"comic_ai/prompts/{name}.txt") as f:
            template = Template(f.read())
        values = {k: ("" if v is None or v is False else v) for k, v in values.items()}
        return template.safe_substitute(values).strip()

    # ── Génération ───────────────────────────────────────────────────────────

    @api.model
    def _generate(self, prompt, system=None, max_tokens=2048, effort="low"):
        """Envoie ``prompt`` au fournisseur actif et retourne le texte produit.

        :param effort: niveau d'effort Claude (``low`` / ``medium`` / ``high``) ;
            ignoré par OpenAI.
        :return: ``{"text": str, "provider": str, "model": str}``
        :raise ComicAiError: configuration absente ou erreur du fournisseur
        """
        cfg = self._get_config()
        if not cfg["api_key"]:
            raise ComicAiError(
                _(
                    "Aucune clé API %(provider)s configurée : renseignez-la dans "
                    "Paramètres > Bandes Dessinées > Intelligence artificielle.",
                    provider=dict(PROVIDERS)[cfg["provider"]],
                )
            )
        if not cfg["model"]:
            raise ComicAiError(_("Aucun modèle IA configuré."))
        call = self._call_claude if cfg["provider"] == "claude" else self._call_openai
        text = call(cfg, system, prompt, max_tokens, effort)
        text = (text or "").strip()
        if not text:
            raise ComicAiError(_("Le fournisseur IA n'a renvoyé aucun texte. Réessayez."))
        return {"text": text, "provider": cfg["provider"], "model": cfg["model"]}

    @api.model
    def _import_sdk(self, name):
        try:
            return importlib.import_module(name)
        except ImportError as exc:
            raise ComicAiError(
                _(
                    "La bibliothèque Python « %(name)s » n'est pas installée sur le serveur " "(pip install %(name)s).",
                    name=name,
                )
            ) from exc

    @api.model
    def _call_claude(self, cfg, system, prompt, max_tokens, effort):
        anthropic = self._import_sdk("anthropic")
        client = anthropic.Anthropic(api_key=cfg["api_key"], timeout=cfg["timeout"], max_retries=1)
        kwargs = {
            "model": cfg["model"],
            "max_tokens": max_tokens,
            "messages": [{"role": "user", "content": prompt}],
        }
        if system:
            kwargs["system"] = system
        # Passés en extra_body / extra_headers : compatibles avec toutes les versions du
        # SDK installé (paramètres récents absents des signatures des versions 0.x).
        extra_body = {"output_config": {"effort": effort}} if effort else {}
        extra_headers = {}
        if cfg["model"] in _CLAUDE_FALLBACK_MODELS:
            # Repli serveur en cas de refus : la même requête repart sur un autre modèle.
            extra_body["fallbacks"] = "default"
            extra_headers["anthropic-beta"] = _CLAUDE_FALLBACK_BETA
        try:
            response = client.messages.create(**kwargs, extra_body=extra_body, extra_headers=extra_headers)
        except anthropic.AuthenticationError as exc:
            raise ComicAiError(_("Clé API Claude invalide ou révoquée.")) from exc
        except anthropic.PermissionDeniedError as exc:
            raise ComicAiError(_("La clé API Claude n'a pas accès à ce modèle.")) from exc
        except anthropic.NotFoundError as exc:
            raise ComicAiError(_("Modèle Claude inconnu : %s.", cfg["model"])) from exc
        except anthropic.RateLimitError as exc:
            raise ComicAiError(_("Quota ou limite de débit Claude atteint : réessayez plus tard.")) from exc
        except anthropic.APITimeoutError as exc:
            raise ComicAiError(_("Délai dépassé : Claude n'a pas répondu à temps.")) from exc
        except anthropic.APIConnectionError as exc:
            raise ComicAiError(_("Impossible de joindre l'API Claude (réseau).")) from exc
        except anthropic.APIStatusError as exc:
            _logger.warning("Claude API error %s: %s", exc.status_code, exc)
            if exc.status_code >= 500:
                raise ComicAiError(_("Claude est momentanément indisponible : réessayez.")) from exc
            raise ComicAiError(_("Requête refusée par Claude : %s", getattr(exc, "message", exc))) from exc
        stop_reason = getattr(response, "stop_reason", None)
        if stop_reason == "refusal":
            raise ComicAiError(_("Claude a refusé de traiter cette demande."))
        text = "".join(block.text for block in (response.content or []) if getattr(block, "type", None) == "text")
        if not text.strip() and stop_reason == "max_tokens":
            raise ComicAiError(_("Réponse de Claude tronquée : la limite de longueur a été atteinte avant le texte."))
        return text

    @api.model
    def _call_openai(self, cfg, system, prompt, max_tokens, effort):
        openai = self._import_sdk("openai")
        client = openai.OpenAI(api_key=cfg["api_key"], timeout=cfg["timeout"], max_retries=1)
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        try:
            response = client.chat.completions.create(
                model=cfg["model"],
                messages=messages,
                max_completion_tokens=max_tokens + OPENAI_REASONING_HEADROOM,
            )
        except openai.AuthenticationError as exc:
            raise ComicAiError(_("Clé API OpenAI invalide ou révoquée.")) from exc
        except openai.PermissionDeniedError as exc:
            raise ComicAiError(_("La clé API OpenAI n'a pas accès à ce modèle.")) from exc
        except openai.NotFoundError as exc:
            raise ComicAiError(_("Modèle OpenAI inconnu : %s.", cfg["model"])) from exc
        except openai.RateLimitError as exc:
            raise ComicAiError(_("Quota ou limite de débit OpenAI atteint : réessayez plus tard.")) from exc
        except openai.APITimeoutError as exc:
            raise ComicAiError(_("Délai dépassé : OpenAI n'a pas répondu à temps.")) from exc
        except openai.APIConnectionError as exc:
            raise ComicAiError(_("Impossible de joindre l'API OpenAI (réseau).")) from exc
        except openai.APIStatusError as exc:
            _logger.warning("OpenAI API error %s: %s", exc.status_code, exc)
            if exc.status_code >= 500:
                raise ComicAiError(_("OpenAI est momentanément indisponible : réessayez.")) from exc
            raise ComicAiError(_("Requête refusée par OpenAI : %s", getattr(exc, "message", exc))) from exc
        choices = response.choices or []
        if not choices:
            return ""
        text = choices[0].message.content or ""
        if not text.strip() and getattr(choices[0], "finish_reason", None) == "length":
            raise ComicAiError(
                _(
                    "Réponse d'OpenAI tronquée : la limite de longueur a été atteinte avant le texte "
                    "(modèle à raisonnement)."
                )
            )
        return text

    # ── Utilitaires partagés ─────────────────────────────────────────────────

    @api.model
    def _test_connection(self):
        """Petit appel de contrôle ; retourne le résultat de ``_generate``."""
        return self._generate("Réponds uniquement par : OK", max_tokens=1024, effort="low")

    @api.model
    def _post_trace(self, record, action_label, result):
        """Trace dans le chatter : action, fournisseur, modèle (la date est celle du message)."""
        if not hasattr(record, "message_post"):
            return
        body = Markup("%s — <b>%s</b> (%s)") % (
            action_label,
            dict(PROVIDERS).get(result.get("provider"), result.get("provider")),
            result.get("model"),
        )
        record.message_post(body=body, message_type="notification", subtype_xmlid="mail.mt_note")
