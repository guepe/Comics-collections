# flake8: noqa
# Script « odoo shell » : la variable env est fournie par le shell Odoo.
# Enrichissement de la base jetable appstore_demo (odoo shell < seed_demo.py)
import sys
import base64
import json
import random
import datetime as dt

sys.path.insert(0, "/work")
from covers import make_cover, to_b64  # noqa: E402
from dataset import EDITEURS, AUTEURS, SERIES  # noqa: E402
from odoo import Command  # noqa: E402

rnd = random.Random(42)
today = dt.date(2026, 11, 10)
admin = env.ref("base.user_admin")
company = env.company

# ── Société / admin en français ──────────────────────────────────────────
eur = env.ref("base.EUR")
eur.active = True
admin.write({"lang": "fr_BE", "tz": "Europe/Brussels"})
admin.partner_id.write({"name": "Alex Dupont", "email": "alex.dupont@example.com"})
try:
    company.write({"currency_id": eur.id})
except Exception as exc:  # écritures comptables de démo
    print("currency via SQL:", exc)
    env.cr.execute("UPDATE res_company SET currency_id=%s WHERE id=%s", (eur.id, company.id))
    company.invalidate_recordset()
company.write({"name": "Bulles & Cases", "country_id": env.ref("base.be").id, "city": "Namur"})
for pl in env["product.pricelist"].search([]):
    try:
        pl.currency_id = eur
    except Exception as exc:
        print("pricelist", exc)
website = env["website"].search([], limit=1)
website.write(
    {
        "name": "Bulles & Cases",
        "default_lang_id": env.ref("base.lang_fr_BE").id,
        "language_ids": [Command.set([env.ref("base.lang_fr_BE").id])],
    }
)

# ── Suppression des données de démo comics (séries réelles) ──────────────
env["comic.customer.album"].search([]).unlink()
env["comic.pret"].search([]).unlink()
demo_authors = env["comic.work.auteur.line"].search([]).partner_id
env["comic.work.auteur.line"].search([]).unlink()
env["comic.isbn"].search([]).unlink()
env["comic.edition"].with_context(active_test=False).search([]).unlink()
env["comic.work"].with_context(active_test=False).search([]).unlink()
env["comic.serie"].with_context(active_test=False).search([]).unlink()
env["comic.editeur"].search([]).unlink()
demo_authors.unlink()

# ── Référentiel fictif ──────────────────────────────────────────────────
Genre = env["comic.genre"]
editeurs = {name: env["comic.editeur"].create({"name": name, "pays_id": env.ref("base.be").id}) for name in EDITEURS}
authors = {
    k: env["res.partner"].create({"name": n, "is_comic_author": True, "is_company": False}) for k, n in AUTEURS.items()
}

isbn_counter = [1000]


def next_isbn():
    isbn_counter[0] += 7
    base = "97910999" + "%04d" % isbn_counter[0]
    s = sum(int(c) * (1 if i % 2 == 0 else 3) for i, c in enumerate(base))
    return base + str((10 - s % 10) % 10)


