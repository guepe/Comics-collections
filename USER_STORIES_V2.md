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
| US-045 | Import automatique depuis commandes client          | US-039, US-035  |

### À faire — Priorité basse 🟡

| US     | Titre                                              | Dépend de       |
| ------ | -------------------------------------------------- | --------------- |
| US-046 | Rapport "BD non vendues les plus suivies"           | US-039          |
| US-047 | Rapport "Séries et auteurs à référencer"            | US-046          |
| US-048 | Notification CRM à la mise en catalogue             | US-047          |
| US-049 | Dashboard commerçant — vue marché                   | US-046, US-047  |

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

**US-045 — Import automatique depuis les commandes client** ⏳ 🟠

```
En tant que client
Je veux que mes achats dans le shop soient automatiquement ajoutés à ma bibliothèque
Afin de ne pas avoir à ajouter manuellement ce que j'ai acheté ici

Critères d'acceptance :
- [ ] À la confirmation d'une commande (état 'sale'), pour chaque ligne de commande
        dont le produit est lié à un comic.album :
        créer (ou mettre à jour) un comic.customer.album avec :
        source = achete_ici, dans_collection = True, sale_order_line_id = ligne
- [ ] Idem pour les ventes POS (US-042)
- [ ] Si l'album est déjà dans la bibliothèque du client (acheté ailleurs),
        mettre à jour source → achete_ici sans écraser note ni commentaire
- [ ] Email de confirmation d'achat inclut un lien "Voir dans ma bibliothèque"
- [ ] Le client peut désactiver cette fonctionnalité dans ses préférences portail
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

## 📋 Récapitulatif V2

| Phase   | Epic                    | US              | Priorité        |
| ------- | ----------------------- | --------------- | --------------- |
| Phase 7 | Catalogue & Lien Produit | US-035 à US-038 | 🔴 Must Have    |
| Phase 8 | Bibliothèque Client      | US-039 à US-045 | 🔴 / 🟠 Must    |
| Phase 9 | Business Intelligence    | US-046 à US-049 | 🟡 Nice to Have |

### Dépendances critiques

```
US-035 (scaffold comic_shop) → US-036 (lien produit) → US-037 (synchro) → US-040 (webshop)
US-040 → US-041 (navigation webshop) → US-041b (pages auteurs et éditeurs)
US-035 → US-039 (customer.album) → US-043 (portail) → US-044 (ajout BD)
US-035 → US-042 (POS), US-045 (import commandes)
US-039 → US-046 → US-047 → US-048
```

---

## 🚀 Pour travailler avec Claude dans VS Code

```
Je travaille sur le projet Odoo 19 Comic Collection — version 2 (shop + bibliothèque client).
Contexte v1 dans comics_collections/CLAUDE.md.
User Stories v2 dans USER_STORIES_V2.md à la racine.
US en cours : [numéro et titre de l'US]
```
