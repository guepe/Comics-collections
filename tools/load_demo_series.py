#!/usr/bin/env python3
"""
Import demo data : Thorgal + Complainte des Landes perdues.
Données extraites du fichier BDGest export "Guepe Collection En Ligne Mai 2026.csv".

Usage:
    python tools/load_demo_series.py
    python tools/load_demo_series.py --url http://localhost:8069 --db mondb --password admin
    python tools/load_demo_series.py --no-covers   # plus rapide, sans images
    python tools/load_demo_series.py --publish      # crée et publie les produits web
"""

import argparse
import base64
import sys
import time
import xmlrpc.client

try:
    import requests
except ImportError:
    sys.exit("pip install requests")


# ── Données extraites du CSV BDGest ───────────────────────────────────────────

SERIES = [
    {
        "name": "Thorgal",
        "type": "bd",
        "editeur": "Le Lombard",
        "genre": "Aventure / Fantasy",
        "albums": [
            # tome, isbn, titre, date_depot_legal, scenariste, dessinateur, dans_collection, etat_lecture
            (5, "2803604078", "Au-delà des ombres", "1983-08-01", "Jean Van Hamme", "Grzegorz Rosinski", True, "lu"),
            (10, "280360549X", "Le pays Qâ", "1986-04-01", "Jean Van Hamme", "Grzegorz Rosinski", True, "lu"),
            (11, "2803605767", "Les yeux de Tanatloc", "1986-10-01", "Jean Van Hamme", "Grzegorz Rosinski", True, "lu"),
            (
                12,
                "2803606399",
                "La cité du dieu perdu",
                "1987-10-01",
                "Jean Van Hamme",
                "Grzegorz Rosinski",
                True,
                "lu",
            ),
            (
                15,
                "2803607549",
                "Le maître des montagnes",
                "1989-10-01",
                "Jean Van Hamme",
                "Grzegorz Rosinski",
                True,
                "lu",
            ),
            (16, "2803608456", "Louve", "1990-11-01", "Jean Van Hamme", "Grzegorz Rosinski", True, "lu"),
            (18, "2803609886", "L'Épée-Soleil", "1992-04-01", "Jean Van Hamme", "Grzegorz Rosinski", True, "lu"),
            (20, "2803611015", "La marque des bannis", "1995-01-01", "Jean Van Hamme", "Grzegorz Rosinski", True, "lu"),
            (21, "2803611619", "La couronne d'Ogotaï", "1995-11-01", "Jean Van Hamme", "Grzegorz Rosinski", True, "lu"),
            (22, "2803612208", "Géants", "1996-11-01", "Jean Van Hamme", "Grzegorz Rosinski", True, "lu"),
            (24, "280361362X", "Arachnéa", "1999-04-01", "Jean Van Hamme", "Grzegorz Rosinski", True, "lu"),
            (25, "2803614146", "Le Mal bleu", "1999-11-01", "Jean Van Hamme", "Grzegorz Rosinski", True, "lu"),
            (
                26,
                "2803616653",
                "Le Royaume sous le Sable",
                "2001-11-01",
                "Jean Van Hamme",
                "Grzegorz Rosinski",
                True,
                "lu",
            ),
            (27, "2803617757", "Le Barbare", "2002-11-01", "Jean Van Hamme", "Grzegorz Rosinski", True, "lu"),
            (28, "2803620030", "Kriss de Valnor", "2004-10-01", "Jean Van Hamme", "Grzegorz Rosinski", True, "lu"),
            (29, "2803621983", "Le Sacrifice", "2006-11-01", "Jean Van Hamme", "Grzegorz Rosinski", False, "non_lu"),
            (30, "9782803622658", "Moi, Jolan", "2007-10-01", "Yves Sente", "Grzegorz Rosinski", True, "lu"),
            (31, "9782803624867", "Le Bouclier de Thor", "2008-11-01", "Yves Sente", "Grzegorz Rosinski", True, "lu"),
            (32, "9782803627547", "La Bataille d'Asgard", "2010-11-01", "Yves Sente", "Grzegorz Rosinski", True, "lu"),
            (33, "9782803629954", "Le Bateau-Sabre", "2011-11-01", "Yves Sente", "Grzegorz Rosinski", True, "lu"),
            (34, "9782803632992", "Kah-Aniel", "2013-11-01", "Yves Sente", "Grzegorz Rosinski", True, "lu"),
            (
                35,
                "9782803635481",
                "Le feu écarlate",
                "2016-11-01",
                "Xavier Dorison",
                "Grzegorz Rosinski",
                False,
                "non_lu",
            ),
            (36, "9782803672172", "Aniel", "2018-11-01", "Yann", "Grzegorz Rosinski", True, "lu"),
            (37, "9782803673728", "L'Ermite de Skellingar", "2019-11-01", "Yann", "Fred Vignaux", True, "lu"),
            (38, "9782803677184", "La Selkie", "2020-11-01", "Yann", "Fred Vignaux", True, "lu"),
            (39, "9782803680313", "Neokóra", "2021-11-01", "Yann", "Fred Vignaux", True, "lu"),
            (40, "9782808203470", "Tupilaks", "2022-11-01", "Yann", "Fred Vignaux", False, "non_lu"),
            (41, "9782808210850", "Mille yeux", "2023-11-01", "Yann", "Fred Vignaux", False, "non_lu"),
            (42, "9782808212939", "Ézurr le Varègue", "2024-11-01", "Yann", "Fred Vignaux", False, "non_lu"),
            (
                43,
                "9782808214865",
                "La vengeance de la déesse Skædhi",
                "2025-11-01",
                "Yann",
                "Fred Vignaux",
                False,
                "non_lu",
            ),
        ],
    },
    {
        "name": "Complainte des Landes perdues",
        "type": "bd",
        "editeur": "Dargaud",
        "genre": "Fantastique",
        "albums": [
            (1, "2871290717", "Sioban", "1993-01-01", "Jean Dufaux", "Grzegorz Rosinski", True, "lu"),
            (2, "2871290784", "Sioban 2 - Blackmore", "1994-01-01", "Jean Dufaux", "Grzegorz Rosinski", True, "lu"),
            (3, "2871291004", "Sioban 3 - Dame Gerfaut", "1996-01-01", "Jean Dufaux", "Grzegorz Rosinski", True, "lu"),
            (
                4,
                "2871291691",
                "Sioban 4 - Kyle of Klanach",
                "1998-10-01",
                "Jean Dufaux",
                "Grzegorz Rosinski",
                True,
                "lu",
            ),
            (
                5,
                "2871296839",
                "Les Chevaliers du Pardon 1 - Moriganes",
                "2004-10-01",
                "Jean Dufaux",
                "Philippe Delaby",
                True,
                "lu",
            ),
            (
                6,
                "9782505004646",
                "Les Chevaliers du Pardon 2 - Le Guinea Lord",
                "2008-10-01",
                "Jean Dufaux",
                "Philippe Delaby",
                True,
                "lu",
            ),
            (
                7,
                "9782505013877",
                "Les Chevaliers du Pardon 3 - La Fée Sanctus",
                "2012-06-01",
                "Jean Dufaux",
                "Philippe Delaby",
                True,
                "lu",
            ),
            (
                8,
                "9782505019794",
                "Les Chevaliers du Pardon 4 - Sill Valt",
                "2014-11-01",
                "Jean Dufaux",
                "Philippe Delaby",
                True,
                "lu",
            ),
            (
                9,
                "9782505063506",
                "Les Sorcières 1 - Tête noire",
                "2015-10-01",
                "Jean Dufaux",
                "Béatrice Tillier",
                True,
                "lu",
            ),
            (
                10,
                "9782505063995",
                "Les Sorcières 2 - Inferno",
                "2019-01-01",
                "Jean Dufaux",
                "Béatrice Tillier",
                True,
                "lu",
            ),
            (
                11,
                "9782505078197",
                "Les Sorcières 3 - Regina Obscura",
                "2023-03-01",
                "Jean Dufaux",
                "Béatrice Tillier",
                True,
                "lu",
            ),
            (13, "9782505082682", "Les Sudenne 1 - Lord Heron", "2021-10-01", "Jean Dufaux", "Paul Teng", True, "lu"),
            (14, "9782505111542", "Les Sudenne 2 - Aylissa", "2022-10-01", "Jean Dufaux", "Paul Teng", True, "lu"),
            (
                15,
                "9782505113607",
                "Les Sudenne 3 - La Folie Seamus",
                "2023-10-01",
                "Jean Dufaux",
                "Paul Teng",
                False,
                "non_lu",
            ),
            (
                16,
                "9782505122739",
                "Les Sudenne 4 - Lady O'Mara",
                "2024-11-01",
                "Jean Dufaux",
                "Paul Teng",
                False,
                "non_lu",
            ),
        ],
    },
]


