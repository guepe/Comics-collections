# USER STORIES V3 — Ce qui reste à faire

> Projet Odoo 19 — Comic Collection + Comic Shop
> Seules les US ouvertes (ou partiellement ouvertes) sont listées ici.
> Légende : ✅ Terminé · ⏳ À faire · 🟠 Priorité moyenne · 🟡 Priorité basse

---

## 🗺️ Table des matières

| US | Titre | Priorité |
|---|---|---|
| US-035 | ✅ Scaffold comic_shop — désinstallation sécurisée | 🟡 |
| US-042 | ✅ Intégration POS (caisse) | 🟠 |
| US-044 | ✅ Ajout BD hors catalogue (portail client) | 🟠 |
| US-045 | ✅ Import POS → bibliothèque (livré dans US-042) | 🟠 |
| US-046 | Rapport "BD non vendues les plus suivies" | 🟡 |
| US-047 | Rapport "Séries et auteurs à référencer" | 🟡 |
| US-048 | Notification CRM à la mise en catalogue | 🟡 |
| US-049 | Dashboard commerçant — vue marché | 🟡 |
| US-026 | Configuration connecteurs IA (module comic_ai) | 🟡 |
| US-027 | Génération synopsis par IA | 🟡 |
| US-028 | Traduction synopsis par IA | 🟡 |
| US-029 | Découverte IA par profil de goûts | 🟡 |

---

## PHASE 7 — Catalogue & Shop

---

**US-035 — Scaffold `comic_shop` — critère restant** ✅

```
- [x] comic_shop désinstallable sans perte de données dans comics_collections
      (vérifier que la désinstallation ne supprime pas les comic.edition, comic.work, etc.)
```

---

**US-042 — Intégration POS (caisse)** ✅

```
En tant que commerçant en magasin
Je veux scanner l'ISBN d'une BD et la retrouver directement à la caisse
Afin de gérer les ventes physiques efficacement

Contexte technique :
  Les produits BD sont des product.template liés à comic.edition via comic_edition_id.
  Le barcode du produit = isbn_13 de l'édition principale (synchro automatique).
  À la vente POS : créer/mettre à jour comic.customer.album si client identifié.

Critères d'acceptance :
- [x] Les produits liés à une comic.edition sont disponibles dans le POS
        (available_in_pos=True syncé dans _sync_to_product et action_create_product)
- [x] Recherche par ISBN dans le POS (scan code-barres = barcode du product.template)
        (barcode syncé depuis isbn_13 via _sync_to_product)
- [x] Affichage dans le POS : couverture miniature, titre, série, tome, prix
        (image_1920 + name format "Série — Titre (T1)" syncés via _sync_to_product)
- [x] À la validation d'une vente POS, si client identifié :
        créer (ou mettre à jour) un comic.customer.album avec source = achete_ici
        (pos.order.action_pos_order_paid() hooké dans comic_pos_order.py)
- [x] Catégorie POS "Bandes Dessinées" créée automatiquement à l'installation
        (pos.category record dans comic_shop_data.xml)

Fichiers concernés :
  comic_shop/models/comic_edition.py  — available_in_pos + pos_categ_ids dans sync
  comic_shop/models/comic_serie.py    — idem dans action_create_products_bulk/from_isbn
  comic_shop/models/comic_pos_order.py — hook action_pos_order_paid
  comic_shop/data/comic_shop_data.xml — catégorie POS
```

---

## PHASE 8 — Bibliothèque Client

---

**US-044 — Ajout d'une BD hors catalogue à la bibliothèque** ✅

```
En tant que client connecté sur le portail
Je veux ajouter dans ma bibliothèque une BD que je n'ai pas achetée dans le shop
Afin de centraliser toute ma collection, pas seulement mes achats ici

Contexte technique :
  Le portail est sur /my/library (comic_shop/controllers/portal.py).
  La recherche BD passe par ComicDataAggregator (comic_datasource/aggregator.py).
  L'import crée comic.work + comic.edition + comic.isbn si l'ISBN est inconnu,
  ou retrouve l'édition existante si l'ISBN est déjà en base.
  Le résultat crée un comic.customer.album (partner_id, edition_id, source).

Critères d'acceptance :
- [x] Bouton "Ajouter une BD" sur la page /my/library (barre de filtres + état vide)
- [x] Formulaire en 2 étapes :
        GET  /my/library/add          — formulaire de recherche
        POST /my/library/add/search   — résultats (local DB + ComicDataAggregator)
        POST /my/library/add/confirm  — sélection + source + état + note → création
- [x] Si ISBN trouvé dans comic.isbn → réutilise l'édition existante
- [x] Si ISBN inconnu → crée comic.work + comic.edition + comic.isbn sans product_tmpl_id
        (télécharge la couverture si cover_url disponible)
- [x] Message flash "X a été ajouté à votre bibliothèque" (via request.session)
- [x] Si l'édition est déjà dans la bibliothèque du client → message d'avertissement
        + bouton "Mettre à jour" (force_update=1) sans créer de doublon

Fichiers modifiés :
  comic_shop/__manifest__.py                  — ajout dépendance comic_datasource
  comic_shop/controllers/portal.py            — 3 nouvelles routes + 4 helpers
  comic_shop/views/portal_library_templates.xml — bouton + template portal_library_add
```

