# USER STORIES — Odoo Comic Collection

> Projet Odoo 19 — Gestion de collection de bandes dessinées
> Format : `US-XXX | En tant que... | Je veux... | Afin de...`
> **Sources de données :** Google Books API (gratuite) + Open Library (gratuite, sans clé)
> + BnF SRU (gratuite, sans clé) + BDGest scraping (fallback, opt-in légal)
> **Pas de scraping par défaut** — toutes les sources primaires sont des APIs officielles ouvertes.

---

## 🏗️ PHASE 1 — Infrastructure ✅ TERMINÉE

### EPIC 1 : Modèles & Sécurité

---

**US-001 — Scaffold du module principal** ✅

```
Critères d'acceptance :
- [x] __manifest__.py correct (version 19.0.1.0.0, LGPL-3)
- [x] Dépendances : base, mail, contacts
- [x] Module installable sans erreur
- [x] Icône présente dans static/description/
- [x] Application = True (apparaît dans le menu Apps)
```

---

**US-002 — Modèle `comic.genre`** ✅

```
Critères d'acceptance :
- [x] Modèle comic.genre avec champs : name, description, color
- [x] Vue list et form
- [x] Données de base pré-chargées (10 genres)
- [x] Droits d'accès configurés
```

---

**US-003 — Modèle `comic.editeur`** ✅

```
Critères d'acceptance :
- [x] Modèle comic.editeur : name, pays_id, site_web, bdgest_editeur_id
- [x] Lien optionnel vers res.partner
- [x] Vue list et form
- [x] Droits d'accès configurés
```

---

**US-004 — Modèle `comic.serie`** ✅

```
Critères d'acceptance :
- [x] Tous les champs du modèle définis (voir CLAUDE.md)
- [x] Héritage mail.thread + mail.activity.mixin
- [x] Champ computed nb_albums_total et nb_albums_possedes
- [x] Vue list et form avec onglets
- [x] Droits d'accès configurés
```

---

**US-005 — Modèle `comic.album` et `comic.album.auteur.line`** ✅

```
Critères d'acceptance :
- [x] Tous les champs du modèle définis (voir CLAUDE.md)
- [x] Table comic.album.auteur.line avec rôles
- [x] Utilisation de res.partner pour les auteurs
- [x] Héritage mail.thread + mail.activity.mixin
- [x] Validation ISBN (format EAN-13)
- [x] Vue list et form avec onglets : Auteurs, Ma Collection, Liens, IA
- [x] Droits d'accès configurés
```

---

**US-007 — Sécurité et droits d'accès** ✅

```
Critères d'acceptance :
- [x] ir.model.access.csv complet pour tous les modèles
- [x] Groupe comic_collection.group_comic_user (lecture/écriture)
- [x] Groupe comic_collection.group_comic_manager (admin)
- [x] Record rules : collection privée par utilisateur (user voit le sien, manager voit tout)
```

---

## 🗂️ PHASE 1b — Layout minimal

> Objectif : rendre le module navigable avec des vues liste simples.
> Suffisant pour valider BDGest et IA sans attendre le design final de l'interface.

### EPIC 2 : Navigation de base

---

**US-008 — Menus et navigation minimale** ✅

```
En tant que collectionneur
Je veux un menu principal pour accéder aux listes de base
Afin de naviguer dans l'application et tester les connecteurs

Critères d'acceptance :
- [x] Menu principal "Bandes Dessinées" visible dans la barre de navigation Odoo
- [x] Ma Collection > Séries (list)
- [x] Ma Collection > Albums (list)
- [x] Catalogues > Éditeurs (list)
- [x] Catalogues > Genres (list)
- [x] Configuration > Paramètres (placeholder, group_comic_manager)
```

---

**US-016 — Données de démonstration** ✅

```
En tant que développeur
Je veux des données de démonstration réalistes
Afin de pouvoir tester BDGest et IA sur un jeu de données existant

Critères d'acceptance :
- [x] 3 séries de démo : Astérix, Blacksad, Largo Winch
- [x] 5 albums par série minimum
- [x] Auteurs liés (res.partner) : Goscinny, Uderzo, Canales, Guarnido, Van Hamme, Francq
- [x] Genres et éditeurs pré-remplis (Albert René, Dargaud, Dupuis)
- [x] Quelques albums en wishlist (Blacksad T4-T5, Largo T5)
```