# ── ISBN normalisation ─────────────────────────────────────────────────────────


def isbn_to_ean13(isbn):
    """Convertit ISBN-10 ou ISBN-13 en EAN-13 valide. Retourne None si impossible."""
    s = isbn.replace("-", "").replace(" ", "").upper()
    if len(s) == 13 and s.isdigit():
        return s  # déjà EAN-13
    if len(s) == 10 and s[:9].isdigit() and s[9] in "0123456789X":
        # ISBN-10 → ISBN-13 (préfixe 978)
        body = "978" + s[:9]
        total = sum(int(d) * (1 if i % 2 == 0 else 3) for i, d in enumerate(body))
        check = (10 - total % 10) % 10
        return body + str(check)
    return None


# ── Cover fetching ─────────────────────────────────────────────────────────────


def fetch_cover(isbn):
    isbn_clean = isbn.replace("-", "").replace(" ", "").strip()
    url = f"https://covers.openlibrary.org/b/isbn/{isbn_clean}-L.jpg"
    try:
        r = requests.get(url, timeout=10)
        if r.status_code == 200 and len(r.content) > 500:
            return base64.b64encode(r.content).decode()
    except Exception:
        pass
    return None


# ── Odoo XML-RPC ──────────────────────────────────────────────────────────────


class Odoo:
    def __init__(self, url, db, user, password):
        self.db, self.password = db, password
        common = xmlrpc.client.ServerProxy(f"{url}/xmlrpc/2/common")
        self.uid = common.authenticate(db, user, password, {})
        if not self.uid:
            sys.exit("❌  Authentification échouée")
        self._m = xmlrpc.client.ServerProxy(f"{url}/xmlrpc/2/object")
        print(f"✅  Connecté  db={db}  uid={self.uid}")

    def call(self, model, method, args, kw=None):
        return self._m.execute_kw(self.db, self.uid, self.password, model, method, args, kw or {})

    def search(self, model, domain):
        return self.call(model, "search", [domain])

    def read(self, model, ids, fields):
        return self.call(model, "read", [ids, fields])

    def create(self, model, vals):
        return self.call(model, "create", [vals])

    def write(self, model, ids, vals):
        ids = [ids] if isinstance(ids, int) else ids
        return self.call(model, "write", [ids, vals])

    def get_or_create(self, model, domain, vals):
        ids = self.search(model, domain)
        return ids[0] if ids else self.create(model, vals)


