"""Découverte IA par profil de goûts (US-029) : profil, exclusions, parse, wishlist, vérification."""

import json
import types
from unittest.mock import patch

from odoo.exceptions import UserError
from odoo.tests import TransactionCase, new_test_user, tagged

from odoo.addons.comic_ai.models.comic_ai_service import ComicAiError
from odoo.addons.comic_ai.wizards.comic_ai_discovery_wizard import (
    ComicAiDiscoveryLine,
    filter_suggestions,
    parse_suggestions,
)
from odoo.addons.comic_datasource.sources.base import ComicSourceResult
from odoo.addons.comic_datasource.sources.google_books import GoogleBooksQuotaError

from .common import configure_ai, make_fake_sdk, patch_sdk

ISBN_T1 = "9782205049428"  # EAN-13 valide


def _reply(*titles):
    return json.dumps(
        {
            "suggestions": [
                {"titre": t, "auteurs": "Auteur %s" % i, "genre": "Polar", "raison": "Proche de vos goûts"}
                for i, t in enumerate(titles)
            ]
        }
    )


def _fake_aggregator(results=None, raise_exc=None):
    def search_list(title, author=None):
        if raise_exc:
            raise raise_exc
        return results or []

    return types.SimpleNamespace(search_list=search_list)


@tagged("post_install", "-at_install", "comic_ai", "comic_ai_discovery")
class TestDiscovery(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = new_test_user(cls.env, login="discovery_user", groups="comics_collections.group_comic_user")
        cls.other = new_test_user(cls.env, login="discovery_other", groups="comics_collections.group_comic_user")
        cls.partner = cls.user.partner_id
        genre = cls.env["comic.genre"].search([], limit=1)
        cls.liked = cls._serie("Les Landes perdues", genre=genre)
        cls.liked2 = cls._serie("Blake et Mortimer")
        cls.average = cls._serie("Série moyenne")
        cls.wished = cls._serie("Série souhaitée")
        cls.followed = cls._serie("Série suivie")
        cls.other_liked = cls._serie("Préférée de l'autre")
        cls.catalog = cls._serie("Blacksad")
        cls.catalog_t2 = cls._work(cls.catalog, "Arctic Nation", 2)
        cls.catalog_t1 = cls._work(cls.catalog, "Quelque part entre les ombres", 1)

        cls._entry(cls.partner, cls._work(cls.liked, "Sioban", 1), note=5)
        cls._entry(cls.partner, cls._work(cls.liked2, "Le Secret de l'Espadon", 1), note=4)
        cls._entry(cls.partner, cls._work(cls.average, "Moyen T1", 1), note=3)
        cls._entry(cls.partner, cls._work(cls.wished, "Souhait T1", 1), dans_collection=False, dans_wishlist=True)
        cls._entry(cls.other.partner_id, cls._work(cls.other_liked, "Autre T1", 1), note=5)
        cls.followed.suivi_user_ids = [(4, cls.user.id)]

    @classmethod
    def _serie(cls, name, genre=None):
        return cls.env["comic.serie"].create({"name": name, "genre_id": genre.id if genre else False})

    @classmethod
    def _work(cls, serie, title, tome):
        return cls.env["comic.work"].create({"serie_id": serie.id, "titre_canonique": title, "tome": tome})

    @classmethod
    def _entry(cls, partner, work, note=0, dans_collection=True, dans_wishlist=False):
        return cls.env["comic.customer.album"].create(
            {
                "partner_id": partner.id,
                "edition_id": work.primary_edition_id.id,
                "note": note,
                "dans_collection": dans_collection,
                "dans_wishlist": dans_wishlist,
            }
        )

    def setUp(self):
        super().setUp()
        configure_ai(self.env)

    def _wizard(self, **vals):
        return self.env["comic.ai.discovery.wizard"].with_user(self.user).create(vals)

    def _generate(self, wizard, reply):
        sdk = make_fake_sdk(reply)
        with patch_sdk(self.env, sdk):
            wizard.action_generate()
        return sdk

    def _line(self, wizard, name, **vals):
        return (
            self.env["comic.ai.discovery.line"]
            .with_user(self.user)
            .create({"wizard_id": wizard.id, "name": name, **vals})
        )

    def _wish(self, edition):
        return self.env["comic.customer.album"].search(
            [("partner_id", "=", self.partner.id), ("edition_id", "=", edition.id)]
        )

    # ── Profil ──────────────────────────────────────────────────────────────

    def test_profile_is_series_rated_4_or_more(self):
        wizard = self._wizard()
        self.assertEqual(wizard.partner_id, self.partner)
        self.assertEqual(wizard.profile_serie_ids, self.liked | self.liked2)
        self.assertEqual(wizard.profile_serie_ids[0], self.liked, "Meilleure note en tête")

    def test_partner_forced_to_current_user(self):
        wizard = self._wizard(partner_id=self.other.partner_id.id)
        self.assertEqual(wizard.partner_id, self.partner)

    def test_empty_profile_is_explicit(self):
        wizard = self._wizard(profile_serie_ids=[(5, 0, 0)])
        with self.assertRaisesRegex(UserError, "notez au moins une BD 4★"):
            wizard.action_generate()

    # ── Parse de la réponse ─────────────────────────────────────────────────

    def test_parse_plain_and_list(self):
        self.assertEqual(parse_suggestions(_reply("Blacksad"))[0]["titre"], "Blacksad")
        items = parse_suggestions('[{"title": "Undertaker", "authors": ["Dorison", "Meyer"], "reason": "Western"}]')
        self.assertEqual(
            items[0], {"titre": "Undertaker", "auteurs": "Dorison, Meyer", "genre": "", "raison": "Western"}
        )

    def test_parse_noisy_answers(self):
        fenced = "Voici mes idées :\n```json\n%s\n```\nBonne lecture !" % _reply("Lanfeust", "Thorgal")
        self.assertEqual([s["titre"] for s in parse_suggestions(fenced)], ["Lanfeust", "Thorgal"])
        prefixed = "Bien sûr ! %s J'espère que cela vous plaira." % _reply("Undertaker")
        self.assertEqual(parse_suggestions(prefixed)[0]["titre"], "Undertaker")
        # Entrées sans titre ignorées
        self.assertEqual(len(parse_suggestions('{"suggestions": [{"titre": ""}, {"titre": "X"}, "y"]}')), 1)

    def test_parse_invalid(self):
        for text in ("Désolé, je ne peux pas.", '{"suggestions": [', '{"suggestions": []}', ""):
            with self.assertRaises(ValueError):
                parse_suggestions(text)

    def test_invalid_answer_gives_clear_error(self):
        wizard = self._wizard()
        with self.assertRaisesRegex(ComicAiError, "illisible"):
            self._generate(wizard, "Je ne sais pas.")

    def test_filter_suggestions(self):
        items = [{"titre": t} for t in ("Landes perdues (Les)", "Nouvelle", "La Nouvelle", "Autre")]
        kept = filter_suggestions(items, {"landes perdues"}, limit=15)
        self.assertEqual([s["titre"] for s in kept], ["Nouvelle", "Autre"])

    # ── Génération et exclusions ────────────────────────────────────────────

    def test_generate_excludes_known_series(self):
        wizard = self._wizard()
        reply = _reply(
            "Landes perdues (Les)",  # profil / collection (titre normalisé)
            "Série moyenne",  # en collection
            "Série souhaitée",  # en wishlist
            "Série suivie",  # suivie = manques de la wishlist
            "Blacksad",
            "BLACKSAD",  # doublon
            "Undertaker",
        )
        sdk = self._generate(wizard, reply)
        self.assertEqual(wizard.state, "suggestions")
        self.assertEqual(wizard.line_ids.mapped("name"), ["Blacksad", "Undertaker"])
        self.assertEqual(wizard.nb_ignored, 5)
        blacksad = wizard.line_ids[0]
        self.assertEqual(blacksad.serie_id, self.catalog)
        self.assertEqual((blacksad.auteurs, blacksad.genre), ("Auteur 4", "Polar"))
        self.assertFalse(wizard.line_ids[1].serie_id)
        prompt = sdk.calls[0]["messages"][0]["content"]
        self.assertIn("Les Landes perdues", prompt)
        self.assertIn("note : 5.0/5", prompt)
        for name in ("Série moyenne", "Série souhaitée", "Série suivie"):
            self.assertIn("- %s" % name, prompt)
        self.assertNotIn("Préférée de l'autre", prompt, "Les goûts d'un autre utilisateur ne fuient pas")
        self.assertIn("français", prompt)
        self.assertNotIn("$", prompt, "Toutes les variables du prompt sont substituées")

    def test_regenerate_replaces_lines(self):
        wizard = self._wizard()
        self._generate(wizard, _reply("Undertaker"))
        self._generate(wizard, _reply("Lanfeust", "Thorgal"))
        self.assertEqual(wizard.line_ids.mapped("name"), ["Lanfeust", "Thorgal"])

    def test_ai_errors_are_clear(self):
        wizard = self._wizard()
        for exc, message in (("AuthenticationError", "Clé API Claude invalide"), ("APITimeoutError", "Délai dépassé")):
            with patch_sdk(self.env, make_fake_sdk(raise_exc=exc)), self.assertRaisesRegex(ComicAiError, message):
                wizard.action_generate()

    # ── Ajout en wishlist ───────────────────────────────────────────────────

    def test_add_existing_series_adds_first_volume(self):
        wizard = self._wizard()
        self._generate(wizard, _reply("Blacksad"))
        wizard.line_ids.selected = True
        nb_series = self.env["comic.serie"].search_count([])
        action = wizard.action_add_to_wishlist()
        self.assertEqual(action["params"]["type"], "success")
        entry = self._wish(self.catalog_t1.primary_edition_id)
        self.assertTrue(entry.dans_wishlist)
        self.assertFalse(entry.dans_collection)
        self.assertFalse(self._wish(self.catalog_t2.primary_edition_id))
        self.assertTrue(wizard.line_ids.added)
        self.assertEqual(self.env["comic.serie"].search_count([]), nb_series)
        wishlist = self.env["comic.wishlist.item"].with_user(self.user).search([("type", "=", "souhait")])
        self.assertIn(self.catalog_t1, wishlist.work_id)

    def test_add_new_series_creates_serie_and_volume_1(self):
        wizard = self._wizard()
        line = self._line(wizard, "Undertaker", selected=True, verified_isbn=ISBN_T1, verified_editeur="Dargaud")
        line2 = self._line(wizard, "Lanfeust de Troy", selected=True)
        wizard._add_selected_to_wishlist()
        serie = self.env["comic.serie"].search([("name", "=", "Undertaker")])
        self.assertEqual(len(serie), 1)
        work = serie.work_ids
        self.assertEqual((work.tome, work.titre_canonique), (1, "Undertaker"))
        edition = work.primary_edition_id
        self.assertEqual(edition.isbn_ids.isbn_13, ISBN_T1)
        self.assertEqual(edition.editeur_id.name, "Dargaud")
        self.assertTrue(self._wish(edition).dans_wishlist)
        self.assertEqual(line.serie_id, serie)
        self.assertTrue(line2.serie_id.work_ids.primary_edition_id)
        self.assertTrue(self._wish(line2.serie_id.work_ids.primary_edition_id))

    def test_add_reuses_known_isbn(self):
        self.env["comic.isbn"].create({"edition_id": self.catalog_t1.primary_edition_id.id, "isbn_13": ISBN_T1})
        wizard = self._wizard()
        self._line(wizard, "Blacksad (édition intégrale)", selected=True, verified_isbn=ISBN_T1)
        wizard._add_selected_to_wishlist()
        self.assertTrue(self._wish(self.catalog_t1.primary_edition_id))

    def test_add_keeps_owned_album(self):
        owned = self._entry(self.partner, self._work(self.catalog, "Hors-série", 0))
        self.catalog_t1.active = False
        self.catalog_t2.active = False
        wizard = self._wizard()
        self._line(wizard, "Blacksad", selected=True)
        wizard._add_selected_to_wishlist()
        self.assertTrue(owned.dans_collection, "Un album possédé reste dans la collection")
        self.assertTrue(owned.dans_wishlist)

    def test_add_requires_selection(self):
        wizard = self._wizard()
        self._line(wizard, "Undertaker")
        with self.assertRaisesRegex(UserError, "Sélectionnez"):
            wizard.action_add_to_wishlist()

    # ── Vérification sur les sources ────────────────────────────────────────

    def _verify(self, line, aggregator):
        with patch.object(ComicAiDiscoveryLine, "_get_aggregator", lambda self: aggregator):
            line.action_verify()

    def test_verify_found_prefers_volume_1(self):
        wizard = self._wizard()
        line = self._line(wizard, "Undertaker")
        results = [
            ComicSourceResult(source="google", title="Undertaker - Tome 2", serie_name="Undertaker", tome=2),
            ComicSourceResult(source="bnf", title="Autre chose", serie_name="Autre"),
            ComicSourceResult(
                source="google",
                title="Le Mangeur d'or",
                serie_name="Undertaker",
                tome=1,
                isbn=ISBN_T1,
                editeur="Dargaud",
                auteurs=[{"name": "Xavier Dorison", "role": "scenariste"}],
            ),
        ]
        self._verify(line, _fake_aggregator(results))
        self.assertEqual(line.verify_state, "found")
        self.assertEqual((line.verified_isbn, line.verified_editeur), (ISBN_T1, "Dargaud"))
        self.assertEqual(line.verified_title, "Le Mangeur d'or")
        self.assertIn("Google Books", line.verify_info)
        self.assertIn("Xavier Dorison", line.verify_info)
        # La vérification renseigne la création
        line.selected = True
        wizard._add_selected_to_wishlist()
        work = self.env["comic.serie"].search([("name", "=", "Undertaker")]).work_ids
        self.assertEqual(work.titre_canonique, "Le Mangeur d'or")
        self.assertEqual(work.primary_edition_id.isbn_ids.isbn_13, ISBN_T1)

    def test_verify_not_found_and_errors(self):
        wizard = self._wizard()
        line = self._line(wizard, "Série imaginaire")
        self._verify(line, _fake_aggregator([ComicSourceResult(source="google", title="Rien à voir")]))
        self.assertEqual(line.verify_state, "not_found")
        self._verify(line, _fake_aggregator(raise_exc=GoogleBooksQuotaError("429")))
        self.assertEqual(line.verify_state, "error")
        self.assertIn("Quota", line.verify_info)
        self._verify(line, _fake_aggregator(raise_exc=RuntimeError("down")))
        self.assertEqual(line.verify_state, "error")

    def test_verify_other_volume_does_not_set_isbn(self):
        wizard = self._wizard()
        line = self._line(wizard, "Undertaker")
        result = ComicSourceResult(
            source="openlibrary", title="Undertaker T3", serie_name="Undertaker", tome=3, isbn=ISBN_T1
        )
        self._verify(line, _fake_aggregator([result]))
        self.assertEqual(line.verify_state, "found")
        self.assertFalse(line.verified_isbn)
