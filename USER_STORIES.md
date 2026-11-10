# User stories — Comic Collection (Odoo 19)

> Document unique de suivi fonctionnel : feuille de route, épics, US à venir et historique du livré.
> Remplace `USER_STORIES.md` (V1), `USER_STORIES_V2.md` et `USER_STORIES_V3.md` (fusionnés le
> 2026-11-07 ; les versions précédentes restent dans l'historique git).

**Légende :** ⏳ à faire · 🔄 partiel · ✅ livré · 💡 piste candidate (à prioriser) · ❌ abandonné

**Conventions**

- Format : *En tant que… / Je veux… / Afin de…*, puis contexte technique et critères `- [ ]`.
- Cocher `[x]` dès qu'un critère est réellement livré — jamais par anticipation. Une US dont
  tous les critères sont cochés prend ✅, puis passe en une ligne dans l'[annexe](#4-annexe--livré).
- Numérotation continue : **prochaine US = US-093**. Une piste 💡 garde son numéro quand elle est
  priorisée.
- **Depuis le 2026-11-10, les US à faire vivent dans les issues GitHub** (label `us`, label
  `epic:E*`, jalon = épic, Project [Comic Collection — Odoo](https://github.com/users/guepe/projects/3)).
  Ce fichier garde la feuille de route, la vue des épics et l'annexe du livré, avec un lien
  `#n` vers chaque issue. Copie locale lisible hors ligne : `python3 tools/sync_backlog.py`
  → `BACKLOG.md`. Une US livrée : issue fermée par `Closes #n`, puis une ligne dans l'annexe.
- Le détail technique de chaque livraison est dans `CHANGE.md` (entrées datées).

---

## 1. Feuille de route

| Horizon        | Épic                                                                      | US                          | État |
| -------------- | ------------------------------------------------------------------------- | --------------------------- | ---- |
| **Maintenant** | [E8 — Qualité & publication OCA](#e8--qualité--publication-oca)           | US-064 (#2)                 | 🔄   |
| **Plus tard**  | [E9 — Shop & commerçant](#e9--shop--commerçant)                           | US-046, 047, 049, 072       | ⏳   |
| **Plus tard**  | [E10 — Internationalisation](#e10--internationalisation)                  | US-092 (#9)                 | 🚧   |

---

## 2. Épics — vue d'ensemble

Les épics ouverts sont numérotés dans l'ordre de priorité (E5 = le plus prioritaire).

| Épic | Domaine                              | Module(s)                           | État | Livré  | Ouvert                    |
| ---- | ------------------------------------ | ----------------------------------- | ---- | ------ | ------------------------- |
| E1   | Catalogue & collection               | `comics_collections`                | ✅   | 30 US  | —                         |
| E2   | Enrichissement multi-sources         | `comic_datasource`                  | ✅   | 11 US  | —                         |
| E3   | Shop & caisse                        | `comic_shop`                        | ✅   | 12 US  | —                         |
| E4   | Bibliothèque client (portail)        | `comic_shop`                        | ✅   | 6 US   | —                         |
| E5   | Tableau de bord & suivi de séries    | `comics_collections` / `comic_shop` | ✅   | 9 US   | —                         |
| E6   | Séries sur le portail                | `comic_shop`                        | ✅   | 3 US   | —                         |
| E7   | IA                                   | `comic_ai` / `comic_ai_shop`        | ✅   | 6 US   | —                         |
| E8   | Qualité & publication OCA            | transverse                          | 🔄   | 10 US  | US-064 (#2)               |
| E9   | Shop & commerçant                    | `comic_shop` (dépôt privé)          | ⏳   | —      | pro#1 → pro#4             |
| E10  | Internationalisation (EN, FR, NL, DE) | tous                               | 🚧   | —      | #9                        |

---

## 3. Épics ouverts — US à venir

> E5 (tableau de bord & suivi de séries) est entièrement livré — voir
> l'[annexe](#e5--tableau-de-bord--suivi-de-séries-livré). Rouvert puis refermé le 2026-11-08
> pour la collection privée (US-087 → 089) : sans `comic_shop`, le module ne montre que *mes*
> BD ; le shop ajoute la couche « toutes les BD ».

### E6 — Séries sur le portail

> E6 est entièrement livré le 2026-11-08 (US-073, US-069, US-070) — voir
> l'[annexe](#e6--séries-sur-le-portail-livré).

---

### E7 — IA (`comic_ai`)

> E7 est entièrement livré : US-026 → 029 (2026-11-09), US-090 et US-091 (2026-11-10) — voir
> l'[annexe](#e7--ia-livré). Modules `comic_ai` (back-office) et `comic_ai_shop`
> (portail, auto-installé avec `comic_shop`).


---

### E8 — Qualité & publication OCA

> Livré : pre-commit, CI (tests + pre-commit), README OCA, manifests, LICENSE, tests.
> Reste la publication, à l'initiative du mainteneur (action visible de l'extérieur).

| US     | Issue | Titre                                         |
| ------ | ----- | --------------------------------------------- |
| US-064 | [#2](https://github.com/guepe/Comics-collections/issues/2) | Dépôt GitHub public + proposition OCA |

---

### E9 — Shop & commerçant

> Priorité la plus basse : outils pour le vendeur. Exploiter les bibliothèques clients
> (`comic.customer.album`) pour savoir quoi référencer. Issues dans le dépôt privé
> `guepe/Comics-collections-pro` (notées `pro#n`).

| US     | Issue | Titre                                         |
| ------ | ----- | --------------------------------------------- |
| US-046 | [pro#1](https://github.com/guepe/Comics-collections-pro/issues/1) | Rapport « BD non vendues les plus suivies » |
| US-047 | [pro#2](https://github.com/guepe/Comics-collections-pro/issues/2) | Rapport « Séries et auteurs à référencer » |
| US-049 | [pro#3](https://github.com/guepe/Comics-collections-pro/issues/3) | Tableau de bord commerçant — vue marché |
| US-072 | [pro#4](https://github.com/guepe/Comics-collections-pro/issues/4) | Réservation de tomes en magasin |

> Bugs ouverts : [#1](https://github.com/guepe/Comics-collections/issues/1) — doublons lors de
> la complétion des séries (à vérifier depuis la déduplication US-050/056) ;
> [#7](https://github.com/guepe/Comics-collections/issues/7) — « Ajouter à ma wishlist » sur un album
> possédé ; [pro#5](https://github.com/guepe/Comics-collections-pro/issues/5) — format des prix des cartes série.

---

### E10 — Internationalisation

> Interface des modules en anglais (l'interface est aujourd'hui en français), puis autres langues.

| US     | Issue | Titre                                         |
| ------ | ----- | --------------------------------------------- |
| US-092 | [#9](https://github.com/guepe/Comics-collections/issues/9) | Interface des modules en anglais |

---

## 4. Annexe — Livré

Une ligne par US. Détail technique : `CHANGE.md` ; texte d'origine : historique git des
anciens fichiers V1 / V2 / V3.

### E1 — Catalogue & collection ✅

| US      | Titre                                                                   |
| ------- | ----------------------------------------------------------------------- |
| US-001  | Scaffold du module principal                                            |
| US-002  | Modèle `comic.genre`                                                    |
| US-003  | Modèle `comic.editeur`                                                  |
| US-004  | Modèle `comic.serie`                                                    |
| US-005  | Modèle album + lignes auteur (devenu `comic.work`, cf. US-051)          |
| US-006  | Prêts (`comic.pret`) — complété par US-076                              |
| US-007  | Sécurité et droits d'accès                                              |
| US-008  | Menus et navigation minimale                                            |
| US-008b | Menus et navigation complète                                            |
| US-009  | Vue kanban des séries                                                   |
| US-010  | Vue kanban des albums                                                   |
| US-011  | Formulaire album enrichi (widget étoiles → US-067)                      |
| US-012  | Filtres et recherche avancée — partiel, reste → US-066                  |
| US-014  | Wishlist                                                                |
| US-015  | Liens d'achat Club.be / Amazon.be / FNAC.be                             |
| US-016  | Données de démonstration                                                |
| US-030  | Modèle de fichier d'import                                              |
| US-031  | Wizard d'import CSV / Excel                                             |
| US-050  | Refactor canonique : analyse, décisions, stratégie de déduplication     |
| US-051  | Refactor canonique : ORM Œuvre / Édition / ISBN, fin de `comic.album`   |
| US-053  | Refactor canonique : vues back-office                                   |
| US-056  | Moteur de déduplication des œuvres                                      |
| US-057  | Façade UX album / tome                                                  |
| US-058  | Nettoyage UI : onglets, menus, synchro des couvertures                  |
| US-075  | Catalogue partagé (droits par créateur pour la suppression) et séries suivies par utilisateur — 2026-11-05 |
| US-076  | Prêts complets : dates par défaut, retour, retards, double prêt, rappel quotidien, prêts privés — 2026-11-05 |
| US-077  | Import fiabilisé : colonnes fixes, politique mise à jour / ignorer, TSV, couverture par URL, vrais n° de ligne — 2026-11-05 |
| US-078  | Albums : tome saisissable, tome 0 = hors-série, création tout-en-un, suppression, liste groupée par série — 2026-11-05 |
| US-083  | Doublons : analyse par blocs, fusion dans les deux sens, nettoyage des paires — 2026-11-05 |
| US-084  | Fiches auteur et éditeur : séries et albums associés — 2026-11-06       |

### E2 — Enrichissement multi-sources ✅

| US     | Titre                                                                    |
| ------ | ------------------------------------------------------------------------ |
| US-017 | Infrastructure du module `comic_datasource`                              |
| US-018 | Source Google Books                                                      |
| US-019 | Source Open Library                                                      |
| US-020 | Source BnF SRU                                                           |
| US-022 | Agrégateur multi-sources                                                 |
| US-023 | Wizard de recherche et import unifié                                     |
| US-024 | Configuration des sources de données                                     |
| US-025 | Enrichissement automatique des liens d'achat                             |
| US-034 | Suivi des séries : détection des tomes manquants                         |
| US-052 | Refactor canonique : adaptation des sources et de l'import               |
| US-079 | Fiabilité : champs vides seulement, réglages effectifs, cron qui avance, coupe-circuit quota Google, dates complètes seulement — 2026-11-05 / 06 |

### E3 — Shop & caisse ✅

| US      | Titre                                                                   |
| ------- | ----------------------------------------------------------------------- |
| US-035  | Scaffold du module `comic_shop`                                         |
| US-036  | Lien album → `product.template`                                         |
| US-037  | Synchronisation album ↔ produit                                         |
| US-037b | Smart button BD et synchro sur la fiche produit                         |
| US-037c | Création de produits en masse depuis la série                           |
| US-040  | Fiche produit webshop enrichie BD                                       |
| US-041  | Navigation webshop par série / auteur / genre                           |
| US-041b | Pages website auteurs et éditeurs                                       |
| US-042  | Intégration POS (caisse)                                                |
| US-054  | Refactor canonique : adaptation de `comic_shop`                         |
| US-074  | Sécurité du shop : pages auteurs limitées aux auteurs, téléchargement de couverture restreint (anti-SSRF), paramètres validés — 2026-11-05 |
| US-080  | Cohérence caisse / ventes : remboursements POS et annulations retirent de la bibliothèque, synchro produit non destructive — 2026-11-05 |

### E4 — Bibliothèque client (portail) ✅

| US     | Titre                                                                    |
| ------ | ------------------------------------------------------------------------ |
| US-039 | Modèle `comic.customer.album`                                            |
| US-043 | Espace bibliothèque client sur le portail                                |
| US-044 | Ajout d'une BD hors catalogue à la bibliothèque                          |
| US-045 | Ajout automatique depuis les commandes client                            |
| US-081 | Modération des fiches créées depuis le portail : valider / refuser (doublon ou incorrect), client notifié — 2026-11-05 |
| US-082 | Bibliothèque portail : pagination, messages, ISBN-10, wishlist sur un album possédé — 2026-11-05 / 06 |

### E5 — Tableau de bord & suivi de séries (livré)

| US     | Titre                                                                    |
| ------ | ------------------------------------------------------------------------ |
| US-086 | Bibliothèque personnelle (`comic.customer.album`) descendue dans `comics_collections` : module utilisable seul, migration des identifiants, menus Ma bibliothèque / Tous les albums — 2026-11-08 |
| US-065 | Tableau de bord collectionneur : back-office (action OWL, prêts en retard) et portail `/my/library/dashboard` — 2026-11-08 |
| US-066 | Filtres Prêtés, Note ≥ 3★ / ≥ 4★, regroupements par genre et type de série — 2026-11-08 |
| US-067 | Note en étoiles : widget en back-office, saisie par étoiles sur le portail — 2026-11-08 |
| US-068 | Alerte nouveautés : notification Odoo aux abonnés d'une série quand un tome paru < 90 j (ou à paraître) est ajouté ; bouton « Ajouter à ma wishlist » — 2026-11-08 |
| US-071 | Prix d'achat / valeur estimée, totaux au tableau de bord, export CSV, inventaire PDF — 2026-11-08 |
| US-087 | Collection privée par défaut : « Mes albums » / « Mes séries » (domaine fixe), création = possession, catalogue complet réservé au gestionnaire (ouvert à tous par `comic_shop`) — 2026-11-08 |
| US-088 | Suivi automatique des séries commencées (création, premier album possédé), désabonnement mémorisé (`suivi_exclu_user_ids`), migration des propriétaires — 2026-11-08 |
| US-089 | Ma wishlist façon BDGest' Online : manques des séries suivies + souhaits manuels, groupés par série ; Je l'ai / Ignorer / Retirer ; tuile « manques · souhaits » — 2026-11-08 |

### E6 — Séries sur le portail (livré)

| US     | Titre                                                                    |
| ------ | ------------------------------------------------------------------------ |
| US-073 | Wishlist partageable par lien secret révocable (`/wishlist/<jeton>`, lecture seule) — 2026-11-08 |
| US-069 | Suivi de séries par les clients (*Mes séries* `/my/library/series`, boutons sur la page série du shop et la fiche album) ; à la mise en vente, assistant « X clients seront prévenus » avec aperçu, email « Bonne nouvelle — … est disponible ! » aux abonnés et aux wishlists, une fois par album, trace dans le chatter *(absorbe US-048)* — 2026-11-08 |
| US-070 | Scan d'ISBN à la caméra : bouton *Scanner* sur l'ajout d'une BD du portail, widget `isbn_scan` en back-office mobile (ISBN album / édition, recherche multi-sources) ; EAN-13 978/979 uniquement, repli sur la saisie manuelle — 2026-11-08 |

### E7 — IA (livré)

| US     | Titre                                                                    |
| ------ | ------------------------------------------------------------------------ |
| US-026 | Paramètres IA (*Bandes Dessinées → Intelligence artificielle*) : fournisseur Claude / OpenAI, clés en `ir.config_parameter`, modèles (défaut `claude-sonnet-5-5`), langue, *Tester la connexion IA* ; service `comic.ai.service` (SDK importés à la demande, erreurs claires, repli serveur en cas de refus) — 2026-11-09 |
| US-027 | *Générer le synopsis* (album / édition, gestionnaires) : prévisualisation modifiable, Appliquer / Régénérer / Annuler, confirmation avant remplacement, trace chatter — 2026-11-09 |
| US-028 | *Traduire le synopsis* (fr / nl / en / de) : remplace le synopsis ou l'écrit sur l'édition de la langue cible — 2026-11-09 |
| US-090 | Synopsis vides remplis en tâche de fond (séries et albums) : cron désactivé par défaut, lots réglables, mention « Généré automatiquement par IA », case `synopsis_auto` + filtre « à relire », arrêt à la première erreur du fournisseur ; aussi synopsis de série dans l'assistant — 2026-11-10 |
| US-091 | Onglet *Biographie* de l'auteur et *Histoire de la maison* de l'éditeur : texte IA (même assistant : aperçu, confirmation, trace « à relire »), listes « A souvent travaillé avec » (co-auteurs, albums en commun) et « Auteurs principaux de la maison » — 2026-11-10 |
| US-029 | *Découvrir de nouvelles BD* : profil 4★ modifiable, 10–15 suggestions hors séries connues, vérification sur les sources, ajout en wishlist ; portail `/my/library/discover` (`comic_ai_shop`, limite quotidienne, création modérée) — 2026-11-09 |

### E8 — Qualité & publication OCA (livré)

| US      | Titre                                                                  |
| ------- | ---------------------------------------------------------------------- |
| US-030b | Pre-commit OCA *(numéroté US-030 dans V3, doublon levé)*               |
| US-032  | Tests unitaires                                                        |
| US-033  | Documentation et README                                                |
| US-055  | Refactor canonique : tests et validation                               |
| US-059  | Fichier LICENSE LGPL-3                                                 |
| US-060  | README format OCA par module                                           |
| US-061  | `__manifest__.py` au format OCA strict                                 |
| US-062  | Tests unitaires CI-compatibles (310 tests, local et CI)                |
| US-063  | GitHub Actions : tests + pre-commit                                    |
| US-085  | CI limitée à nos modules (~3 min), README / documentation à jour — 2026-11-05 / 06 |

### Abandonné ou non attribué

| US     | Statut                                                                    |
| ------ | ------------------------------------------------------------------------- |
| US-013 | Repris en US-065 (livré)                                                  |
| US-048 | Fusionné dans US-069 (notification des clients à la mise en vente)        |
| US-021 | ❌ Source BDGest (scraping) — module `comic_bdgest` supprimé le 2026-06-02 |
| US-038 | Numéro jamais attribué                                                    |
