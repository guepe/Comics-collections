# CLAUDE.md — Projet Odoo Comic Collection

> Ce fichier est le contexte principal à fournir à Claude dans Visual Studio Code.
> Il décrit l'architecture, les conventions et les règles du projet.

---

## 🎯 Objectif du projet

Développer un ensemble de modules Odoo 19 (open source) permettant à un utilisateur de gérer sa collection personnelle de bandes dessinées, avec :

- Un module principal de gestion de collection
- Un connecteur de scraping vers BDGest / Bedetheque
- Un connecteur IA (Claude + OpenAI) pour enrichir les fiches
- Un système d'import CSV/XLS/XLSX

---

## 🗂️ Structure des modules

> Les modules sont directement à la racine du projet (pas de dossier `addons/`).

```
Comics-collections/
├── comics_collections/      # Module principal
│   ├── models/
│   ├── views/
│   ├── wizards/
│   │   └── comic_import_wizard.py   # Import CSV/XLS/XLSX (intégré ici, pas de module séparé)
│   ├── data/
│   │   ├── comic_genre_data.xml
│   │   └── comic_cron_data.xml      # Cron quotidien enrichissement via datasource
│   ├── demo/
│   ├── security/
│   └── static/
├── comic_datasource/        # Connecteur multi-sources (Google Books, Open Library, BnF, BDGest)
│   ├── sources/
│   │   ├── base.py
│   │   ├── google_books.py
│   │   ├── open_library.py
│   │   ├── bnf.py
│   │   └── bdgest.py        # fallback scraping
│   ├── aggregator.py
│   ├── models/
│   ├── wizards/
│   │   ├── comic_datasource_search_wizard.py
│   │   ├── comic_serie_missing_wizard.py
│   │   └── comic_serie_update_wizard.py
│   └── data/
│       ├── comic_datasource_config.xml
│       └── comic_serie_cron.xml     # Cron hebdomadaire suivi séries
├── comic_bdgest/            # Ancien module scraping BDGest (coexiste en attendant migration)
│   ├── scraper/
│   ├── models/
│   └── wizards/
└── comic_ai/                # Connecteur IA Claude + OpenAI (à implémenter — US-026 à US-029)
```

---

## ⚙️ Environnement technique

| Paramètre       | Valeur               |
| --------------- | -------------------- |
| Version Odoo    | **19.0**             |
| Licence         | LGPL-3 (OCA style)   |
| Python          | 3.12+                |
| Base de données | PostgreSQL 16        |
| Style de code   | PEP8, OCA guidelines |
| Branche Git     | `19.0`               |

### Dépendances Python externes

```
requests
beautifulsoup4
lxml
openai
anthropic
openpyxl
xlrd
xmltodict
```

### APIs externes utilisées (sans scraping)

| API               | Auth             | Usage                                | Limite                |
| ----------------- | ---------------- | ------------------------------------ | --------------------- |
| Google Books API  | Clé API gratuite | Métadonnées + synopsis + couvertures | 1000 req/jour gratuit |
| Open Library API  | Aucune           | Couvertures + métadonnées + auteurs  | Illimitée             |
| BnF SRU API       | Aucune           | BD francophones (dépôt légal)        | Illimitée             |
| BDGest (scraping) | Login optionnel  | Fallback uniquement                  | Délai 2s obligatoire  |

---

## 📦 Module 1 — `comics_collections`

### Modèles

#### `comic.serie`

| Champ                | Type      | Description                            |
| -------------------- | --------- | -------------------------------------- |
| `name`               | Char      | Titre de la série                      |
| `type`               | Selection | `bd` / `manga` / `comics` / `one_shot` |
| `statut`             | Selection | `en_cours` / `terminee` / `abandonnee` |
| `genre_id`           | Many2one  | → `comic.genre`                        |
| `editeur_id`         | Many2one  | → `comic.editeur`                      |
| `image_couverture`   | Image     | Couverture de la série                 |
| `synopsis`           | Html      | Résumé (peut être généré par IA)       |
| `bdgest_id`          | Integer   | ID BDGest de la série                  |
| `bedetheque_url`     | Char      | URL Bedetheque                         |
| `album_ids`          | One2many  | → `comic.album`                        |
| `nb_albums_total`    | Integer   | Nombre total de tomes (computed)       |
| `nb_albums_possedes` | Integer   | Tomes possédés (computed)              |
| `active`             | Boolean   | Archivage standard Odoo                |

