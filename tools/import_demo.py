#!/usr/bin/env python3
"""
Import BD demo data from Excel into Odoo via XML-RPC.

Usage:
    python tools/import_demo.py --file mes_bds.xlsx
    python tools/import_demo.py --file mes_bds.xlsx --url http://localhost:8069 --db mondb --password admin

Colonnes Excel attendues (noms flexibles, insensible à la casse) :
    serie / série       Nom de la série
    type                bd | manga | comics | one_shot (ou BD, Manga…)
    editeur / éditeur   Nom de l'éditeur
    genre               Genre (optionnel)
    tome                Numéro du tome (entier)
    titre               Titre de l'album
    isbn                ISBN-13 (utilisé pour récupérer la couverture automatiquement)
    date_parution       Date de parution (YYYY-MM-DD ou DD/MM/YYYY)
    nb_pages            Nombre de pages (optionnel)
    scenariste          Nom du scénariste (optionnel)
    dessinateur         Nom du dessinateur (optionnel)
    coloriste           Nom du coloriste (optionnel)
    synopsis            Synopsis texte (optionnel)
    dans_collection     oui / non / 1 / 0
    publier_sur_web     oui / non / 1 / 0  → crée et publie le produit website_sale

Dépendances : pip install openpyxl requests
"""

import argparse
import base64
import sys
import time
import xmlrpc.client
from datetime import datetime, date

try:
    import openpyxl
except ImportError:
    sys.exit("❌  Manque : pip install openpyxl")

try:
    import requests
except ImportError:
    sys.exit("❌  Manque : pip install requests")


# ── Helpers ────────────────────────────────────────────────────────────────────

def _bool(val):
    if val is None:
        return False
    return str(val).strip().lower() in ('oui', 'yes', '1', 'true', 'vrai', 'x')


def _str(val):
    if val is None:
        return ''
    return str(val).strip()


def _int(val):
    try:
        return int(val)
    except (TypeError, ValueError):
        return 0


def _date(val):
    if not val:
        return False
    if isinstance(val, (datetime, date)):
        return val.strftime('%Y-%m-%d')
    s = str(val).strip()
    for fmt in ('%Y-%m-%d', '%d/%m/%Y', '%d-%m-%Y', '%Y/%m/%d'):
        try:
            return datetime.strptime(s, fmt).strftime('%Y-%m-%d')
        except ValueError:
            pass
    return False


_TYPE_MAP = {
    'bd': 'bd', 'bande dessinée': 'bd', 'bande dessinee': 'bd',
    'manga': 'manga',
    'comics': 'comics', 'comic': 'comics',
    'one_shot': 'one_shot', 'one-shot': 'one_shot', 'oneshot': 'one_shot',
}


def _type(val):
    return _TYPE_MAP.get(_str(val).lower(), 'bd')


def _normalize_header(h):
    if h is None:
        return ''
    return (str(h).strip().lower()
            .replace('é', 'e').replace('è', 'e').replace('ê', 'e')
            .replace('à', 'a').replace('â', 'a')
            .replace('î', 'i').replace('ï', 'i')
            .replace('ô', 'o').replace('û', 'u')
            .replace(' ', '_').replace('-', '_'))


# ── Cover fetching ─────────────────────────────────────────────────────────────

def fetch_cover(isbn, size='L'):
    """Retourne base64 de la couverture Open Library ou None."""
    if not isbn:
        return None
    isbn_clean = str(isbn).replace('-', '').replace(' ', '').strip()
    if not isbn_clean.isdigit():
        return None
    url = f"https://covers.openlibrary.org/b/isbn/{isbn_clean}-{size}.jpg"
    try:
        resp = requests.get(url, timeout=10)
        # Open Library retourne une image 1x1 quand introuvable (< 500 octets)
        if resp.status_code == 200 and len(resp.content) > 500:
            return base64.b64encode(resp.content).decode()
    except Exception:
        pass
    return None


# ── Odoo XML-RPC ──────────────────────────────────────────────────────────────

