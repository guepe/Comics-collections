# Comics Collections — Guide des modules Odoo 19

[![tests](https://github.com/Belspace/Comics-collections/actions/workflows/test.yml/badge.svg?branch=19.0)](https://github.com/Belspace/Comics-collections/actions/workflows/test.yml)
[![pre-commit](https://github.com/Belspace/Comics-collections/actions/workflows/pre-commit.yml/badge.svg?branch=19.0)](https://github.com/Belspace/Comics-collections/actions/workflows/pre-commit.yml)
[![License: LGPL-3](https://img.shields.io/badge/license-LGPL--3-blue.svg)](http://www.gnu.org/licenses/lgpl-3.0-standalone.html)

Ensemble de modules Odoo 19 pour gérer une collection de bandes dessinées, l'enrichir
depuis des sources en ligne et la vendre (webshop, caisse, bibliothèque client).
Auteur : Belspace — Licence : LGPL-3

---

## Vue d'ensemble

```
Comics-collections/
├── comics_collections/    # Module principal (requis)
├── comic_datasource/      # Enrichissement multi-sources (optionnel, recommandé)
└── comic_shop/            # Shop, caisse, bibliothèque client (optionnel)
```

Les modules se déposent dans le répertoire `addons` de votre instance Odoo.

---

## Module 1 — `comics_collections` *(requis)*

**Gestion complète de la collection de bandes dessinées.**

### Ce qu'il fait

- **Catalogue partagé** : séries, albums, éditions et ISBN visibles et modifiables par tous
  les utilisateurs BD (suppression : créateur ou gestionnaire)
- Séries et albums avec couvertures, synopsis, auteurs, éditeurs ; liste des albums groupée
  par série, tome `0` = hors-série / sans numéro
- **Bibliothèque personnelle** : collection, wishlist, état de lecture, note en étoiles,
  par utilisateur ; **tableau de bord** (albums, séries complètes / en cours, genres,
  lecture, meilleures séries, prêts en retard) — le module suffit seul pour une
  collection privée
- Valeur de la collection (prix d'achat, valeur estimée), export CSV et inventaire PDF
- Alertes nouveautés : notification Odoo quand un tome récent d'une série suivie arrive
- Séries suivies par utilisateur (alimente la détection des tomes manquants)
- Auteurs = contacts Odoo (`res.partner`) avec rôle ; fiches auteur et éditeur listant
  leurs séries et albums
- Prêts privés : dates par défaut, bouton *Retourner*, retards signalés et rappel quotidien
- Liens d'achat auto-générés (Club.be, Amazon.be, FNAC.be)
- Import CSV / TSV / XLS / XLSX via wizard (mapping, mise à jour ou ignorer, couverture par URL)
- Détection et fusion des doublons
- Deux groupes de sécurité : **Utilisateur** et **Gestionnaire** (catégorie *Bandes Dessinées*)

### Dépendances Odoo

```python
depends = ['base', 'mail', 'contacts']
```

### Dépendances Python

Aucune dépendance Python externe (`openpyxl` / `xlrd` pour l'import Excel sont fournis
avec les images Odoo officielles).

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

Recherche et fusionne les métadonnées depuis trois sources, dans cet ordre de priorité :

| Priorité | Source | Auth | Données |
|---|---|---|---|
| 1 | **Google Books API** | Clé API gratuite | Synopsis, couvertures HD, métadonnées |
| 2 | **Open Library API** | Aucune | Couvertures, auteurs, éditions |
| 3 | **BnF SRU API** | Aucune | BD francophones (dépôt légal officiel) |

- Ne remplit que les **champs vides** : une saisie utilisateur n'est jamais écrasée.
- Wizard de recherche par ISBN ou titre, avec comparaison des résultats et import.
- Mise à jour d'une série en un clic, détection des tomes manquants (ajout au catalogue
  ou à la wishlist).
- Deux crons optionnels (désactivés par défaut) ; coupe-circuit si le quota Google est atteint.

### Dépendances Odoo

```python
depends = ['comics_collections']
```

### Dépendances Python

```bash
pip install requests lxml xmltodict
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
| Open Library / BnF | Activables / désactivables (actives par défaut) |
| Ordre des sources | Paramètre système `comic.datasource_order` (liste JSON) |

---

## Module 3 — `comic_shop` *(optionnel)*

**Vente en ligne, caisse et bibliothèque client.**

- Synchronisation édition ↔ `product.template` (nom, couverture, ISBN → code-barres)
- Création de produits en masse depuis une série
- Pages webshop `/shop/series`, `/shop/auteurs`, `/shop/editeurs` (produits publiés uniquement)
- Bibliothèque client sur `/my/library` (la bibliothèque personnelle du cœur, ouverte
  aux clients) : collection, wishlist, état de lecture, notes en étoiles, tableau de
  bord `/my/library/dashboard`, ajout de BD achetées ailleurs (recherche ISBN / titre),
  wishlist partageable par lien secret
- Achats (commande confirmée, POS payé) ajoutés à la bibliothèque ; annulations et
  remboursements POS les retirent
- Modération des fiches créées depuis le portail : *Valider* ou *Refuser* (doublon / incorrect)

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
3. comic_shop                ← si vente / bibliothèque client (requiert les deux autres)
```

---

## Structure d'un déploiement type

```
odoo/addons/
├── comics_collections/
├── comic_datasource/
└── comic_shop/
```

Ajouter le chemin dans `odoo.conf` :

```ini
addons_path = /chemin/vers/odoo/addons,/chemin/vers/Comics-collections
```

> Après chaque mise à jour du code : `odoo -d <base> -u comics_collections,comic_datasource,comic_shop
> --stop-after-init`, puis redémarrer Odoo (sinon : colonnes manquantes / champs inconnus).

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

Tous les tests sont des tests Odoo (`TransactionCase` / `BaseCase` / `HttpCase`, avec
`@tagged`) ; ils ne se lancent pas avec pytest seul.

```bash
odoo -d mydb --stop-after-init \
  -u comics_collections,comic_datasource,comic_shop \
  --test-tags /comics_collections,/comic_datasource,/comic_shop
```

La CI GitHub (`tests`, `pre-commit`) exécute la même sélection à chaque push sur `19.0`.

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