---

**US-045 — critère restant** ✅

```
- [x] Idem import auto bibliothèque pour les ventes POS — livré dans US-042
        (pos.order.action_pos_order_paid() → _add_comics_to_library() dans comic_pos_order.py)
```

---

## PHASE 9 — Business Intelligence commerçant

---

**US-046 — Rapport "BD non vendues les plus suivies"** ⏳ 🟡

```
En tant que commerçant
Je veux voir quelles BD présentes dans les bibliothèques clients ne sont pas dans mon catalogue
Afin d'identifier les titres à référencer en priorité

Contexte technique :
  comic.customer.album.edition_id.work_id.serie_id
  "hors catalogue" = edition_id.product_tmpl_id = False
  Groupement par comic.serie, trié par nb clients distincts DESC.
  Vue ir.ui.view de type list avec group_by, pas un rapport QWeb.

Critères d'acceptance :
- [ ] Vue rapport accessible depuis menu back-office "Rapports > Bibliothèques clients"
- [ ] Colonnes : série / nb clients distincts / nb éditions concernées / source principale
        Filtré sur : edition_id.product_tmpl_id = False
        Groupé par : work_id.serie_id, trié par nb_clients DESC
- [ ] Filtre par période (date_ajout des customer.album)
- [ ] Filtre par source (achete_ailleurs uniquement, ou tous)
- [ ] Export CSV du rapport (bouton standard Odoo)
- [ ] Décoration visuelle : vert si > 5 clients, orange si 2–5, gris si 1

Modèle à créer : comic.customer.album.report (ir.ui.view + ir.actions.act_window)
  ou vue SQL read-only (_auto = False) si agrégation complexe.
```

---

**US-047 — Rapport "Séries et auteurs à référencer"** ⏳ 🟡

```
En tant que commerçant
Je veux voir les auteurs les plus suivis par mes clients pour des BD hors catalogue
Afin de prendre des décisions d'achat basées sur la demande réelle

Contexte technique :
  Traversée : comic.customer.album → edition_id → work_id → auteur_line_ids → partner_id
  "hors catalogue" = edition_id.product_tmpl_id = False

Critères d'acceptance :
- [ ] Rapport "Top auteurs hors catalogue" :
        Groupé par work_id.auteur_line_ids.partner_id
        Filtré sur : edition_id.product_tmpl_id = False
        Colonnes : auteur / rôle principal / nb clients / nb séries concernées
- [ ] Rapport "Top séries hors catalogue" (complémentaire US-046, vue auteurs)
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

Contexte technique :
  Déclencheur : action_create_product() sur comic.edition (comic_shop/models/comic_edition.py).
  Clients concernés : comic.customer.album filtrés sur edition_id + source != achete_ici.
  Email template Odoo (mail.template) + message_post sur le chatter de l'édition.

Critères d'acceptance :
- [ ] Lors de la création d'un produit depuis une comic.edition :
        si des clients ont cette édition en bibliothèque (source != achete_ici)
        → popup : "X clients ont déjà cet album. Voulez-vous les notifier ?"
- [ ] Si confirmation : envoi email template "Bonne nouvelle — [Titre] est disponible !"
        avec lien vers la page produit du webshop
- [ ] Wizard de prévisualisation avant envoi (liste des clients concernés, aperçu email)
- [ ] Log dans le chatter de la comic.edition : date, nb destinataires
- [ ] Option configurable : créer une opportunité CRM (crm.lead) par client notifié
```

---

**US-049 — Dashboard commerçant — vue marché** ⏳ 🟡

```
En tant que commerçant
Je veux un tableau de bord synthétique sur la demande marché de mes clients
Afin d'avoir une vue d'ensemble pour mes décisions d'achat

Contexte technique :
  Vue Odoo dashboard (ir.ui.view type=qweb ou ir.actions.act_window kanban).
  Données issues de comic.customer.album + comic.edition + comic.work + comic.serie.
  Dépend de US-046 et US-047 pour les vues sous-jacentes.

Critères d'acceptance :
- [ ] Accessible depuis "Rapports > Vue Marché"
- [ ] KPI (stat buttons) :
        Nb clients avec une bibliothèque active
        Nb éditions hors catalogue dans les bibliothèques
        Nb séries hors catalogue distinctes
        Taux de couverture : % des éditions des bibliothèques vendues par le shop
- [ ] Graphique barres horizontales : Top 10 séries hors catalogue
- [ ] Graphique barres : Top 10 auteurs hors catalogue
- [ ] Graphique ligne : évolution du nb d'ajouts bibliothèque par semaine
- [ ] Tableau : séries avec le plus fort ratio "clients intéressés / tomes vendus"
- [ ] Filtre par période et par genre
```

---

