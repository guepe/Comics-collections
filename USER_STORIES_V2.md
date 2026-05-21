# USER STORIES V2 — Comic Shop & Bibliothèque Client

> Projet Odoo 19 — Extension commerciale et bibliothèque personnelle client
> Format : `US-XXX | En tant que... | Je veux... | Afin de...`
> **Contexte :** Extension des modules `comics_collections` et `comic_datasource` existants (v1).
> Ce fichier couvre la vision v2 : shop en ligne, caisse, et espace bibliothèque par client.

---

## 🗺️ Table des matières — Ce qui reste à faire

> Légende : ✅ Terminé · 🔄 Partiel · ⏳ À faire · 🔴 Priorité haute · 🟠 Moyenne · 🟡 Basse

### À faire — Priorité haute 🔴

| US     | Titre                                              | Dépend de       |
| ------ | -------------------------------------------------- | --------------- |
| US-035 | Scaffold `comic_shop` + extension `comic.album` sans retrait ✅ | —       |
| US-036 | Lien `comic.album` → `product.template` ✅          | US-035          |
| US-037 | Synchronisation album ↔ produit ✅                  | US-036          |
| US-037b | Smartbutton album BD + sync sur product.template ✅ | US-037         |
| US-037c | Création produits en masse depuis la fiche série ✅ | US-037         |
| US-039 | Modèle `comic.customer.album` ✅                   | US-035          |

### À faire — Priorité moyenne 🟠

| US     | Titre                                              | Dépend de       |
| ------ | -------------------------------------------------- | --------------- |
| US-040 | Fiche produit webshop enrichie BD ✅                | US-037          |
| US-041 | Navigation webshop par série / auteur / genre ✅    | US-040          |
| US-041b | Pages website auteurs et éditeurs ✅               | US-040, US-041  |
| US-042 | Intégration POS (caisse)                           | US-035          |
| US-043 | Espace bibliothèque client sur le portail ✅         | US-039          |
| US-044 | Ajout BD hors catalogue à la bibliothèque          | US-039          |
| US-045 | Import automatique depuis commandes client ✅       | US-039, US-035  |

### À faire — Priorité basse 🟡

| US     | Titre                                              | Dépend de       |
| ------ | -------------------------------------------------- | --------------- |
| US-046 | Rapport "BD non vendues les plus suivies"           | US-039          |
| US-047 | Rapport "Séries et auteurs à référencer"            | US-046          |
| US-048 | Notification CRM à la mise en catalogue             | US-047          |
| US-049 | Dashboard commerçant — vue marché                   | US-046, US-047  |

### EPIC 11 — Refactoring modèle canonique (Œuvre / Édition / ISBN)

| US     | Titre                                              | Dépend de       |
| ------ | -------------------------------------------------- | --------------- |
| US-050 | Analyse + décisions architecturales + déduplication | —              |
| US-051 | Implémentation ORM (comic.work, .edition, .isbn)   | US-050          |
| US-052 | Adaptation datasources et import                   | US-051          |
| US-053 | Vues back-office (list/form/search) ✅              | US-051          |
| US-054 | Adaptation comic_shop et bibliothèque client ✅    | US-051, US-050  |
| US-057 | Façade UX album/tome après refactor canonique ✅   | US-053, US-054  |
| US-055 | Tests unitaires et validation                      | US-051, US-054, US-057 |
| US-056 | Moteur de déduplication des œuvres                 | US-051, US-050  |

---

## 🏗️ ARCHITECTURE V2 — Vue d'ensemble

```
comic.serie ─────────────────────────────────────────────────────────────────
    └── comic.album (registre universel des BD)
            ├── product_tmpl_id (optionnel) ──→ product.template
            │                                       ├── webshop (website_sale)
            │                                       ├── POS (point_of_sale)
            │                                       └── stock / prix
            ├── ISBN / couverture / auteurs / synopsis
            └── datasource (Google Books, BnF, BDGest...)

comic.customer.album (bibliothèque personnelle par client)
    ├── partner_id       → res.partner
    ├── album_id         → comic.album (registre universel)
    ├── source           → acheté_ici / acheté_ailleurs / cadeau / wishlist
    ├── etat_lecture     → non_lu / en_cours / lu
    ├── dans_collection  → boolean
    ├── note             → float (0.0–5.0)
    └── commentaire      → Text
```

### Nouveaux modules

| Module              | Dépend de                                                    | Rôle                                         |
| ------------------- | ------------------------------------------------------------ | -------------------------------------------- |
| `comic_shop`        | `comics_collections`, `sale`, `website`, `website_sale`      | Lien produit, webshop, POS, bibliothèque web |

> **Principe d'indépendance :** `comics_collections` reste un module autonome et complet — utilisable seul pour gérer une collection personnelle. `comic_shop` ne retire rien, il ajoute par-dessus via `_inherit`. Les champs `dans_collection`, `dans_wishlist`, `etat_lecture`, `note` restent sur `comic.album` pour l'usage solo. `comic.customer.album` les duplique par client uniquement quand `comic_shop` est installé.

---

## 🔄 PHASE 7 — Catalogue universel & Lien Produit

> Refactoring du modèle `comic.album` existant pour le préparer à la double fonction : registre universel + produit vendable.
> **Règle fondamentale :** `comic.album` reste le registre de référence. `product.template` est le lien commerce — optionnel, pas obligatoire.

### EPIC 8 : Migration et extension du catalogue

---

**US-035 — Scaffold du module `comic_shop` + extension non-destructive de `comic.album`** ✅

```
En tant que développeur
Je veux créer comic_shop comme module additionnel indépendant
Afin que comics_collections reste utilisable seul et que comic_shop ajoute la couche commerce par-dessus

Principe d'architecture :
  comics_collections = module autonome et complet (collection personnelle, usage solo)
  comic_shop = module optionnel qui étend par _inherit, sans rien retirer
  Les champs dans_collection, dans_wishlist, etat_lecture, note restent sur comic.album.
  comic.customer.album coexiste — c'est une vue par client, pas un remplacement.

Critères d'acceptance :
- [x] __manifest__.py comic_shop correct (version 19.0.1.0.0, LGPL-3)
- [x] Dépendances déclarées : comics_collections, sale, website, website_sale,
        point_of_sale, portal
- [x] Structure standard Odoo : models/, views/, wizards/, data/, security/
- [x] ir.model.access.csv pour tous les nouveaux modèles de comic_shop
- [x] Groupe comic_shop.group_shop_manager (hérite de comic_manager)
- [x] Module installable sans erreur sur Odoo 19 avec ou sans comic_shop
- [x] comics_collections installé seul → comportement identique à la v1
- [x] Données de base : catégorie produit "Bandes Dessinées", liste de prix par défaut
- [ ] comic_shop désinstallable sans perte de données dans comics_collections
```

