"""Export et valeur de la collection (US-071) : statistiques, CSV, inventaire PDF."""

import datetime
import json

from odoo.exceptions import UserError
from odoo.tests import HttpCase, new_test_user, tagged
from odoo.tests.common import TransactionCase

REPORT_REF = "comics_collections.action_report_comic_collection_inventory"
ISBN_BY_PREFIX = {"Exp": "9782800152851", "Autre": "9782205049435", "Vide": "9782840550006"}


def _populate(env, user, prefix, with_values=True):
    """Create 3 owned albums over 2 series (+1 wishlist) for ``user``.

    Valeurs (si ``with_values``) : T1 12,50 / 20 ; T2 10 / — ; autre série — / 7,25.
    """
    Album = env["comic.customer.album"]
    partner = user.partner_id
    serie_a = env["comic.serie"].create({"name": f"{prefix} Alpha"})
    serie_b = env["comic.serie"].create({"name": f"{prefix} Beta"})
    editions = {}
    for serie, tome in ((serie_a, 1), (serie_a, 2), (serie_a, 3), (serie_b, 1)):
        work = env["comic.work"].create(
            {"serie_id": serie.id, "titre_canonique": f"{serie.name} titre {tome}", "tome": tome}
        )
        editions[(serie.id, tome)] = env["comic.edition"].create({"work_id": work.id})
    env["comic.isbn"].create({"edition_id": editions[(serie_a.id, 1)].id, "isbn_13": ISBN_BY_PREFIX[prefix]})
    values = with_values
    Album.create(
        {
            "partner_id": partner.id,
            "edition_id": editions[(serie_a.id, 1)].id,
            "etat_lecture": "lu",
            "note": 4,
            "prix_achat": 12.5 if values else 0,
            "valeur_estimee": 20 if values else 0,
            "date_ajout": datetime.date(2026, 5, 1),
        }
    )
    Album.create(
        {"partner_id": partner.id, "edition_id": editions[(serie_a.id, 2)].id, "prix_achat": 10 if values else 0}
    )
    Album.create(
        {"partner_id": partner.id, "edition_id": editions[(serie_b.id, 1)].id, "valeur_estimee": 7.25 if values else 0}
    )
    # Wishlist : ses montants ne comptent pas dans la valeur de la collection
    Album.create(
        {
            "partner_id": partner.id,
            "edition_id": editions[(serie_a.id, 3)].id,
            "dans_collection": False,
            "dans_wishlist": True,
            "prix_achat": 99 if values else 0,
        }
    )
    return serie_a, serie_b


