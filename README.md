# Comics Collections — Guide des modules Odoo 19

Ensemble de modules Odoo 19 pour gérer une collection personnelle de bandes dessinées.
Auteur : Belspace — Licence : LGPL-3

---

## Vue d'ensemble

```
Comics-collections/
├── comics_collections/    # Module principal (requis)
├── comic_datasource/      # Enrichissement multi-sources (optionnel)
└── comic_bdgest/          # Connecteur BDGest legacy (déprécié)
```

Les modules se déposent dans le répertoire `addons` de votre instance Odoo.

---

## Module 1 — `comics_collections` *(requis)*

**Gestion complète de la collection de bandes dessinées.**

### Ce qu'il fait

- Séries et albums avec couvertures, synopsis, auteurs, éditeurs
- Vues Kanban avec grille de couvertures et barre de progression par série
- Wishlist, état de lecture (Non lu / En cours / Lu), notes par album
- Gestion des prêts, genres, éditeurs
- Liens d'achat auto-générés (Club.be, Amazon.be, FNAC.be)
- Import CSV / XLS / XLSX via wizard
- Auteurs liés aux contacts Odoo natifs (`res.partner`)
- Deux groupes de sécurité : **Utilisateur BD** et **Gestionnaire BD**

### Dépendances Odoo

```python
depends = ['base', 'mail', 'contacts']
```

### Dépendances Python

Aucune dépendance Python externe requise.

### Installation

1. Copier le dossier `comics_collections` dans votre répertoire `addons` Odoo.
2. Redémarrer Odoo (ou recharger la liste des modules).
3. Activer le mode développeur si nécessaire : *Paramètres → Activer le mode développeur*.
4. Dans *Applications*, rechercher **Comic Collection** et cliquer sur **Installer**.

### Configuration après installation

1. Aller dans **Bandes Dessinées → Configuration**.
2. Créer vos premiers genres et éditeurs, ou activer les données de démonstration.

---

## Module 2 — `comic_datasource` *(optionnel, recommandé)*

**Enrichissement automatique des fiches BD depuis plusieurs sources de données.**

### Ce qu'il fait

Recherche et fusionne les métadonnées depuis quatre sources, dans cet ordre de priorité :

| Priorité | Source | Auth | Données |
|---|---|---|---|
| 1 | **Google Books API** | Clé API gratuite | Synopsis, couvertures HD, métadonnées |
| 2 | **Open Library API** | Aucune | Couvertures, auteurs, éditions |
| 3 | **BnF SRU API** | Aucune | BD francophones (dépôt légal officiel) |
| 4 | **BDGest scraping** | Login optionnel | Fallback uniquement — voir avertissement |

> **Avertissement BDGest :** Le scraping de BDGest est un fallback de dernier recours.
> Un avertissement légal s'affiche dans l'interface avant toute activation.
> Un délai de 2 secondes entre chaque requête est imposé automatiquement.

Inclut un wizard de recherche par ISBN ou titre, avec prévisualisation des résultats
et sélection des champs à importer.

### Dépendances Odoo

```python
depends = ['comics_collections']
```

### Dépendances Python

```bash
pip install requests beautifulsoup4 lxml xmltodict
```

### Installation

1. Installer d'abord `comics_collections`.
2. Copier le dossier `comic_datasource` dans votre répertoire `addons`.
3. Mettre à jour la liste des modules dans Odoo.
4. Rechercher **Comic Datasource** dans *Applications* et l'installer.

### Configuration

Aller dans **Bandes Dessinées → Configuration → Sources de données** :