---

**US-036 — Lien `comic.album` → `product.template`** ✅

```
En tant que commerçant
Je veux qu'un album du catalogue puisse être lié à un produit Odoo
Afin de le vendre via le webshop et la caisse

Contexte de conception :
  Choix architectural : lien Many2one optionnel (pas d'_inherits).
  Raison : tous les albums ne sont pas forcément vendus (raretés, OP, BD
  que les clients ont ajouté à leur bibliothèque mais que le shop n'a pas).
  Un _inherits créerait un product.template pour chaque BD de l'univers,
  ce qui est trop lourd et incorrect sémantiquement.

Critères d'acceptance :
- [x] Champ product_tmpl_id (Many2one → product.template, optionnel) sur comic.album
- [x] Champ inverse comic_album_id (Many2one → comic.album) sur product.template
        via _inherit = 'product.template' dans comic_shop
- [x] Bouton "Créer le produit" sur la fiche album (visible si product_tmpl_id vide)
- [x] Bouton "Voir le produit" sur la fiche album (visible si product_tmpl_id renseigné)
- [x] Bouton "Dissocier le produit" (avec confirmation) pour retirer le lien
- [x] La suppression d'un comic.album ne supprime pas le product.template associé
- [x] Droits d'accès : seul le groupe comic_manager peut lier/délier les produits
```

---

**US-037 — Synchronisation album ↔ produit** ✅

```
En tant que commerçant
Je veux que les données communes soient synchronisées automatiquement
Afin d'éviter de saisir deux fois le titre, la couverture et l'ISBN

Critères d'acceptance :
- [x] À la création du produit depuis comic.album (_onchange / _create) :
        - product.name ← comic.album.name (+ série + tome)
        - product.image_1920 ← comic.album.image_couverture
        - product.barcode ← comic.album.isbn
        - product.description_sale ← comic.album.synopsis (texte brut)
        - product.categ_id ← catégorie "Bandes Dessinées" (créée si absente)
- [x] Bouton "Resynchroniser" sur la fiche album pour forcer la mise à jour
- [x] La synchronisation est unidirectionnelle : album → produit
        (le commerçant peut surcharger le produit sans que l'album soit modifié)
- [x] Si l'ISBN change sur l'album, le barcode produit est mis à jour automatiquement
- [x] Champ `sync_product` (Boolean) sur comic.album pour désactiver la synchro auto
        si le commerçant veut gérer le produit manuellement
- [x] Si l'image_couverture change, image_1920 du produit est mise à jour automatiquement
        (_SYNC_TRIGGER_FIELDS couvre : isbn, image_couverture, name, tome, serie_id, synopsis)
```

---

**US-037b — Smartbutton album BD et bouton sync sur product.template** ✅

```
En tant que commerçant
Je veux naviguer depuis la fiche produit vers l'album BD associé et pouvoir
resynchroniser les données depuis l'album
Afin de ne pas avoir à chercher l'album manuellement

Critères d'acceptance :
- [x] Smartbutton "Album BD" (icône fa-book) dans le button_box de product.template
        → ouvre la fiche comic.album correspondante (invisible si pas de lien)
- [x] Bouton "Sync depuis album" dans le header de product.template avec
        confirmation → force _sync_to_product() (restreint au groupe comic_manager)
- [x] Champ comic_album_id visible en lecture sur la fiche produit (invisible technique)
- [x] Fichiers : comic_shop/views/product_template_views.xml (nouveau),
        comic_shop/models/product_template.py (méthodes action_view_comic_album,
        action_sync_from_album)
```

---

**US-037c — Création de produits en masse depuis la fiche série** ✅

```
En tant que commerçant
Je veux pouvoir créer en un clic tous les produits manquants pour une série entière
Afin de publier rapidement plusieurs tomes sans les traiter un par un

Critères d'acceptance :
- [x] Stat button "X Produits liés" sur la fiche série (cliquable → liste filtrée)
- [x] Stat button "Y Albums à publier" visible si au moins un album avec ISBN sans produit
        → déclenche action_create_products_from_isbn()
- [x] action_create_products_from_isbn() : crée un product.template par album éligible
        (isbn renseigné et product_tmpl_id vide), appelle _sync_to_product() sur chacun
- [x] action_view_products() : ouvre la liste des produits liés à la série
- [x] Colonnes ISBN et "Produit lié" ajoutées à la liste inline des albums sur la fiche série
- [x] Fichiers : comic_shop/models/comic_serie.py (nouveau),
        comic_shop/views/comic_serie_views.xml (nouveau)
```

---

## 👤 PHASE 8 — Bibliothèque Client

> Chaque client inscrit sur le portail peut gérer sa collection personnelle de BD,
> qu'il les ait achetées dans le shop ou ailleurs.

### EPIC 9 : Modèle et portail bibliothèque

---

**US-039 — Modèle `comic.customer.album`** ✅

```
En tant que développeur
Je veux créer le modèle comic.customer.album
Afin de stocker la bibliothèque personnelle de chaque client

Critères d'acceptance :
- [x] Modèle comic.customer.album avec champs :
        partner_id (Many2one → res.partner, requis)
        album_id (Many2one → comic.album, requis)
        source (Selection : achete_ici / achete_ailleurs / cadeau / inconnu)
        etat_lecture (Selection : non_lu / en_cours / lu)
        dans_collection (Boolean, défaut True)
        dans_wishlist (Boolean, défaut False)
        note (Float 0.0–5.0)
        commentaire (Text)
        date_ajout (Date, défaut aujourd'hui)
        sale_order_line_id (Many2one → sale.order.line, optionnel)
- [x] Contrainte unique : (partner_id, album_id) — un client ne peut avoir
        qu'une seule entrée par album
- [x] Vue list et form (back-office, accès manager)
- [x] Droits d'accès :
        - comic_user : lecture/écriture sur ses propres enregistrements (record rule)
        - comic_manager : accès total
        - portal : lecture/écriture sur ses propres enregistrements (via portail)
- [x] Computed field has_product (Boolean) : True si album_id.product_tmpl_id renseigné
```

---

**US-040 — Fiche produit webshop enrichie BD** ✅

```
En tant que visiteur du webshop
Je veux voir les informations complètes d'une BD sur sa page produit
Afin de prendre une décision d'achat éclairée

Critères d'acceptance :
- [x] Template website_sale hérité pour les produits liés à un comic.album
- [x] Affichage sur la page produit : série, tome, auteurs avec rôles, éditeur,
        genre, date de parution, nombre de pages, ISBN
- [x] Synopsis complet (champ Html)
- [ ] Couverture haute résolution (zoom au clic) — couverture affichée via image standard produit
- [x] Badge "Tome X de la série Y" avec lien vers la page de la série
- [x] Section "Les autres tomes de la série" (carrousel des albums liés ayant un produit)
- [x] Si l'utilisateur est connecté et a cet album en bibliothèque :
        badge "Dans votre bibliothèque" visible sur la page produit
```

