# CLAUDE.md — Projet Odoo Comic Collection

> Ce fichier est le contexte principal à fournir à Claude dans Visual Studio Code.
> Il décrit l'architecture, les conventions et les règles du projet.

---

## 🎯 Objectif du projet

Développer un ensemble de modules Odoo 19 (open source) permettant à un utilisateur de gérer sa collection personnelle de bandes dessinées, avec :
- Un module principal de gestion de collection
- Un connecteur de scraping vers BDGest / Bedetheque
- Un connecteur IA (Claude + OpenAI) pour enrichir les fiches
- Un système d'import CSV/XLSX

---

## 🗂️ Structure des modules

```
addons/
├── comic_collection/        # Module principal
├── comic_bdgest/            # Connecteur scraping BDGest
├── comic_ai/                # Connecteur IA Claude + OpenAI
└── comic_import/            # Import CSV/XLSX
```

---

## ⚙️ Environnement technique

| Paramètre | Valeur |
|---|---|
| Version Odoo | **19.0** |
| Licence | LGPL-3 (OCA style) |
| Python | 3.12+ |
| Base de données | PostgreSQL 16 |
| Style de code | PEP8, OCA guidelines |
| Branche Git | `19.0` |

### Dépendances Python externes
```
requests
beautifulsoup4
lxml
openai
anthropic
openpyxl
```

---

## 📦 Module 1 — `comic_collection`

### Modèles

#### `comic.serie`
| Champ | Type | Description |
|---|---|---|
| `name` | Char | Titre de la série |
| `type` | Selection | `bd` / `manga` / `comics` / `one_shot` |
| `statut` | Selection | `en_cours` / `terminee` / `abandonnee` |
| `genre_id` | Many2one | → `comic.genre` |
| `editeur_id` | Many2one | → `comic.editeur` |
| `image_couverture` | Image | Couverture de la série |
| `synopsis` | Html | Résumé (peut être généré par IA) |
| `bdgest_id` | Integer | ID BDGest de la série |
| `bedetheque_url` | Char | URL Bedetheque |
| `album_ids` | One2many | → `comic.album` |
| `nb_albums_total` | Integer | Nombre total de tomes (computed) |
| `nb_albums_possedes` | Integer | Tomes possédés (computed) |
| `active` | Boolean | Archivage standard Odoo |

#### `comic.album`
| Champ | Type | Description |
|---|---|---|
| `name` | Char | Titre de l'album |
| `serie_id` | Many2one | → `comic.serie` |
| `tome` | Integer | Numéro du tome |
| `isbn` | Char | ISBN (validé format EAN-13) |
| `date_depot_legal` | Date | Date dépôt légal |
| `date_parution` | Date | Date de parution |
| `nb_pages` | Integer | Nombre de pages |
| `image_couverture` | Image | Couverture de l'album |
| `synopsis` | Html | Résumé (peut être généré par IA) |
| `note` | Float | Note 0.0 à 5.0 |
| `etat_lecture` | Selection | `non_lu` / `en_cours` / `lu` |
| `dans_collection` | Boolean | Album physiquement possédé |
| `dans_wishlist` | Boolean | Album sur liste de souhaits |
| `url_club_be` | Char | Lien achat club.be |
| `url_amazon_be` | Char | Lien achat amazon.com.be |
| `bdgest_album_id` | Integer | ID album sur BDGest |
| `auteur_line_ids` | One2many | → `comic.album.auteur.line` |
| `active` | Boolean | Archivage standard Odoo |

#### `comic.album.auteur.line`
Table de liaison album ↔ auteur avec rôle.

| Champ | Type | Description |
|---|---|---|
| `album_id` | Many2one | → `comic.album` |
| `partner_id` | Many2one | → `res.partner` (contacts Odoo natifs) |
| `role` | Selection | `scenariste` / `dessinateur` / `coloriste` / `encreur` / `traducteur` / `autre` |

#### `comic.editeur`
| Champ | Type | Description |
|---|---|---|
| `name` | Char | Nom de l'éditeur |
| `partner_id` | Many2one | → `res.partner` (optionnel) |
| `pays_id` | Many2one | → `res.country` |
| `site_web` | Char | Site web |
| `bdgest_editeur_id` | Integer | ID BDGest |

