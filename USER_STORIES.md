# USER STORIES — Odoo Comic Collection

> Projet Odoo 18 — Gestion de collection de bandes dessinées
> Format : `US-XXX | En tant que... | Je veux... | Afin de...`

---

## 🏗️ PHASE 1 — Infrastructure ✅ TERMINÉE

### EPIC 1 : Modèles & Sécurité

---

**US-001 — Scaffold du module principal** ✅

```
Critères d'acceptance :
- [x] __manifest__.py correct (version 18.0.1.0.0, LGPL-3)
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

## 🔌 PHASE 2 — Connecteur BDGest

> Priorité haute : permet de peupler rapidement la collection sans saisie manuelle.

### EPIC 3 : Scraping et import BDGest

---

**US-017 — Infrastructure scraping BDGest** ✅ (couche scraping) / 🔲 (UI Odoo → US-019)

```
En tant que développeur
Je veux une couche de scraping robuste pour BDGest/Bedetheque
Afin de récupérer les données de BD automatiquement

Critères d'acceptance :
- [x] Module comic_bdgest avec __manifest__ correct
- [x] Dépend de : comic_collection
- [x] Classe BdgestScraper dans comic_bdgest/scraper/bdgest_scraper.py
- [x] Méthode search_by_title(term) → liste de résultats
- [x] Méthode search_by_isbn(isbn) → résultat unique
- [x] Méthode search_by_author(term) → liste de résultats
- [x] Méthode get_album_detail(bdgest_id) → dict complet
- [x] Méthode get_serie_albums(serie_id) → liste d'albums
- [x] Délai de 2 secondes entre chaque requête (rate limiting)
- [x] Gestion des erreurs (timeout, 404, blocage IP, captcha)
- [x] User-Agent correct dans les headers
- [ ] Bouton à côté de l'ISBN pour enrichir une fiche depuis BDGest  → US-019
- [ ] Sélection multiple en list view + action "Enrichir depuis BDGest"  → US-019
```

---

**US-018 — Parsing des données BDGest**

```
En tant que développeur
Je veux extraire correctement toutes les données d'une fiche BDGest
Afin d'avoir des informations complètes lors de l'import

Critères d'acceptance :
- [x] Extraction : titre, tome, série, ISBN
- [x] Extraction : scénariste(s), dessinateur(s), coloriste(s)
- [x] Extraction : éditeur, date parution, dépôt légal, nb pages
- [x] Extraction : URL image de couverture
- [x] Extraction : ID BDGest de la série et de l'album
- [x] Téléchargement et encodage base64 de la couverture
- [x] Mapping automatique des rôles auteurs

Notes implémentation :
- `comic_bdgest/scraper/bdgest_parser.py` — classe stateless BdgestParser (testable sans HTTP)
- `comic_bdgest/tests/test_bdgest_parser.py` — 46 tests unitaires (fixtures HTML)
- `BdgestScraper` délègue tout le parsing HTML à BdgestParser
```

---

**US-022 — Configuration BDGest**

```
En tant qu'administrateur
Je veux configurer les paramètres de connexion BDGest
Afin de pouvoir utiliser un compte authentifié si nécessaire

Critères d'acceptance :
- [ ] Page de configuration dans Paramètres Odoo
- [ ] Champs : login BDGest (optionnel), mot de passe (password field)
- [ ] Bouton "Tester la connexion"
- [ ] Paramètre : délai entre requêtes (défaut 2s)
- [ ] Stockage sécurisé via ir.config_parameter
```

---

**US-019 — Wizard de recherche et d'import BDGest**

```
En tant que collectionneur
Je veux rechercher un album sur BDGest depuis Odoo et l'importer en un clic
Afin d'éviter la saisie manuelle des informations

Critères d'acceptance :
- [ ] Wizard accessible depuis le menu BDGest et depuis le bouton sur comic.album
- [ ] Étape 1 : saisie du terme de recherche + type (titre / ISBN / auteur)
- [ ] Étape 2 : liste des résultats avec couverture miniature, titre, auteur, éditeur
- [ ] Case à cocher pour sélectionner les albums à importer
- [ ] Étape 3 : confirmation et import
- [ ] Gestion des doublons (si bdgest_album_id déjà présent → alerte)
- [ ] Création automatique des res.partner auteurs si non existants
- [ ] Création automatique de la série si non existante
```

---

**US-020 — Import d'une série complète depuis BDGest**

```
En tant que collectionneur
Je veux importer tous les tomes d'une série en une seule action
Afin de peupler rapidement ma collection

Critères d'acceptance :
- [ ] Bouton "Synchroniser depuis BDGest" sur le formulaire comic.serie
- [ ] Récupère tous les albums de la série via bdgest_id
- [ ] N'importe que les albums non encore présents (pas de doublon)
- [ ] Rapport final : X albums ajoutés, Y déjà présents, Z erreurs
- [ ] Progression affichée pendant la synchro (si longue)
```

---

**US-021 — Enrichissement liens d'achat automatique**

```
En tant que collectionneur
Je veux que les liens club.be et amazon.com.be soient générés automatiquement à l'import
Afin de ne pas avoir à les chercher manuellement