ALBUM_SYNOPSES = {
    ("argos", 1): "Maëlle, apprentie cartographe, hérite d'une carte des vents que personne ne sait lire. "
    "Quand une caravane disparaît sur la route du Col, elle comprend que la carte dessine l'avenir.",
    ("argos", 2): "Pour retrouver la caravane, Maëlle franchit le Col des Murmures, où chaque écho révèle un secret.",
    ("argos", 3): "La Cité d'ambre accueille les héritiers des sept clans. Maëlle y découvre que son père "
    "n'a pas seulement dessiné des cartes : il a tracé des frontières.",
    ("nebula", 1): "Un signal inconnu traverse les boucliers de la station Nébula. L'ingénieure Ada Novak "
    "a douze heures pour en trouver l'origine avant que la compagnie n'efface tout.",
    ("nebula", 8): "Après sept ans d'exil, l'équipage de Nébula rentre enfin sur une Terre qui ne l'attend plus. "
    "Le final très attendu de la saga.",
    ("brumes", 1): "Saint-Malo, 1952. Un cargo s'échoue au pied des remparts, cale vide et équipage introuvable. "
    "Première enquête de l'inspectrice Jeanne Le Goff.",
    ("ombelline", 1): "Ombelline hérite du Goéland, un vieux voilier, et d'une carte au trésor gribouillée "
    "au dos d'un menu de crêperie. Larguez les amarres !",
    ("kaito", 1): "Kaïto livre les lettres les plus dangereuses de la capitale. Son secret : quelques secondes "
    "hors du temps, le « pas du renard ».",
    ("mercure", 1): "Florence, 1492. Sous les terrasses des Médicis, un jeune jardinier trouve un herbier codé.",
    ("phare", 1): "Le gardien du dernier phare d'Ys rallume chaque nuit une lanterne qui ne guide plus aucun navire.",
}
AI_ALBUM = ("argos", 4)
AI_ALBUM_TEXT = (
    "Alors que l'hiver s'abat sur Argos, Maëlle rejoint les héritiers du Nord pour négocier "
    "une trêve fragile. Entre alliances de circonstance et vieilles rancunes, la cartographe "
    "doit apprendre à lire les hommes aussi bien que les cartes."
)

serie_recs, works = {}, {}
for si, s in enumerate(SERIES):
    names = " · ".join(AUTEURS[k] for k, r in s["auteurs"] if r != "coloriste")
    cover = make_cover(s["name"], None, None, names, s["editeur"], s["palette"], s["motif"], s["accent"], seed=si * 100)
    serie = env["comic.serie"].create(
        {
            "name": s["name"],
            "type": "manga" if s["genre"] == "Manga" else "bd",
            "statut": s["statut"],
            "genre_id": Genre.search([("name", "=", s["genre"])], limit=1).id,
            "editeur_id": editeurs[s["editeur"]].id,
            "image_couverture": to_b64(cover),
            "synopsis": "<p>%s</p>" % s["synopsis"],
        }
    )
    serie_recs[s["key"]] = serie
    n = len(s["titres"])
    for t, titre in enumerate(s["titres"], start=1):
        year = s["year"] + (t - 1)
        if s["key"] == "nebula" and t == n:
            date = dt.date(2026, 10, 15)
        else:
            date = dt.date(min(year, 2026), rnd.randint(1, 9), rnd.choice((1, 15)))
        img = make_cover(
            s["name"], titre, t, names, s["editeur"], s["palette"], s["motif"], s["accent"], seed=si * 100 + t
        )
        vals = {
            "serie_id": serie.id,
            "titre_canonique": titre,
            "tome": t,
            "editeur_id": editeurs[s["editeur"]].id,
            "date_parution": date,
            "nb_pages": 48 if s["genre"] != "Manga" else 192,
            "langue": "fr",
            "format": "broche" if s["genre"] == "Manga" else "cartonne",
            "image_couverture": to_b64(img),
            "isbn_ids": [Command.create({"isbn_13": next_isbn()})],
        }
        if (s["key"], t) in ALBUM_SYNOPSES:
            vals["synopsis"] = "<p>%s</p>" % ALBUM_SYNOPSES[(s["key"], t)]
        work = env["comic.work"].create(vals)
        env["comic.work.auteur.line"].create(
            [{"work_id": work.id, "partner_id": authors[k].id, "role": r} for k, r in s["auteurs"]]
        )
        works[(s["key"], t)] = work

# Synopsis IA (mention + case « généré automatiquement »)
ai_ed = works[AI_ALBUM].primary_edition_id
ai_ed.with_context(comic_ai_auto_text=True).write(
    {
        "synopsis": "<p>%s</p><p><em>(Généré automatiquement par IA)</em></p>" % AI_ALBUM_TEXT,
        "synopsis_auto": True,
    }
)
serie_recs["basilic"].with_context(comic_ai_auto_text=True).write(
    {
        "synopsis": "<p>Agent de terrain malgré lui, le traducteur Paul Varga se retrouve au cœur d'une opération "
        "d'espionnage qui le dépasse.</p><p><em>(Généré automatiquement par IA)</em></p>",
        "synopsis_auto": True,
    }
)