---

**US-041 — Navigation webshop par série / auteur / genre** ✅

```
En tant que visiteur du webshop
Je veux naviguer dans le catalogue de BD par série, auteur ou genre
Afin de trouver facilement les BD qui m'intéressent

Critères d'acceptance :
- [x] Page "/shop/series" listant toutes les séries disponibles (kanban couvertures)
- [x] Page "/shop/series/<id>" listant tous les tomes disponibles d'une série
- [x] Filtre "Série" dans la sidebar du webshop standard
- [x] Filtre "Auteur" dans la sidebar (scénariste ou dessinateur)
- [x] Filtre "Genre" dans la sidebar
- [x] Filtre "Type" (BD / Manga / Comics / One-shot)
- [x] Breadcrumb : Boutique > Série > Tome
```

---

**US-041b — Pages website auteurs et éditeurs** ✅

```
En tant que visiteur du webshop
Je veux accéder à des pages dédiées pour les auteurs et les éditeurs
Afin de découvrir leurs BD disponibles et de naviguer naturellement dans le catalogue

Critères d'acceptance :
- [x] Page "/shop/auteurs" listant les auteurs ayant au moins une BD vendue sur le webshop
- [x] Page "/shop/auteurs/<id>" affichant la fiche auteur et la liste de ses BD disponibles
        avec rôle(s), série, tome, couverture, prix et lien vers la fiche produit
- [x] Les noms d'auteurs affichés sur les pages produit pointent vers leur page dédiée
- [x] Page "/shop/editeurs" listant les éditeurs ayant au moins une série ou BD disponible
        sur le webshop, avec compteur de séries et d'albums
- [x] Page "/shop/editeurs/<id>" affichant la fiche éditeur et la liste des séries / BD
        disponibles chez cet éditeur, avec liens vers les séries et produits
- [x] Les noms d'éditeurs affichés sur les pages produit et série pointent vers leur page dédiée
- [x] Breadcrumbs cohérents :
        Boutique > Auteurs > Auteur > BD
        Boutique > Éditeurs > Éditeur > Série / BD
- [x] Les pages publiques n'affichent que les albums liés à un product.template (product_tmpl_id != False)
```

---

**US-042 — Intégration POS (caisse)** ⏳ 🟠

```
En tant que commerçant en magasin
Je veux scanner l'ISBN d'une BD et la retrouver directement à la caisse
Afin de gérer les ventes physiques efficacement

Critères d'acceptance :
- [ ] Les produits liés à un comic.album sont disponibles dans le POS
- [ ] Recherche par ISBN dans le POS (scan code-barres = champ barcode du produit)
- [ ] Affichage dans le POS : couverture miniature, titre, série, tome, prix
- [ ] À la validation de la vente POS, création automatique d'un comic.customer.album
        pour le client (si client identifié et source = achete_ici)
- [ ] Catégorie POS "Bandes Dessinées" créée automatiquement à l'installation
```

---

**US-043 — Espace bibliothèque client sur le portail** ✅

```
En tant que client connecté sur le portail
Je veux accéder à ma bibliothèque personnelle de BD
Afin de gérer ma collection et voir mes albums

Critères d'acceptance :
- [x] Menu "Ma Bibliothèque" dans le portail client (/my/library)
        entrée "Ma Bibliothèque BD" sur /my/home (pattern portal_client_category Odoo 19)
- [x] Vue liste et vue kanban (couvertures) de mes albums
- [x] Filtres : Tous / Dans ma collection / Wishlist / En cours de lecture
- [x] Tri : par série, par date d'ajout, par titre
- [x] Sur chaque carte : couverture, titre, série, tome, état de lecture, note (étoiles)
- [x] Clic sur un album → fiche détail avec mes données personnelles (note, commentaire)
- [x] Bouton "Mettre à jour" (état de lecture, note, commentaire, dans_collection, dans_wishlist)
- [x] Bouton "Supprimer de ma bibliothèque" (avec confirmation JS)
- [x] Compteurs en haut de page : X albums / Y séries / Z en cours de lecture
```

---

**US-044 — Ajout d'une BD hors catalogue à la bibliothèque** ⏳ 🟠

```
En tant que client connecté sur le portail
Je veux ajouter dans ma bibliothèque une BD que je n'ai pas achetée dans le shop
Afin de centraliser toute ma collection, pas seulement mes achats ici

Critères d'acceptance :
- [ ] Bouton "Ajouter une BD" sur la page /my/library
- [ ] Wizard en 2 étapes :
        Étape 1 : Recherche par ISBN (scan possible) ou par titre
            → appelle le ComicDataAggregator existant
            → liste les résultats avec couverture, titre, auteurs
        Étape 2 : Confirmation + sélection source (acheté_ailleurs / cadeau / inconnu)
                  + état de lecture + note
- [ ] Si la BD trouvée existe déjà dans comic.album (par ISBN) → réutilise l'enregistrement
- [ ] Si la BD n'existe pas dans comic.album → crée un nouveau comic.album
        sans product_tmpl_id (hors catalogue de vente)
- [ ] Message de confirmation : "X a été ajouté à votre bibliothèque"
- [ ] Gestion doublon : si le client a déjà cet album → message d'avertissement
        avec proposition de mise à jour de ses informations personnelles
```

---

**US-045 — Import automatique depuis les commandes client** ✅

```
En tant que client
Je veux que mes achats dans le shop soient automatiquement ajoutés à ma bibliothèque
Afin de ne pas avoir à ajouter manuellement ce que j'ai acheté ici

Critères d'acceptance :
- [x] À la confirmation d'une commande (état 'sale'), pour chaque ligne de commande
        dont le produit est lié à un comic.album :
        créer (ou mettre à jour) un comic.customer.album avec :
        source = achete_ici, dans_collection = True, sale_order_line_id = ligne
- [ ] Idem pour les ventes POS (US-042) — dépend de US-042 non implémentée
- [x] Si l'album est déjà dans la bibliothèque du client (acheté ailleurs),
        mettre à jour source → achete_ici sans écraser note ni commentaire
- [x] Email de confirmation d'achat inclut un lien "Voir dans ma bibliothèque"
        (via message_post sur la commande avec partner_ids → email envoyé au client)
- [x] Le client peut désactiver cette fonctionnalité dans ses préférences portail
        (toggle switch dans /my/library, champ comic_auto_library sur res.partner)
```

---

## 📊 PHASE 9 — Business Intelligence commerçant

> Le registre universel des BD, enrichi par les bibliothèques clients, devient une
> source d'intelligence marché : quelles séries référencer, quels auteurs promouvoir.