| Paramètre | Description |
|---|---|
| Clé Google Books | Clé API gratuite — créer sur [console.cloud.google.com](https://console.cloud.google.com) |
| Login BDGest | Optionnel — active les résultats membres |
| Mot de passe BDGest | Stocké chiffré |
| Ordre des sources | Priorité personnalisable |
| Délai BDGest | Délai entre requêtes (défaut : 2 s) |

---

## Module 3 — `comic_bdgest`

**Connecteur BDGest / Bedetheque.**

Scraping ciblé sur BDGest : recherche par ISBN ou titre, import détaillé par album,
enrichissement en lot depuis la vue liste. Inclut un parser HTML autonome et des tests
unitaires offline.

> **Avertissement :** N'utiliser que si vous disposez du droit légal de scraper BDGest.
> Un délai de 2 secondes entre requêtes est imposé automatiquement.

### Dépendances Python

```bash
pip install requests beautifulsoup4 lxml
```

---

## Module 4 — `comic_shop`

**Vente en ligne et bibliothèque client.**

- Synchronisation album ↔ `product.template` (couverture, titre, ISBN → code-barres)
- Création de produits en masse depuis une série
- Webshop sur `/shop` (filtres genre / série / auteur)
- Bibliothèque client sur `/my/library` : collection, wishlist, état de lecture, notes
- Intégration POS : scan ISBN, transfert automatique vers la bibliothèque à la vente
- Import auto bibliothèque lors d'une commande en ligne confirmée

### Dépendances Odoo

```python
depends = ['comics_collections', 'comic_datasource', 'sale',
           'website', 'website_sale', 'point_of_sale', 'portal']
```

---

## Modules à venir (roadmap)

| Module | Description | Statut |
|---|---|---|
| `comic_ai` | Génération de synopsis et traduction via Claude / OpenAI | Planifié |

---

## Prérequis communs

- Odoo **19.0**
- Python **3.12+**
- PostgreSQL **16**

---

## Ordre d'installation recommandé

```
1. comics_collections       ← toujours en premier
2. comic_datasource          ← si enrichissement souhaité
```

---

## Structure d'un déploiement type

```
odoo/addons/
├── comics_collections/
└── comic_datasource/
```

Ajouter le chemin dans `odoo.conf` :

```ini
addons_path = /chemin/vers/odoo/addons,/chemin/vers/Comics-collections
```

---

## Développement

### Prérequis

```bash
# Installer pre-commit (une seule fois)
brew install pre-commit

# Activer les hooks dans le dépôt (une seule fois par clone)
pre-commit install
```

### Qualité de code

```bash
# Vérifier tous les fichiers (black + flake8 + pylint-odoo)
pre-commit run --all-files

# Vérifier uniquement les fichiers modifiés (mode normal sur git commit)
pre-commit run

# Mettre à jour les environnements des hooks
pre-commit autoupdate
```

### Formatage manuel

```bash
# Formater avec black (line-length 120, configuré dans pyproject.toml)
black --check .          # aperçu sans modifier
black .                  # applique les modifications
```

### Docker (développement local)

```bash
# Construire l'image
docker build -t odoo-comics .

# Lancer (adapter les variables d'environnement)
docker run -p 8069:8069 \
  -e DB_HOST=localhost \
  -e DB_USER=odoo \
  -e DB_PASSWORD=odoo \
  odoo-comics

# Suivre les logs
docker logs -f odoo-web

# Vider le cache Python après modification de .py
find . -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
```

### Tests

```bash
# Tests unitaires standalone (sans Odoo)
python -m pytest comics_collections/tests/test_import_wizard.py -v
python -m pytest comic_bdgest/tests/ -v
python -m pytest comic_datasource/tests/ -v

# Tests Odoo (nécessite une instance en cours)
./odoo-bin -d mydb --test-enable --stop-after-init \
  -i comics_collections,comic_datasource,comic_shop
```

### Workflow Git

```bash
# Branche de travail
git checkout -b feature/ma-fonctionnalite

# Commit (pre-commit vérifie automatiquement black + flake8 + pylint)
git add <fichiers>
git commit -m "feat: description concise"

# La branche principale du projet est 19.0
git push origin feature/ma-fonctionnalite
```