---

## 🔌 PHASE 3 — Connecteur Multi-Sources

> Priorité haute : permet de peupler rapidement la collection via APIs ouvertes, sans scraping par défaut.

### EPIC 3 : APIs ouvertes + BDGest fallback

---

**US-017 — Infrastructure du module `comic_datasource`** ✅

```
En tant que développeur
Je veux créer la structure de base du module comic_datasource
Afin d'avoir un connecteur multi-sources propre et extensible

Critères d'acceptance :
- [x] Module comic_datasource avec __manifest__ correct
- [x] Dépend de : comic_collection
- [x] Structure sources/ avec un fichier par source
- [x] Classe de base abstraite BaseComicSource avec interface commune
- [x] Modèle normalisé de retour (dict) défini et documenté
- [x] Classe ComicDataAggregator dans aggregator.py
- [x] Tests unitaires avec mocks HTTP pour chaque source
```

---

**US-018 — Source Google Books API** ✅

```
En tant que collectionneur
Je veux que le système récupère les données depuis Google Books
Afin d'obtenir synopsis, couvertures HD et métadonnées de qualité

Critères d'acceptance :
- [x] Classe GoogleBooksSource opérationnelle
- [x] Recherche par ISBN (prioritaire)
- [x] Recherche par titre + auteur optionnel
- [x] Extraction : titre, auteurs, éditeur, date, pages, synopsis, couvertures
- [x] Couvertures disponibles en 4 tailles (small/medium/large/extraLarge)
- [x] Clé API configurable dans Paramètres Odoo
- [x] Gestion erreur quota dépassé (HTTP 429) avec message clair
- [x] Fonctionne sans clé pour les requêtes de base (mode anonyme)
```

---

**US-019 — Source Open Library API**

```
En tant que collectionneur
Je veux que le système récupère les couvertures depuis Open Library
Afin d'avoir des images de couverture sans avoir besoin d'une clé API

Critères d'acceptance :
- [ ] Classe OpenLibrarySource opérationnelle
- [ ] Recherche par ISBN → métadonnées complètes
- [ ] URL couverture générée directement : covers.openlibrary.org/b/isbn/{ISBN}-L.jpg
- [ ] Vérification existence couverture avant téléchargement (évite les 404)
- [ ] Extraction auteurs avec mapping rôles si disponible
- [ ] Aucune configuration requise (pas de clé API)
- [ ] Utilisée automatiquement comme source de couverture alternative
```

---

**US-020 — Source BnF SRU API**

```
En tant que collectionneur
Je veux que le système interroge la BnF pour les BD francophones
Afin d'avoir des données officielles de dépôt légal pour les BD FR/BE

Critères d'acceptance :
- [ ] Classe BnfSource opérationnelle
- [ ] Recherche par ISBN via API SRU
- [ ] Parsing XML de la réponse (xmltodict)
- [ ] Extraction : titre, auteurs, éditeur, date dépôt légal, ISBN
- [ ] Priorité sur les autres sources pour les champs date_depot_legal
- [ ] Aucune configuration requise
- [ ] Gestion timeout (la BnF peut être lente)
```

---

**US-021 — Source BDGest (fallback scraping)**

```
En tant que collectionneur
Je veux pouvoir utiliser BDGest comme source de dernier recours
Afin de récupérer des BD non trouvées dans les APIs ouvertes

Critères d'acceptance :
- [ ] Classe BdgestSource opérationnelle (scraping BeautifulSoup)
- [ ] DISCLAIMER légal affiché à la première activation dans les paramètres
- [ ] Case à cocher "J'accepte les CGU de BDGest" obligatoire pour activer
- [ ] Désactivée par défaut (opt-in explicite)
- [ ] Délai de 2 secondes entre chaque requête (rate limiting)
- [ ] Credentials optionnels (login/mdp) pour accès authentifié
- [ ] Recherche par ISBN, titre, auteur
- [ ] Import série complète via bdgest_serie_id
- [ ] Gestion blocage IP avec message d'erreur explicite
```

