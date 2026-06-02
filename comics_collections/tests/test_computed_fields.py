"""Tests unitaires pour les champs computed de comic.serie et comic.work.

On injecte des faux recordsets afin de tester la logique sans base de données.
"""

import unittest


# ── Faux objets imitant l'interface Odoo recordset ────────────────────────────


class FakeAlbum:
    def __init__(self, dans_collection=False, image_couverture=None, tome=0):
        self.dans_collection = dans_collection
        self.image_couverture = image_couverture
        self.tome = tome


class FakeAlbumSet:
    def __init__(self, items):
        self._items = list(items)

    def __len__(self):
        return len(self._items)

    def __bool__(self):
        return bool(self._items)

    def __getitem__(self, index):
        return self._items[index]

    def filtered(self, attr):
        return FakeAlbumSet([i for i in self._items if getattr(i, attr, False)])

    def sorted(self, key):
        return FakeAlbumSet(sorted(self._items, key=lambda x: getattr(x, key, 0)))


class FakeSerie:
    """Simule un enregistrement comic.serie unique, itérable comme un recordset Odoo."""

    def __init__(self, albums=None, image_couverture=None):
        self.album_ids = FakeAlbumSet(albums or [])
        self.image_couverture = image_couverture
        self.nb_albums_total = 0
        self.nb_albums_possedes = 0
        self.has_cover = False
        self.first_album_cover_id = False

    def __iter__(self):
        yield self


# ── Logique extraite (miroir exact du code production) ────────────────────────


def _compute_albums(self):
    for serie in self:
        serie.nb_albums_total = len(serie.album_ids)
        serie.nb_albums_possedes = len(serie.album_ids.filtered("dans_collection"))


def _compute_has_cover(self):
    for rec in self:
        rec.has_cover = bool(rec.image_couverture)


def _compute_first_album_cover(self):
    for serie in self:
        album = serie.album_ids.filtered("image_couverture").sorted("tome")
        serie.first_album_cover_id = album[0] if album else False


# ── Tests ─────────────────────────────────────────────────────────────────────


class TestComputeAlbums(unittest.TestCase):

    def _run(self, albums):
        serie = FakeSerie(albums)
        _compute_albums(serie)
        return serie

    def test_no_albums(self):
        s = self._run([])
        self.assertEqual(s.nb_albums_total, 0)
        self.assertEqual(s.nb_albums_possedes, 0)

    def test_all_in_collection(self):
        s = self._run([FakeAlbum(True), FakeAlbum(True), FakeAlbum(True)])
        self.assertEqual(s.nb_albums_total, 3)
        self.assertEqual(s.nb_albums_possedes, 3)

    def test_none_in_collection(self):
        s = self._run([FakeAlbum(False), FakeAlbum(False)])
        self.assertEqual(s.nb_albums_total, 2)
        self.assertEqual(s.nb_albums_possedes, 0)

    def test_partial_collection(self):
        s = self._run([FakeAlbum(True), FakeAlbum(False), FakeAlbum(True)])
        self.assertEqual(s.nb_albums_total, 3)
        self.assertEqual(s.nb_albums_possedes, 2)

    def test_single_possessed(self):
        s = self._run([FakeAlbum(True)])
        self.assertEqual(s.nb_albums_total, 1)
        self.assertEqual(s.nb_albums_possedes, 1)


class TestComputeHasCover(unittest.TestCase):

    def _run(self, image):
        serie = FakeSerie(image_couverture=image)
        _compute_has_cover(serie)
        return serie

    def test_with_cover(self):
        s = self._run(b"fake_image_data")
        self.assertTrue(s.has_cover)

    def test_without_cover(self):
        s = self._run(None)
        self.assertFalse(s.has_cover)

    def test_empty_bytes(self):
        s = self._run(b"")
        self.assertFalse(s.has_cover)


class TestComputeFirstAlbumCover(unittest.TestCase):

    def _run(self, albums):
        serie = FakeSerie(albums)
        _compute_first_album_cover(serie)
        return serie

    def test_no_albums(self):
        s = self._run([])
        self.assertFalse(s.first_album_cover_id)

    def test_no_cover_at_all(self):
        s = self._run([FakeAlbum(tome=1), FakeAlbum(tome=2)])
        self.assertFalse(s.first_album_cover_id)

    def test_picks_lowest_tome_with_cover(self):
        a1 = FakeAlbum(tome=3, image_couverture=b"img3")
        a2 = FakeAlbum(tome=1, image_couverture=b"img1")
        a3 = FakeAlbum(tome=2, image_couverture=None)
        s = self._run([a1, a2, a3])
        self.assertIs(s.first_album_cover_id, a2)

    def test_single_album_with_cover(self):
        a = FakeAlbum(tome=1, image_couverture=b"img")
        s = self._run([a])
        self.assertIs(s.first_album_cover_id, a)


if __name__ == "__main__":
    unittest.main()