# Biographie d'auteur
authors["marchetti"].write(
    {
        "comic_bio": "<p>Née à Liège en 1984, <strong>Léa Marchetti</strong> découvre la bande dessinée dans la "
        "bibliothèque de son grand-père, marin au long cours. Après des études de lettres et quelques "
        "années comme scénariste pour le théâtre jeunesse, elle signe en 2014 le premier tome des "
        "<em>Chroniques d'Argos</em> avec Hugo Castelnau.</p>"
        "<p>Son écriture mêle le souffle de la fantasy et le goût du détail géographique : chaque album "
        "s'ouvre sur une carte qu'elle dessine elle-même. Elle crée en 2016 <em>Capitaine Ombelline</em>, "
        "une série d'aventure familiale dessinée par Clara Venturi, récompensée par plusieurs prix "
        "de lecteurs jeunesse.</p>",
        "function": "Scénariste",
        "city": "Liège",
        "country_id": env.ref("base.be").id,
    }
)

# ── Bibliothèque de l'admin ──────────────────────────────────────────────
Album = env["comic.customer.album"].with_user(admin).sudo()
owned = {
    "argos": range(1, 9),
    "nebula": range(1, 7),
    "brumes": range(1, 7),
    "ombelline": range(1, 5),
    "phare": range(1, 4),
    "kaito": range(1, 6),
    "mercure": range(1, 6),
    "basilic": range(1, 4),
}
en_cours = {("argos", 8), ("nebula", 6), ("kaito", 5)}
non_lu = {("ombelline", 4), ("phare", 3)}
rare = {("brumes", 1): 45.0, ("argos", 1): 38.0, ("mercure", 1): 30.0}
for key, rng in owned.items():
    for t in rng:
        k = (key, t)
        prix = rnd.choice((12.5, 13.95, 14.5, 15.0, 15.95, 16.5, 9.9 if key == "kaito" else 17.5))
        etat = "en_cours" if k in en_cours else ("non_lu" if k in non_lu else "lu")
        note = 0 if etat == "non_lu" else rnd.choice((3, 4, 4, 5, 5, 5, 4, 3, 2))
        Album.create(
            {
                "partner_id": admin.partner_id.id,
                "edition_id": works[k].primary_edition_id.id,
                "dans_collection": True,
                "etat_lecture": etat,
                "note": note,
                "prix_achat": prix,
                "valeur_estimee": rare.get(k, round(prix * rnd.uniform(0.8, 1.35), 2)),
                "source": rnd.choice(("achete_ailleurs", "achete_ailleurs", "cadeau", "achete_ici")),
                "date_ajout": today - dt.timedelta(days=rnd.randint(5, 700)),
                "commentaire": "Superbe dessin, l'intrigue monte en puissance." if k == ("argos", 3) else False,
            }
        )
for k in (("argos", 9), ("kaito", 6), ("basilic", 4)):
    Album.create(
        {
            "partner_id": admin.partner_id.id,
            "edition_id": works[k].primary_edition_id.id,
            "dans_collection": False,
            "dans_wishlist": True,
            "date_ajout": today - dt.timedelta(days=10),
        }
    )
# Suivi : toutes les séries possédées (automatique) ; Basilic : désabonné
serie_recs["basilic"].write(
    {"suivi_user_ids": [Command.unlink(admin.id)], "suivi_exclu_user_ids": [Command.link(admin.id)]}
)

# Prêts
friend1 = env["res.partner"].create({"name": "Antoine Lefèvre", "email": "antoine.lefevre@example.com"})
friend2 = env["res.partner"].create({"name": "Sarah Dubois", "email": "sarah.dubois@example.com"})
Pret = env["comic.pret"].with_user(admin).sudo()
Pret.create(
    {
        "edition_id": works[("brumes", 2)].primary_edition_id.id,
        "partner_id": friend1.id,
        "date_pret": dt.date(2026, 9, 2),
        "date_retour_prevue": dt.date(2026, 10, 2),
        "notes": "Relancer à la prochaine soirée jeux.",
    }
)
Pret.create(
    {
        "edition_id": works[("argos", 4)].primary_edition_id.id,
        "partner_id": friend2.id,
        "date_pret": dt.date(2026, 11, 1),
        "date_retour_prevue": dt.date(2026, 12, 1),
    }
)

