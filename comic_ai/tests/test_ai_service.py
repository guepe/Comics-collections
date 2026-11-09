"""Socle IA (US-026) : configuration, appel Claude / OpenAI, erreurs claires."""

from odoo.tests import TransactionCase, tagged

from odoo.addons.comic_ai.models.comic_ai_service import ComicAiError

from .common import configure_ai, make_fake_sdk, patch_sdk


@tagged("post_install", "-at_install", "comic_ai")
class TestAiService(TransactionCase):
    def setUp(self):
        super().setUp()
        self.service = self.env["comic.ai.service"]

    def test_defaults(self):
        cfg = self.service._get_config()
        self.assertEqual((cfg["provider"], cfg["model"]), ("claude", "claude-sonnet-5-5"))
        self.assertEqual(self.service._get_default_lang(), "fr")
        self.assertEqual(self.service._lang_name("nl"), "néerlandais")

    def test_missing_key_is_clear(self):
        with self.assertRaisesRegex(ComicAiError, "Aucune clé API Claude"):
            self.service._generate("Bonjour")

    def test_claude_request_and_text(self):
        configure_ai(self.env)
        sdk = make_fake_sdk("Un synopsis.")
        with patch_sdk(self.env, sdk):
            result = self.service._generate("Prompt", system="Système", max_tokens=100, effort="medium")
        self.assertEqual(result, {"text": "Un synopsis.", "provider": "claude", "model": "claude-sonnet-5-5"})
        call = sdk.calls[0]
        self.assertEqual(call["model"], "claude-sonnet-5-5")
        self.assertEqual(call["system"], "Système")
        self.assertEqual(call["messages"], [{"role": "user", "content": "Prompt"}])
        self.assertEqual(call["extra_body"]["output_config"], {"effort": "medium"})
        # Repli serveur en cas de refus sur les modèles qui l'acceptent
        self.assertEqual(call["extra_body"]["fallbacks"], "default")
        self.assertEqual(call["extra_headers"]["anthropic-beta"], "server-side-fallback-2026-07-01")
        self.assertEqual(sdk.client_kwargs["api_key"], "test-key")

    def test_claude_other_model_without_fallback(self):
        configure_ai(self.env, model="claude-haiku-5-5")
        sdk = make_fake_sdk()
        with patch_sdk(self.env, sdk):
            self.service._generate("Prompt")
        self.assertNotIn("fallbacks", sdk.calls[0]["extra_body"])
        self.assertFalse(sdk.calls[0]["extra_headers"])

    def test_openai_request(self):
        configure_ai(self.env, provider="openai")
        sdk = make_fake_sdk("Hello")
        with patch_sdk(self.env, sdk):
            result = self.service._generate("Prompt", system="Sys", max_tokens=50)
        self.assertEqual((result["provider"], result["model"], result["text"]), ("openai", "gpt-5-mini", "Hello"))
        self.assertEqual(sdk.calls[0]["messages"][0], {"role": "system", "content": "Sys"})
        self.assertEqual(sdk.calls[0]["max_completion_tokens"], 50)

    def test_errors_are_clear(self):
        cases = {
            "AuthenticationError": "Clé API Claude invalide",
            "RateLimitError": "Quota",
            "APITimeoutError": "Délai dépassé",
            "APIConnectionError": "réseau",
            "NotFoundError": "Modèle Claude inconnu",
            ("APIStatusError", 529): "momentanément indisponible",
        }
        configure_ai(self.env)
        for exc, message in cases.items():
            with self.subTest(exc=exc), patch_sdk(self.env, make_fake_sdk(raise_exc=exc)):
                with self.assertRaisesRegex(ComicAiError, message):
                    self.service._generate("Prompt")
        configure_ai(self.env, provider="openai")
        with patch_sdk(self.env, make_fake_sdk(raise_exc="AuthenticationError")):
            with self.assertRaisesRegex(ComicAiError, "Clé API OpenAI invalide"):
                self.service._generate("Prompt")

    def test_refusal_and_empty_reply(self):
        configure_ai(self.env)
        with patch_sdk(self.env, make_fake_sdk(stop_reason="refusal")):
            with self.assertRaisesRegex(ComicAiError, "refusé"):
                self.service._generate("Prompt")
        with patch_sdk(self.env, make_fake_sdk(reply="  ")):
            with self.assertRaisesRegex(ComicAiError, "aucun texte"):
                self.service._generate("Prompt")

    def test_missing_library(self):
        configure_ai(self.env)
        with self.assertRaisesRegex(ComicAiError, "pip install"):
            self.service._import_sdk("comic_ai_library_qui_n_existe_pas")

    def test_settings_test_button(self):
        settings = self.env["res.config.settings"].create(
            {"comic_ai_provider": "claude", "comic_ai_claude_api_key": "k-123", "comic_ai_lang": "nl"}
        )
        with patch_sdk(self.env, make_fake_sdk("OK")):
            action = settings.action_test_ai_connection()
        self.assertEqual(action["params"]["type"], "success")
        self.assertEqual(self.env["ir.config_parameter"].sudo().get_param("comic_ai.claude_api_key"), "k-123")
        self.assertEqual(self.service._get_default_lang(), "nl")
        with patch_sdk(self.env, make_fake_sdk(raise_exc="AuthenticationError")):
            action = settings.action_test_ai_connection()
        self.assertEqual(action["params"]["type"], "danger")
        self.assertIn("invalide", action["params"]["message"])

    def test_post_trace(self):
        work = self.env["comic.work"].create({"titre_canonique": "Album IA"})
        self.service._post_trace(work, "Synopsis généré", {"provider": "claude", "model": "claude-sonnet-5-5"})
        self.assertIn("claude-sonnet-5-5", work.message_ids[0].body)
