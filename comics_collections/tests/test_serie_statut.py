"""Statut de série « Inconnu » par défaut et migration 19.0.4.6.0."""

import importlib.util

from odoo.tests import tagged
from odoo.tests.common import TransactionCase
from odoo.tools.misc import file_path


@tagged("post_install", "-at_install", "comics_collections")
class TestSerieStatut(TransactionCase):
    def test_new_serie_status_unknown(self):
        serie = self.env["comic.serie"].create({"name": "Série statut neuve"})
        self.assertEqual(serie.statut, "inconnu")
        self.assertIn(serie, self.env["comic.serie"].search([("statut", "=", "inconnu")]))

    def test_migration_only_untouched_ongoing(self):
        Serie = self.env["comic.serie"]
        untouched = Serie.create({"name": "Série jamais vérifiée", "statut": "en_cours"})
        checked = Serie.create({"name": "Série vérifiée", "statut": "en_cours"})
        # Trace de suivi d'un changement de statut : choix explicite de l'utilisateur
        message = checked.message_post(body="Status checked")
        self.env["mail.tracking.value"].create(
            {
                "mail_message_id": message.id,
                "field_id": self.env["ir.model.fields"]._get("comic.serie", "statut").id,
                "old_value_char": "Unknown",
                "new_value_char": "Ongoing",
            }
        )
        done = Serie.create({"name": "Série terminée", "statut": "terminee"})
        path = file_path("comics_collections/migrations/19.0.4.6.0/post-migrate.py")
        spec = importlib.util.spec_from_file_location("comics_post_migrate_46", path)
        migration = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(migration)
        migration.migrate(self.env.cr, "19.0.4.5.0")
        self.assertEqual(untouched.statut, "inconnu")
        self.assertEqual(checked.statut, "en_cours")
        self.assertEqual(done.statut, "terminee")


@tagged("post_install", "-at_install", "comics_collections")
class TestMyRatingStars(TransactionCase):
    def test_album_rating_and_series_average(self):
        from odoo.tests import new_test_user

        user = new_test_user(self.env, login="stars_user", groups="comics_collections.group_comic_user")
        serie = self.env["comic.serie"].create({"name": "Série étoiles"})
        Work = self.env["comic.work"]
        w1 = Work.create({"serie_id": serie.id, "titre_canonique": "É1", "tome": 1})
        w2 = Work.create({"serie_id": serie.id, "titre_canonique": "É2", "tome": 2})
        Album = self.env["comic.customer.album"]
        for work in (w1, w2):
            Album.create({"partner_id": user.partner_id.id, "edition_id": work.primary_edition_id.id})
        w1.with_user(user).my_note_etoiles = "5"
        w2.with_user(user).my_note_etoiles = "2"
        self.assertEqual(w1.with_user(user).my_note_etoiles, "5")
        entry = Album.search([("partner_id", "=", user.partner_id.id), ("work_id", "=", w2.id)])
        self.assertEqual(entry.note, 2.0)
        serie.invalidate_recordset()
        self.assertEqual(serie.with_user(user).my_rating_stars, "4")  # (5 + 2) / 2 = 3.5 → 4
        # Pas possédé : pas de note (et l'écriture ne crée rien)
        other = new_test_user(self.env, login="stars_other", groups="comics_collections.group_comic_user")
        self.assertEqual(w1.with_user(other).my_note_etoiles, "0")