---

**US-022 — Aggregateur multi-sources**

```
En tant que développeur
Je veux un aggregateur qui fusionne intelligemment les données de toutes les sources
Afin d'obtenir la fiche la plus complète possible automatiquement

Critères d'acceptance :
- [ ] Classe ComicDataAggregator avec méthode search(isbn, title, author)
- [ ] Cascade dans l'ordre : Google → Open Library → BnF → BDGest
- [ ] Fusion des champs : prend le premier champ non-vide trouvé
- [ ] Exception : synopsis priorité Google > BnF > BDGest
- [ ] Exception : date_depot_legal priorité BnF > autres
- [ ] Exception : couverture priorité Google Large > OpenLib L > BDGest
- [ ] Résultat indique quelle source a fourni chaque champ
- [ ] Cache des résultats en session (évite les appels répétés)
- [ ] Log des sources interrogées pour debugging
```

---

**US-023 — Wizard de recherche et import unifié** ✅

```
En tant que collectionneur
Je veux rechercher un album dans toutes les sources en un seul geste
Afin d'importer facilement n'importe quelle BD dans ma collection

Critères d'acceptance :
- [x] Wizard accessible depuis menu et depuis bouton sur comic.album
- [x] Champ de recherche unique (ISBN ou titre)
- [x] Détection automatique ISBN vs titre (format EAN-13)
- [x] Affichage des résultats avec badge source (Google/OpenLib/BnF/BDGest)
- [x] Couverture preview dans le wizard
- [x] Sélection multiple pour import en lot
- [x] Gestion des doublons (ISBN déjà en base → avertissement + mise à jour)
- [x] Gestion conflit de titre (EN vs FR) : choix keep / use_new / skip par ligne
- [x] Import crée automatiquement : série, auteurs (res.partner), éditeur
- [x] Rapport post-import : X créés, Y mis à jour, Z ignorés
- [x] Bouton "Mettre à jour les albums" sur la fiche Série (lot)
```

---

**US-024 — Configuration des sources de données**

```
En tant qu'administrateur
Je veux configurer les sources de données dans les paramètres Odoo
Afin de contrôler quelles APIs sont utilisées et dans quel ordre

Critères d'acceptance :
- [ ] Section "Sources de données BD" dans Paramètres > Configuration
- [ ] Champ clé API Google Books avec lien vers console.cloud.google.com
- [ ] Bouton "Tester Google Books" avec retour visuel
- [ ] Toggle activation Open Library (activé par défaut)
- [ ] Toggle activation BnF (activé par défaut)
- [ ] Toggle activation BDGest avec disclaimer légal (désactivé par défaut)
- [ ] Champs login/mdp BDGest (conditionnels si BDGest activé)
- [ ] Champ délai BDGest (défaut : 2 secondes)
- [ ] Ordre de priorité des sources (drag & drop ou sélection)
```

---

**US-025 — Enrichissement automatique des liens d'achat** ✅

```
En tant que collectionneur
Je veux que les liens club.be et amazon.com.be soient générés automatiquement
Afin de pouvoir acheter rapidement un album manquant

Critères d'acceptance :
- [x] À la création, construction URL librairieclub.be depuis l'ISBN
- [x] À la création, construction URL amazon.com.be depuis l'ISBN
- [x] À la création, construction URL fnac.be depuis l'ISBN (bonus)
- [x] Bouton "Régénérer les liens" sur le formulaire album
- [x] Les liens s'ouvrent dans un nouvel onglet (via action_open_*)
- [x] Boutons grisés si URL vide
- [x] Auto-remplissage à la saisie ISBN (onchange) si champs vides
```

---

## 🤖 PHASE 4a — Connecteur IA

> Priorité haute : enrichissement des fiches BD via Claude / OpenAI.

### EPIC 4 : Intelligence Artificielle

---

**US-026 — Configuration des connecteurs IA**