### EPIC 10 : Rapports et tableaux de bord commerçant

---

**US-046 — Rapport "BD non vendues les plus suivies"** ⏳ 🟡

```
En tant que commerçant
Je veux voir quelles BD présentes dans les bibliothèques clients ne sont pas dans mon catalogue
Afin d'identifier les titres à référencer en priorité

Critères d'acceptance :
- [ ] Vue rapport accessible depuis le menu back-office "Rapports > Bibliothèques clients"
- [ ] Table : série / nb clients distincts / nb albums concernés / source principale
        Filtré sur : album_id.product_tmpl_id = False (non vendu par le shop)
        Groupé par : comic.serie, trié par nb clients DESC
- [ ] Filtre par période (date_ajout des customer.album)
- [ ] Filtre par source (achete_ailleurs uniquement, ou tous)
- [ ] Export CSV du rapport
- [ ] Indicateur visuel : vert si > 5 clients, orange si 2–5, gris si 1
```

---

**US-047 — Rapport "Séries et auteurs à référencer"** ⏳ 🟡

```
En tant que commerçant
Je veux voir les auteurs les plus suivis par mes clients pour des BD hors catalogue
Afin de prendre des décisions d'achat basées sur la demande réelle

Critères d'acceptance :
- [ ] Rapport "Top auteurs hors catalogue" :
        Groupé par auteur (comic.album.auteur.line.partner_id)
        Filtré sur : album.product_tmpl_id = False
        Colonnes : auteur / rôle principal / nb clients / nb séries concernées
- [ ] Rapport "Top séries hors catalogue" (complément de US-046 avec vue auteurs)
- [ ] Vue pivot (tableau croisé) : auteurs × genres
- [ ] Graphique barre "Top 10 séries à référencer"
- [ ] Graphique camembert "Répartition par genre des BD hors catalogue"
```

---

**US-048 — Notification CRM à la mise en catalogue** ⏳ 🟡

```
En tant que commerçant
Je veux notifier automatiquement les clients intéressés quand je référence une nouvelle série
Afin de générer des ventes immédiates sur les BD déjà désirées

Critères d'acceptance :
- [ ] Lors de la liaison comic.album ↔ product.template (US-036) :
        si des clients ont cet album en bibliothèque (source = achete_ailleurs / inconnu)
        → afficher un popup : "X clients ont déjà cet album dans leur bibliothèque.
        Voulez-vous les notifier ?"
- [ ] Si confirmation : envoi d'un email template "Bonne nouvelle — [Titre] est disponible !"
        avec lien vers la page produit du webshop
- [ ] Wizard de prévisualisation avant envoi (liste des clients concernés)
- [ ] Log des notifications envoyées (date, nb destinataires) dans le chatter du comic.album
- [ ] Option : créer une opportunité CRM par client notifié (configurable)
```

---

**US-049 — Dashboard commerçant — vue marché** ⏳ 🟡

```
En tant que commerçant
Je veux un tableau de bord synthétique sur la demande marché de mes clients
Afin d'avoir une vue d'ensemble pour mes décisions d'achat

Critères d'acceptance :
- [ ] Accessible depuis le menu "Rapports > Vue Marché"
- [ ] KPI en haut de page :
        Nb clients avec une bibliothèque active
        Nb albums hors catalogue dans les bibliothèques
        Nb séries hors catalogue distinctes
        Taux de couverture : % des albums des bibliothèques clients vendus par le shop
- [ ] Graphique : Top 10 séries hors catalogue (barres horizontales)
- [ ] Graphique : Top 10 auteurs hors catalogue
- [ ] Graphique : Évolution du nb d'ajouts bibliothèque par semaine (tendance)
- [ ] Tableau : Séries avec le plus fort ratio "clients intéressés / tomes vendus"
        (= séries populaires dont le client n'achète pas les suites ici)
- [ ] Filtre par période et par genre
```

---

## 🏗️ EPIC 11 — Refactoring modèle canonique : Œuvre / Édition / ISBN

> **Motivation :** Un ISBN identifie une édition commerciale précise, pas l'œuvre elle-même.
> La même BD peut avoir des dizaines d'ISBN selon le pays, la langue, l'éditeur, le format ou
> la réédition. Utiliser l'ISBN comme identifiant principal de `comic.album` crée des doublons
> et rend impossible de relier les éditions d'une même œuvre.
>
> **Contexte :** Projet neuf — aucune donnée existante à préserver. Le refactoring est un
> remplacement propre et complet : `comic.album` et `comic.album.auteur.line` sont supprimés
> et remplacés par `comic.work` + `comic.work.auteur.line` + `comic.edition` + `comic.isbn`.
> Toutes les relations (prêts, bibliothèque client, shop, datasource, portail, webshop) doivent
> être adaptées dès l'implémentation initiale — aucune couche de compatibilité temporaire.

### Nouveau schéma cible

```
comic.serie (inchangé comme parent)
  └── comic.work  (œuvre canonique — un par tome)
        ├── serie_id          → comic.serie
        ├── tome              → Integer
        ├── titre_canonique   → Char
        ├── slug              → Char (unique, indexé)
        ├── auteur_line_ids   → One2many → comic.work.auteur.line
        ├── refs: wikidata_id, openlibrary_id, bedetheque_id, comicvine_id
        └── edition_ids       → One2many → comic.edition

comic.work.auteur.line  (remplace comic.album.auteur.line)
  ├── work_id    → comic.work (Many2one, required)
  ├── partner_id → res.partner (Many2one, required)
  └── role       → Selection (scenariste / dessinateur / coloriste / encreur / traducteur / autre)

comic.edition  (édition commerciale — un produit = une édition)
  ├── work_id          → comic.work (Many2one, required)
  ├── titre_affiche    → Char
  ├── langue           → Selection (fr / nl / en / de / es / autre)
  ├── pays_id          → Many2one → res.country
  ├── editeur_id       → Many2one → comic.editeur
  ├── date_parution    → Date
  ├── format           → Selection (broche / cartonne / integrale / collector / numerique / autre)
  ├── nb_pages         → Integer
  ├── image_couverture → Image
  ├── synopsis         → Html
  ├── isbn_ids         → One2many → comic.isbn
  └── notes_edition    → Text

comic.isbn
  ├── edition_id → comic.edition (Many2one, required)
  ├── isbn_13    → Char (unique, indexé, normalisé)
  ├── isbn_10    → Char (optionnel)
  └── [contrainte unicité isbn_13 + validation checksum EAN-13]
```

### Modèles supprimés

| Supprimé | Remplacé par |
|---|---|
| `comic.album` | `comic.work` (métadonnées œuvre) + `comic.edition` (données édition physique) |
| `comic.album.auteur.line` | `comic.work.auteur.line` |