## PHASE 4a — Module comic_ai (nouveau)

> Nouveau module, dépend de `comics_collections` uniquement.
> Providers : Anthropic (claude-sonnet-4-6) et OpenAI (gpt-4o) — configurable en settings.
> Clés API en `ir.config_parameter` — jamais en dur.
> Wizard `comic.ai.wizard` s'ouvre depuis la fiche `comic.edition`.

---

**US-026 — Configuration des connecteurs IA** ⏳ 🟡

```
En tant qu'administrateur
Je veux configurer les API Claude et OpenAI dans les paramètres Odoo
Afin de pouvoir utiliser l'IA pour enrichir mes fiches BD

Contexte technique :
  res.config.settings hérité dans comic_ai/models/res_config_settings.py.
  Clés stockées en ir.config_parameter (champs password, non exportés).

Critères d'acceptance :
- [ ] Section "IA — Bandes Dessinées" dans Paramètres > Configuration
- [ ] Sélecteur provider actif : Claude (Anthropic) / OpenAI
- [ ] Champ clé API Claude (password) → ir.config_parameter 'comic_ai.claude_api_key'
- [ ] Champ modèle Claude (défaut: claude-sonnet-4-6)
- [ ] Champ clé API OpenAI (password) → ir.config_parameter 'comic_ai.openai_api_key'
- [ ] Champ modèle OpenAI (défaut: gpt-4o)
- [ ] Langue de génération par défaut : fr / nl / en
- [ ] Bouton "Tester la connexion IA" → appel ping à l'API, message succès/erreur
```

---

**US-027 — Génération de synopsis par IA** ⏳ 🟡

```
En tant que collectionneur / commerçant
Je veux générer automatiquement un synopsis pour une édition BD via l'IA
Afin d'enrichir la fiche sans rédiger manuellement

Contexte technique :
  Bouton sur comic.edition (managers uniquement), ouvre comic.ai.wizard.
  Prompt inclut : titre_canonique, serie_id.name, tome, auteur_line_ids, editeur_id, synopsis existant.
  Prompts dans comic_ai/prompts/prompt_synopsis.txt.

Critères d'acceptance :
- [ ] Bouton "✨ Générer le synopsis" sur la fiche comic.edition (managers uniquement)
- [ ] Wizard de prévisualisation : champ Html readonly + boutons Appliquer / Régénérer / Annuler
- [ ] Appliquer → écrit dans comic.edition.synopsis
- [ ] Indicateur de chargement pendant la génération (spinner)
- [ ] Gestion d'erreur : clé API invalide, timeout, quota → message utilisateur clair
- [ ] Log dans le chatter de la comic.edition : provider utilisé + date
```

---

**US-028 — Traduction du synopsis par IA** ⏳ 🟡

```
En tant que collectionneur / commerçant
Je veux traduire le synopsis d'un album dans une autre langue
Afin de gérer une collection multilingue (FR/NL/EN)

Contexte technique :
  Action supplémentaire dans comic.ai.wizard (action_type = 'translate').
  Prompt dans comic_ai/prompts/prompt_translate.txt.
  La traduction peut cibler comic.edition.synopsis ou une nouvelle édition (autre langue).

Critères d'acceptance :
- [ ] Action "Traduire le synopsis" dans le wizard IA (action_type = 'translate')
- [ ] Sélecteur de langue cible (fr / nl / en / de)
- [ ] Prévisualisation avant application
- [ ] Appliquer → remplace ou complète comic.edition.synopsis selon la langue
- [ ] Gestion d'erreur identique à US-027
```

---

**US-029 — Découverte IA par profil de goûts** ⏳ 🟡

```
En tant que collectionneur
Je veux que l'IA me suggère des séries inconnues basées sur mes séries préférées
Afin de découvrir de nouvelles BD correspondant à mon profil de goût

Contexte technique :
  Distinct de US-034 (suivi de séries connues — déjà livré).
  Profil de goût = comic.customer.album filtrés note ≥ 4.0.
  L'IA reçoit genres, auteurs, titres des séries appréciées → retourne 10-15 suggestions.
  Suggestions ajoutables en wishlist (comic.customer.album avec dans_wishlist=True).
  Prompt dans comic_ai/prompts/prompt_suggest_similar.txt.

Critères d'acceptance :
- [ ] Bouton "Découvrir de nouvelles BD" accessible depuis /my/library (portail)
        ou depuis le menu back-office Bandes Dessinées > Ma Collection
- [ ] Wizard : affiche les séries notées ≥ 4★ comme profil (liste modifiable)
- [ ] L'IA retourne 10-15 suggestions : titre, auteur, genre, raison
- [ ] Filtre automatique : exclut les séries déjà dans la collection ou la wishlist
- [ ] Sélection manuelle des suggestions qui intéressent l'utilisateur
- [ ] Ajout en wishlist des suggestions sélectionnées
- [ ] Bouton "Vérifier sur le datasource" par suggestion (évite les hallucinations IA)
- [ ] Gestion d'erreur : clé API invalide ou timeout → message clair
```