```
En tant qu'administrateur
Je veux configurer les API Claude et OpenAI dans les paramètres Odoo
Afin de pouvoir utiliser l'IA pour enrichir mes fiches BD

Critères d'acceptance :
- [ ] Section "IA - Bandes Dessinées" dans Paramètres > Configuration
- [ ] Sélecteur de provider actif : Claude (Anthropic) / OpenAI
- [ ] Champ clé API Claude (password, stocké en ir.config_parameter)
- [ ] Champ modèle Claude (défaut: claude-sonnet-4-6)
- [ ] Champ clé API OpenAI (password, stocké en ir.config_parameter)
- [ ] Champ modèle OpenAI (défaut: gpt-4o)
- [ ] Langue de génération par défaut : FR / NL / EN
- [ ] Bouton "Tester la connexion IA"
```

---

**US-027 — Génération de synopsis par IA**

```
En tant que collectionneur
Je veux générer automatiquement un synopsis pour un album via l'IA
Afin d'enrichir ma fiche sans avoir à rédiger manuellement

Critères d'acceptance :
- [ ] Bouton "✨ Générer le synopsis" dans l'onglet IA du formulaire album
- [ ] Le prompt inclut : titre, série, tome, auteurs, éditeur, genre, date
- [ ] Wizard de prévisualisation avant d'appliquer
- [ ] Bouton "Appliquer" → insère dans le champ synopsis
- [ ] Bouton "Régénérer" → nouvelle génération
- [ ] Bouton "Annuler" → ferme sans modifier
- [ ] Indicateur de chargement pendant la génération
- [ ] Gestion d'erreur si clé API invalide ou timeout
```

---

**US-028 — Traduction du synopsis par IA**

```
En tant que collectionneur
Je veux traduire le synopsis d'un album dans une autre langue
Afin de gérer une collection multilingue (FR/NL/EN)

Critères d'acceptance :
- [ ] Action "Traduire le synopsis" dans le wizard IA
- [ ] Sélection de la langue cible
- [ ] Prévisualisation avant application
- [ ] Le synopsis traduit remplace ou complète le champ existant
```

---

**US-029 — Suggestions de BD similaires par IA**

```
En tant que collectionneur
Je veux que l'IA me suggère des BD similaires à celles que j'ai notées 4-5 étoiles
Afin de découvrir de nouvelles BD correspondant à mes goûts

Critères d'acceptance :
- [ ] Action "Suggérer des BD similaires" dans le wizard IA
- [ ] L'IA reçoit : genre, auteurs, synopsis, note de l'album
- [ ] Retourne une liste de 5 suggestions avec titre, auteur, raison
- [ ] Résultat affiché dans une vue dédiée (non sauvegardé en base)
- [ ] Bouton "Rechercher sur BDGest" pour chaque suggestion (si module bdgest installé)
```

---

## 🎨 PHASE 4 — Interface complète

> À démarrer une fois le design validé et les connecteurs BDGest/IA fonctionnels.

### EPIC 5 : Vues avancées et navigation complète

---

**US-008b — Menus et navigation complète**

```
En tant que collectionneur
Je veux un menu principal complet avec toutes les fonctions
Afin de naviguer dans toute l'application

Critères d'acceptance :
- [x] Sous-menus : Ma Collection > Séries / Albums
- [x] Sous-menu : Wishlist
- [ ] Sous-menu : Prêts (US-006 non encore implémenté)
- [ ] Sous-menus : Catalogues > Auteurs (res.partner filtré)
- [x] Catalogues > Éditeurs / Genres
- [ ] Menu Configuration avec accès paramètres IA et BDGest (partiel)
```

---

**US-009 — Vue Kanban des séries** ✅

```
En tant que collectionneur
Je veux voir mes séries sous forme de grille avec les couvertures
Afin d'avoir une vue visuelle de ma collection

Critères d'acceptance :
- [x] Vue kanban comic.serie avec image de couverture
- [x] Affichage : titre, nb tomes possédés / total
- [x] Barre de progression (tomes possédés)
- [x] Badge couleur selon statut (en cours / terminée / abandonnée)
- [x] Clic sur la carte → ouvre le form
- [x] Image placeholder (fond INK + titre) si pas de couverture
```

