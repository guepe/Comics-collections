"""Assistant IA : génération (US-027) et traduction (US-028) du synopsis."""

from odoo import Command
from odoo.exceptions import AccessError, UserError
from odoo.tests import TransactionCase, new_test_user, tagged

from odoo.addons.comic_ai.models.comic_ai_service import ComicAiError
from odoo.addons.comic_ai.wizards.comic_ai_wizard import text_to_html

from .common import configure_ai, make_fake_sdk, patch_sdk


@tagged("post_install", "-at_install", "comic_ai")
class TestAiWizard(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        configure_ai(cls.env)
        cls.manager = new_test_user(cls.env, login="ai_manager", groups="comics_collections.group_comic_manager")
        cls.user = new_test_user(cls.env, login="ai_user", groups="comics_collections.group_comic_user")
        cls.serie = cls.env["comic.serie"].create({"name": "Les Mondes d'Aldébaran"})
        cls.editeur = cls.env["comic.editeur"].create({"name": "Dargaud"})
        cls.leo = cls.env["res.partner"].create({"name": "Leo"})
        cls.work = cls.env["comic.work"].create(
            {
                "titre_canonique": "La Catastrophe",
                "serie_id": cls.serie.id,
                "tome": 1,
                "editeur_id": cls.editeur.id,
                "auteur_line_ids": [
                    Command.create({"partner_id": cls.leo.id, "role": "scenariste"}),
                    Command.create({"partner_id": cls.leo.id, "role": "dessinateur"}),
                ],
            }
        )
        cls.edition = cls.work.primary_edition_id

    def _wizard(self, record=None, mode=None):
        record = record or self.edition
        if mode:
            record = record.with_context(comic_ai_mode=mode)
        action = record.with_user(self.manager).action_open_ai_wizard()
        return self.env["comic.ai.wizard"].with_user(self.manager).browse(action["res_id"])

    def _generate(self, wizard, reply="Premier paragraphe.\n\nSecond <paragraphe> & fin."):
        sdk = make_fake_sdk(reply)
        with patch_sdk(self.env, sdk):
            action = wizard.action_generate()
        return sdk, action

    # ── Prompt ───────────────────────────────────────────────────────────────

    def test_synopsis_prompt_contains_album_info(self):
        self.edition.synopsis = "<p>Une catastrophe frappe la colonie.</p>"
        wizard = self._wizard()
        wizard.lang = "nl"
        prompt = wizard._build_prompt()
        for expected in (
            "La Catastrophe",
            "Les Mondes d'Aldébaran",
            "Tome : 1",
            "Leo (scénario), Leo (dessin)",
            "Dargaud",
            "Une catastrophe frappe la colonie.",
            "en néerlandais",
            "4 à 6 phrases",
            "spoiler",
            "N'invente aucun fait",
        ):
            self.assertIn(expected, prompt)
        self.assertNotIn("$", prompt)

    def test_text_to_html(self):
        html = text_to_html("Un <b>texte</b> & co.\nSuite.\n\nAutre paragraphe.")
        self.assertIn("&lt;b&gt;", html)
        self.assertIn("&amp;", html)
        self.assertRegex(str(html), r"<br ?/?>")
        self.assertEqual(html.count("<p>"), 2)
        self.assertEqual(text_to_html("  "), "")

    # ── Génération / application ─────────────────────────────────────────────

    def test_generate_preview_and_apply_on_empty_edition(self):
        wizard = self._wizard()
        self.assertEqual((wizard.mode, wizard.lang, wizard.state), ("synopsis", "fr", "draft"))
        sdk, action = self._generate(wizard)
        # Le wizard reste ouvert sur la prévisualisation
        self.assertEqual(
            (action["res_model"], action["res_id"], action["target"]), ("comic.ai.wizard", wizard.id, "new")
        )
        self.assertEqual(wizard.state, "preview")
        self.assertIn("La Catastrophe", sdk.calls[0]["messages"][0]["content"])
        self.assertFalse(wizard.destination_has_synopsis)
        self.assertEqual((wizard.provider, wizard.model_name), ("claude", "claude-sonnet-5-5"))
        self.assertEqual(wizard.action_apply()["type"], "ir.actions.act_window_close")
        self.assertIn("<p>Premier paragraphe.</p>", self.edition.synopsis)
        self.assertIn("&lt;paragraphe&gt; &amp; fin.", self.edition.synopsis)
        # Visible aussi sur la fiche album (related vers l'édition principale)
        self.assertEqual(self.work.synopsis, self.edition.synopsis)

    def test_refuse_overwrite_without_confirmation(self):
        self.edition.synopsis = "<p>Saisie manuelle.</p>"
        wizard = self._wizard()
        self._generate(wizard)
        self.assertTrue(wizard.destination_has_synopsis)
        self.assertIn("Saisie manuelle.", wizard.destination_synopsis)
        with self.assertRaisesRegex(UserError, "Remplacer le synopsis existant"):
            wizard.action_apply()
        self.assertIn("Saisie manuelle.", self.edition.synopsis)
        wizard.replace_confirmed = True
        wizard.action_apply()
        self.assertIn("Premier paragraphe.", self.edition.synopsis)

    def test_apply_requires_generation(self):
        wizard = self._wizard()
        with self.assertRaisesRegex(UserError, "Générez d'abord"):
            wizard.action_apply()

    def test_regenerate(self):
        wizard = self._wizard()
        self._generate(wizard, "Version 1")
        sdk, action = self._generate(wizard, "Version 2")
        self.assertEqual(len(sdk.calls), 1)
        self.assertEqual((wizard.generated_text, wizard.state, action["res_id"]), ("Version 2", "preview", wizard.id))
        wizard.action_apply()
        self.assertIn("Version 2", self.edition.synopsis)

    def test_user_can_edit_text_before_apply(self):
        wizard = self._wizard()
        self._generate(wizard, "Texte IA")
        wizard.generated_text = "Texte retouché"
        wizard.action_apply()
        self.assertIn("Texte retouché", self.edition.synopsis)

    def test_provider_error_is_raised_as_is(self):
        wizard = self._wizard()
        for exc, message in (
            ("AuthenticationError", "Clé API Claude invalide"),
            ("APITimeoutError", "Délai dépassé"),
            ("RateLimitError", "Quota"),
        ):
            with self.subTest(exc=exc), patch_sdk(self.env, make_fake_sdk(raise_exc=exc)):
                with self.assertRaisesRegex(ComicAiError, message):
                    wizard.action_generate()
        self.assertEqual(wizard.state, "draft")

    def test_chatter_trace_on_apply(self):
        wizard = self._wizard()
        self._generate(wizard)
        wizard.action_apply()
        body = self.edition.message_ids[0].body
        self.assertIn("Synopsis généré par IA", body)
        self.assertIn("Claude (Anthropic)", body)
        self.assertIn("claude-sonnet-5-5", body)

    # ── Traduction (US-028) ──────────────────────────────────────────────────

    def test_translate_replaces_current_synopsis(self):
        self.edition.synopsis = "<p>Une catastrophe frappe la colonie.</p>"
        wizard = self._wizard(mode="translate")
        self.assertEqual(wizard.mode, "translate")
        wizard.target_lang = "en"
        # Pas d'édition anglaise : seul choix possible, remplacer celle-ci
        self.assertFalse(wizard.target_edition_id)
        self.assertEqual(wizard.translate_destination, "current")
        prompt = wizard._build_prompt()
        self.assertIn("Traduis en anglais", prompt)
        self.assertIn("langue d'origine : français", prompt)
        self.assertIn("Une catastrophe frappe la colonie.", prompt)
        self._generate(wizard, "A disaster strikes the colony.")
        self.assertEqual(wizard.destination_edition_id, self.edition)
        wizard.replace_confirmed = True
        wizard.action_apply()
        self.assertIn("A disaster strikes the colony.", self.edition.synopsis)
        self.assertIn("Synopsis traduit par IA (fr → en)", self.edition.message_ids[0].body)

    def test_translate_writes_on_target_language_edition(self):
        self.edition.synopsis = "<p>Une catastrophe frappe la colonie.</p>"
        edition_nl = self.env["comic.edition"].create({"work_id": self.work.id, "langue": "nl"})
        wizard = self._wizard(record=self.work, mode="translate")
        wizard.target_lang = "nl"
        self.assertEqual(wizard.target_edition_id, edition_nl)
        self.assertEqual(wizard.translate_destination, "target")
        self.assertEqual(wizard.destination_edition_id, edition_nl)
        self._generate(wizard, "Een ramp treft de kolonie.")
        # L'édition néerlandaise est vide : pas de confirmation nécessaire
        self.assertFalse(wizard.destination_has_synopsis)
        wizard.action_apply()
        self.assertIn("Een ramp treft de kolonie.", edition_nl.synopsis)
        self.assertIn("Une catastrophe frappe la colonie.", self.edition.synopsis)
        self.assertIn("Synopsis traduit par IA", edition_nl.message_ids[0].body)

    def test_translate_choice_current_even_if_target_exists(self):
        self.edition.synopsis = "<p>Texte FR.</p>"
        self.env["comic.edition"].create({"work_id": self.work.id, "langue": "nl"})
        wizard = self._wizard(mode="translate")
        wizard.write({"target_lang": "nl", "translate_destination": "current"})
        self.assertEqual(wizard.destination_edition_id, self.edition)
        self._generate(wizard, "Tekst NL.")
        with self.assertRaises(UserError):
            wizard.action_apply()
        wizard.replace_confirmed = True
        wizard.action_apply()
        self.assertIn("Tekst NL.", self.edition.synopsis)

    def test_translate_without_synopsis(self):
        wizard = self._wizard(mode="translate")
        with self.assertRaisesRegex(UserError, "pas de synopsis à traduire"):
            wizard.action_generate()

    def test_default_target_lang_differs_from_edition(self):
        wizard = self._wizard(mode="translate")
        self.assertNotEqual(wizard.target_lang, self.edition.langue)

    # ── Boutons, actions, droits ─────────────────────────────────────────────

    def test_action_from_album_targets_primary_edition(self):
        wizard = self._wizard(record=self.work)
        self.assertEqual(wizard.edition_id, self.edition)
        self.assertEqual(wizard.work_id, self.work)

    def test_buttons_visible_for_managers_only(self):
        for model in ("comic.work", "comic.edition"):
            with self.subTest(model=model):
                arch = self.env[model].with_user(self.manager).get_views([(False, "form")])["views"]["form"]["arch"]
                self.assertIn("action_open_ai_wizard", arch)
                self.assertIn("Générer le synopsis", arch)
                arch = self.env[model].with_user(self.user).get_views([(False, "form")])["views"]["form"]["arch"]
                self.assertNotIn("action_open_ai_wizard", arch)

    def test_simple_user_cannot_use_wizard(self):
        with self.assertRaises(AccessError):
            self.edition.with_user(self.user).action_open_ai_wizard()
        with self.assertRaises(AccessError):
            self.env["comic.ai.wizard"].with_user(self.user).create({"edition_id": self.edition.id})
        wizard = self._wizard()
        with self.assertRaises(AccessError):
            wizard.with_user(self.user).action_generate()

    # ── Synopsis de série ────────────────────────────────────────────────────

    def test_serie_synopsis_prompt_and_apply(self):
        self.serie.write({"genre_id": self.env["comic.genre"].create({"name": "SF"}).id, "editeur_id": self.editeur.id})
        wizard = self._wizard(record=self.serie)
        self.assertEqual((wizard.serie_id, wizard.edition_id), (self.serie, self.env["comic.edition"]))
        prompt = wizard._build_prompt()
        for expected in ("Les Mondes d'Aldébaran", "SF", "Dargaud", "Leo (scénario)", "T1 : La Catastrophe"):
            self.assertIn(expected, prompt)
        self._generate(wizard, reply="Une série de science-fiction.")
        self.assertFalse(wizard.destination_has_synopsis)
        wizard.action_apply()
        self.assertIn("Une série de science-fiction.", self.serie.synopsis)
        self.assertFalse(self.edition.synopsis, "La série ne touche pas aux éditions")
        self.assertTrue(self.serie.message_ids.filtered(lambda m: "Synopsis généré par IA" in (m.body or "")))

    def test_serie_overwrite_needs_confirmation_and_translate(self):
        self.serie.synopsis = "<p>Une colonie isolée.</p>"
        wizard = self._wizard(record=self.serie, mode="translate")
        wizard.target_lang = "nl"
        self.assertFalse(wizard.target_edition_id)
        self.assertIn("Une colonie isolée.", wizard._build_prompt())
        self._generate(wizard, reply="Een geïsoleerde kolonie.")
        with self.assertRaises(UserError):
            wizard.action_apply()
        wizard.replace_confirmed = True
        wizard.action_apply()
        self.assertIn("Een geïsoleerde kolonie.", self.serie.synopsis)

    def test_serie_wizard_reserved_to_managers(self):
        with self.assertRaises(AccessError):
            self.serie.with_user(self.user).action_open_ai_wizard()

    # ── Biographie d'auteur / histoire d'éditeur (US-091) ────────────────────

    def test_author_bio_prompt_apply_and_trace(self):
        wizard = self._wizard(record=self.leo)
        self.assertEqual(wizard.partner_id, self.leo)
        prompt = wizard._build_prompt()
        for expected in ("Leo", "Les Mondes d'Aldébaran", "Dargaud", "homonyme"):
            self.assertIn(expected, prompt)
        self._generate(wizard, reply="Leo est un auteur brésilien de BD.")
        wizard.action_apply()
        self.assertIn("Leo est un auteur", self.leo.comic_bio)
        self.assertTrue(self.leo.message_ids.filtered(lambda m: "Biographie générée par IA" in (m.body or "")))

    def test_publisher_history_needs_confirmation(self):
        self.editeur.comic_histoire = "<p>Maison fondée par…</p>"
        wizard = self._wizard(record=self.editeur)
        self.assertIn("Les Mondes d'Aldébaran", wizard._build_prompt())
        self._generate(wizard, reply="Dargaud est une maison d'édition.")
        with self.assertRaises(UserError):
            wizard.action_apply()
        wizard.replace_confirmed = True
        wizard.action_apply()
        self.assertIn("Dargaud est une maison", self.editeur.comic_histoire)

    def test_bio_wizard_reserved_to_managers(self):
        with self.assertRaises(AccessError):
            self.leo.with_user(self.user).action_open_ai_wizard()
        with self.assertRaises(AccessError):
            self.editeur.with_user(self.user).action_open_ai_wizard()