#### `comic.album`

| Champ              | Type      | Description                      |
| ------------------ | --------- | -------------------------------- |
| `name`             | Char      | Titre de l'album                 |
| `serie_id`         | Many2one  | → `comic.serie`                  |
| `tome`             | Integer   | Numéro du tome                   |
| `isbn`             | Char      | ISBN (validé format EAN-13)      |
| `date_depot_legal` | Date      | Date dépôt légal                 |
| `date_parution`    | Date      | Date de parution                 |
| `nb_pages`         | Integer   | Nombre de pages                  |
| `image_couverture` | Image     | Couverture de l'album            |
| `synopsis`         | Html      | Résumé (peut être généré par IA) |
| `note`             | Float     | Note 0.0 à 5.0                   |
| `etat_lecture`     | Selection | `non_lu` / `en_cours` / `lu`     |
| `dans_collection`  | Boolean   | Album physiquement possédé       |
| `dans_wishlist`    | Boolean   | Album sur liste de souhaits      |
| `url_club_be`      | Char      | Lien achat club.be               |
| `url_amazon_be`    | Char      | Lien achat amazon.com.be         |
| `bdgest_album_id`  | Integer   | ID album sur BDGest              |
| `auteur_line_ids`  | One2many  | → `comic.album.auteur.line`      |
| `active`           | Boolean   | Archivage standard Odoo          |

#### `comic.album.auteur.line`

Table de liaison album ↔ auteur avec rôle.

| Champ        | Type      | Description                                                                     |
| ------------ | --------- | ------------------------------------------------------------------------------- |
| `album_id`   | Many2one  | → `comic.album`                                                                 |
| `partner_id` | Many2one  | → `res.partner` (contacts Odoo natifs)                                          |
| `role`       | Selection | `scenariste` / `dessinateur` / `coloriste` / `encreur` / `traducteur` / `autre` |

#### `comic.editeur`

| Champ               | Type     | Description                 |
| ------------------- | -------- | --------------------------- |
| `name`              | Char     | Nom de l'éditeur            |
| `partner_id`        | Many2one | → `res.partner` (optionnel) |
| `pays_id`           | Many2one | → `res.country`             |
| `site_web`          | Char     | Site web                    |
| `bdgest_editeur_id` | Integer  | ID BDGest                   |

#### `comic.genre`

| Champ         | Type    | Description                   |
| ------------- | ------- | ----------------------------- |
| `name`        | Char    | Nom du genre                  |
| `description` | Text    | Description                   |
| `color`       | Integer | Couleur (kanban color widget) |

#### `comic.pret`

