# CLAUDE.md — Projet Odoo Comic Collection

> Contexte principal pour Claude dans VS Code.
> Architecture, conventions et règles du projet — à jour au 2026-05-23.

---

## 🎯 Objectif

Modules Odoo 19 pour gérer une collection de BD et vendre en ligne :

| Module | Rôle | État |
|---|---|---|
| `comics_collections` | Collection, catalogue, import CSV/XLSX, déduplication | ✅ livré |
| `comic_datasource` | Enrichissement multi-sources (Google Books, Open Library, BnF, BDGest fallback) | ✅ livré |
| `comic_bdgest` | Scraping BDGest enrichissement | ✅ livré |
| `comic_shop` | Shop en ligne, caisse (POS partiel), bibliothèque client portail | ✅ majeure partie livrée |
| `comic_ai` | Génération IA (synopsis, traduction) — Claude + OpenAI | ⏳ non commencé |

---

## ⚙️ Environnement technique

| Paramètre | Valeur |
|---|---|
| Odoo | **19.0** |
| Python | 3.12+ |
| PostgreSQL | 16 |
| Licence | LGPL-3 (OCA style) |
| Style | PEP8, OCA guidelines |
| Branche Git | `19.0` |

**Dépendances Python :** `requests`, `beautifulsoup4`, `lxml`, `openai`, `anthropic`, `openpyxl`, `xlrd`, `xmltodict`

**APIs externes :**

| API | Auth | Usage | Limite |
|---|---|---|---|
| Google Books | Clé API gratuite | Métadonnées + couvertures | 1000 req/jour |
| Open Library | Aucune | Couvertures + auteurs | Illimitée |
| BnF SRU | Aucune | BD francophones (dépôt légal) | Illimitée |
| BDGest | Login optionnel | Fallback scraping uniquement | Délai 2s obligatoire |

---

## 🗂️ Structure des modules

```
Comics-collections/
├── comics_collections/      # Module principal
│   ├── models/
│   │   ├── comic_serie.py, comic_work.py, comic_edition.py
│   │   ├── comic_isbn.py, comic_pret.py, comic_editeur.py
│   │   ├── comic_genre.py, comic_dedup_pair.py, res_partner.py
│   ├── views/               # Vues back-office
│   ├── wizards/
│   │   ├── comic_import_wizard.py      # Import CSV/XLS/XLSX
│   │   └── comic_dedup_wizard.py       # Wizard fusion doublons
│   ├── utils/normalize.py              # normalize_title()
│   ├── data/comic_genre_data.xml, comic_cron_data.xml
│   ├── demo/comic_demo.xml
│   ├── security/
│   └── tests/
├── comic_datasource/        # Enrichissement multi-sources
│   ├── sources/             # google_books.py, open_library.py, bnf.py, bdgest.py
│   ├── aggregator.py        # ComicDataAggregator
│   ├── models/comic_edition.py   # _inherit = 'comic.edition'
│   ├── wizards/             # search_wizard, serie_missing_wizard, serie_update_wizard
│   └── data/comic_datasource_config.xml, comic_serie_cron.xml
├── comic_bdgest/            # Scraping BDGest
│   ├── scraper/
│   ├── models/comic_edition.py   # _inherit = 'comic.edition'
│   └── wizards/
└── comic_shop/              # Shop + bibliothèque client
    ├── models/
    │   ├── comic_edition.py      # _inherit = 'comic.edition' (product_tmpl_id, sync)
    │   ├── comic_serie.py        # _inherit = 'comic.serie' (création produits en masse)
    │   ├── comic_customer_album.py
    │   ├── comic_sale_order.py
    │   ├── product_template.py
    │   └── res_partner.py
    ├── controllers/main.py  # Webshop + portail
    ├── views/
    └── tests/
```

---

## 🏗️ ERD — Architecture canonique (en production)

```
comic.serie
  │  name, type, statut, genre_id, editeur_id, image_couverture, synopsis
  │  slug (auto-généré), name_normalise (compute, store, index)
  └──< comic.work
         │  titre_canonique (required), tome, slug, titre_normalise (compute, store, index)
         │  wikidata_id, openlibrary_id, bedetheque_id, comicvine_id
         │  Constraint UNIQUE(serie_id, tome)
         │  hérite mail.thread + mail.activity.mixin
         ├──< comic.work.auteur.line
         │      work_id, partner_id → res.partner, role
         └──< comic.edition
                │  work_id, editeur_id, date_parution, langue, format
                │  image_couverture, synopsis, nb_pages
                │  url_club_be, url_amazon_be, url_fnac_be
                │  product_tmpl_id → product.template   (ajouté par comic_shop)
                │  hérite mail.thread + mail.activity.mixin
                └──< comic.isbn
                       edition_id, isbn_13 (EAN-13 validé, UNIQUE), isbn_10 (optionnel)

comic.customer.album   (comic_shop)
  partner_id, edition_id, work_id (compute), source, etat_lecture
  dans_collection, dans_wishlist, note, commentaire, date_ajout
  Constraint UNIQUE(partner_id, edition_id)

comic.pret
  edition_id → comic.edition, partner_id, date_pret, date_retour_prevue
  date_retour_effective, retourne, notes

comic.dedup.pair
  work_a_id, work_b_id, score, reason, ignored
  Constraint UNIQUE(work_a_id, work_b_id)
```

**Façade UX :** `comic.work` s'affiche en "Albums / Tomes" pour les utilisateurs. "Œuvre" et "Édition" sont réservés au menu Configuration > Référentiel avancé (managers uniquement).

---

## 🔁 Normalisation et déduplication (US-050/056)