### Interactions avec les autres modèles

Toutes les relations vers `comic.album` doivent être mises à jour lors de l'implémentation.

| Modèle | Relation actuelle | Nouvelle relation | Justification |
|---|---|---|---|
| `comic.pret` | `album_id → comic.album` | `edition_id → comic.edition` | On prête un exemplaire physique = édition précise |
| `comic.customer.album` | `album_id → comic.album` | `edition_id → comic.edition` + `work_id` (computed) | La bibliothèque référence l'édition possédée ; le groupement par œuvre se fait via `work_id` |
| `product.template` (comic_shop) | `comic_album_id → comic.album` | `comic_edition_id → comic.edition` | Option A — une édition = un produit (FR vs NL, collector vs standard) |
| `sale.order.line` | via product → album | via product → edition | Lien indirect, logique inchangée |
| `ComicDataAggregator` | crée `comic.album` | crée `comic.work` + `comic.edition` + `comic.isbn` | Adapté dans US-052 |
| Import wizard (CSV/XLS/XLSX) | importe vers `comic.album` | importe vers `comic.work` + `comic.edition` + `comic.isbn` | Adapté dans US-052 |
| Portal `/my/library` | liste `customer.album.album_id` | liste `customer.album.edition_id` + regroupement par `work_id` | Groupement par œuvre possible en vue liste |
| Webshop `/shop` | `product_tmpl_id` sur `comic.album` | `comic_edition_id` sur `product.template` | Logique inchangée, modèle pivot changé |
| Webshop `/shop/series/<id>` | albums d'une série | works d'une série + édition de référence par work | Affiche la première édition `fr` ou la plus récente |
| Cron enrichissement (`comic_cron_data.xml`) | enrichit `comic.album` | enrichit `comic.edition` | Adapté lors de US-052 |

---

**US-050 — Analyse + décisions architecturales + stratégie de déduplication** ✅

```
En tant que développeur
Je veux inventorier toutes les références à comic.album, valider les décisions d'architecture
et concevoir la stratégie anti-doublons
Afin de ne rien manquer lors du remplacement et de garantir la qualité des données dès le départ

── A. INVENTAIRE ET DÉCISIONS ARCHITECTURALES ────────────────────────────────

- [x] Inventaire exhaustif de tous les fichiers référençant comic.album et comic.album.auteur.line
      (models, views, controllers, wizards, data XML, security CSV, templates Qweb)
      → Voir inventaire complet ci-dessous (section "Inventaire US-050")
- [x] Décision documentée : Option A validée — product.template lié à comic.edition
        Raison : une édition = un SKU distinct (langue, format, éditeur différents = produits différents)
- [x] Décision documentée : comic.pret → edition_id
        Raison : on prête un exemplaire physique d'une édition spécifique
- [x] Décision documentée : comic.customer.album → edition_id + work_id computed
        Raison : on possède une édition, mais les vues "par œuvre" nécessitent work_id
- [x] Décision documentée : comic.work.auteur.line remplace comic.album.auteur.line
        (authorship appartient à l'œuvre, pas à une édition commerciale)
- [x] Stratégie d'affichage webshop validée : série → works → édition de référence (fr/date la plus récente)
- [x] Choix de slug validé : `{serie.slug}-t{tome:02d}` ex. `thorgal-t05`
- [x] ERD final mis à jour dans CLAUDE.md (section "ERD final — Architecture canonique")

── B. ANALYSE DES RISQUES DE DOUBLONS ────────────────────────────────────────

Problèmes identifiés :
  1. Même tome, ISBN différents selon l'édition/pays/format (déjà géré par comic.work + comic.edition)
  2. Même tome, titre légèrement différent selon la source
       ex. "Landes Perdues" ≠ "Les Landes perdues" ≠ "Les landes perdues (Les)"
       → risque de créer 2 comic.work distincts pour le même tome
  3. Même série, nom de série variant selon la source
       ex. "Thorgal" vs "Thorgal (Les aventures de)"
  4. Albums incomplets dans les datasources (champs manquants : tome absent,
       ISBN absent, titre tronqué) → entrées orphelines ou impossibles à rattacher

- [x] Recenser les cas de variation observés dans les sources (Google Books, Open Library,
      BnF, BDGest) et documenter les patterns les plus fréquents (articles définis,
      casse, accents, suffixes entre parenthèses, abréviations)
      → Patterns recensés : articles en tête (le/la/les/l'/de/het/een/the/a/an),
        suffixes catalogue (Les)/(De)/(The), casse, accents, tirets
- [x] Définir les règles de normalisation de titre retenues :
      - Passage en minuscules + suppression des accents (unicodedata, catégorie Mn)
      - Suppression des articles définis en tête de chaîne :
          FR : le / la / les / l'
          NL : de / het / een
          EN : the / a / an
      - Suppression des suffixes "(Les)" / "(De)" / "(The)" en fin de chaîne (variante catalogue)
      - Suppression des caractères de ponctuation non significatifs (tirets, points, virgules)
      - Normalisation des espaces multiples
      Exemple : "Les Landes perdues" → "landes perdues"
                "Landes perdues (Les)" → "landes perdues"  → identiques ✓
- [x] Définir les règles de normalisation de nom de série (mêmes règles)
- [x] Choisir et documenter l'algorithme de similarité pour la détection de candidats :
      - Ratio SequenceMatcher (stdlib Python, ratio ≥ 0.85 recommandé)
      - ou distance Levenshtein ≤ 3 (bibliothèque python-Levenshtein ou rapidfuzz)
      - Décision : ratio SequenceMatcher (pas de dépendance externe) avec seuil 0.85
        → "conflit certain" si même (serie_id, tome) + titre normalisé identique
        → "doublon probable" si même serie_id + ratio ≥ 0.85 + tome identique
        → "doublon possible" si ratio ≥ 0.85 sur titre ET série normalisés

── C. STRATÉGIE DE RÉSOLUTION DES DOUBLONS ───────────────────────────────────

- [x] Décision documentée sur le workflow de détection (applicable dans US-056) :
      Lors de la création d'un comic.work (import datasource OU saisie manuelle) :
        1. Chercher d'abord par (serie_id, tome) → conflit certain → bloquer avec message
        2. Chercher par titre normalisé + série normalisée + tome → doublon probable
           → afficher une popup "Ce tome ressemble à [X]. Fusionner ou créer séparément ?"
        3. Si aucun candidat → création normale
- [x] Décision documentée sur le champ d'index anti-doublons :
      comic.work.titre_normalise (Char, compute, store=True, index=True)
      comic.serie.name_normalise  (Char, compute, store=True, index=True)
      Ces champs sont calculés automatiquement à chaque write, non modifiables par l'utilisateur
- [x] Décision UX documentée :
      Le modèle canonique technique est `comic.work` / `comic.edition` / `comic.isbn`,
      mais les interfaces courantes gardent le vocabulaire utilisateur "album / tome".
      Les vues "Œuvres" et "Éditions" sont réservées au référentiel avancé.
      → Détails opérationnels dans US-057.
- [x] Cas particulier "album incomplet" :
      Un comic.work peut exister sans comic.edition (tome connu mais aucune édition disponible)
      Un comic.edition peut exister sans comic.isbn (édition connue mais ISBN non trouvé)
      → les deux cas sont valides et ne doivent pas être bloqués
      → vue back-office : filtre "Œuvres sans édition" et "Éditions sans ISBN" pour revue manuelle
- [x] Note : la fiabilisation des sources de données (confiance par source, réconciliation
      automatique de conflits entre sources) est hors périmètre US-050 — à traiter dans
      une EPIC dédiée ultérieure

── INVENTAIRE US-050 — Fichiers référençant comic.album ──────────────────────

Module comics_collections (module principal) :
  models/comic_album.py            — définition _name = 'comic.album'
  models/comic_auteur_line.py      — définition _name = 'comic.album.auteur.line'
  models/comic_serie.py            — album_ids One2many, first_album_cover_id computed
  models/res_partner.py            — auteur_line_ids One2many
  views/comic_album_views.xml      — list, form, kanban, search, wishlist
  views/comic_serie_views.xml      — URL couverture /web/image/comic.album/
  views/comic_menu.xml             — menu Albums
  security/comic_security.xml      — record rules comic.album
  security/ir.model.access.csv     — droits comic.album + comic.album.auteur.line
  wizards/comic_import_wizard.py   — création comic.album
  data/comic_cron_data.xml         — cron référence model_comic_album
  demo/comic_demo.xml              — données démo comic.album + comic.album.auteur.line
  tests/test_computed_fields.py    — tests unitaires champs computed

Module comic_datasource :
  models/comic_album.py                      — _inherit = 'comic.album'
  models/__init__.py                         — import comic_album
  views/comic_datasource_album_inherit_views.xml — hérite vue form comic.album
  views/comic_datasource_wizard_views.xml    — binding_model comic.album
  wizards/comic_datasource_search_wizard.py  — crée comic.album + comic.album.auteur.line
  wizards/comic_serie_missing_wizard.py      — crée comic.album
  data/comic_serie_cron.xml                  — cron référence model_comic_album

Module comic_bdgest :
  models/comic_album.py                  — _inherit = 'comic.album'
  models/__init__.py                     — import comic_album
  views/comic_album_inherit_views.xml    — hérite form + server action
  wizards/comic_bdgest_enrich_wizard.py  — album_id Many2one comic.album
  __manifest__.py                        — liste comic_album_inherit_views.xml

Module comic_shop :
  models/comic_album.py            — _inherit = 'comic.album' (ajoute product_tmpl_id)
  models/comic_customer_album.py   — album_id Many2one → comic.album
  models/comic_sale_order.py       — uses comic.album
  models/comic_serie.py            — création produits depuis albums
  models/product_template.py      — comic_album_id Many2one → comic.album
  models/__init__.py               — import comic_album
  controllers/main.py              — recherches comic.album + comic.album.auteur.line
  views/comic_album_views.xml      — hérite form comic.album
  views/portal_library_templates.xml    — URL /web/image/comic.album/.../image_couverture
  views/product_template_views.xml      — smart button comic_album_id
  views/website_sale_templates.xml      — variable comic_album (toutes les infos produit)
  __manifest__.py                       — liste comic_album_views.xml

Outils externes (tools/) :
  tools/import_demo.py       — appels RPC comic.album + comic.album.auteur.line
  tools/load_demo_series.py  — appels RPC comic.album + comic.album.auteur.line
```