---

**US-010 — Vue Kanban des albums** ✅

```
En tant que collectionneur
Je veux voir mes albums sous forme de grille de couvertures
Afin d'avoir une vraie bibliothèque visuelle

Critères d'acceptance :
- [x] Vue kanban comic.album avec couverture en grand (200×270)
- [x] Affichage : titre, tome, note en étoiles (5★)
- [x] Badge état de lecture coloré (lu / en cours / non lu)
- [x] Icône ♥ wishlist si dans_wishlist = True
- [x] Filtres rapides : dans ma collection / wishlist / non lu / en cours
- [x] Placeholder coloré éditorial (8 palettes) si pas de couverture
```

---

**US-011 — Formulaire album enrichi**

```
En tant que collectionneur
Je veux un formulaire détaillé et ergonomique pour chaque album
Afin de saisir et consulter toutes les informations

Critères d'acceptance :
- [ ] Onglet "Informations" : titre, série, tome, ISBN, dates, pages, éditeur, couverture
- [ ] Onglet "Auteurs" : liste des auteurs avec leur rôle (widget editable inline)
- [ ] Onglet "Ma Collection" : état lecture, note étoiles, prêts liés
- [ ] Onglet "Liens" : url_club_be, url_amazon_be avec boutons "Ouvrir"
- [ ] Onglet "IA" : synopsis + bouton génération IA
- [ ] Bouton "Ajouter à la wishlist" / "Dans ma collection"
- [ ] Widget note en étoiles (priority widget ou custom)
```

---

**US-012 — Filtres et recherche avancée**

```
En tant que collectionneur
Je veux filtrer et rechercher dans ma collection
Afin de retrouver rapidement un album ou une série

Critères d'acceptance :
- [x] Barre de recherche sur : titre, ISBN, série
- [ ] Recherche auteur, éditeur
- [x] Filtres prédéfinis : Dans ma collection / Wishlist / Non lus / En cours de lecture
- [ ] Filtre Prêtés (US-006 requis)
- [x] Group by : Série / État de lecture
- [ ] Group by : Genre / Éditeur / Type
- [ ] Filtre par note (> 3 étoiles, etc.)
```

---

**US-013 — Dashboard statistiques**

```
En tant que collectionneur
Je veux voir les statistiques de ma collection sur un tableau de bord
Afin de connaître l'état de ma bibliothèque

Critères d'acceptance :
- [ ] Nb total d'albums possédés
- [ ] Nb de séries (complètes / en cours)
- [ ] Répartition par genre (graphique camembert)
- [ ] Répartition par état de lecture (graphique barre)
- [ ] Top 5 séries les mieux notées
- [ ] Albums prêtés en retard (alerte)
- [ ] Albums récemment ajoutés
```

---

**US-014 — Gestion de la Wishlist**

```
En tant que collectionneur
Je veux gérer une liste de souhaits d'albums à acquérir
Afin de savoir quoi acheter lors de mes prochains passages en librairie

Critères d'acceptance :
- [ ] Vue dédiée Wishlist (kanban ou list)
- [ ] Bouton "Marquer comme acquis" → passe dans_collection=True, wishlist=False
- [ ] Liens rapides vers club.be et amazon.com.be
- [ ] Tri par série pour grouper les tomes manquants
```

---

**US-015 — Liens d'achat club.be et amazon.com.be** ✅

```
En tant que collectionneur
Je veux avoir des liens directs vers club.be et amazon.com.be pour chaque album
Afin d'acheter facilement un album manquant

Critères d'acceptance :
- [x] Boutons "Acheter sur Club.be" et "Acheter sur Amazon.be" dans le form
- [x] Si URL vide, bouton désactivé (grisé)
- [x] Ouverture dans un nouvel onglet (target="_blank")
```

---

## 📚 PHASE 5 — Gestion des Prêts

> Fonctionnalité utile mais indépendante des connecteurs. À faire après validation de l'interface.

### EPIC 6 : Suivi des prêts

---

**US-006 — Modèle `comic.pret`**