**`comics_collections/utils/normalize.py` — `normalize_title(title)`**

1. NFD + suppression accents (catégorie Mn)
2. `lower()`
3. Suppression articles en tête : FR `le/la/les/l'` · NL `de/het/een` · EN `the/a/an`
4. Suppression suffixes catalogue : `(les)` / `(de)` / `(the)` en fin de chaîne
5. Suppression ponctuation non significative (tirets, virgules, points, guillemets)
6. Normalisation espaces

Exemples : `"Les Landes perdues"` → `"landes perdues"` = `"Landes perdues (Les)"`

**Scores de déduplication (`_find_duplicate_candidates`) :**

| Score | Raison | Déclencheur |
|---|---|---|
| 1.0 | `conflit_certain` | même `(serie_id, tome)` |
| 0.9 | `doublon_probable` | même `serie_id` + `titre_ratio ≥ 0.85` |
| 0.7+ | `doublon_possible` | `titre_ratio ≥ 0.85` ET `serie_ratio ≥ 0.85` |

Algorithme : `difflib.SequenceMatcher` (seuil 0.85, pas de dépendance externe).

---

## 📦 comic_datasource — dict normalisé

Chaque source retourne :

```python
{
    'title': str, 'serie_name': str|None, 'tome': int|None,
    'isbn': str, 'date_parution': str,  # YYYY-MM-DD
    'nb_pages': int|None, 'editeur': str|None,
    'auteurs': [{'name': str, 'role': 'scenariste'|'dessinateur'|'coloriste'|'autre'}],
    'synopsis': str|None, 'cover_url': str|None, 'cover_url_small': str|None,
    'source': 'google'|'openlibrary'|'bnf'|'bdgest',
}
```

Cascade priorité : Google > Open Library > BnF > BDGest (fallback, délai 2s obligatoire).

---

## 🕐 Crons configurés

| Module | Fichier | Fréquence | Action |
|---|---|---|---|
| `comics_collections` | `data/comic_cron_data.xml` | Hebdomadaire | Liens d'achat manquants |
| `comic_datasource` | `data/comic_serie_cron.xml` | Quotidien (désactivé par défaut) | Enrichissement éditions incomplètes |
| `comic_datasource` | `data/comic_serie_cron.xml` | Hebdomadaire (désactivé par défaut) | Détection tomes manquants |

---

## 🧑‍💻 Conventions de code

**Nommage :** modèles `comic.xxx` · classes `ComicXxx` · fichiers `comic_xxx.py` / `comic_xxx_views.xml`

**Module XML ID prefix :** `comics_collections.` (avec "s") — ex. `comics_collections.group_comic_manager`

**`__manifest__.py` :**
```python
{
    'name': '...', 'version': '19.0.1.0.0', 'category': 'Leisure',
    'license': 'LGPL-3', 'depends': ['base', 'mail', ...],
    'data': [...], 'installable': True,
}
```

---

## 🚦 Règles importantes

1. **ORM uniquement** — jamais de SQL brut sauf exception justifiée
2. Modèles principaux héritent `mail.thread` + `mail.activity.mixin`
3. Toujours `_description` sur chaque modèle
4. Toujours mettre les droits dans `ir.model.access.csv`
5. `fields.Image` (pas `Binary`) pour les couvertures
6. Clés API en `ir.config_parameter` — jamais en dur
7. Scraping BDGest : délai **2 secondes** obligatoire entre requêtes
8. Odoo 19 uniquement — pas d'API dépréciées
9. **Vocabulaire UX** : "album" / "tome" / "série" pour les utilisateurs. "Œuvre" / "Édition" réservés au référentiel avancé (managers).
10. Contraintes DB : `models.Constraint(...)` — pas `_sql_constraints` (déprécié Odoo 19)

---

## ⚠️ Incompatibilités Odoo 19

| Modèle / contexte | Changement |
|---|---|
| `res.groups.category_id` | **Supprimé** — utiliser `res.groups.privilege` |
| `res.groups.users` | **Renommé** en `user_ids` |
| `ir.actions.server.groups_id` | **Renommé** en `group_ids` |
| `_sql_constraints` | **Déprécié** — utiliser `models.Constraint(...)` |
| Search view `<group expand string>` | `expand`/`string` supprimés — utiliser `<group name="group_by">` |
| Vue héritée `<page string="..." position="...">` | `string` interdit comme sélecteur — utiliser `<xpath>` avec `name` ou classe |
| `t-if` dans `arch` de form view | **Interdit** — utiliser `invisible="..."` |

**Many2many XML (Odoo 19) :**
```xml
<!-- ✅ -->
<field name="implied_ids" eval="[Command.link(ref('base.group_user'))]"/>
<!-- ❌ Odoo ≤18 -->
<field name="implied_ids" eval="[(4, ref('base.group_user'))]"/>
```

**Groupes de sécurité :**
```
ir.module.category  ←  res.groups.privilege  ←  res.groups
```

**Cache Docker (après modif `.py`) :**
```bash
find /chemin/module -name "__pycache__" -exec rm -rf {} +
~/.docker/bin/docker logs -f odoo-web
```

---

## 📋 Suivi de projet — Handoff entre sessions

Maintenir à jour en fin de session, avant le commit :

- **`USER_STORIES_V3.md`** : cocher `[x]` dès qu'un critère est fait. Ajouter `✅` au titre quand tous les critères sont cochés. Ne jamais cocher par anticipation.
- **`CHANGE.md`** : ajouter une entrée datée avec tous les fichiers modifiés, méthodes ajoutées, bugs corrigés, décisions techniques. Ne pas relire tout le fichier — juste appender.