class OdooClient:
    def __init__(self, url, db, user, password):
        self.db = db
        self.password = password
        common = xmlrpc.client.ServerProxy(f"{url}/xmlrpc/2/common")
        self.uid = common.authenticate(db, user, password, {})
        if not self.uid:
            sys.exit("❌  Authentification Odoo échouée. Vérifiez --user et --password.")
        self._models = xmlrpc.client.ServerProxy(f"{url}/xmlrpc/2/object")
        print(f"✅  Connecté à {url} (db={db}, uid={self.uid})")

    def _call(self, model, method, args, kwargs=None):
        return self._models.execute_kw(
            self.db, self.uid, self.password,
            model, method, args, kwargs or {}
        )

    def search(self, model, domain):
        return self._call(model, 'search', [domain])

    def read(self, model, ids, fields):
        return self._call(model, 'read', [ids, fields])

    def create(self, model, vals):
        return self._call(model, 'create', [vals])

    def write(self, model, ids, vals):
        return self._call(model, 'write', [[ids] if isinstance(ids, int) else ids, vals])

    def get_or_create(self, model, domain, create_vals):
        ids = self.search(model, domain)
        if ids:
            return ids[0]
        return self.create(model, create_vals)


# ── Import logic ───────────────────────────────────────────────────────────────

def load_rows(filepath):
    wb = openpyxl.load_workbook(filepath, data_only=True)
    ws = wb.active
    rows = list(ws.iter_rows(values_only=True))
    if not rows:
        sys.exit("❌  Fichier Excel vide.")

    raw_headers = rows[0]
    headers = [_normalize_header(h) for h in raw_headers]
    print(f"📋  Colonnes détectées : {headers}")

    required = {'serie', 'titre'}
    missing = required - set(headers)
    if missing:
        sys.exit(f"❌  Colonnes obligatoires manquantes : {missing}")

    def col(row_dict, *names):
        for n in names:
            n2 = _normalize_header(n)
            if n2 in row_dict:
                return row_dict[n2]
        return None

    records = []
    for row in rows[1:]:
        d = dict(zip(headers, row))
        if not any(v for v in d.values()):
            continue  # ligne vide
        records.append(d)

    return records, col


