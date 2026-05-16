# Journal des modifications — Odoo Comic Collection

> Format : date · module · fichier · description du changement + raison
> Odoo version : **19.0** (docker `odoo:latest`, image du 2026-03-05)
> À maintenir à jour à chaque session de travail.

---

## 2026-05-15

### Incompatibilités Odoo 19 découvertes et corrigées

Odoo 19 a supprimé ou renommé plusieurs champs qui existaient en 17/18.
Ces erreurs bloquaient l'installation/mise à jour des modules.

#### `comics_collections/security/comic_security.xml`

| Champ supprimé | Raison | Fix appliqué |
|---|---|---|
| `category_id` sur `res.groups` | Supprimé en Odoo 19 | Champ retiré |
| `users` sur `res.groups` | Renommé en `user_ids` | Champ corrigé |

**Nouvelle architecture Odoo 19 pour les groupes de sécurité :**
```
ir.module.category  ←  res.groups.privilege  ←  res.groups
                          (nouveau modèle)
```
Ajout d'un enregistrement `res.groups.privilege` (id: `privilege_comic_collection`)
qui lie la catégorie aux groupes, et ajout de `privilege_id` sur chaque groupe.
Les groupes apparaissent maintenant dans le formulaire utilisateur sous
la section "Bandes Dessinées" avec sélection "Aucun accès / Utilisateur / Gestionnaire".

Syntaxe Odoo 19 pour les Many2many dans XML :
```xml
<!-- ✅ Odoo 19 -->
<field name="implied_ids" eval="[Command.link(ref('base.group_user'))]"/>
<field name="user_ids" eval="[Command.link(ref('base.user_root'))]"/>

<!-- ❌ Odoo ≤18 (ne fonctionne plus) -->
<field name="implied_ids" eval="[(4, ref('base.group_user'))]"/>
<field name="users" eval="[(4, ref('base.user_root'))]"/>
```

#### `comics_collections/views/comic_serie_views.xml` et `comic_album_views.xml`

| Attributs supprimés | Fix |
|---|---|
| `<group expand="0" string="...">` dans les vues search | Remplacé par `<group name="group_by">` |

`expand` et `string` ne sont plus des attributs valides sur `<group>` selon le RNG Odoo 19.

#### `comics_collections/views/comic_menu.xml`

Mauvais préfixe de module sur toutes les références :
- `comic_collection.group_comic_user` → `comics_collections.group_comic_user`
- `comic_collection.group_comic_manager` → `comics_collections.group_comic_manager`
- `web_icon="comic_collection,..."` → `web_icon="comics_collections,..."`

#### `comics_collections/security/ir.model.access.csv`

Ajout du préfixe de module manquant sur `group_id:id` :
- `group_comic_user` → `comics_collections.group_comic_user`
- `group_comic_manager` → `comics_collections.group_comic_manager`

#### `comic_bdgest/views/comic_album_inherit_views.xml`

| Champ renommé | Fix |
|---|---|
| `groups_id` sur `ir.actions.server` | Renommé en `group_ids` en Odoo 19 |

---

### Nouvelles fonctionnalités — US-017 (cases manquantes)

#### Wizard d'enrichissement BDGest (US-017 → bouton ISBN + action batch)

Fichiers créés dans `comic_bdgest/` :

```
comic_bdgest/
├── wizards/
│   ├── __init__.py                          (nouveau)
│   └── comic_bdgest_enrich_wizard.py        (nouveau)
├── models/
│   └── comic_album.py                       (nouveau — inherit comic.album)
├── views/
│   ├── comic_bdgest_enrich_wizard_views.xml (nouveau)
│   └── comic_album_inherit_views.xml        (nouveau)
└── security/
    └── ir.model.access.csv                  (nouveau)
```

Fichiers modifiés dans `comic_bdgest/` :
- `__init__.py` — ajout `from . import wizards`
- `models/__init__.py` — ajout `from . import comic_album`
- `__manifest__.py` — ajout des nouveaux fichiers dans `data`