# ── Import ─────────────────────────────────────────────────────────────────────


def import_series(odoo, publish, no_covers):
    category_id = False
    cat_ids = odoo.search("product.category", [("name", "=", "BD")])
    if cat_ids:
        category_id = cat_ids[0]

    stats = {"series": 0, "albums": 0, "products": 0, "covers": 0}
    partner_cache = {}
    genre_cache = {}

    for serie_data in SERIES:
        sname = serie_data["name"]

        # Genre
        genre_id = False
        gname = serie_data.get("genre", "")
        if gname:
            if gname not in genre_cache:
                genre_cache[gname] = odoo.get_or_create("comic.genre", [("name", "=", gname)], {"name": gname})
            genre_id = genre_cache[gname]

        # Éditeur
        ename = serie_data.get("editeur", "")
        editeur_id = False
        if ename:
            editeur_id = odoo.get_or_create("comic.editeur", [("name", "=", ename)], {"name": ename})

        # Série
        serie_id = odoo.get_or_create(
            "comic.serie",
            [("name", "=", sname)],
            {"name": sname, "type": serie_data["type"], "genre_id": genre_id, "editeur_id": editeur_id},
        )
        stats["series"] += 1
        print(f"\n📚  Série : {sname}  (id={serie_id})")

        for tome, isbn, titre, date_depot, scenariste, dessinateur, dans_collection, etat_lecture in serie_data[
            "albums"
        ]:

            # Déduplique : cherche un album existant pour ce tome
            existing = odoo.search("comic.album", [("serie_id", "=", serie_id), ("tome", "=", tome)])
            if existing:
                album_id = existing[0]
                print(f"  ⏭️   T{tome:02d} déjà présent")
            else:
                ean13 = isbn_to_ean13(isbn)
                album_vals = {
                    "name": titre,
                    "serie_id": serie_id,
                    "tome": tome,
                    "isbn": ean13 or False,
                    "date_depot_legal": date_depot,
                    "dans_collection": dans_collection,
                    "etat_lecture": etat_lecture,
                }
                album_id = odoo.create("comic.album", album_vals)
                stats["albums"] += 1
                print(f"  📖  T{tome:02d} — {titre}")

            # Auteurs
            for role, aname in [("scenariste", scenariste), ("dessinateur", dessinateur)]:
                if not aname:
                    continue
                if aname not in partner_cache:
                    partner_cache[aname] = odoo.get_or_create(
                        "res.partner",
                        [("name", "=", aname), ("is_company", "=", False)],
                        {"name": aname},
                    )
                pid = partner_cache[aname]
                if not odoo.search(
                    "comic.album.auteur.line",
                    [
                        ("album_id", "=", album_id),
                        ("partner_id", "=", pid),
                        ("role", "=", role),
                    ],
                ):
                    odoo.create("comic.album.auteur.line", {"album_id": album_id, "partner_id": pid, "role": role})

            # Couverture via Open Library
            ean13 = isbn_to_ean13(isbn)
            if not no_covers and ean13:
                data = odoo.read("comic.album", [album_id], ["image_couverture"])
                if data and not data[0].get("image_couverture"):
                    print(f"     🖼️   ISBN {ean13}…", end=" ", flush=True)
                    cover = fetch_cover(ean13)
                    if cover:
                        odoo.write("comic.album", album_id, {"image_couverture": cover})
                        stats["covers"] += 1
                        print("✅")
                    else:
                        print("(introuvable)")
                    time.sleep(0.4)

            # Produit web
            if publish and isbn:
                data = odoo.read("comic.album", [album_id], ["product_tmpl_id", "image_couverture"])
                if data and not data[0].get("product_tmpl_id"):
                    pname = f"{sname} — {titre} (T{tome})"
                    pvals = {
                        "name": pname,
                        "type": "consu",
                        "comic_album_id": album_id,
                        "barcode": isbn,
                        "is_published": True,
                    }
                    if category_id:
                        pvals["categ_id"] = category_id
                    if data[0].get("image_couverture"):
                        pvals["image_1920"] = data[0]["image_couverture"]
                    pid = odoo.create("product.template", pvals)
                    odoo.write("comic.album", album_id, {"product_tmpl_id": pid})
                    odoo.write("product.template", pid, {"comic_album_id": album_id})
                    stats["products"] += 1
                    print("     🛒  Produit publié")

    return stats


# ── Main ───────────────────────────────────────────────────────────────────────


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--url", default="http://localhost:8069")
    p.add_argument("--db", default="guepe-comics-collections-19-0-32453836")
    p.add_argument("--user", default="admin")
    p.add_argument("--password", default="admin")
    p.add_argument("--publish", action="store_true", help="Créer et publier les produits web")
    p.add_argument("--no-covers", action="store_true", help="Ne pas récupérer les couvertures")
    args = p.parse_args()

    print("\n🚀  Import démo — Thorgal + Complainte des Landes perdues")
    print(f"    {args.url}  db={args.db}\n")

    odoo = Odoo(args.url, args.db, args.user, args.password)
    stats = import_series(odoo, publish=args.publish, no_covers=args.no_covers)

    print("\n✅  Terminé :")
    print(f"    Séries  : {stats['series']}")
    print(f"    Albums  : {stats['albums']} créés")
    print(f"    Produits: {stats['products']}")
    print(f"    Covers  : {stats['covers']} récupérées depuis Open Library")


if __name__ == "__main__":
    main()