def run_import(odoo, records, col, publish, no_covers):
    category_ids = odoo.search('product.category', [('name', '=', 'BD')])
    category_id = category_ids[0] if category_ids else False

    stats = {'series': 0, 'albums': 0, 'products': 0, 'covers': 0, 'skipped': 0}
    serie_cache = {}
    genre_cache = {}
    editeur_cache = {}
    partner_cache = {}

    for i, row in enumerate(records, 1):
        serie_name = _str(col(row, 'serie', 'série'))
        titre = _str(col(row, 'titre', 'titre_album', 'album'))
        if not serie_name or not titre:
            print(f"  ⚠️  Ligne {i+1} ignorée (série ou titre vide)")
            stats['skipped'] += 1
            continue

        # ── Série ──────────────────────────────────────────────────────
        if serie_name not in serie_cache:
            genre_name = _str(col(row, 'genre'))
            editeur_name = _str(col(row, 'editeur', 'éditeur'))
            genre_id = False
            editeur_id = False

            if genre_name:
                if genre_name not in genre_cache:
                    genre_cache[genre_name] = odoo.get_or_create(
                        'comic.genre',
                        [('name', '=', genre_name)],
                        {'name': genre_name},
                    )
                genre_id = genre_cache[genre_name]

            if editeur_name:
                if editeur_name not in editeur_cache:
                    editeur_cache[editeur_name] = odoo.get_or_create(
                        'comic.editeur',
                        [('name', '=', editeur_name)],
                        {'name': editeur_name},
                    )
                editeur_id = editeur_cache[editeur_name]

            serie_id = odoo.get_or_create(
                'comic.serie',
                [('name', '=', serie_name)],
                {
                    'name': serie_name,
                    'type': _type(col(row, 'type')),
                    'genre_id': genre_id,
                    'editeur_id': editeur_id,
                },
            )
            serie_cache[serie_name] = serie_id
            if not odoo.search('comic.serie', [('name', '=', serie_name), ('id', '<', serie_id)]):
                stats['series'] += 1
                print(f"  📚  Série créée : {serie_name}")
        else:
            serie_id = serie_cache[serie_name]

        # ── Album ──────────────────────────────────────────────────────
        isbn = _str(col(row, 'isbn'))
        tome = _int(col(row, 'tome'))
        date_parution = _date(col(row, 'date_parution', 'date', 'parution'))
        dans_collection = _bool(col(row, 'dans_collection', 'collection'))

        existing = odoo.search('comic.album', [
            ('serie_id', '=', serie_id),
            ('tome', '=', tome),
        ])
        if existing:
            album_id = existing[0]
            print(f"  ⏭️  Album existant : {serie_name} T{tome} — {titre}")
        else:
            album_vals = {
                'name': titre,
                'serie_id': serie_id,
                'tome': tome,
                'isbn': isbn or False,
                'date_parution': date_parution,
                'nb_pages': _int(col(row, 'nb_pages', 'pages')) or False,
                'synopsis': _str(col(row, 'synopsis')) or False,
                'dans_collection': dans_collection,
                'etat_lecture': 'non_lu',
            }
            album_id = odoo.create('comic.album', album_vals)
            stats['albums'] += 1
            print(f"  📖  Album créé   : {serie_name} T{tome} — {titre}")

        # ── Auteurs ────────────────────────────────────────────────────
        roles = {
            'scenariste': _str(col(row, 'scenariste', 'scénariste')),
            'dessinateur': _str(col(row, 'dessinateur')),
            'coloriste': _str(col(row, 'coloriste')),
        }
        for role, name in roles.items():
            if not name:
                continue
            if name not in partner_cache:
                partner_cache[name] = odoo.get_or_create(
                    'res.partner',
                    [('name', '=', name), ('is_company', '=', False)],
                    {'name': name},
                )
            partner_id = partner_cache[name]
            already = odoo.search('comic.album.auteur.line', [
                ('album_id', '=', album_id),
                ('partner_id', '=', partner_id),
                ('role', '=', role),
            ])
            if not already:
                odoo.create('comic.album.auteur.line', {
                    'album_id': album_id,
                    'partner_id': partner_id,
                    'role': role,
                })

        # ── Couverture (Open Library par ISBN) ─────────────────────────
        if not no_covers and isbn:
            existing_data = odoo.read('comic.album', [album_id], ['image_couverture'])
            if existing_data and not existing_data[0].get('image_couverture'):
                print(f"     🖼️  Récupération couverture ISBN {isbn}…", end=' ', flush=True)
                cover = fetch_cover(isbn)
                if cover:
                    odoo.write('comic.album', album_id, {'image_couverture': cover})
                    stats['covers'] += 1
                    print("✅")
                else:
                    print("(introuvable)")
                time.sleep(0.5)  # politesse envers Open Library

        # ── Produit website ────────────────────────────────────────────
        should_publish = _bool(col(row, 'publier_sur_web', 'web', 'website', 'published'))
        if (publish or should_publish) and isbn:
            album_data = odoo.read('comic.album', [album_id], ['product_tmpl_id'])[0]
            if not album_data.get('product_tmpl_id'):
                product_vals = {
                    'name': f"{serie_name} — {titre}" + (f" (T{tome})" if tome else ''),
                    'type': 'consu',
                    'comic_album_id': album_id,
                    'barcode': isbn,
                    'is_published': True,
                }
                if category_id:
                    product_vals['categ_id'] = category_id

                # Image depuis l'album
                album_data2 = odoo.read('comic.album', [album_id], ['image_couverture'])[0]
                if album_data2.get('image_couverture'):
                    product_vals['image_1920'] = album_data2['image_couverture']

                product_id = odoo.create('product.template', product_vals)
                odoo.write('comic.album', album_id, {'product_tmpl_id': product_id})
                odoo.write('product.template', product_id, {'comic_album_id': album_id})
                stats['products'] += 1
                print(f"     🛒  Produit créé et publié")

    return stats


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description='Import BD demo data into Odoo')
    parser.add_argument('--file', required=True, help='Fichier Excel (.xlsx)')
    parser.add_argument('--url', default='http://localhost:8069', help='URL Odoo')
    parser.add_argument('--db', default='guepe-comics-collections-19-0-32453836',
                        help='Nom de la base de données')
    parser.add_argument('--user', default='admin', help='Login Odoo')
    parser.add_argument('--password', default='admin', help='Mot de passe Odoo')
    parser.add_argument('--publish', action='store_true',
                        help='Forcer la publication sur le web (même si colonne manquante)')
    parser.add_argument('--no-covers', action='store_true',
                        help='Ne pas récupérer les couvertures (plus rapide)')
    args = parser.parse_args()

    print(f"\n🚀  Import BD demo — {args.file}")
    print(f"    Odoo : {args.url}  db={args.db}  user={args.user}\n")

    records, col = load_rows(args.file)
    print(f"📊  {len(records)} lignes à traiter\n")

    odoo = OdooClient(args.url, args.db, args.user, args.password)
    stats = run_import(odoo, records, col, publish=args.publish, no_covers=args.no_covers)

    print(f"\n✅  Import terminé :")
    print(f"    Séries créées  : {stats['series']}")
    print(f"    Albums créés   : {stats['albums']}")
    print(f"    Produits créés : {stats['products']}")
    print(f"    Couvertures    : {stats['covers']}")
    print(f"    Lignes ignorées: {stats['skipped']}")


if __name__ == '__main__':
    main()