---

**US-051 — Implémentation ORM + remplacement de comic.album** ✅

```
En tant que développeur
Je veux créer les nouveaux modèles et supprimer comic.album et comic.album.auteur.line
Afin d'avoir un schéma propre et cohérent dès le départ

Critères d'acceptance :
- [x] `comic.work` créé dans models/comic_work.py :
      - hérite mail.thread + mail.activity.mixin
      - _description, _rec_name = 'titre_canonique'
      - display_name = "{serie} T{tome:02d} — {titre_canonique}"
      - models.Constraint unicité (serie_id, tome) — pas _sql_constraints (déprécié Odoo 19)
      - slug : Char unique, indexé ; auto-généré à la création si vide
      - champs refs : wikidata_id, openlibrary_id, bedetheque_id, comicvine_id (Char, optional)
      - edition_ids, auteur_line_ids en One2many
- [x] `comic.work.auteur.line` créé (même fichier models/comic_work.py) :
      - work_id, partner_id, role — même structure que l'ancien comic.album.auteur.line
- [x] `comic.edition` créé dans models/comic_edition.py :
      - hérite mail.thread + mail.activity.mixin
      - display_name = "{work.display_name} ({langue} — {editeur_id.name}, {date_parution.year})"
      - format : Selection broche/cartonne/integrale/collector/numerique/autre
      - isbn_ids One2many → comic.isbn
- [x] `comic.isbn` créé dans models/comic_isbn.py :
      - @api.constrains('isbn_13') : validation checksum EAN-13 (algorithme ×1/×3)
      - @api.constrains('isbn_10') : validation ISBN-10 si renseigné
      - normalisation automatique : suppression tirets et espaces avant stockage (create/write)
      - models.Constraint unicité isbn_13
- [x] `comic.pret` créé dans models/comic_pret.py avec edition_id (Many2one → comic.edition)
- [x] `comic.album` et `comic.album.auteur.line` supprimés (fichiers Python et vues XML)
- [x] `ir.model.access.csv` mis à jour : 6 nouveaux modèles (work, work.auteur.line, edition, isbn, pret + wizard), 2 anciens retirés
- [x] `__init__.py` (module et models/) mis à jour
- [x] Module installable sans erreur sur une base vierge
      Note : comic_datasource, comic_bdgest et comic_shop référencent encore comic.album
      → ces modules seront adaptés dans US-052 et US-054
```

---

**US-052 — Adaptation des datasources et de l'import** ✅