#### `comic.genre`
| Champ | Type | Description |
|---|---|---|
| `name` | Char | Nom du genre |
| `description` | Text | Description |
| `color` | Integer | Couleur (kanban color widget) |

#### `comic.pret`
| Champ | Type | Description |
|---|---|---|
| `album_id` | Many2one | → `comic.album` |
| `partner_id` | Many2one | → `res.partner` (l'ami) |
| `date_pret` | Date | Date du prêt |
| `date_retour_prevue` | Date | Date retour prévue |
| `date_retour_effective` | Date | Date retour réelle |
| `retourne` | Boolean | Retourné ? |
| `notes` | Text | Notes libres |

### Vues à créer
- `comic.serie` : list, form, kanban (avec couverture), search
- `comic.album` : list, form, kanban (avec couverture + étoiles), search
- `comic.pret` : list, form
- `comic.genre` : list, form
- `comic.editeur` : list, form
- Dashboard : statistiques de la collection

### Menus
```
Bandes Dessinées
├── Ma Collection
│   ├── Séries
│   ├── Albums
│   └── Prêts
├── Catalogues
│   ├── Auteurs (res.partner filtré)
│   ├── Éditeurs
│   └── Genres
├── Wishlist
└── Configuration
    ├── Paramètres IA
    └── BDGest
```

---

## 📦 Module 2 — `comic_bdgest`

### Dépend de
`comic_collection`

### Fonctionnement
- Scraping HTTP de `bedetheque.com` via `requests` + `BeautifulSoup4`
- Pas d'API officielle disponible → scraping respectueux (délai entre requêtes)
- Stockage du `bdgest_album_id` et `bdgest_id` pour éviter les doublons

### Wizard `comic.bdgest.import.wizard`
Champs :
- `search_term` : terme de recherche
- `search_type` : `title` / `isbn` / `auteur`
- `result_ids` : One2many vers `comic.bdgest.result.line`

`comic.bdgest.result.line` :
- `wizard_id`, `bdgest_album_id`, `serie_name`, `tome`, `titre`, `auteur`, `isbn`, `couverture_url`, `selected`

### Actions
- `action_search()` : appel scraping, peuple `result_ids`
- `action_import_selected()` : crée les enregistrements Odoo depuis les lignes sélectionnées
- `action_sync_serie()` : importe tous les tomes d'une série

### Enrichissement automatique
- Résolution des liens club.be via `https://www.club.be/search?q={isbn}`
- Résolution des liens amazon.com.be via `https://www.amazon.com.be/s?k={isbn}`

---

## 📦 Module 3 — `comic_ai`

### Dépend de
`comic_collection`

### Configuration (`res.config.settings`)
| Paramètre | Description |
|---|---|
| `comic_ai_provider` | `claude` / `openai` |
| `comic_ai_claude_api_key` | Clé API Anthropic (champ password) |
| `comic_ai_openai_api_key` | Clé API OpenAI (champ password) |
| `comic_ai_model_claude` | ex: `claude-sonnet-4-20250514` |
| `comic_ai_model_openai` | ex: `gpt-4o` |
| `comic_ai_language` | Langue par défaut des résumés (`fr` / `nl` / `en`) |

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

### Format CSV/XLSX
Colonnes attendues (ordre flexible, mapping configurable) :
```
serie_name, tome, titre_album, isbn, date_parution, nb_pages,
editeur, scenariste, dessinateur, coloriste, genre,
etat_lecture, note, url_couverture, url_club_be, url_amazon_be
```

### Wizard `comic.import.wizard`
- Upload du fichier (CSV ou XLSX)
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
comic_collection/
├── __init__.py
├── __manifest__.py
├── models/
│   ├── __init__.py
│   ├── comic_serie.py
│   ├── comic_album.py
│   ├── comic_auteur_line.py
│   ├── comic_editeur.py
│   ├── comic_genre.py
│   └── comic_pret.py
├── views/
│   ├── comic_serie_views.xml
│   ├── comic_album_views.xml
│   ├── comic_pret_views.xml
│   ├── comic_genre_views.xml
│   ├── comic_editeur_views.xml
│   ├── comic_menu.xml
│   └── comic_dashboard.xml
├── wizards/
│   └── (wizards ici)
├── data/
│   └── comic_genre_data.xml    # genres de base
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