| Champ                   | Type     | Description                                        |
| ----------------------- | -------- | -------------------------------------------------- |
| `edition_id`            | Many2one | → `comic.edition` (remplace album_id après US-051) |
| `partner_id`            | Many2one | → `res.partner` (l'ami)                            |
| `date_pret`             | Date     | Date du prêt                                       |
| `date_retour_prevue`    | Date     | Date retour prévue                                 |
| `date_retour_effective` | Date     | Date retour réelle                                 |
| `retourne`              | Boolean  | Retourné ?                                         |
| `notes`                 | Text     | Notes libres                                       |

---

### ERD final — Architecture canonique (Phase 10 — US-050 → US-055)

> **Décision US-050 :** `comic.album` est remplacé par trois modèles distincts.
> `comic.album.auteur.line` est remplacé par `comic.work.auteur.line`.
>
> **Décision UX associée :** le modèle technique expose `comic.work` et `comic.edition`,
> mais les parcours courants doivent continuer à parler de **séries**, **tomes** et
> **albums**. Les termes "Œuvre" et "Édition" sont réservés aux vues avancées,
> au référentiel technique et aux diagnostics.

```
comic.serie ──────────────────────────────────────────────────────────────────
  │  name, type, statut, genre_id, editeur_id, image_couverture, synopsis    │
  │  slug: Char (unique, indexé) — auto-généré                               │
  │  name_normalise: Char (compute, store=True, index=True)                  │
  └──< comic.work  ──────────────────────────────────────────────────────────┘
         │  titre_canonique: Char (required)                                 │
         │  tome: Integer                                                    │
         │  slug: Char (unique, indexé) — ex. "thorgal-t05"                 │
         │  titre_normalise: Char (compute, store=True, index=True)         │
         │  wikidata_id, openlibrary_id, bedetheque_id, comicvine_id: Char  │
         │  Constraint UNIQUE(serie_id, tome)                                │
         │  hérite mail.thread + mail.activity.mixin                        │
         ├──< comic.work.auteur.line  ─────────────────────────────────────  │
         │      work_id → comic.work (required, cascade)                    │
         │      partner_id → res.partner                                    │
         │      role: Selection (scenariste/dessinateur/coloriste/…)        │
         └──< comic.edition ───────────────────────────────────────────────  │
                │  work_id → comic.work (required, restrict)               │
                │  editeur_id → comic.editeur                              │
                │  date_parution: Date                                     │
                │  langue: Selection (fr/nl/en/de/autre)                   │
                │  format: Selection (broche/cartonne/integrale/           │
                │           collector/numerique/autre)                     │
                │  image_couverture: Image                                 │
                │  synopsis: Html                                          │
                │  nb_pages: Integer                                       │
                │  url_club_be, url_amazon_be, url_fnac_be: Char           │
                │  product_tmpl_id → product.template (One2one-like)       │
                │  hérite mail.thread + mail.activity.mixin                │
                └──< comic.isbn ──────────────────────────────────────────
                       edition_id → comic.edition (required, cascade)
                       isbn_13: Char (EAN-13 validé, UNIQUE)
                       isbn_10: Char (optionnel, validé si renseigné)
                       normalisation auto (tirets/espaces supprimés)

comic.customer.album ──────────────────────────────────────────────────────────
  partner_id → res.partner (required)
  edition_id → comic.edition (required — remplace album_id)
  work_id: Many2one compute (edition_id.work_id, store=True)
  source, etat_lecture, dans_collection, dans_wishlist, note, commentaire
  Constraint UNIQUE(partner_id, edition_id)

comic.pret ─────────────────────────────────────────────────────────────────
  edition_id → comic.edition (required — remplace album_id)
  partner_id → res.partner
  date_pret, date_retour_prevue, date_retour_effective, retourne, notes
```

#### Règles de normalisation de titre (stratégie anti-doublons — US-050 B)

```python
# Appliquées sur comic.work.titre_normalise et comic.serie.name_normalise
# 1. unicodedata.normalize('NFD') + suppression des accents (catégorie Mn)
# 2. lower()
# 3. Suppression des articles définis en tête :
#    FR : le / la / les / l'   |   NL : de / het / een   |   EN : the / a / an
# 4. Suppression des suffixes de catalogue : " (les)" / " (de)" / " (the)" en fin de chaîne
# 5. Suppression des ponctuations non significatives : tirets, points, virgules, guillemets
# 6. Normalisation des espaces multiples → strip()

# Exemples :
# "Les Landes perdues"          → "landes perdues"
# "Landes perdues (Les)"        → "landes perdues"   ✓ identiques
# "Thorgal (Les aventures de)"  → "thorgal"
# "l'Enfant des étoiles"        → "enfant des etoiles"
```

#### Algorithme de détection de doublons (US-056)

| Score                | Critère                                                      | Action                       |
| -------------------- | ------------------------------------------------------------ | ---------------------------- |
| **Conflit certain**  | Même `(serie_id, tome)` → Constraint UNIQUE bloque           | Erreur bloquante             |
| **Doublon probable** | Même `serie_id` + même `tome` + `titre_normalise` identique  | Popup "Fusionner ou créer ?" |
| **Doublon possible** | `SequenceMatcher(titre_norm_A, titre_norm_B).ratio() ≥ 0.85` | Popup de confirmation        |
| **OK**               | Aucun candidat trouvé                                        | Création normale             |

> Algorithme retenu : `difflib.SequenceMatcher` (stdlib Python, seuil 0.85) — pas de dépendance externe.

### Vues à créer

- `comic.serie` : list, form, kanban (avec couverture), search
- façade utilisateur "Albums / Tomes" : basée sur `comic.work` + édition de référence,
  avec vues techniques `comic.work`, `comic.edition`, `comic.isbn` pour les managers
- `comic.pret` : list, form
- `comic.genre` : list, form
- `comic.editeur` : list, form
- Dashboard : statistiques de la collection

### Menus

```
Bandes Dessinées
├── Ma Collection
│   ├── Séries
│   ├── Albums / Tomes
│   └── Prêts
├── Catalogues
│   ├── Auteurs (res.partner filtré)
│   ├── Éditeurs
│   └── Genres
├── Wishlist
└── Configuration
    ├── Paramètres IA
    ├── Référentiel avancé (Œuvres / Éditions / ISBNs)
    └── BDGest
```

---

## 📦 Module 2 — `comic_datasource`

> Remplace l'ancien module `comic_bdgest`.
> Agrège plusieurs sources de données ouvertes + BDGest en fallback.

### Dépend de

`comic_collection`

### Architecture — Cascade de sources

La recherche suit cette priorité automatique :

1. **Google Books API** → synopsis, couverture HD, métadonnées générales
2. **Open Library API** → couverture alternative, auteurs, éditions multiples
3. **BnF SRU API** → données officielles BD francophones (dépôt légal)
4. **BDGest scraping** → fallback uniquement, avec avertissement légal à l'utilisateur

### Sous-modules

#### `comic_datasource/sources/google_books.py`

- Classe `GoogleBooksSource`
- Méthode `search_by_isbn(isbn)` → dict normalisé
- Méthode `search_by_title(title, author=None)` → liste de résultats
- Endpoint : `https://www.googleapis.com/books/v1/volumes?q=isbn:{isbn}&key={key}`
- Retourne : titre, auteurs, éditeur, date, pages, synopsis, URL couverture (small/medium/large/extraLarge)
- Clé API stockée en `ir.config_parameter` : `comic.google_books_api_key`

#### `comic_datasource/sources/open_library.py`

- Classe `OpenLibrarySource`
- Méthode `search_by_isbn(isbn)` → dict normalisé
- Méthode `get_cover_url(isbn, size='L')` → URL directe (S/M/L)
- Endpoint données : `https://openlibrary.org/api/books?bibkeys=ISBN:{isbn}&format=json&jscmd=data`
- Endpoint couverture : `https://covers.openlibrary.org/b/isbn/{isbn}-L.jpg`
- Aucune clé API requise

#### `comic_datasource/sources/bnf.py`

- Classe `BnfSource`
- Méthode `search_by_isbn(isbn)` → dict normalisé
- Méthode `search_by_title(title)` → liste de résultats
- Endpoint : `http://catalogue.bnf.fr/api/SRU?version=1.2&operation=searchRetrieve&query=bib.isbn+adj+"{isbn}"`
- Parsing XML (utiliser `xmltodict`)
- Aucune clé API requise

#### `comic_datasource/sources/bdgest.py`

- Classe `BdgestSource` (scraping — fallback uniquement)
- AVERTISSEMENT : afficher disclaimer légal avant activation
- Méthode `search_by_isbn(isbn)` → dict normalisé
- Méthode `search_by_title(title)` → liste de résultats
- Méthode `get_serie_albums(bdgest_serie_id)` → liste complète
- Délai 2 secondes entre requêtes (OBLIGATOIRE)
- Credentials optionnels : `comic.bdgest_login` / `comic.bdgest_password`

#### `comic_datasource/aggregator.py`

- Classe `ComicDataAggregator`
- Méthode `search(isbn=None, title=None, author=None)` → résultat fusionné
- Logique de cascade : tente chaque source dans l'ordre, fusionne les champs
- Priorité couverture : Google Large > Open Library L > BDGest
- Priorité synopsis : Google > BnF > BDGest
- Priorité métadonnées BD FR : BnF > Google > Open Library

### Modèle normalisé retourné par chaque source

```python
{
    'title': str,
    'serie_name': str | None,
    'tome': int | None,
    'isbn': str,
    'date_parution': str,  # YYYY-MM-DD
    'nb_pages': int | None,
    'editeur': str | None,
    'auteurs': [
        {'name': str, 'role': 'scenariste'|'dessinateur'|'coloriste'|'autre'}
    ],
    'synopsis': str | None,  # HTML ou texte brut
    'cover_url': str | None,
    'cover_url_small': str | None,
    'source': 'google'|'openlibrary'|'bnf'|'bdgest',
}
```

### Wizard `comic.datasource.search.wizard`

- Champ `search_term` (isbn ou titre)
- Champ `search_type` : `isbn` / `title`
- Bouton `action_search()` → appelle l'aggregator, affiche résultats fusionnés
- `result_ids` : One2many vers `comic.datasource.result.line`
- Affichage source utilisée pour chaque champ (badge coloré)
- Case à cocher multi-sélection
- `action_import_selected()` → crée les enregistrements Odoo

### Configuration (`res.config.settings`)

| Paramètre        | ir.config_parameter key      | Description                           |
| ---------------- | ---------------------------- | ------------------------------------- |
| Clé Google Books | `comic.google_books_api_key` | Gratuite sur console.cloud.google.com |
| Login BDGest     | `comic.bdgest_login`         | Optionnel                             |
| MDP BDGest       | `comic.bdgest_password`      | Optionnel, champ password             |
| Sources actives  | `comic.datasource_order`     | Ordre de priorité (JSON list)         |
| Délai BDGest     | `comic.bdgest_delay`         | Délai en secondes (défaut: 2)         |

---

## 📦 Module 3 — `comic_ai`

### Dépend de

`comic_collection`

### Configuration (`res.config.settings`)

| Paramètre                 | Description                                        |
| ------------------------- | -------------------------------------------------- |
| `comic_ai_provider`       | `claude` / `openai`                                |
| `comic_ai_claude_api_key` | Clé API Anthropic (champ password)                 |
| `comic_ai_openai_api_key` | Clé API OpenAI (champ password)                    |
| `comic_ai_model_claude`   | ex: `claude-sonnet-4-6`                            |
| `comic_ai_model_openai`   | ex: `gpt-4o`                                       |
| `comic_ai_language`       | Langue par défaut des résumés (`fr` / `nl` / `en`) |

### Actions IA sur `comic.album`

Bouton "✨ Générer avec l'IA" dans le formulaire album, ouvrant un wizard :

`comic.ai.wizard` :

- `album_id`
- `action_type` : `synopsis` / `translate` / `suggest_similar` / `full_sheet`
- `target_language` : pour la traduction
- `result` : Html (prévisualisation)
- `action_apply()` : colle le résultat dans le champ cible
- `action_regenerate()` : relance la génération

### Prompts (dans `comic_ai/prompts/`)

- `prompt_synopsis.txt`
- `prompt_translate.txt`
- `prompt_suggest_similar.txt`
- `prompt_full_sheet.txt`

---

## 📦 Module 4 — `comic_import`

### Dépend de

`comic_collection`

### Format CSV/XLS/XLSX

Colonnes attendues (ordre flexible, mapping configurable) :

```
serie_name, tome, titre_album, isbn, date_parution, nb_pages,
editeur, scenariste, dessinateur, coloriste, genre,
etat_lecture, note, url_couverture, url_club_be, url_amazon_be
```

### Wizard `comic.import.wizard`

- Upload du fichier (CSV, XLS ou XLSX)
- Détection automatique du séparateur CSV
- Étape 1 : mapping des colonnes
- Étape 2 : prévisualisation (10 premières lignes)
- Étape 3 : import avec rapport d'erreurs

---

## 🧑‍💻 Conventions de code

### Nommage

- Modèles : `comic.xxx` (snake_case avec point)
- Classes Python : `ComicXxx` (PascalCase)
- Fichiers XML : `views/comic_xxx_views.xml`
- Fichiers Python : `models/comic_xxx.py`

### Structure d'un module

```
comics_collections/
├── __init__.py
├── __manifest__.py
├── models/
│   ├── __init__.py
│   ├── comic_serie.py
│   ├── comic_album.py
│   ├── comic_auteur_line.py
│   ├── comic_editeur.py
│   ├── comic_genre.py
│   └── res_partner.py
├── views/
│   ├── comic_serie_views.xml
│   ├── comic_album_views.xml
│   ├── comic_genre_views.xml
│   ├── comic_editeur_views.xml
│   ├── comic_menu.xml
│   └── comic_dashboard.xml
├── wizards/
│   └── comic_import_wizard.py  # Import CSV/XLS/XLSX
├── data/
│   ├── comic_genre_data.xml    # genres de base
│   └── comic_cron_data.xml     # cron enrichissement
├── demo/
│   └── comic_demo.xml
├── security/
│   ├── ir.model.access.csv
│   └── comic_security.xml
├── static/
│   └── description/
│       └── icon.png
└── README.rst
```

### `__manifest__.py` type

```python
{
    'name': 'Comic Collection',
    'version': '19.0.1.0.0',
    'category': 'Leisure',
    'summary': 'Gérez votre collection de bandes dessinées',
    'author': 'Votre Nom',
    'license': 'LGPL-3',
    'depends': ['base', 'mail', 'contacts'],
    'data': [...],
    'demo': [...],
    'installable': True,
    'application': True,
    'auto_install': False,
}
```

### Identifiants de module XML

Le module principal s'appelle **`comics_collections`** (avec "s"). Tous les identifiants XML doivent utiliser ce préfixe :

```xml
<!-- ✅ correct -->
comics_collections.group_comic_user
comics_collections.group_comic_manager

<!-- ❌ incorrect -->
comic_collection.group_comic_user
```

---

## 🚦 Règles importantes pour Claude

1. **Toujours** utiliser l'ORM Odoo, jamais de SQL brut sauf exception justifiée
2. **Toujours** hériter de `mail.thread` et `mail.activity.mixin` sur les modèles principaux
3. **Toujours** ajouter `_description` sur chaque modèle
4. **Toujours** mettre les droits d'accès dans `ir.model.access.csv`
5. Les champs `image_couverture` utilisent `fields.Image` (pas `Binary`) pour le resize automatique
6. Les clés API sont stockées en `config_parameter` (jamais en dur)
7. Le scraping BDGest doit respecter un délai de **2 secondes** entre chaque requête
8. Chaque module a son propre `__manifest__.py` avec les bonnes dépendances
9. Les vues Kanban des albums doivent afficher la couverture en priorité
10. Compatible Odoo 19.0 uniquement — ne pas utiliser d'API dépréciées
11. Le module `comic_datasource` utilise UNIQUEMENT des APIs publiques et légales en priorité (Google Books, Open Library, BnF) — le scraping BDGest est un fallback de dernier recours avec avertissement légal explicite à l'utilisateur
12. Les clés API Google Books sont gratuites mais doivent être créées sur console.cloud.google.com par l'utilisateur final — ne jamais hardcoder de clé
13. L'aggregator fusionne les données de plusieurs sources — en cas de conflit, les métadonnées BnF sont prioritaires pour les BD francophones

---

## ⚠️ Incompatibilités Odoo 19 — référence rapide

Ces changements cassent silencieusement le code Odoo 17/18. À vérifier systématiquement.

| Modèle              | Champ/attribut                       | Changement                                                                                      |
| ------------------- | ------------------------------------ | ----------------------------------------------------------------------------------------------- |
| `res.groups`        | `category_id`                        | **Supprimé** — utiliser `res.groups.privilege` (nouveau modèle)                                 |
| `res.groups`        | `users`                              | **Renommé** en `user_ids`                                                                       |
| `ir.actions.server` | `groups_id`                          | **Renommé** en `group_ids`                                                                      |
| Modèles ORM         | `_sql_constraints`                   | **Déprécié/non supporté** — déclarer des attributs `models.Constraint(...)`                     |
| Vues search         | `<group expand string>`              | `expand` et `string` **supprimés** — utiliser `<group name="group_by">`                         |
| Vues héritées       | `<page string="..." position="...">` | `string` interdit comme sélecteur — utiliser un `<xpath>` stable (`name`, champ enfant, classe) |

### Syntaxe Many2many en XML

```xml
<!-- ✅ Odoo 19 -->
<field name="implied_ids" eval="[Command.link(ref('base.group_user'))]"/>
<field name="user_ids" eval="[Command.link(ref('base.user_root'))]"/>

<!-- ❌ Odoo ≤18 (ne fonctionne plus) -->
<field name="implied_ids" eval="[(4, ref('base.group_user'))]"/>
<field name="users" eval="[(4, ref('base.user_root'))]"/>
```

### Architecture groupes de sécurité Odoo 19

```
ir.module.category  ←  res.groups.privilege  ←  res.groups
                          (nouveau modèle)
```

Les groupes doivent avoir un `privilege_id` pointant vers un `res.groups.privilege`.

### Cache Docker

Après modification d'un `.py` avec un volume Docker monté, supprimer le cache :

```bash
find /chemin/module -name "__pycache__" -exec rm -rf {} +
docker logs -f odoo-web

ou les logs /var/lib/docker/containers/1a1388a3d44137e1d6807a00a76dae51ce907c08b0c704523a271b9b21a7bd48/1a1388a3d44137e1d6807a00a76dae51ce907c08b0c704523a271b9b21a7bd48-json.log

```

---

## 🕐 Crons configurés

| Module               | Fichier                     | Fréquence        | Action                                       |
| -------------------- | --------------------------- | ---------------- | -------------------------------------------- |
| `comics_collections` | `data/comic_cron_data.xml`  | Quotidien (2h00) | Enrichissement des albums via datasource     |
| `comic_datasource`   | `data/comic_serie_cron.xml` | Hebdomadaire     | Vérification nouveaux tomes (séries suivies) |

---

## 📋 Suivi de projet — Règles de handoff entre sessions

Ces deux fichiers doivent être maintenus à jour **à la fin de chaque session de travail**, avant le commit final.

### `USER_STORIES.md`

**Règle :** Dès qu'une US est terminée (tous ses critères d'acceptance validés), cocher toutes ses cases `[ ]` → `[x]` et ajouter `✅` après le titre.

- Cocher **uniquement** les critères réellement implémentés et testés
- Ne jamais cocher par anticipation
- Si une US est partiellement faite, ne cocher que les cases correspondantes

### `CHANGE.md` (à la racine du projet)

**Règle :** Ajouter une entrée datée à chaque fin de session couvrant **tout** ce qui a été fait.

Format d'une entrée :

```
## YYYY-MM-DD (suite N) — Titre court

### US-XXX — Titre
Fichiers modifiés/créés, description des changements.

### Correctif — Titre
Description du bug et du fix.
```

- Inclure : fichiers créés/modifiés, méthodes ajoutées, bugs corrigés, décisions techniques
- Inclure les **erreurs rencontrées et leurs solutions** (précieux pour les sessions suivantes)
- Ne pas résumer ce qui est déjà dans `USER_STORIES.md` — aller dans le détail technique
- ne pas relire tout le fichier, just append.