# ── Shop : produits publiés ──────────────────────────────────────────────
for key in ("argos", "nebula", "ombelline", "kaito", "phare", "mercure"):
    for (k, t), work in works.items():
        if k != key:
            continue
        ed = work.primary_edition_id
        ed.action_create_product()
        ed.product_tmpl_id.write(
            {
                "list_price": 9.95 if key == "kaito" else rnd.choice((12.5, 13.95, 14.95, 15.5, 16.95, 17.95)),
                "is_published": True,
            }
        )

# Clients portail
portal_group = env.ref("base.group_portal")


def portal_user(name, login, email, pwd):
    return (
        env["res.users"]
        .with_context(no_reset_password=True)
        .create(
            {
                "name": name,
                "login": login,
                "email": email,
                "password": pwd,
                "group_ids": [Command.set([portal_group.id])],
                "lang": "fr_BE",
            }
        )
    )


camille = portal_user("Camille Martin", "camille", "camille.martin@example.com", "camille")
others = [
    portal_user(n, l, e, l + "pwd")
    for n, l, e in (
        ("Lucas Bernard", "lucas", "lucas.bernard@example.com"),
        ("Emma Lambert", "emma", "emma.lambert@example.com"),
    )
]
noah = env["res.partner"].create({"name": "Noah Petit", "email": "noah.petit@example.com"})

CA = env["comic.customer.album"].sudo()
cam_p = camille.partner_id
cam_lib = (
    [("nebula", t) for t in range(1, 8)]
    + [("kaito", t) for t in range(1, 5)]
    + [("ombelline", 1), ("ombelline", 2), ("phare", 1)]
)
for i, k in enumerate(cam_lib):
    etat = "en_cours" if k in (("nebula", 7), ("kaito", 4)) else ("non_lu" if k == ("phare", 1) else "lu")
    CA.create(
        {
            "partner_id": cam_p.id,
            "edition_id": works[k].primary_edition_id.id,
            "dans_collection": True,
            "etat_lecture": etat,
            "note": 0 if etat == "non_lu" else rnd.choice((3, 4, 5, 5, 4)),
            "source": "achete_ici" if i % 3 else "achete_ailleurs",
            "prix_achat": 9.95 if k[0] == "kaito" else 15.5,
            "valeur_estimee": 9.95 if k[0] == "kaito" else 16.0,
            "date_ajout": today - dt.timedelta(days=8 + i * 23),
        }
    )
for k in (("argos", 1), ("mercure", 1)):
    CA.create(
        {
            "partner_id": cam_p.id,
            "edition_id": works[k].primary_edition_id.id,
            "dans_collection": False,
            "dans_wishlist": True,
            "date_ajout": today - dt.timedelta(days=3),
        }
    )
cam_p._comic_wishlist_enable()
# Suivi de séries par les clients (Nébula Station : T8 attendu)
serie_recs["nebula"].write({"suivi_user_ids": [Command.link(camille.id)] + [Command.link(u.id) for u in others]})
serie_recs["kaito"].write({"suivi_user_ids": [Command.link(camille.id)]})
CA.create({"partner_id": others[0].partner_id.id, "edition_id": works[("nebula", 3)].primary_edition_id.id})
CA.create(
    {
        "partner_id": noah.id,
        "edition_id": works[("nebula", 8)].primary_edition_id.id,
        "dans_collection": False,
        "dans_wishlist": True,
    }
)

nebula8 = works[("nebula", 8)].primary_edition_id
print("RECIPIENTS", nebula8.release_recipient_count, nebula8._get_release_recipients().mapped("name"))

# ── Assistants pré-remplis (sans appel réseau) ────────────────────────────
rel = env["comic.release.notify.wizard"].with_user(admin).create({"edition_ids": [Command.set(nebula8.ids)]})