Critères d'acceptance :
- [ ] À l'import BDGest, construction URL club.be : https://www.club.be/search?q={isbn}
- [ ] À l'import BDGest, construction URL amazon.be : https://www.amazon.com.be/s?k={isbn}
- [ ] URLs sauvegardées sur comic.album
- [ ] Possibilité de rafraîchir les liens manuellement (bouton)
```

---

## 🤖 PHASE 3 — Connecteur IA

> Priorité haute : enrichissement des fiches BD via Claude / OpenAI.

### EPIC 4 : Intelligence Artificielle

---

**US-023 — Configuration des connecteurs IA**

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

**US-024 — Génération de synopsis par IA**

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

**US-025 — Traduction du synopsis par IA**

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

**US-026 — Suggestions de BD similaires par IA**

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
- [ ] Sous-menus : Ma Collection > Séries / Albums / Prêts
- [ ] Sous-menu : Wishlist
- [ ] Sous-menus : Catalogues > Auteurs (res.partner filtré) / Éditeurs / Genres
- [ ] Menu Configuration avec accès paramètres IA et BDGest
```

---

**US-009 — Vue Kanban des séries**

```
En tant que collectionneur
Je veux voir mes séries sous forme de grille avec les couvertures
Afin d'avoir une vue visuelle de ma collection

Critères d'acceptance :
- [ ] Vue kanban comic.serie avec image de couverture
- [ ] Affichage : titre, type, nb tomes possédés / total
- [ ] Barre de progression (tomes possédés)
- [ ] Badge couleur selon statut (en cours / terminée)
- [ ] Clic sur la carte → ouvre le form
- [ ] Image placeholder si pas de couverture
```

---

**US-010 — Vue Kanban des albums**

```
En tant que collectionneur
Je veux voir mes albums sous forme de grille de couvertures
Afin d'avoir une vraie bibliothèque visuelle

Critères d'acceptance :
- [ ] Vue kanban comic.album avec couverture en grand
- [ ] Affichage : titre, tome, note en étoiles
- [ ] Badge état de lecture (lu / en cours / non lu)
- [ ] Icône wishlist si dans_wishlist = True
- [ ] Filtres rapides : dans ma collection / wishlist / non lu
- [ ] Image placeholder si pas de couverture
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
- [ ] Barre de recherche sur : titre, ISBN, auteur, série, éditeur
- [ ] Filtres prédéfinis : Dans ma collection / Wishlist / Prêtés /
        Non lus / En cours de lecture
- [ ] Group by : Série / Genre / Éditeur / Type / État de lecture
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

**US-015 — Liens d'achat club.be et amazon.com.be**

```
En tant que collectionneur
Je veux avoir des liens directs vers club.be et amazon.com.be pour chaque album
Afin d'acheter facilement un album manquant

Critères d'acceptance :
- [ ] Boutons "Acheter sur Club.be" et "Acheter sur Amazon.be" dans le form
- [ ] Si URL vide, bouton désactivé (grisé)
- [ ] Ouverture dans un nouvel onglet (target="_blank")
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

## 📥 PHASE 6 — Import CSV/XLSX

### EPIC 7 : Import de données

---

**US-027 — Modèle de fichier d'import**

```
En tant que collectionneur
Je veux un modèle CSV/XLSX à télécharger pour importer ma collection existante
Afin de migrer facilement depuis une autre gestion (Excel, autre logiciel)

Critères d'acceptance :
- [ ] Fichier modèle téléchargeable depuis le wizard d'import
- [ ] Format CSV (UTF-8, séparateur ;) et XLSX disponibles
- [ ] Colonnes : serie_name, tome, titre_album, isbn, date_parution, nb_pages,
        editeur, scenariste, dessinateur, coloriste, genre, etat_lecture,
        note, url_couverture, url_club_be, url_amazon_be
- [ ] Ligne d'exemple incluse dans le modèle
- [ ] README inclus dans le XLSX (onglet "Instructions")
```

---

**US-028 — Wizard d'import CSV/XLSX**

```
En tant que collectionneur
Je veux importer ma collection depuis un fichier CSV ou XLSX
Afin de ne pas tout saisir manuellement

Critères d'acceptance :
- [ ] Wizard en 3 étapes : Upload → Mapping → Prévisualisation → Import
- [ ] Détection automatique CSV/XLSX selon l'extension
- [ ] Détection automatique du séparateur CSV (; ou ,)
- [ ] Étape Mapping : associer chaque colonne du fichier au champ Odoo
- [ ] Prévisualisation des 10 premières lignes avant import
- [ ] Import avec rapport : X créés, Y mis à jour, Z erreurs (avec détail)
- [ ] Option : "Mettre à jour si ISBN existant" ou "Toujours créer"
- [ ] Téléchargement du rapport d'erreurs en CSV
```

---

## 🔧 TRANSVERSE — Qualité & Packaging

---

**US-029 — Tests unitaires**

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

**US-030 — Documentation et README**

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

| Phase      | Epic                     | US                      | Statut                          |
| ---------- | ------------------------ | ----------------------- | ------------------------------- |
| Phase 1    | Infrastructure & Modèles | US-001 à US-005, US-007 | ✅ Terminée                     |
| Phase 1b   | Layout minimal           | US-008, US-016          | ✅ Terminée                     |
| Phase 2    | Connecteur BDGest        | US-017 à US-022         | 🔄 En cours (US-017 ✅, US-018 ✅) |
| Phase 3    | Connecteur IA            | US-023 à US-026         | 🔲 À faire                      |
| Phase 4    | Interface complète       | US-008b à US-015        | ⏳ Design validé — en attente   |
| Phase 5    | Gestion des prêts        | US-006                  | ⏳ En attente                   |
| Phase 6    | Import CSV/XLSX          | US-027, US-028          | ⏳ En attente                   |
| Transverse | Qualité                  | US-029, US-030          | ⏳ En attente                   |

---

## 🚀 Pour travailler avec Claude dans VS Code

```
Je travaille sur le projet Odoo 18 Comic Collection.
Contexte complet dans CLAUDE.md à la racine du projet.
US en cours : [numéro et titre de l'US]
```
