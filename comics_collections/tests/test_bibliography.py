"""Fiches auteur et éditeur : séries et albums auxquels ils ont participé."""

from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install", "comics_collections", "bibliography")
class TestBibliography(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.author = cls.env["res.partner"].create({"name": "Auteur Biblio"})
        cls.other = cls.env["res.partner"].create({"name": "Autre Auteur Biblio"})
        cls.editeur = cls.env["comic.editeur"].create({"name": "Éditeur Biblio"})
        cls.editeur_serie = cls.env["comic.editeur"].create({"name": "Éditeur Série Biblio"})
        cls.serie_a = cls.env["comic.serie"].create({"name": "Biblio A"})
        cls.serie_b = cls.env["comic.serie"].create({"name": "Biblio B", "editeur_id": cls.editeur_serie.id})
        Work = cls.env["comic.work"]
        cls.a2 = Work.create({"serie_id": cls.serie_a.id, "tome": 2, "titre_canonique": "A2"})
        cls.a1 = Work.create({"serie_id": cls.serie_a.id, "tome": 1, "titre_canonique": "A1"})
        cls.b1 = Work.create({"serie_id": cls.serie_b.id, "tome": 1, "titre_canonique": "B1"})
        Line = cls.env["comic.work.auteur.line"]
        for work, role in (
            (cls.a1, "scenariste"),
            (cls.a2, "scenariste"),
            (cls.a2, "dessinateur"),
            (cls.b1, "coloriste"),
        ):
            Line.create({"work_id": work.id, "partner_id": cls.author.id, "role": role})
        Line.create({"work_id": cls.a1.id, "partner_id": cls.other.id, "role": "dessinateur"})
        (cls.a1 | cls.a2).primary_edition_id.editeur_id = cls.editeur

    def test_author_works_and_series(self):
        self.assertEqual(self.author.comic_work_count, 3)  # A2 compté une fois malgré 2 rôles
        self.assertEqual(self.author.comic_serie_count, 2)
        self.assertEqual(self.author.comic_work_ids.ids, (self.a1 | self.a2 | self.b1).ids)
        self.assertEqual(self.author.comic_serie_ids, self.serie_a | self.serie_b)
        self.assertEqual(self.other.comic_work_ids, self.a1)

    def test_author_line_related_fields(self):
        line = self.author.auteur_work_line_ids.filtered(lambda ln: ln.work_id == self.a2)[:1]
        self.assertEqual(line.serie_id, self.serie_a)
        self.assertEqual(line.tome, 2)

    def test_editeur_catalogue(self):
        self.assertEqual(self.editeur.comic_work_ids.ids, (self.a1 | self.a2).ids)
        self.assertEqual(self.editeur.comic_serie_ids, self.serie_a)
        # éditeur principal d'une série sans édition rattachée : la série apparaît quand même
        self.assertEqual(self.editeur_serie.comic_serie_ids, self.serie_b)
        self.assertEqual(self.editeur_serie.comic_work_count, 0)

    def test_actions(self):
        action = self.author.action_view_comic_works()
        self.assertEqual(action["res_model"], "comic.work")
        self.assertEqual(set(action["domain"][0][2]), set((self.a1 | self.a2 | self.b1).ids))
        action = self.editeur.action_view_comic_series()
        self.assertEqual(action["res_model"], "comic.serie")
        self.assertEqual(action["domain"][0][2], self.serie_a.ids)

    def test_forms_load(self):
        self.env["res.partner"].get_views([(False, "form")])
        self.env["comic.editeur"].get_views([(False, "form")])