ai_target = works[("argos", 5)].primary_edition_id
aiw = (
    env["comic.ai.wizard"]
    .with_user(admin)
    .create(
        {
            "edition_id": ai_target.id,
            "mode": "synopsis",
            "lang": "fr",
            "state": "preview",
            "provider": "openai",
            "model_name": "gpt-5-mini",
            "generated_text": "Réfugiée à Kaldor, Maëlle découvre que le serment qui lie les sept clans repose sur une "
            "carte falsifiée. Tandis que Hadrien rassemble une armée aux portes de la ville, la jeune "
            "cartographe doit choisir : révéler la vérité au risque d'une guerre, ou se taire pour "
            "préserver une paix bâtie sur un mensonge. Un tome charnière, sombre et haletant, où les "
            "Chroniques d'Argos basculent dans l'épopée.",
        }
    )
)

csv_text = (
    "Série;Tome;Titre;ISBN;Éditeur;Date de parution;Statut;Note\n"
    "Les Veilleurs de Mistral;1;Le Vent du sud;9791099912346;Éditions du Phare;2023-03-15;Lu;4\n"
    "Les Veilleurs de Mistral;2;La Tour des signaux;9791099912353;Éditions du Phare;2024-04-02;En cours;\n"
    "Atlas mécanique;1;Rouages;9791099912360;Atelier Boréal;2022-09-20;Lu;5\n"
)
imp = (
    env["comic.import.wizard"]
    .with_user(admin)
    .create({"import_file": base64.b64encode(csv_text.encode("utf-8")), "import_filename": "ma_collection.csv"})
)
imp.action_prepare_mapping()

disc = (
    env["comic.ai.discovery.wizard"]
    .with_user(camille)
    .sudo()
    .create(
        {
            "portal": True,
            "state": "suggestions",
            "profile_serie_ids": [Command.set([serie_recs["nebula"].id, serie_recs["kaito"].id])],
            "line_ids": [
                Command.create(
                    {
                        "sequence": 1,
                        "name": "Les Veilleurs de Mistral",
                        "auteurs": "Nora Valette, Elio Brand",
                        "genre": "Science-fiction",
                        "raison": "Comme Nébula Station, un huis clos spatial où l'équipage compte plus que la mission.",
                    }
                ),
                Command.create(
                    {
                        "sequence": 2,
                        "name": "Atlas mécanique",
                        "auteurs": "Pablo Serrat",
                        "genre": "Steampunk",
                        "raison": "Un univers foisonnant et une héroïne ingénieure, dans l'esprit d'Ada Novak.",
                        "verify_state": "found",
                        "verify_info": "Trouvée : tome 1 « Rouages » (2022)",
                    }
                ),
                Command.create(
                    {
                        "sequence": 3,
                        "name": "La Ballade de Kiyo",
                        "auteurs": "Mei Aragaki",
                        "genre": "Manga",
                        "raison": "Vous avez adoré Kaïto : même souffle d'aventure et de messages secrets dans une "
                        "capitale en ébullition.",
                    }
                ),
                Command.create(
                    {
                        "sequence": 4,
                        "name": "Les Cartographes de l'ombre",
                        "auteurs": "Iris Moulin",
                        "genre": "Fantasy",
                        "raison": "Une quête initiatique servie par un dessin lumineux, idéale après vos manga préférés.",
                    }
                ),
            ],
        }
    )
)

env.cr.commit()
out = {
    "camille_uid": camille.id,
    "disc_wizard": disc.id,
    "rel_wizard": rel.id,
    "ai_wizard": aiw.id,
    "import_wizard": imp.id,
    "token": cam_p.sudo().comic_wishlist_token,
    "work_album": works[("argos", 3)].id,
    "serie_form": serie_recs["argos"].id,
    "author": authors["marchetti"].id,
    "nebula8_product": nebula8.product_tmpl_id.id,
    "product_page": works[("argos", 3)].primary_edition_id.product_tmpl_id.id,
    "shop_serie": serie_recs["nebula"].id,
    "nebula8_edition": nebula8.id,
}
json.dump(out, open("/work/ids.json", "w"))
print("IDS", out)