@tagged("post_install", "-at_install", "comics_collections", "comic_collection_export")
class TestCollectionValue(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        group = "comics_collections.group_comic_user"
        cls.user = new_test_user(cls.env, login="exp_user", groups=group)
        cls.other = new_test_user(cls.env, login="exp_other", groups=group)
        cls.novalue = new_test_user(cls.env, login="exp_novalue", groups=group)
        cls.serie_a, cls.serie_b = _populate(cls.env, cls.user, "Exp")
        _populate(cls.env, cls.other, "Autre")
        _populate(cls.env, cls.novalue, "Vide", with_values=False)
        cls.Album = cls.env["comic.customer.album"]

    def test_currency_is_company_currency(self):
        entry = self.Album.with_user(self.user).search([], limit=1)
        self.assertEqual(entry.currency_id, self.env.company.currency_id)

    def test_stats_totals(self):
        stats = self.Album._get_collection_stats(self.user.partner_id)
        self.assertAlmostEqual(stats["total_prix_achat"], 22.5)
        self.assertAlmostEqual(stats["total_valeur"], 27.25)
        self.assertEqual(stats["nb_values"], 3)

    def test_dashboard_has_values_and_json(self):
        data = self.Album.with_user(self.user).get_dashboard_data()
        json.loads(json.dumps(data))
        self.assertTrue(data["has_values"])
        self.assertEqual(data["nb_values"], 3)
        self.assertIn("22.50", data["total_prix_achat_display"].replace(",", "."))
        self.assertIn("27.25", data["total_valeur_display"].replace(",", "."))
        self.assertIn(self.env.company.currency_id.symbol, data["total_valeur_display"])

    def test_dashboard_without_values(self):
        data = self.Album.with_user(self.novalue).get_dashboard_data()
        json.loads(json.dumps(data))
        self.assertFalse(data["has_values"])
        self.assertEqual(data["nb_values"], 0)
        self.assertEqual(data["total_prix_achat"], 0)

    def test_action_print_my_inventory_targets_own_collection(self):
        action = self.Album.with_user(self.user).action_print_my_inventory()
        self.assertEqual(action["type"], "ir.actions.report")
        self.assertEqual(action["report_name"], "comics_collections.report_comic_collection_inventory")
        ids = action["context"]["active_ids"]
        entries = self.Album.browse(ids)
        self.assertEqual(len(entries), 3)
        self.assertEqual(entries.partner_id, self.user.partner_id)
        self.assertTrue(all(entries.mapped("dans_collection")))

    def test_action_print_my_inventory_empty(self):
        empty = new_test_user(self.env, login="exp_empty", groups="comics_collections.group_comic_user")
        with self.assertRaises(UserError):
            self.Album.with_user(empty).action_print_my_inventory()

    def test_report_html(self):
        action = self.Album.with_user(self.user).action_print_my_inventory()
        ids = action["context"]["active_ids"]
        html, _fmt = self.env["ir.actions.report"]._render_qweb_html(REPORT_REF, ids)
        html = html.decode()
        self.assertIn("My Collection Inventory", html)
        self.assertIn("Exp Alpha", html)
        self.assertIn("Exp Beta", html)
        self.assertIn("Subtotal", html)
        self.assertIn("Grand total", html)
        self.assertIn("9782800152851", html)
        self.assertIn(self.user.partner_id.name, html)
        # Montants : sous-total Alpha 22,50 ; total valeur 27,25 ; 3 albums
        normalized = html.replace(",", ".")
        self.assertIn("22.50", normalized)
        self.assertIn("27.25", normalized)
        self.assertIn("3 albums", html)
        # Rien de l'autre utilisateur ni de la wishlist
        self.assertNotIn("Autre Alpha", html)
        self.assertNotIn("99.00", normalized)

    def test_report_bound_to_library_list(self):
        report = self.env.ref(REPORT_REF)
        self.assertEqual(report.binding_model_id.model, "comic.customer.album")
        self.assertEqual(report.report_type, "qweb-pdf")


@tagged("post_install", "-at_install", "comics_collections", "comic_collection_export")
class TestCollectionCsvExport(HttpCase):
    URL = "/comics/collection/export.csv"

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        group = "comics_collections.group_comic_user"
        cls.user = new_test_user(cls.env, login="csv_user", password="csv_user_pwd", groups=group)
        cls.other = new_test_user(cls.env, login="csv_other", groups=group)
        _populate(cls.env, cls.user, "Exp")
        _populate(cls.env, cls.other, "Autre")

    def test_csv_content(self):
        self.authenticate("csv_user", "csv_user_pwd")
        response = self.url_open(self.URL)
        self.assertEqual(response.status_code, 200)
        self.assertIn("text/csv", response.headers["Content-Type"])
        disposition = response.headers["Content-Disposition"]
        self.assertRegex(disposition, r'^attachment; filename="my_collection_\d{4}-\d{2}-\d{2}\.csv"$')
        raw = response.content
        self.assertTrue(raw.startswith(b"\xef\xbb\xbf"), "BOM UTF-8 attendu")
        lines = raw.decode("utf-8-sig").splitlines()
        header = lines[0].split(";")
        self.assertEqual(header[0], "Series")
        self.assertEqual(len(header), 12)
        self.assertIn("Purchase price", header)
        rows = [line.split(";") for line in lines[1:]]
        # 3 albums possédés + 1 wishlist, uniquement ceux de l'utilisateur
        self.assertEqual(len(rows), 4)
        self.assertTrue(all(row[0].startswith("Exp ") for row in rows))
        self.assertNotIn("Autre", raw.decode("utf-8-sig"))
        first = rows[0]
        self.assertEqual(first[:4], ["Exp Alpha", "1", "Exp Alpha titre 1", "9782800152851"])
        self.assertEqual(first[5], "Read")
        self.assertEqual(first[6:11], ["Yes", "No", "4.0", "12.50", "20.00"])
        self.assertEqual(first[11], "2026-05-01")
        wishlist = [row for row in rows if row[7] == "Yes"]
        self.assertEqual(len(wishlist), 1)
        self.assertEqual(wishlist[0][6], "No")

    def test_anonymous_refused(self):
        self.authenticate(None, None)
        response = self.url_open(self.URL, allow_redirects=False)
        self.assertIn(response.status_code, (302, 303, 401, 403))
        if response.status_code in (302, 303):
            self.assertIn("/web/login", response.headers["Location"])
        self.assertNotIn(b"Exp Alpha", response.content)
