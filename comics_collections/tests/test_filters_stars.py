"""Filtres et regroupements des albums (US-066) et note en étoiles (US-067).

Lancement :
    docker exec odoo-web odoo -d odoo -u comics_collections \
        --test-tags /comics_collections:TestFiltersStars
"""

from odoo.tests import new_test_user, tagged
from odoo.tests.common import TransactionCase

# Domaines repris tels quels de view_comic_work_search
DOMAIN_PRETES = [("edition_ids.pret_ids", "any", [("retourne", "=", False)])]


def domain_note(uid, minimum):
    return [
        (
            "edition_ids.customer_album_ids",
            "any",
            [("partner_id.user_ids", "in", [uid]), ("note", ">=", minimum)],
        )
    ]


@tagged("post_install", "-at_install", "comics_collections", "filters_stars")
class TestFiltersStars(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        groups = "comics_collections.group_comic_user"
        cls.user_a = new_test_user(cls.env, login="comic_stars_a", groups=groups)
        cls.user_b = new_test_user(cls.env, login="comic_stars_b", groups=groups)
        cls.genre = cls.env["comic.genre"].create({"name": "Genre Étoiles"})
        cls.serie = cls.env["comic.serie"].create({"name": "Série Étoiles", "type": "manga", "genre_id": cls.genre.id})
        cls.works = cls.env["comic.work"].create(
            [{"serie_id": cls.serie.id, "titre_canonique": f"Étoiles T{i}", "tome": i} for i in (1, 2, 3)]
        )
        cls.editions = cls.works.mapped("primary_edition_id")
        cls.Album = cls.env["comic.customer.album"]
        cls.borrower = cls.env["res.partner"].create({"name": "Emprunteur Étoiles"})

    # ── US-067 : note_etoiles ───────────────────────────────────────────────

    def test_note_etoiles_compute(self):
        album = self.Album.create({"partner_id": self.user_a.partner_id.id, "edition_id": self.editions[0].id})
        self.assertEqual(album.note_etoiles, "0")
        album.note = 3.0
        self.assertEqual(album.note_etoiles, "3")
        album.note = 4.6
        self.assertEqual(album.note_etoiles, "5")
        album.note = 1.2
        self.assertEqual(album.note_etoiles, "1")

    def test_note_etoiles_inverse(self):
        album = self.Album.create({"partner_id": self.user_a.partner_id.id, "edition_id": self.editions[0].id})
        album.note_etoiles = "4"
        self.assertEqual(album.note, 4.0)
        album.note_etoiles = "0"
        self.assertEqual(album.note, 0.0)
        # À la création aussi
        other = self.Album.create(
            {"partner_id": self.user_a.partner_id.id, "edition_id": self.editions[1].id, "note_etoiles": "2"}
        )
        self.assertEqual(other.note, 2.0)

    # ── US-066 : related stockés ────────────────────────────────────────────

    def test_related_genre_and_type(self):
        work = self.works[0]
        self.assertEqual(work.genre_id, self.genre)
        self.assertEqual(work.serie_type, "manga")
        self.assertTrue(self.env["comic.work"]._fields["genre_id"].store)
        self.assertTrue(self.env["comic.work"]._fields["serie_type"].store)
        # Suivent la série
        other_genre = self.env["comic.genre"].create({"name": "Autre Genre Étoiles"})
        self.serie.write({"genre_id": other_genre.id, "type": "bd"})
        self.assertEqual(work.genre_id, other_genre)
        self.assertEqual(work.serie_type, "bd")
        # Recherche / regroupement possibles (champs stockés)
        groups = self.env["comic.work"]._read_group([("serie_id", "=", self.serie.id)], ["genre_id"], ["__count"])
        self.assertEqual(groups, [(other_genre, 3)])

    def test_library_related_genre(self):
        album = self.Album.create({"partner_id": self.user_a.partner_id.id, "edition_id": self.editions[0].id})
        self.assertEqual(album.genre_id, self.genre)

    # ── US-066 : filtre « Prêtés » (record rules, pas de sudo) ──────────────

    def test_filter_pretes_respects_private_loans(self):
        Pret = self.env["comic.pret"]
        Pret.with_user(self.user_a).create({"edition_id": self.editions[0].id, "partner_id": self.borrower.id})
        rendu = Pret.with_user(self.user_a).create({"edition_id": self.editions[1].id, "partner_id": self.borrower.id})
        rendu.action_retourner()
        Pret.with_user(self.user_b).create({"edition_id": self.editions[2].id, "partner_id": self.borrower.id})

        Work = self.env["comic.work"]
        base = [("serie_id", "=", self.serie.id)]
        self.assertEqual(Work.with_user(self.user_a).search(base + DOMAIN_PRETES), self.works[0])
        self.assertEqual(Work.with_user(self.user_b).search(base + DOMAIN_PRETES), self.works[2])

    def test_edition_pret_ids(self):
        pret = self.env["comic.pret"].create({"edition_id": self.editions[0].id, "partner_id": self.borrower.id})
        self.assertEqual(self.editions[0].pret_ids, pret)

    # ── US-066 : filtres par note de l'utilisateur courant ──────────────────

    def test_filter_note_current_user(self):
        a, b = self.user_a.partner_id, self.user_b.partner_id
        self.Album.create(
            [
                {"partner_id": a.id, "edition_id": self.editions[0].id, "note": 4.0},
                {"partner_id": a.id, "edition_id": self.editions[1].id, "note": 3.0},
                {"partner_id": b.id, "edition_id": self.editions[2].id, "note": 5.0},
            ]
        )
        Work = self.env["comic.work"]
        base = [("serie_id", "=", self.serie.id)]
        self.assertEqual(Work.with_user(self.user_a).search(base + domain_note(self.user_a.id, 4)), self.works[0])
        self.assertEqual(Work.with_user(self.user_a).search(base + domain_note(self.user_a.id, 3)), self.works[:2])
        self.assertEqual(Work.with_user(self.user_b).search(base + domain_note(self.user_b.id, 4)), self.works[2])
