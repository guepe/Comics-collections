"""Synopsis vides remplis en tâche de fond (US-090)."""

from odoo.tests import TransactionCase, tagged

from .common import configure_ai, make_fake_sdk, patch_sdk


@tagged("post_install", "-at_install", "comic_ai")
class TestAutoSynopsis(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        configure_ai(cls.env)
        # Ces tests portent sur les synopsis ; les biographies ont leurs propres tests
        cls.env["ir.config_parameter"].sudo().set_param("comic_ai.auto_bio", "False")
        Serie, Work = cls.env["comic.serie"], cls.env["comic.work"]
        # Le cron parcourt toute la base : on neutralise les fiches existantes
        Serie.search([]).write({"synopsis": "<p>Existant</p>"})
        Work.search([("primary_edition_id", "!=", False)]).primary_edition_id.write({"synopsis": "<p>Existant</p>"})
        cls.empty_serie = Serie.create({"name": "Série sans synopsis"})
        cls.full_serie = Serie.create({"name": "Série avec synopsis", "synopsis": "<p>Écrit à la main.</p>"})
        cls.empty_work = Work.create({"titre_canonique": "Album vide", "serie_id": cls.full_serie.id, "tome": 1})
        cls.full_work = Work.create({"titre_canonique": "Album rempli", "serie_id": cls.full_serie.id, "tome": 2})
        cls.full_work.primary_edition_id.synopsis = "<p>Saisi par l'utilisateur.</p>"
        cls.archived = Work.create({"titre_canonique": "Album archivé", "tome": 3})
        cls.archived.active = False

    def _run(self, limit=None, **sdk_kwargs):
        sdk = make_fake_sdk(sdk_kwargs.pop("reply", "Un synopsis automatique."), **sdk_kwargs)
        with patch_sdk(self.env, sdk):
            written = self.env["comic.ai.service"]._cron_fill_empty_synopses(limit=limit)
        return written, sdk

    def test_only_empty_synopses_are_filled_with_mention(self):
        written, sdk = self._run()
        self.assertEqual(written, 2)
        for record in (self.empty_serie, self.empty_work.primary_edition_id):
            self.assertIn("Un synopsis automatique.", record.synopsis)
            self.assertIn("Généré automatiquement par IA", record.synopsis)
            self.assertTrue(record.synopsis_auto)
            self.assertTrue(record.message_ids.filtered(lambda m: "tâche de fond" in (m.body or "")))
        self.assertTrue(self.empty_work.synopsis_auto)
        self.assertEqual(self.full_serie.synopsis, "<p>Écrit à la main.</p>")
        self.assertEqual(self.full_work.primary_edition_id.synopsis, "<p>Saisi par l'utilisateur.</p>")
        self.assertFalse(self.archived.primary_edition_id.synopsis)
        self.assertEqual(len(sdk.calls), 2)
        # Second passage : plus rien à faire
        self.assertEqual(self._run()[0], 0)

    def test_batch_limit_and_series_first(self):
        written, _sdk = self._run(limit=1)
        self.assertEqual(written, 1)
        self.assertTrue(self.empty_serie.synopsis_auto)
        self.assertFalse(self.empty_work.primary_edition_id.synopsis)

    def test_batch_size_parameter(self):
        self.env["ir.config_parameter"].sudo().set_param("comic_ai.auto_synopsis_batch", "1")
        self.assertEqual(self._run()[0], 1)

    def test_provider_error_stops_the_batch(self):
        written, sdk = self._run(raise_exc="RateLimitError")
        self.assertEqual(written, 0)
        self.assertEqual(len(sdk.calls), 1, "Pas d'appels en rafale après une erreur du fournisseur")
        self.assertFalse(self.empty_serie.synopsis)

    def test_manual_edit_clears_the_flag(self):
        self._run()
        self.empty_serie.synopsis = "<p>Relu et corrigé.</p>"
        self.assertFalse(self.empty_serie.synopsis_auto)
        edition = self.empty_work.primary_edition_id
        edition.write({"synopsis": "<p>Corrigé.</p>"})
        self.assertFalse(edition.synopsis_auto)

    def test_edition_language_is_used(self):
        edition = self.empty_work.primary_edition_id
        edition.langue = "nl"
        _written, sdk = self._run()
        prompts = [call["messages"][0]["content"] for call in sdk.calls]
        self.assertTrue(any("néerlandais" in p and "Album vide" in p for p in prompts))

    def test_settings_toggle_and_run_now(self):
        cron = self.env.ref("comic_ai.ir_cron_fill_empty_synopses")
        self.assertFalse(cron.active, "Désactivé par défaut (appels payants)")
        settings = self.env["res.config.settings"].create({"comic_ai_auto_synopsis": True})
        settings.execute()
        self.assertTrue(cron.active)
        self.assertTrue(self.env["res.config.settings"].create({}).comic_ai_auto_synopsis)
        action = settings.action_run_auto_synopsis_now()
        self.assertEqual(action["params"]["type"], "info")
        self.assertTrue(self.env["ir.cron.trigger"].search([("cron_id", "=", cron.id)]))

    def test_bios_and_histories_after_synopses(self):
        self.env["ir.config_parameter"].sudo().set_param("comic_ai.auto_bio", "True")
        Partner = self.env["res.partner"]
        Partner.search([("auteur_work_line_ids", "!=", False)]).write({"comic_bio": "<p>Existante</p>"})
        self.env["comic.editeur"].search([]).write({"comic_histoire": "<p>Existante</p>"})
        author = Partner.create({"name": "Auteur Sans Bio"})
        self.env["comic.work.auteur.line"].create(
            {"work_id": self.empty_work.id, "partner_id": author.id, "role": "scenariste"}
        )
        editeur = self.env["comic.editeur"].create({"name": "Éditeur Sans Histoire"})
        self.full_work.primary_edition_id.editeur_id = editeur
        customer = Partner.create({"name": "Client sans rôle BD"})
        written, _sdk = self._run()
        self.assertEqual(written, 4)  # série + album + biographie + histoire
        self.assertIn("Généré automatiquement par IA", author.comic_bio)
        self.assertTrue(author.comic_bio_auto)
        self.assertIn("Généré automatiquement par IA", editeur.comic_histoire)
        self.assertTrue(editeur.comic_histoire_auto)
        self.assertFalse(customer.comic_bio, "Seuls les auteurs crédités ont une biographie")
        author.comic_bio = "<p>Relue.</p>"
        self.assertFalse(author.comic_bio_auto)

    def test_bio_option_in_settings(self):
        Settings = self.env["res.config.settings"]
        Settings.create({"comic_ai_auto_bio": True}).execute()
        self.assertTrue(self.env["comic.ai.service"]._auto_bio_enabled())
        Settings.create({"comic_ai_auto_bio": False}).execute()
        self.assertFalse(self.env["comic.ai.service"]._auto_bio_enabled())
        self.assertFalse(Settings.create({}).comic_ai_auto_bio)