**Modèles transients créés :**
- `comic.bdgest.enrich.wizard` — wizard de recherche/import (2 états: search / results)
- `comic.bdgest.result.line` — ligne de résultat dans le wizard

**Méthodes ajoutées sur `comic.album` (via inherit) :**
- `action_enrich_from_bdgest()` — ouvre le wizard (bouton formulaire)
- `action_batch_enrich_from_bdgest()` — enrichissement batch par ISBN (action liste)
- `_bdgest_import_from_id(bdgest_album_id, ...)` — fetch + apply détail BDGest
- `_bdgest_apply_detail(detail, scraper)` — mappe un dict BDGest sur les champs Odoo

**Flux ISBN (bouton formulaire) :**
1. Wizard s'ouvre avec l'ISBN pré-rempli
2. "Rechercher" → search/albums?RechISBN=... → 1er résultat → get_album_detail → import direct → fermeture (pas d'étape de sélection)

**Flux titre :**
1. Saisie du titre → liste de résultats → sélection manuelle → import

**Flux batch (action liste, multi-sélection) :**
- Traite chaque album ayant un ISBN, affiche notification résumée

---

### Correction du scraper BDGest

`comic_bdgest/scraper/bdgest_scraper.py`

| Avant (cassé) | Après |
|---|---|
| Endpoint : `/recherche-albums.html` | `/search/albums` |
| Paramètre titre : `RechAlbumTitre` | `RechTitre` |
| Paramètre ISBN : `RechAlbumEan` | `RechISBN` |
| Paramètre auteur : `RechAlbumAuteur` | `RechAuteur` |
| Pas de CSRF token | `csrf_token_bel` extrait via `_get_csrf_token()` |

Ajouts :
- `_search_params(**criteria)` — construit les paramètres avec tous les champs vides requis + CSRF
- `_get_csrf_token()` — GET sur la page de recherche, extrait le token `<input name="csrf_token_bel">`, mis en cache par session
- `search_by_isbn()` retourne maintenant le **détail complet** (2 requêtes : search + album page) et non plus le résultat partiel

⚠️ **Note** : après modification d'un `.py`, supprimer les `__pycache__` si Odoo est en Docker avec volume monté :
```bash
find /chemin/module -name "__pycache__" -exec rm -rf {} +
```

---

## État actuel des modules (2026-05-15)

### `comics_collections`
- ✅ Installé et fonctionnel en Odoo 19
- ✅ Groupes de sécurité visibles dans le formulaire utilisateur
- ✅ Droits d'accès corrects sur tous les modèles
- ✅ Menus fonctionnels (Bandes Dessinées > Ma Collection, Catalogues, Configuration)

### `comic_bdgest`
- ✅ Installé et fonctionnel en Odoo 19
- ✅ Bouton "Enrichir depuis BDGest" dans le formulaire album (à côté de l'ISBN)
- ✅ Action "Enrichir depuis BDGest" dans le menu Action de la vue liste
- ⚠️ Le parser HTML (`bdgest_parser.py`) a été conçu pour l'ancienne URL — à valider sur la nouvelle structure HTML de `/search/albums`
- ⏳ Module destiné à être remplacé par `comic_datasource` (non encore implémenté)

### `partner_vcard_import`
- Non modifié dans cette session

---

## 2026-05-15 (suite) — Restructuration architecture multi-sources

### Documentation : migration `comic_bdgest` → `comic_datasource`

**Fichiers modifiés :**
- `comics_collections/CLAUDE.md`
- `comics_collections/USER_STORIES.md`

**Changements dans `CLAUDE.md` :**

| Section | Changement |
|---|---|
| Dépendances Python | Ajout `xmltodict` |
| APIs externes | Nouveau tableau (Google Books, Open Library, BnF SRU, BDGest) |
| Module 2 | Renommé `comic_bdgest` → `comic_datasource` |
| Structure `addons/` | Mise à jour avec sous-dossiers `sources/`, `aggregator.py`, `wizards/` |
| Règles Claude | Ajout règles 11, 12, 13 (légalité APIs, clés Google, priorité BnF) |

**Nouvelle architecture `comic_datasource` (cascade de sources) :**
1. Google Books API → synopsis, couverture HD, métadonnées générales
2. Open Library API → couverture alternative, auteurs, éditions
3. BnF SRU API → données officielles BD francophones
4. BDGest scraping → fallback uniquement avec avertissement légal

**Changements dans `USER_STORIES.md` :**

| Changement | Détail |
|---|---|
| En-tête | Ajout note sur source de rédaction |
| EPIC 3 | Réécrit intégralement : était BDGest-only (US-017→022), maintenant multi-sources (US-017→025) |
| Renumérotation | US-023→US-026 … US-030→US-033 (décalage +3 pour toutes les US post-EPIC 3) |
| Phases | "Phase 3 IA" renommée "Phase 4a IA" ; ajout Phase 3 Datasource |
| Tableau récap | Mis à jour avec nouvelles priorités MoSCoW |

**Nouvelles US (EPIC 3 — multi-sources) :**
- US-017 : Configuration sources de données (Google Books API key, BDGest credentials)
- US-018 : Enrichissement ISBN via aggregator (cascade automatique)
- US-019 : Wizard recherche multi-sources (affichage source par champ)
- US-020 : Import couverture depuis URL source
- US-021 : Scraping BDGest (fallback, avec disclaimer légal)
- US-022 : Import série complète BDGest
- US-023 : Source BnF SRU (données officielles FR)
- US-024 : Source Open Library
- US-025 : Tests et monitoring sources

> ⚠️ **À implémenter** : Le module `comic_datasource` est documenté mais pas encore créé.
> Le module `comic_bdgest` existant reste installé en attendant.

---

## Référence rapide — Incompatibilités Odoo 19 vs 17/18

| Modèle | Champ | Changement |
|---|---|---|
| `res.groups` | `category_id` | **Supprimé** — utiliser `res.groups.privilege` |
| `res.groups` | `users` | **Renommé** en `user_ids` |
| `ir.actions.server` | `groups_id` | **Renommé** en `group_ids` |
| Vues search | `<group expand string>` | `expand` et `string` **supprimés** — utiliser `<group name="group_by">` |
| XML Many2many | `(4, ref(...))` | Remplacer par `Command.link(ref(...))` (recommandé) |

---

---

## 2026-05-15 (suite 2) — US-017 : Infrastructure `comic_datasource`

### Nouveau module `comic_datasource/`

Fichiers créés :

```
comic_datasource/
├── __manifest__.py          (dépend de comics_collections)
├── __init__.py
├── aggregator.py            (ComicDataAggregator)
├── sources/
│   ├── __init__.py
│   ├── base.py              (BaseComicSource + ComicSourceResult)
│   ├── google_books.py      (GoogleBooksSource)
│   ├── open_library.py      (OpenLibrarySource)
│   ├── bnf.py               (BnfSource — SRU API + xmltodict)
│   └── bdgest.py            (BdgestSource — fallback scraping, désactivé par défaut)
├── wizards/__init__.py      (stub — implémenté en US-023)
├── tests/
│   ├── __init__.py
│   ├── test_sources.py      (tests unitaires avec mocks HTTP)
│   └── test_aggregator.py   (tests de fusion + priorités)
├── security/ir.model.access.csv
├── data/comic_datasource_config.xml   (params par défaut)
└── views/                   (stubs — implémentés en US-023/024)
```

**`BaseComicSource` (sources/base.py) :**
- Classe abstraite avec `search_by_isbn()` et `search_by_title()` à implémenter
- `ComicSourceResult` (dataclass) : modèle normalisé commun à toutes les sources
- Champs : title, serie_name, tome, isbn, date_parution, date_depot_legal, nb_pages, editeur, auteurs, synopsis, cover_url, cover_url_small, source, source_id, raw

**Cascade de sources par défaut :** Google Books → Open Library → BnF SRU → BDGest

**Règles de fusion dans `ComicDataAggregator` :**
- synopsis : Google > BnF > BDGest > Open Library
- date_depot_legal : BnF uniquement (source officielle)
- cover_url : Google Large > Open Library L > BDGest
- auteurs : source avec la liste la plus complète
- Cache session pour éviter les appels répétés

**BDGest désactivé par défaut** (`comic.bdgest_enabled = False`) — opt-in légal requis.

**Tests :** 17 tests unitaires (mocks HTTP, pas d'accès réseau requis) — syntaxe validée.
À lancer dans Docker : `odoo-bin test -d <db> --test-tags /comic_datasource`

---

## 2026-05-15 (suite 3) — US-018 : Google Books API dans Paramètres Odoo

### Fichiers modifiés/créés dans `comic_datasource/`

| Fichier | Action | Description |
|---|---|---|
| `models/__init__.py` | créé | Import `res_config_settings` |
| `models/res_config_settings.py` | créé | Extend `res.config.settings` |
| `sources/google_books.py` | modifié | Ajout `GoogleBooksQuotaError` + gestion HTTP 403 |
| `aggregator.py` | modifié | Re-raise `GoogleBooksQuotaError` (non silencé) |
| `views/comic_datasource_config_views.xml` | modifié | Vue Paramètres Odoo 19 (`<app>` + `<block>` + `<setting>`) |
| `__init__.py` | modifié | Ajout `from . import models` |
| `__manifest__.py` | modifié | `external_dependencies` + `models` dans `data` |

**Nouveaux champs `res.config.settings` :**
- `comic_google_books_api_key` → `ir.config_parameter` `comic.google_books_api_key`
- `comic_bdgest_enabled` → `comic.bdgest_enabled`
- `comic_bdgest_login` / `comic_bdgest_password`

**Bouton "Tester la connexion Google Books" :**
- Appel direct à l'API avec l'ISBN Astérix T1 comme test
- Retourne une notification verte si OK
- `UserError` explicite pour HTTP 429 (quota) et HTTP 403 (clé invalide)

**Structure vue Odoo 19 :** `inherit_id = base.res_config_settings_view_form` + `xpath //form` + balise `<app name="comic_datasource">` (pattern identique à `website`, `base_setup`, etc.)

---

## 2026-05-15 (suite 4) — US-023 : Wizard de recherche et import unifié

### Nouveaux fichiers dans `comic_datasource/`

| Fichier | Description |
|---|---|
| `wizards/comic_datasource_search_wizard.py` | Deux TransientModels |
| `models/comic_album.py` | Inherit `comic.album` → `action_search_datasource()` |
| `views/comic_datasource_wizard_views.xml` | Vue wizard 3 états |
| `views/comic_datasource_album_inherit_views.xml` | Bouton stat dans le form album |
| `views/comic_datasource_menu.xml` | Menu "Rechercher des BD" |

**Modèles :**
- `comic.datasource.search.wizard` — wizard principal (états: search / results / done)
- `comic.datasource.result.line` — lignes de résultats (cover_data Binary, source badge)

**Flux ISBN :** `action_search()` → `aggregator.search(isbn=...)` → 1 ligne fusionnée
**Flux titre :** `action_search()` → `aggregator.search_list(title=...)` → N lignes par source

**Logique import (`_import_line`) :**
- Find-or-create `comic.editeur`, `comic.serie`, `res.partner` (auteurs)
- Si ISBN déjà en base : mise à jour (pas duplication)
- Téléchargement couverture HD au moment de l'import
- Dates converties str `YYYY-MM-DD` → `date`

**Points Odoo 19 spécifiques :**
- `invisible="state != 'results'"` (Python, pas domain)
- `env[...]` interdit dans les vues → champ `bdgest_enabled` computed sur le wizard
- `role="status"` requis sur `div.alert-info`
- `button_box` absent de la vue album → inséré via `xpath` avant `oe_title`
- Action liste liée via `binding_model_id` + `binding_view_types="list"`

*Maintenu par sessions — ajouter une entrée datée à chaque modification significative.*

---

## 2026-05-15 (suite 5) — US-023 complété + Epic 5 (Vues avancées)

### US-023 — Conflits de titres dans le wizard de résultats

**`comic_datasource/views/comic_datasource_wizard_views.xml`**

- Ajout de `decoration-danger="title_conflict"` et `decoration-warning="is_duplicate and not title_conflict"` sur la liste de résultats
- Nouvelles colonnes `existing_title` et `title_action` (visibles uniquement si `title_conflict`)
- Bannière d'avertissement : "⚠️ Certains titres diffèrent de la version en base" (masquée si `not has_title_conflicts`)
- Ajout de `has_title_conflicts` dans le bloc de champs cachés

---

### Nouveau — Wizard mise à jour des albums d'une série depuis les sources

**Fichiers créés dans `comic_datasource/` :**

| Fichier | Description |
|---|---|
| `models/comic_serie.py` | Inherit `comic.serie` → `action_update_albums_from_datasource()` |
| `wizards/comic_serie_update_wizard.py` | TransientModel `comic.serie.update.wizard` |
| `views/comic_datasource_serie_inherit_views.xml` | Bouton dans le form Serie + vue wizard |

**`comic_serie_update_wizard.py` :**
- États : `confirm` / `done`
- `action_run()` : itère `serie_id.album_ids.sorted('tome')`, cherche par ISBN ou titre via aggregator
- `_apply_data()` : met à jour synopsis, nb_pages, isbn (si manquant), date_parution, date_depot_legal, couverture (via `requests`), auteurs manquants
- `_best_match()` : résultat dont le tome correspond, ou premier résultat en fallback
- `_build_report()` : HTML ✅/⏭️/❌ par album
- Classe `_FakeAgg` : enveloppe les résultats de recherche par titre dans la même interface que les résultats ISBN

**Vue wizard :**
- État `confirm` : message informatif + bouton "Lancer la mise à jour"
- État `done` : rapport HTML inline + bouton "Fermer"
- Bouton dans le form série via `xpath` avant `oe_title` → `button_box` avec icône `fa-refresh`

---

### US-025 — Génération automatique des liens d'achat (depuis ISBN)

**`comics_collections/models/comic_album.py`**

Nouveaux champs :
- `url_fnac_be = fields.Char(string='Lien FNAC.be')`
- `has_cover = fields.Boolean(compute='_compute_has_cover', store=True)` (utilisé par les kanbans)

Templates de liens :
```python
_PURCHASE_LINK_TEMPLATES = {
    'url_club_be':   'https://www.librairieclub.be/c/search?filter=search({isbn})&page=1&page_size=24&sort=RelevanceClub&sort_type=desc',
    'url_amazon_be': 'https://www.amazon.com.be/s?k={isbn}',
    'url_fnac_be':   'https://www.fnac.be/SearchResult/ResultList.aspx?Search={isbn}&sft=2',
}
```

- `create()` surchargé avec `@api.model_create_multi` → `setdefault()` pour ne pas écraser les liens existants à l'import CSV
- `@api.onchange('isbn')` → remplit les champs vides dans l'interface form
- `action_generate_purchase_links()` : régénère les 3 liens depuis l'ISBN courant
- `action_open_club_be()`, `action_open_amazon_be()` : `ir.actions.act_url` avec `target: 'new'`

**`comics_collections/views/comic_album_views.xml`** :
- Nouvel onglet "Liens d'achat" avec les 3 URL (`widget="url"`)
- Bouton "Régénérer les liens" (masqué si pas d'ISBN)

---

### Epic 5 — Vues avancées (US-009, US-010)

#### Infrastructure SCSS

**`comics_collections/static/src/scss/comics_theme.scss`** (nouveau)

Design system : INK `#022E51`, CREAM `#f3eee4`, ACCENT `#B74803`, STAR `#CC6D3D`, polices Instrument Serif + Instrument Sans.

Composants CSS :
- `.o_comic_album_card` — carte 200px avec hover
- `.o_comic_cover` — zone couverture 200×270px
- `.o_comic_cover_placeholder` — 8 palettes de couleurs (`.o_comic_pal_0` … `.o_comic_pal_7`), layout éditorial (bande, titre série, séparateur, titre, numéro tome)
- `.o_comic_reading_badge` — badges `.o_badge_lu` / `.o_badge_en_cours` / `.o_badge_non_lu`
- `.o_comic_stars` — étoiles pleines/vides
- `.o_comic_serie_card` — carte série avec couverture 120px, badge statut, barre de progression
- Scoping via `.o_kanban_view.o_comic_kanban_albums` et `.o_kanban_view.o_comic_kanban_series` + `!important` (libsass)

#### Correctif — Polices Google Fonts (render-blocking)

**Problème :** `@import url('https://fonts.googleapis.com/...')` dans un fichier CSS compilé dans le bundle Odoo bloque le rendu entier de l'interface si Google Fonts CDN est lent ou inaccessible.

**Fix :**
- Suppression de `comics_fonts.css` des assets
- Création de `comics_collections/views/comic_fonts_template.xml` : hérite `web.layout`, injecte dans `<head>` des balises `<link rel="preconnect">` + `<link rel="stylesheet">` non-bloquantes

#### US-010 — Kanban Albums

**`comics_collections/views/comic_album_views.xml`** :
- Nouvelle vue kanban `view_comic_album_kanban` (`class="o_comic_kanban_albums"`)
- Couverture ou placeholder avec palette selon `id % 8`
- Étoiles : `t-foreach="[1, 2, 3, 4, 5]"` avec `s <= (record.note.raw_value || 0)`
- Badge état lecture : `t-attf-class="o_comic_reading_badge o_badge_#{record.etat_lecture.raw_value}"`
- Cœur wishlist : `♥` si `dans_wishlist`
- `action_comic_album` → `view_mode: kanban,list,form`
- Nouvelle action `action_comic_wishlist` (`domain: dans_wishlist = True`)

#### US-009 — Kanban Séries

**`comics_collections/views/comic_serie_views.xml`** :
- Nouvelle vue kanban `view_comic_serie_kanban` (`class="o_comic_kanban_series"`)
- Barre de progression : `Math.round(nb_possedes / nb_total * 100)%`
- Badge statut dans la couverture
- `action_comic_serie` → `view_mode: kanban,list,form`

#### Menu Wishlist

**`comics_collections/views/comic_menu.xml`** :
- Ajout menu "Wishlist" (sequence 25) pointant vers `action_comic_wishlist`

#### `comics_collections/models/comic_serie.py`
- `has_cover = fields.Boolean(compute='_compute_has_cover', store=True)` (utilisé dans le kanban série)

---

### Correctif Odoo 19 — Template kanban `card`

**Problème :** `KanbanArchParser.parse: Missing 'card' template` — Odoo 19 (OWL) impose `t-name="card"` au lieu de `t-name="kanban-box"` (Odoo ≤18).

**Fix :** `replace_all=true` sur `comic_album_views.xml` et `comic_serie_views.xml`.

---

### `__manifest__.py` mis à jour

```python
'data': [
    ...
    'views/comic_fonts_template.xml',
],
'assets': {
    'web.assets_backend': [
        'comics_collections/static/src/scss/comics_theme.scss',
    ],
},
```