```
En tant que collectionneur
Je veux enregistrer les prêts d'albums à mes amis
Afin de ne pas perdre mes BD et savoir qui a quoi

Critères d'acceptance :
- [ ] Modèle comic.pret avec tous les champs (voir CLAUDE.md)
- [ ] Alerte visuelle si date_retour_prevue dépassée
- [ ] Vue list avec filtre "en cours" par défaut
- [ ] Vue form
- [ ] Bouton "Marquer comme retourné"
- [ ] Droits d'accès configurés
```

---

## 📥 PHASE 6 — Import CSV/Excel

### EPIC 7 : Import de données

---

**US-030 — Modèle de fichier d'import** ✅

```
En tant que collectionneur
Je veux un modèle CSV/XLSX à télécharger pour importer ma collection existante
Afin de migrer facilement depuis une autre gestion (Excel, autre logiciel)

Critères d'acceptance :
- [x] Fichier modèle téléchargeable depuis le wizard d'import
- [x] Format CSV (UTF-8, séparateur ;) et XLSX disponibles
- [x] Colonnes : serie_name, tome, titre_album, isbn, date_parution, nb_pages,
        editeur, scenariste, dessinateur, coloriste, genre, etat_lecture,
        note, url_couverture, url_club_be, url_amazon_be
- [x] Ligne d'exemple incluse dans le modèle
- [x] README inclus dans le XLSX (onglet "Instructions")
```

---

**US-031 — Wizard d'import CSV/Excel** ✅

```
En tant que collectionneur
Je veux importer ma collection depuis un fichier CSV, XLS ou XLSX
Afin de ne pas tout saisir manuellement

Critères d'acceptance :
- [x] Wizard en 4 étapes : Upload → Mapping → Prévisualisation → Import
- [x] Détection automatique CSV/XLS/XLSX selon l'extension
- [x] Détection automatique du séparateur CSV (; ou ,)
- [x] Étape Mapping : associer chaque colonne du fichier au champ Odoo
- [x] Prévisualisation des 10 premières lignes avant import
- [x] Import avec rapport : X créés, Y mis à jour, Z erreurs (avec détail)
- [x] Option : "Mettre à jour si ISBN existant" ou "Toujours créer"
- [x] Téléchargement du rapport d'erreurs en CSV
```

---

## 🔧 TRANSVERSE — Qualité & Packaging

---

**US-032 — Tests unitaires**

```
En tant que développeur
Je veux des tests unitaires pour les fonctions critiques
Afin de garantir la stabilité du module

Critères d'acceptance :
- [ ] Tests pour la validation ISBN
- [ ] Tests pour le scraper BDGest (avec mock HTTP)
- [ ] Tests pour les champs computed (nb_albums_possedes, etc.)
- [ ] Tests pour l'import CSV
- [ ] Lancement via : python -m pytest ou ./odoo-bin test
```

---

**US-033 — Documentation et README**

```
En tant qu'utilisateur externe
Je veux une documentation claire pour installer et utiliser les modules
Afin de pouvoir les déployer sur mon Odoo

Critères d'acceptance :
- [ ] README.rst pour chaque module (format OCA)
- [ ] Section : Description, Installation, Configuration, Usage
- [ ] CHANGELOG.rst
- [ ] requirements.txt à la racine du projet
```

---

## 📊 Récapitulatif

| Phase | Epic | US | Priorité |
|---|---|---|---|
| Phase 1 | Infrastructure | US-001 à US-007 | 🔴 Must Have |
| Phase 2 | Interface | US-008 à US-016 | 🔴 Must Have |
| Phase 3 | Multi-sources | US-017 à US-025 | 🟠 Should Have |
| Phase 4a | IA | US-026 à US-029 | 🟡 Nice to Have |
| Phase 4b | Import | US-030 à US-031 | 🟠 Should Have |
| Transverse | Qualité | US-032 à US-033 | 🟡 Nice to Have |

---

## 🚀 Pour travailler avec Claude dans VS Code

```
Je travaille sur le projet Odoo 19 Comic Collection.
Contexte complet dans CLAUDE.md à la racine du projet.
US en cours : [numéro et titre de l'US]
```
