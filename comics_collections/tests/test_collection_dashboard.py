"""Tableau de bord collectionneur (US-065) : données sérialisables, propres à l'utilisateur."""

import datetime
import json

from odoo.tests import HttpCase, new_test_user, tagged
from odoo.tests.common import TransactionCase

# Attend le rendu de l'action client puis signale le succès (un console.error fait échouer le test).
WAIT_FOR_DASHBOARD = """
const deadline = Date.now() + 20000;
(function check() {
    const root = document.querySelector('.o_comic_dashboard');
    if (root && root.querySelector('%s')) {
        console.log('test successful');
    } else if (Date.now() > deadline) {
        console.error('Tableau de bord collectionneur non rendu');
    } else {
        setTimeout(check, 100);
    }
})();
"""


def _populate(env, user, prefix):
    """Create a small library for ``user``: 2 owned albums (1 rated), 1 wishlist."""
    serie = env["comic.serie"].create({"name": f"{prefix} Série"})
    editions = []
    for tome in (1, 2, 3):
        work = env["comic.work"].create({"serie_id": serie.id, "titre_canonique": f"{prefix} T{tome}", "tome": tome})
        editions.append(env["comic.edition"].create({"work_id": work.id}))
    Album = env["comic.customer.album"]
    partner = user.partner_id
    Album.create(
        {
            "partner_id": partner.id,
            "edition_id": editions[0].id,
            "etat_lecture": "lu",
            "note": 4,
            "date_ajout": datetime.date(2026, 5, 1),
        }
    )
    Album.create({"partner_id": partner.id, "edition_id": editions[1].id, "date_ajout": datetime.date(2026, 6, 1)})
    Album.create(
        {"partner_id": partner.id, "edition_id": editions[2].id, "dans_collection": False, "dans_wishlist": True}
    )
    return serie


@tagged("post_install", "-at_install", "comics_collections", "comic_collection_dashboard")
class TestCollectionDashboard(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = new_test_user(cls.env, login="dash_user", groups="comics_collections.group_comic_user")
        cls.other = new_test_user(cls.env, login="dash_other", groups="comics_collections.group_comic_user")
        cls.empty = new_test_user(cls.env, login="dash_empty", groups="comics_collections.group_comic_user")
        cls.serie = _populate(cls.env, cls.user, "Dash")
        # Bibliothèque plus fournie chez l'autre utilisateur, qui ne doit jamais apparaître
        _populate(cls.env, cls.other, "Autre")
        _populate(cls.env, cls.other, "Autre bis")
        edition = cls.env["comic.edition"].search([("work_id.serie_id", "=", cls.serie.id)], limit=1)
        cls.env["comic.pret"].with_user(cls.user).create(
            {
                "edition_id": edition.id,
                "partner_id": cls.other.partner_id.id,
                "date_pret": datetime.date(2026, 1, 1),
                "date_retour_prevue": datetime.date(2026, 1, 15),
            }
        )

    def _data(self, user):
        return self.env["comic.customer.album"].with_user(user).get_dashboard_data()

    def test_json_serializable(self):
        data = self._data(self.user)
        # Lève TypeError si une date ou un objet non JSON subsiste
        json.loads(json.dumps(data))
        self.assertEqual(data["recent"][0]["date"], "2026-06-01")

    def test_current_user_figures(self):
        data = self._data(self.user)
        self.assertEqual(data["nb_albums"], 2)
        self.assertEqual(data["nb_wishlist"], 1)
        self.assertEqual(data["nb_series"], 1)
        self.assertEqual(data["series_completes"], 0)
        self.assertEqual(data["series_en_cours"], 1)
        self.assertEqual(data["loans_late"], 1)
        self.assertEqual([row["name"] for row in data["top_series"]], ["Dash Série"])
        self.assertEqual({row["work_id"] for row in data["recent"]}, set(self.serie.work_ids[:2].ids))

    def test_other_user_figures(self):
        data = self._data(self.other)
        self.assertEqual(data["nb_albums"], 4)
        self.assertEqual(data["nb_wishlist"], 2)
        self.assertEqual(data["loans_late"], 0)
        self.assertNotIn("Dash Série", [row["name"] for row in data["top_series"]])

    def test_breakdowns_with_percent(self):
        data = self._data(self.user)
        self.assertEqual(data["by_genre"], [{"label": "No genre", "count": 2, "percent": 100.0}])
        reading = {row["key"]: (row["label"], row["count"], row["percent"]) for row in data["by_reading"]}
        self.assertEqual(reading["lu"], ("Read", 1, 50.0))
        self.assertEqual(reading["non_lu"], ("Unread", 1, 50.0))
        self.assertEqual(reading["en_cours"], ("Reading", 0, 0.0))

    def test_empty_library(self):
        data = self._data(self.empty)
        json.dumps(data)
        self.assertEqual(data["nb_albums"], 0)
        self.assertEqual(data["recent"], [])
        self.assertTrue(all(row["percent"] == 0.0 for row in data["by_reading"]))


@tagged("post_install", "-at_install", "comics_collections", "comic_collection_dashboard")
class TestCollectionDashboardUi(HttpCase):
    """Le bundle JS se charge et l'action client se rend dans le navigateur headless."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = new_test_user(cls.env, login="dash_ui", groups="comics_collections.group_comic_user")
        cls.empty = new_test_user(cls.env, login="dash_ui_empty", groups="comics_collections.group_comic_user")
        _populate(cls.env, cls.user, "UI")

    def test_dashboard_renders(self):
        self.browser_js(
            "/odoo/action-comics_collections.action_comic_collection_dashboard",
            WAIT_FOR_DASHBOARD % ".o_comic_kpi",
            login="dash_ui",
        )

    def test_dashboard_empty_state(self):
        self.browser_js(
            "/odoo/action-comics_collections.action_comic_collection_dashboard",
            WAIT_FOR_DASHBOARD % ".o_comic_dashboard .o_view_nocontent",
            login="dash_ui_empty",
        )