```
En tant que développeur
Je veux que le ComicDataAggregator, les wizards datasource et l'import CSV/XLSX
créent les bons modèles dès le départ
Afin que toute entrée de données produise des comic.work + comic.edition + comic.isbn

Critères d'acceptance :
- [x] `ComicDataAggregator.search()` adapté :
      - au lieu de créer/retourner un comic.album, retourne un dict normalisé inchangé
        (le dict normalisé existant est déjà compatible — seul le mapping ORM change)
- [x] `action_import_selected()` du wizard datasource :
      - cherche d'abord comic.isbn existant → retrouve edition + work sans doublon
      - sinon : cherche comic.work (serie_id, tome) existant → crée une nouvelle edition liée
      - sinon : crée comic.work + comic.edition + comic.isbn en cascade
      - migre les auteurs vers comic.work.auteur.line
- [x] Import wizard (CSV/XLS/XLSX) adapté :
      - colonnes cibles : serie_name, tome, titre_canonique, langue, editeur, date_parution,
        nb_pages, isbn, format, scenariste, dessinateur, coloriste, genre
      - même logique de déduplication (isbn → edition → work) que le wizard datasource
- [x] Cron `comic_cron_data.xml` (enrichissement quotidien) adapté :
      - itère sur comic.edition au lieu de comic.album
      - met à jour edition.synopsis, edition.image_couverture, etc.
- [x] Cron `comic_serie_cron.xml` (suivi séries) : inchangé — itère déjà sur comic.serie
```

---

**US-053 — Vues back-office** ✅

```
En tant qu'administrateur
Je veux des vues list/form/search pour comic.work, comic.edition et comic.isbn
Afin de gérer le nouveau schéma depuis l'interface Odoo

Critères d'acceptance :
- [x] views/comic_work_views.xml :
      - List : titre canonique, série, tome, nb éditions (computed), nb auteurs (computed)
      - Form : onglet "Œuvre" (titre_canonique, serie_id, tome, slug, refs externes)
               onglet "Auteurs" (auteur_line_ids avec partner_id et role)
               onglet "Éditions" (edition_ids inline list : langue, éditeur, date, format, nb ISBN)
      - Search : par titre, série, tome, auteur, slug, wikidata_id
      - Kanban (optionnel) : image de la première édition fr, titre, série, tome
- [x] views/comic_edition_views.xml :
      - List : titre affiché, langue, éditeur, date, format, nb ISBN
      - Form : champs édition + sous-liste isbn_ids inline (isbn_13, isbn_10)
               smartbutton "Produit lié" si product_tmpl_id renseigné (comic_shop uniquement)
- [x] Menu mis à jour :
      "Ma Collection > Œuvres" + "Ma Collection > Éditions" + "Ma Collection > Prêts"
- [x] Vue comic.serie : smartbutton/compteur "nb_works" (computed via work_ids)
- [x] Vue comic.pret : affiche edition_id avec lien vers l'œuvre parente
- [ ] Recherche globale par ISBN : remonte comic.isbn → comic.edition → comic.work
- [x] Vues comic.album et comic.album.auteur.line supprimées (plus de modèle)
```

---

**US-054 — Adaptation comic_shop** ✅

```
En tant que développeur
Je veux adapter comic_shop pour utiliser comic.edition comme pivot du lien produit
Afin que shop, bibliothèque client et portail fonctionnent correctement avec le nouveau schéma

Critères d'acceptance :
- [x] product.template (comic_shop/_inherit) :
      - champ comic_edition_id (Many2one → comic.edition)
      - champ computed comic_work_id (→ comic_edition_id.work_id, store=True)
      - smartbutton "Édition BD" → fiche comic.edition
      - action_sync_from_edition()
- [x] comic.edition (comic_shop/_inherit) :
      - champ product_tmpl_id (Many2one → product.template, optionnel)
      - boutons "Créer le produit" / "Voir le produit" / "Dissocier" / "Resync"
      - _sync_to_product() : sync name, image_couverture, isbn → barcode, synopsis → description_sale
      - _SYNC_TRIGGER_FIELDS : isbn_ids, image_couverture, synopsis, editeur_id, work_id
- [x] comic.serie (comic_shop/_inherit) :
      - action_create_products_from_isbn()
      - smartbutton "Produits liés" (nb_albums_with_product)
      - smartbutton "Éditions à publier" (nb_albums_isbn_sans_produit)
- [x] comic.customer.album :
      - edition_id (Many2one → comic.edition, required)
      - work_id (compute → edition_id.work_id, store=True, index=True)
      - contrainte UNIQUE(partner_id, edition_id)
- [x] comic_sale_order.py : retrouve l'edition via la ligne de commande → crée customer.album
- [x] portal.py (/my/library) : filtre par partner_id, tri par série/titre/date
- [x] Webshop product page : lit les infos via comic_edition.work_id (série, tome, auteurs)
- [x] Webshop /shop/series/<id> : liste editions par work_id, filtrées product_tmpl_id
```

---

**US-057 — Façade UX album/tome après refactor canonique** ✅

```
En tant qu'utilisateur / commerçant
Je veux continuer à manipuler des séries, tomes et albums dans l'interface
Afin que le refactor comic.work / comic.edition / comic.isbn reste invisible dans les parcours courants

Critères d'acceptance :
- [x] Pages webshop corrigées :
      - /shop/series/<id> : template lit edition.work_id.* (contrôleur passe `editions`)
      - /shop/auteurs/<id> : template lit edition.work_id.serie_id / .tome / .titre_canonique
- [x] Portail client :
      - placeholder "Mes notes sur cet album…"
      - confirm "Supprimer cet album de votre bibliothèque ?"
- [x] Webshop public :
      - "Informations sur l'édition" → "Informations BD"
- [x] Back-office collection :
      - menu "Ma Collection" : Séries + Albums/Tomes + Prêts + Import
      - Œuvres et Éditions dans Configuration > Référentiel avancé (managers uniquement)
      - fiche Série : onglet "Albums / Tomes"
      - action comic.work titrée "Albums / Tomes"
- [x] Fiche produit Odoo :
      - smartbutton "Album BD" (champ technique comic_edition_id inchangé)
      - bouton "Sync depuis album"
- [x] comic.customer.album.work_id implémenté (US-054)
- [x] Règle 14 ajoutée dans CLAUDE.md : vocabulaire technique vs utilisateur
```

---

**US-055 — Tests unitaires et validation** ⏳ 🟡

```
En tant que développeur
Je veux des tests couvrant les nouveaux modèles et leurs interactions
Afin de garantir la robustesse du schéma refactorisé

Critères d'acceptance :
- [ ] tests/test_comic_isbn.py :
      - Validation EAN-13 : cas valide, checksum incorrect, mauvaise longueur, tirets acceptés
      - Validation ISBN-10 si renseigné
      - Normalisation : "978-2-205-07567-7" → "9782205075677"
      - Contrainte unicité : deux comic.isbn avec le même isbn_13 → UserError
- [ ] tests/test_comic_work.py :
      - Contrainte unique (serie_id, tome)
      - Génération slug : serie "Thorgal" tome 5 → "thorgal-t05", conflit → "thorgal-t05-2"
      - display_name : format "{serie} T05 — {titre}" correct
      - auteur_line_ids : ajout/suppression d'un auteur avec rôle
- [ ] tests/test_comic_edition.py :
      - Création edition liée à un work : vérifier display_name complet
      - Plusieurs editions pour un même work (fr + nl + collector) : toutes accessibles via work.edition_ids
      - edition sans isbn : valide (champ optionnel)
      - Lien edition → product.template (comic_shop) : _sync_to_product() copie les bons champs
- [ ] tests/test_comic_customer_album.py :
      - Contrainte unique (partner_id, edition_id)
      - work_id computed = edition_id.work_id
      - Import automatique depuis commande : customer.album créé avec source='achete_ici'
- [ ] Tous les tests passent : `./odoo-bin -d test -i comics_collections,comic_shop --test-tags refactor`
```

---

---

**US-056 — Moteur de déduplication des œuvres** ⏳ 🟠

```
En tant que développeur / administrateur
Je veux un mécanisme automatique de détection et de résolution des doublons de comic.work
Afin d'éviter que les imports et saisies manuelles créent des entrées dupliquées

Contexte : stratégie définie en US-050 section B & C. À implémenter après US-051
(les champs titre_normalise et name_normalise nécessitent les nouveaux modèles).

Critères d'acceptance :
- [ ] Champ compute + store sur comic.work :
      titre_normalise (Char) : lowercase + strip accents + suppression articles + strip ponctuation
      Algorithme de normalisation centralisé dans un helper comics_collections/utils/normalize.py
- [ ] Champ compute + store sur comic.serie :
      name_normalise (Char) : même algorithme
- [ ] Méthode comic.work._find_duplicate_candidates(serie_id, tome, titre) :
      1. Retourne une liste de comic.work candidats avec leur score de similarité
      2. Conflit certain   : même (serie_id, tome) → score = 1.0
      3. Doublon probable  : même serie_id + ratio SequenceMatcher(titre_normalise) ≥ 0.85 + même tome
      4. Doublon possible  : ratio SequenceMatcher sur titre ET série normalisés ≥ 0.85
- [ ] Contrainte ORM renforcée :
      @api.constrains déclenche _find_duplicate_candidates → UserError si conflit certain
      (la contrainte models.Constraint sur (serie_id, tome) couvre le cas exact ; l'IA
      de similarité couvre les variations de titre)
- [ ] Popup de confirmation lors de la création manuelle d'un comic.work :
      Si doublon probable détecté → wizard rapide "Ce tome ressemble à [X — titre — éditeur].
      Créer quand même / Fusionner / Voir l'existant"
- [ ] Wizard back-office "Revue des doublons" (menu Configuration > Doublons potentiels) :
      - Liste toutes les paires (work_a, work_b) avec ratio ≥ 0.85 non encore résolues
      - Colonnes : titre A, titre B, série, tome, nb éditions chacun, score
      - Bouton "Fusionner A → B" : transfère les editions et customer.album de A vers B,
        puis archive A
      - Bouton "Pas un doublon" : marque la paire comme ignorée (champ Many2many blacklist)
- [ ] Vues de diagnostic (filtre dans les vues list existantes) :
      - comic.work : filtre "Sans édition"
      - comic.edition : filtre "Sans ISBN"
      - comic.edition : filtre "Sans image couverture"
- [ ] Méthode de fusion sécurisée comic.work._merge_into(target_work) :
      - Transfère edition_ids vers target_work
      - Transfère les comic.customer.album (via edition_id → work_id)
      - Transfère les auteur_line_ids (dédupliqués)
      - Archive self (active=False)
      - Log dans le chatter de target_work
- [ ] Tests :
      - normalize("Les Landes perdues") == normalize("Landes perdues (Les)") == "landes perdues"
      - normalize("Thorgal") == normalize("THORGAL") == "thorgal"
      - _find_duplicate_candidates retourne le bon score pour cas certain / probable / possible
      - Fusion : vérifier que les editions et customer.album sont bien sur target_work après merge
```

---

### Dépendances EPIC 11

```
US-050 (analyse + décisions + stratégie dédup) → US-051 (nouveaux modèles ORM + suppression comic.album)
US-051 → US-052 (adaptation datasources + import)
US-051 → US-053 (vues back-office)
US-051 + US-052 → US-054 (adaptation comic_shop)
US-053 + US-054 → US-057 (façade UX album/tome)
US-051 + US-054 + US-057 → US-055 (tests)
US-051 + US-050 → US-056 (moteur déduplication) — peut être fait en parallèle de US-053/054
```

> ⚠️ **Point d'attention :** US-054 est un breaking change complet sur `comic_shop` (tous les
> champs `comic_album_id` deviennent `comic_edition_id`). Traiter US-051 et US-054 dans la même
> session pour éviter un état intermédiaire incohérent. L'option A (edition = pivot produit) est
> la décision retenue — pas de choix à faire en cours d'implémentation.
>
> 📌 **Hors périmètre EPIC 11 (déféré) :** Fiabilisation des sources de données — confiance par
> source, réconciliation automatique des conflits entre Google Books / BnF / BDGest, scoring de
> qualité par champ. À traiter dans une EPIC dédiée après US-056.

---

## 📋 Récapitulatif V2

| Phase    | Epic                           | US               | Priorité        |
| -------- | ------------------------------ | ---------------- | --------------- |
| Phase 7  | Catalogue & Lien Produit       | US-035 à US-038  | 🔴 Must Have    |
| Phase 8  | Bibliothèque Client            | US-039 à US-045  | 🔴 / 🟠 Must    |
| Phase 9  | Business Intelligence          | US-046 à US-049  | 🟡 Nice to Have |
| Phase 10 | Refactoring modèle canonique   | US-050 à US-057  | 🔴 Structurant  |

### Dépendances critiques

```
US-035 (scaffold comic_shop) → US-036 (lien produit) → US-037 (synchro) → US-040 (webshop)
US-040 → US-041 (navigation webshop) → US-041b (pages auteurs et éditeurs)
US-035 → US-039 (customer.album) → US-043 (portail) → US-044 (ajout BD)
US-035 → US-042 (POS), US-045 (import commandes)
US-039 → US-046 → US-047 → US-048

US-050 (analyse) → US-051 (ORM) → US-052 (migration) → US-054 (comic_shop)
US-051 → US-053 (vues) → US-057 (façade UX) → US-055 (tests)
⚠️  US-050 doit décider Option A/B avant US-051 (voir EPIC 11)
```

---

## 🚀 Pour travailler avec Claude dans VS Code

```
Je travaille sur le projet Odoo 19 Comic Collection — version 2 (shop + bibliothèque client).
Contexte v1 dans comics_collections/CLAUDE.md.
User Stories v2 dans USER_STORIES_V2.md à la racine.
US en cours : [numéro et titre de l'US]
```
