# Journal des modifications — Odoo Comic Collection

> Format : date · module · fichier · description du changement + raison
> Odoo version : **19.0** (docker `odoo:latest`, image du 2026-03-05)
> À maintenir à jour à chaque session de travail.

---

## 2026-05-21 — US-053 : Vues back-office + correctifs import et templates

### US-053 — Vues back-office comic.work / comic.edition / comic.pret ✅

**comics_collections/models/comic_work.py**
- Ajout champs computed+stored `nb_editions` (depends `edition_ids`) et `nb_auteurs` (depends `auteur_line_ids`)
- Ajout méthode `action_view_editions()` pour le smartbutton de la fiche work

**comics_collections/models/comic_edition.py**
- Ajout champ computed+stored `nb_isbn` (depends `isbn_ids`)

**comics_collections/models/comic_serie.py**
- Ajout méthode `action_view_works()` pour le smartbutton de la fiche série

**comics_collections/views/comic_work_views.xml** (réécrit)
- List : colonnes série, tome, titre, nb_editions, nb_auteurs
- Form : smartbutton Éditions, onglets Auteurs + Éditions (avec nb_isbn)
- Search : filtre auteur (via auteur_line_ids.partner_id), slug, wikidata_id, filtre "sans édition"

**comics_collections/views/comic_edition_views.xml** (nouveau fichier)
- List : work, langue, éditeur, date, format, nb_pages, nb_isbn
- Form : image couverture, group champs + liens achat, onglets ISBNs + Synopsis, chatter
- Search : filtre par ISBN (ilike sur isbn_ids.isbn_13), group-by langue/éditeur/format

**comics_collections/views/comic_pret_views.xml** (nouveau fichier)
- List : colorée (rouge = en retard, vert = retourné), avec decoration-danger/success
- Form : edition_id (album prêté), partenaire, dates, retourne, notes, chatter
- Search : filtres "en cours / retournés / en retard", action par défaut "en cours"

**comics_collections/views/comic_serie_views.xml**
- Smartbutton "Œuvres" (nb_works_total) sur la fiche série → ouvre comic.work filtré par série

**comics_collections/views/comic_menu.xml**
- Ajout entrée "Prêts" (sequence 30) dans Ma Collection

**comics_collections/__manifest__.py**
- Déclaration des nouveaux fichiers `comic_edition_views.xml` et `comic_pret_views.xml`

### Correctifs session

**comics_collections/wizards/comic_import_wizard.py**
- `action_import` : chaque ligne wrappée dans `self.env.cr.savepoint()` pour éviter que l'exception d'une ligne n'avorte la transaction entière (erreur `InFailedSqlTransaction`)
- `_get_or_create_work` (nouvelle méthode) : tente le create dans un savepoint interne ; sur contrainte UNIQUE `(serie_id, tome)`, fait un fallback `search` au lieu de planter
- `_normalise_header` : ajout alias BDGest (`num→tome`, `dl→date_parution`, `lu→etat_lecture`, `wishlist→dans_wishlist`, `table→_table`) + colonnes à ignorer
- `_normalise_import_rows` : filtre sur `_table == 'album'` pour exclure les lignes REVUE/PARABDE du CSV BDGest
- `_parse_reading_state` : accepte `'0'` → `non_lu` et `'1'` → `lu` (format BDGest)
- `_sync_customer_album` : crée/met à jour `comic.customer.album` pour l'utilisateur courant

**comic_shop/views/website_sale_shop_templates.xml**
- `shop_serie_detail_page` : `albums` → `editions` (le contrôleur envoie `comic.edition`, pas `comic.album`)
- Page auteur : boucle `album.*` → `edition.work_id.*` (`serie_id`, `tome`, `name` → `titre_canonique`)

---

## 2026-05-21 — US-057 : Façade UX album/tome

### US-057 — Cohérence vocabulaire utilisateur ✅

**comic_shop/views/website_sale_templates.xml**
- "Informations sur l'édition" → "Informations BD"

**comic_shop/views/product_template_views.xml**
- Smartbutton "Édition BD" → "Album BD"
- Bouton "Sync depuis édition" → "Sync depuis album" + confirmation mise à jour

**comic_shop/views/portal_library_templates.xml**
- Template renommé "Détail album — Ma Bibliothèque"
- Placeholder "Mes notes sur cet album…"
- Confirm "Supprimer cet album de votre bibliothèque ?"

**comics_collections/views/comic_menu.xml** (réécrit)
- Menu "Ma Collection" : Séries + Albums/Tomes + Prêts + Import (utilisateurs)
- Entrée "Albums / Tomes" remplace "Œuvres" pour les utilisateurs standard
- Nouveau sous-menu "Configuration > Référentiel avancé" (managers uniquement)
  avec Œuvres et Éditions dedans

**comics_collections/views/comic_work_views.xml**
- Action `action_comic_work` renommée "Albums / Tomes"

**comics_collections/views/comic_serie_views.xml**
- Onglet "Œuvres" → "Albums / Tomes" sur la fiche série
- Colonne "Éditions" (nb_editions) dans la liste inline au lieu de many2many_tags

**CLAUDE.md**
- Règle 14 ajoutée : vocabulaire technique (comic.work/edition) vs utilisateur (album/tome)

---

## 2026-05-21 — US-054 : Adaptation comic_shop (complétion)

### US-054 — Champs manquants + sync triggers ✅

**comic_shop/models/product_template.py**
- Ajout champ `comic_work_id` (Many2one → comic.work, compute sur `comic_edition_id.work_id`, store=True)
- Utile pour les vues back-office et les filtres search

**comic_shop/models/comic_album.py** (inherit comic.edition)
- `_SYNC_TRIGGER_FIELDS` étendu : ajout `isbn_ids` (barcode) et `work_id` (nom produit)
- Le nom du produit se re-synchronise automatiquement si le titre canonique ou le tome de l'œuvre change

**comic_shop/models/comic_customer_album.py**
- Ajout champ `work_id` (Many2one → comic.work, compute sur `edition_id.work_id`, store=True, index=True)
- Permet filtres et groupements par œuvre dans les vues back-office

_Note : le reste de US-054 était déjà implémenté lors des sessions précédentes :_
_`comic_edition_id` sur product.template, smartbuttons série, portal.py, webshop templates,_
_comic_sale_order.py, et la contrainte UNIQUE sur comic.customer.album._

---

## 2026-05-21 — US-052 : Adaptation datasources et import

### US-052 — Entrées de données vers work / edition / isbn ✅

**comic_datasource** — Adaptation des créations ORM :
- Le wizard de recherche datasource déduplique maintenant dans l'ordre `comic.isbn`
  → `comic.edition` → `comic.work` avant de créer une nouvelle édition.
- Si le couple série/tome existe déjà, l'import crée une `comic.edition` liée au
  `comic.work` existant au lieu de recréer une œuvre.
- Les auteurs issus des sources sont ajoutés sur `comic.work.auteur.line` sans écraser
  les lignes existantes.
- L'enrichissement quotidien cible `comic.edition` via `_cron_update_editions()`, avec
  alias de compatibilité `_cron_update_albums()`.
- La vue héritée datasource est rattachée au formulaire `comic.edition` et rechargée
  dans le manifest.

**comics_collections / import CSV-XLS-XLSX** — Import canonique :
- Colonnes cibles alignées sur le nouveau modèle : `serie_name`, `tome`,
  `titre_canonique`, `langue`, `editeur`, `date_parution`, `nb_pages`, `isbn`,
  `format`, `scenariste`, `dessinateur`, `coloriste`, `genre`.
- Déduplication import alignée sur datasource : ISBN existant d'abord, puis œuvre
  série/tome, puis création `comic.work` + `comic.edition` + `comic.isbn`.
- Les anciens alias (`titre_album`, exports BDGest, colonne `Contenu`) restent supportés.

**USER_STORIES_V2.md** — US-052 cochée.

**Tests** — Tests purs du wizard d'import alignés sur `titre_canonique` et sur la
normalisation `langue` / `format`.

---

## 2026-05-21 — US-050 : Analyse + décisions architecturales + stratégie déduplication

### US-050 — Inventaire + ERD + stratégie anti-doublons ✅

**Inventaire exhaustif** réalisé par grep récursif sur toute la codebase.
Fichiers référençant `comic.album` ou `comic.album.auteur.line` : 35 fichiers dans 4 modules
(`comics_collections`, `comic_datasource`, `comic_bdgest`, `comic_shop`) + 2 outils scripts.

**CLAUDE.md** — Section "ERD final — Architecture canonique (Phase 10)" ajoutée :
- Diagramme ASCII complet : `comic.serie` → `comic.work` → `comic.edition` → `comic.isbn`
- `comic.work.auteur.line` (remplace `comic.album.auteur.line`)
- `comic.customer.album` mis à jour : `edition_id` + `work_id` computed
- `comic.pret` mis à jour : `edition_id` remplace `album_id`
- Règles de normalisation de titre documentées (unicodedata + articles + suffixes catalogue)
- Tableau algorithme de détection doublons (SequenceMatcher seuil 0.85)

**USER_STORIES_V2.md** — Toutes les cases US-050 cochées + inventaire complet inséré dans le corps de l'US.

**Décisions architecturales validées :**
- Option A : `product.template` lié à `comic.edition` (1 édition = 1 SKU)
- `comic.pret.edition_id` (on prête un exemplaire physique d'une édition)
- `comic.customer.album.edition_id` + `work_id` computed
- `comic.work.auteur.line` : authorship sur l'œuvre, pas l'édition
- Slug : `{serie.slug}-t{tome:02d}` (ex. `thorgal-t05`)
- Webshop : série → works → édition de référence (fr / date la plus récente)
- Algorithme déduplication : `difflib.SequenceMatcher` (stdlib, seuil 0.85, pas de dépendance externe)
- Cas incomplets : `comic.work` sans édition et `comic.edition` sans ISBN sont valides
- Façade UX validée : conserver le vocabulaire "album / tome" dans les parcours courants ;
  réserver "Œuvre / Édition / ISBN" au référentiel avancé et aux vues techniques (détaillé en US-057)

---

## 2026-05-20 (suite 8) — Enrichissement données démo (Thorgal + Complainte)

### Données démo — `comics_collections/demo/comic_demo.xml`

**Contexte :** Le script `tools/load_demo_series.py` contenait des données structurées pour
Thorgal et Complainte des Landes perdues. Ces données ont été migrées vers le fichier de démo
XML officiel (`demo/` + déclaration dans le manifest) pour être chargées automatiquement lors
de l'installation avec l'option "Charger les données de démonstration".

**Ajouts :**

- **9 auteurs** (res.partner) : `partner_rosinski` (Grzegorz Rosinski), `partner_sente`
  (Yves Sente), `partner_dorison` (Xavier Dorison), `partner_yann` (Yann), `partner_vignaux`
  (Fred Vignaux), `partner_dufaux` (Jean Dufaux), `partner_delaby` (Philippe Delaby),
  `partner_tillier` (Béatrice Tillier), `partner_teng` (Paul Teng).

- **1 éditeur** : `editeur_le_lombard` (Le Lombard, Belgique).

- **Série Thorgal** (`serie_thorgal`) : genre aventure, éditeur Le Lombard, avec synopsis.
  **29 albums** (T5, T10–T12, T15–T16, T18, T20–T22, T24–T43) avec `auteur.line` par arc :
  - Scénariste : Van Hamme (T5–T29) → Sente (T30–T34) → Dorison (T35) → Yann (T36–T43)
  - Dessinateur : Rosinski (T5–T36) → Vignaux (T37–T43)

- **Série Complainte des Landes perdues** (`serie_complainte`) : genre fantastique, éditeur
  Dargaud. **15 albums** (T1–T11, T13–T16) avec `auteur.line` par cycle :
  - Scénariste : Dufaux (tous les tomes)
  - Dessinateur : Rosinski (T1–T4) → Delaby (T5–T8) → Tillier (T9–T11) → Teng (T13–T16)

**Conversion ISBN-10 → EAN-13 :** Les albums antérieurs à 2007 (ISBN-10 uniquement) ont eu
leur EAN-13 calculé manuellement : préfixe "978" + 9 premiers chiffres + chiffre de contrôle
EAN-13 (algorithme alternance ×1/×3).

---

## 2026-05-20 (suite 7) — Icône portail Ma Bibliothèque BD

### Asset — Icône SVG bibliothèque client

**Fichiers modifiés :**
- `comic_shop/static/src/img/icon_library.svg` :
  - remplacement par un SVG standalone en `viewBox="0 0 100 100"` ;
  - dessin d'une étagère de BD vue de face avec 4 albums, couleurs vives dont le violet
    Odoo `#875A7B`, planche bois et badge doré `#F5C518` ;
  - suppression des commentaires et de tout texte visuel pour garder un asset pur et lisible
    en petite taille ;
  - validation XML avec `xmllint --noout`.

---

## 2026-05-20 (suite 6) — US-045 auto-ajout bibliothèque à l'achat + correctif CSS assets + bugs portail

### US-045 — Import automatique depuis les commandes client ✅

**Fichiers créés :**
- `comic_shop/models/comic_sale_order.py` : hérite `sale.order`, override `action_confirm()`.
  - `_add_comics_to_library()` : vérifie `partner.comic_auto_library`, puis pour chaque ligne
    liée à un `comic.album` : créer ou mettre à jour `comic.customer.album` (source, sale_order_line).
  - `_notify_customer_library_added()` : `message_post` sur la commande avec `partner_ids=[partner.id]`
    → envoie un email au client listant les BD ajoutées avec lien "Voir ma bibliothèque".
- `comic_shop/models/res_partner.py` : champ `comic_auto_library` (Boolean, default=True) sur
  `res.partner` — permet au client de désactiver l'ajout automatique.
- `comic_shop/models/__init__.py` : ajout `from . import comic_sale_order` et `from . import res_partner`.

**Portail (/my/library) :**
- `comic_shop/controllers/portal.py` :
  - Route POST `/my/library/preferences` : écrit `comic_auto_library` sur `request.env.user.partner_id`
    (sudo après vérification implicite via `request.env.user`).
  - Deux bugs corrigés :
    1. `_prepare_home_portal_values` ne filtrait pas par partner → compteur affichait tous les clients
    2. `my_library()` — domain ne filtrait pas par `partner_id` → montrait les albums de TOUS les clients
- `comic_shop/views/portal_library_templates.xml` : toggle switch "Ajouter automatiquement mes achats"
  (form POST vers `/my/library/preferences`, `onchange="this.form.submit()"`), inséré juste avant
  les filtres dans la page `/my/library`.

### Correctif assets CSS (ValueError: External ID not found)

**Cause :** `website_sale_shop_templates.xml` contenait un template héritant de
`website.assets_frontend` — cet ID XML n'existe pas en Odoo 19 → upgrade bloqué.

**Fix :**
- `comic_shop/views/website_sale_shop_templates.xml` : suppression du template `shop_bd_assets_css`.
- `comic_shop/static/src/css/comic_shop.css` : nouveau fichier CSS avec `object-fit:contain`
  pour les images de la grille shop Odoo.
- `comic_shop/__manifest__.py` : ajout clé `assets` → `web.assets_frontend` →
  `'comic_shop/static/src/css/comic_shop.css'`. Méthode correcte pour injecter du CSS en Odoo 19.

---

## 2026-05-20 (suite 5) — US-043 bibliothèque portail + menus shop + correctifs sidebar/button_box

### US-043 — Espace bibliothèque client sur le portail ✅

**Fichiers créés :**
- `comic_shop/controllers/portal.py` : hérite `CustomerPortal`, 4 routes :
  - `GET /my/library` — index avec filtres (`all/collection/wishlist/reading`), tri (`date/serie/title`),
    toggle vue (`kanban/list`), compteurs albums/séries/en cours.
  - `GET /my/library/<id>` — fiche détail, vérifie `record.partner_id == request.env.user.partner_id`.
  - `POST /my/library/<id>/update` — met à jour `etat_lecture`, `note`, `commentaire`,
    `dans_collection`, `dans_wishlist` via `record.sudo().write(vals)`.
  - `POST /my/library/<id>/remove` — supprime via `record.sudo().unlink()`
    (access CSV interdit `unlink` portal → sudo après vérification ownership manuelle).
- `comic_shop/views/portal_library_templates.xml` : 3 templates QWeb :
  - `portal_my_home_library` : hérite `portal.portal_my_home` avec le pattern Odoo 19
    (`portal_client_category_enable` + injection dans `div#portal_client_category` via
    `portal.portal_docs_entry`). Pas le pattern naïf `//div[hasclass('o_portal_docs')]`.
  - `portal_library_index` : compteurs colorés, filtres-tabs, sort select + toggle grille/liste,
    vue kanban (cartes couverture + badge état + étoiles) et vue liste (table Bootstrap).
  - `portal_library_detail` : info album (auteurs, date, pages), formulaire POST avec CSRF,
    champs `etat_lecture` (select), `note` (number 0–5 step 0.5), checkboxes, textarea.
    Bouton "Supprimer" avec `onsubmit="return confirm(…)"`.

**Fichiers modifiés :**
- `comic_shop/controllers/__init__.py` : ajout `from . import portal`.
- `comic_shop/__manifest__.py` : ajout `'views/portal_library_templates.xml'`.

**Erreurs rencontrées et solutions :**
1. **Template non chargé silencieusement** : upgrade via XML-RPC après modification du manifest
   ne recharge pas les nouveaux fichiers si le worker Odoo garde une copie en mémoire.
   Solution : `docker restart odoo-web` complet, puis l'upgrade suivant charge le fichier.
2. **`portal_my_home` pattern Odoo 19** : le pattern simple `//div[hasclass('o_portal_docs')]`
   position="inside" ne fonctionne pas — Odoo 19 utilise des catégories nommées
   (`portal_client_category`, `portal_alert_category`…). Il faut activer la catégorie via
   `<t t-set="portal_client_category_enable" t-value="True"/>` puis injecter dedans.
3. **`t-attf-onchange` oublié** : le `onchange` du select de tri utilisait `{{ filter }}`
   sans `t-attf-` → variables non interpolées. Corrigé en `t-attf-onchange`.

### Correctifs menus shop et sidebar

**Menu website "Catalogue BD" :**
- `comic_shop/data/comic_shop_data.xml` : ajout de 4 `website.menu` records (noupdate=1) :
  "Catalogue BD" (parent = Top Menu), "Séries", "Auteurs", "Maisons d'édition" en sous-items.

**Sidebar filtres auteurs :**
- `comic_shop/views/website_sale_shop_templates.xml` : police des auteurs passée de `small`
  (0.875em dans un contexte déjà petit) à `0.85rem` fixe. Cap à 8 auteurs + lien "+ N de plus".
  En-tête avec "Tous →" vers `/shop/auteurs`. Boutons bas de sidebar : Séries + Auteurs + Éditeurs.

### Correctif button_box série (double button_box)

**Cause :** `comic_datasource` et `comic_shop` créaient chacun un `<div name="button_box">`
via leur propre xpath, résultant en deux button_boxes séparés dans la fiche série.

**Fix :**
- `comics_collections/views/comic_serie_views.xml` : ajout `<div name="button_box" class="oe_button_box"/>` vide dans la vue de base (premier enfant de `<sheet>`).
- `comic_datasource/views/comic_datasource_serie_inherit_views.xml` : xpath changé en
  `//div[@name='button_box']` position="inside".
- `comic_shop/views/comic_serie_views.xml` : idem, plus injection des champs invisibles
  via `//div[@name='button_box']` position="after".

### Correctif groupes button_box série invisibles

**Cause :** boutons `action_view_products` et `action_create_products_from_isbn` portaient
`groups="comics_collections.group_comic_manager"` — admin n'étant dans aucun groupe comic,
les boutons étaient invisibles pour tout le monde en dev.
**Fix :** suppression des `groups=` sur les stat buttons (sécurité assurée par `invisible=` et
le droit d'accès modèle). Correction aussi du xpath pour positionner le button_box comme premier
enfant de `<sheet>` (avant `image_couverture`).

---

## 2026-05-20 (suite 4) — Sync image album↔produit, smartbuttons, création produits en masse, import démo

### Correctif — ValueError ORM `order` avec dot-notation dans `shop_auteur_detail`

**Cause :** `order='album_id.serie_id, album_id.tome'` n'est pas une syntaxe ORM valide (dot-notation uniquement autorisée dans les domaines `search`, pas dans `order=`).
**Fix :** Suppression du `order=` dans le `search()`, remplacement par `.sorted(key=lambda l: (l.album_id.serie_id.name or '', l.album_id.tome or 0))` en Python.
- Fichier : `comic_shop/controllers/main.py` — méthode `shop_auteur_detail`

### Amélioration US-037 — Sync album → produit étendue aux images et métadonnées

**Avant :** `_SYNC_TRIGGER_FIELDS` ne contenait que `isbn` → seul un changement d'ISBN déclenchait la sync auto.
**Après :** Jeu de champs élargi : `{'isbn', 'image_couverture', 'name', 'tome', 'serie_id', 'synopsis'}`.
- Fichier : `comic_shop/models/comic_album.py` — constante `_SYNC_TRIGGER_FIELDS` + `write()`

### US-037b — Smartbutton "Album BD" et bouton "Sync depuis album" sur product.template

Fichiers créés / modifiés :
- `comic_shop/views/product_template_views.xml` *(nouveau)* :
  - Smartbutton `fa-book` "Album BD" dans le button_box → ouvre la fiche album (invisible si pas d'album lié).
  - Bouton `<header>` "Sync depuis album" avec confirmation → force `_sync_to_product()`. Restreint au groupe `comic_manager`.
  - Champ `comic_album_id` invisible pour le contrôle de visibilité.
  - **Note Odoo 19 :** `t-out` interdit dans les vues backend → remplacé par `<span class="o_stat_text">Album BD</span>` statique (correctif appliqué après erreur `Forbidden owl directive`).
- `comic_shop/models/product_template.py` : méthodes `action_view_comic_album()` et `action_sync_from_album()`.
- `comic_shop/__manifest__.py` : ajout de `'views/product_template_views.xml'`.

### US-037c — Bouton création de produits en masse sur la fiche série

Fichiers créés / modifiés :
- `comic_shop/models/comic_serie.py` *(nouveau)* :
  - Hérite `comic.serie`, ajoute `nb_albums_with_product` (Integer stored) et `nb_albums_isbn_sans_produit` (Integer stored).
  - `@api.depends('album_ids.product_tmpl_id', 'album_ids.isbn')`.
  - `action_create_products_from_isbn()` : crée un `product.template` pour chaque album ayant un ISBN sans produit, puis appelle `_sync_to_product()`. Retourne une notification succès/warning.
  - `action_view_products()` : ouvre la liste des produits liés à la série.
- `comic_shop/views/comic_serie_views.xml` *(nouveau)* :
  - Hérite `comics_collections.view_comic_serie_form`.
  - Stat button "Produits liés" (cliquable → liste filtrée).
  - Stat button "À publier" (visible si `nb_albums_isbn_sans_produit > 0`, cliquable → `action_create_products_from_isbn`).
  - Colonnes ISBN et produit ajoutées à la liste inline des albums.
- `comic_shop/models/__init__.py` : ajout `from . import comic_serie`.
- `comic_shop/__manifest__.py` : ajout de `'views/comic_serie_views.xml'`.

### Infrastructure démo — Import Excel / CSV → Odoo

Fichiers créés dans `tools/` :
- `tools/create_demo_template.py` : génère `tools/demo_template.xlsx` avec 16 albums d'exemple (Tintin, Astérix, Thorgal, Lucky Luke, Largo Winch, Blacksad) pour illustrer le format attendu.
- `tools/import_demo.py` : import générique depuis fichier Excel vers Odoo via XML-RPC. Colonnes flexibles (insensible accents/casse), récupération couvertures via Open Library, création produits website. Usage : `python tools/import_demo.py --file mesbd.xlsx`.
- `tools/load_demo_series.py` : import hardcodé de deux séries extraites du CSV BDGest réel de l'utilisateur.
  - **Thorgal** : 29 albums (T05–T43), Le Lombard, scénaristes Van Hamme/Sente/Dorison/Yann, dessinateurs Rosinski/Vignaux.
  - **Complainte des Landes perdues** : 15 albums (T01–T16), Dargaud, scénariste Dufaux, dessinateurs Rosinski/Delaby/Tillier/Teng.
  - Résultat : 37 albums créés, 45 produits publiés, 36 couvertures Open Library.

**Erreurs rencontrées et solutions :**

1. **Mauvaise base de données** : `guepe-comics-collections-19-0-32453836` n'existe pas localement. Vraie BDD : `odoo` (trouvée via `docker exec odoo-postgres psql -U odoo -c "\l"`).

2. **ISBN-10 rejeté par Odoo** (`'L'ISBN "280360549X" n'est pas un EAN-13 valide'`) : les tomes Thorgal antérieurs à 2007 ont un ISBN-10. Ajout de `isbn_to_ean13()` : préfixe `978` aux 9 premiers chiffres, recalcule le check digit EAN-13 (`total = sum(int(d) * (1 if i%2==0 else 3) for i,d in enumerate(body)); check = (10 - total%10)%10`).

3. **Encodage CSV BDGest** : mojibake UTF-8 lu en Latin-1 (`"Ã©"` → `"é"`). Contourné en hardcodant les données propres dans le script.

---

## 2026-05-20 (suite 3) — Correctif filtres BD : bins vs products + keep() propagation

### Correctif US-041 — Filtres séries/genres/auteurs/type ne filtraient rien

**Cause racine 1 — `bins` vs `products` :** Le template shop Odoo 19 rend la grille depuis `bins` (`TableCompute().process(products, ppg, ppr)`), pas depuis `products`. Post-filtrer `ctx['products']` après `super().shop()` ne modifiait pas `bins` déjà calculé → aucun effet visible.

**Cause racine 2 — `keep()` / QueryURL :** La fonction `keep()` dans les templates website_sale n'inclut que les paramètres avec lesquels elle a été initialisée (search, category, attrib, min_price, max_price, order, tags). Nos paramètres `bd_*` n'étaient pas dans sa liste → pagination/tri supprimait les filtres BD à chaque navigation.

**Fix appliqué :**
- `comic_shop/controllers/main.py` entièrement réécrit :
  - **`_shop_lookup_products()`** : filtre `search_result` (recordset `product.template`) AVANT que `bins` soit calculé. Construit un domaine sur `comic.album` selon les params BD, récupère les `product_tmpl_id` autorisés, filtre avec `.filtered()`. Retourne `fuzzy_term, len(search_result), search_result`.
  - **`_shop_get_query_url_kwargs()`** : ajoute les params BD non-vides au dict retourné → `keep()` les inclut automatiquement dans tous les liens pagination/tri.
  - **`shop()`** : ne fait plus que injecter les données de sidebar (séries, genres, auteurs, types + sélections actives). La logique de filtrage a été retirée de cet override.

---

## 2026-05-20 (suite 2) — US-041 correctif sidebar + US-041b pages auteurs/éditeurs

### Correctif US-041 — Sidebar filtres BD non affichée

**Cause :** `website_sale.products_attributes` en Odoo 19 est un **toggle de vue** (vérifié via `is_view_active()`), pas un template HTML. L'héritage `position="inside"` n'avait aucun effet visible.

**Fix appliqué :**
- `comic_shop/views/website_sale_shop_templates.xml` :
  - Changement d'`inherit_id` : `website_sale.products_attributes` → `website_sale.sidebar_dropzone_at_bottom`.
  - Xpath : `//div[@id='oe_structure_website_sale_sidebar_bottom']` position inside.
  - Filtres redessinés en **liens `keep()`** (fonction native Odoo website_sale) au lieu de `<select>` → préserve tous les paramètres URL existants (search, attrib, price…) lors du changement de filtre BD.
  - Interface : liste scrollable pour les séries/auteurs, badges cliquables pour genres/types, lien "Effacer" visible quand un filtre BD est actif.

Structure Odoo 19 confirmée par inspection du container Docker :
```
aside#products_grid_before
  sidebar_dropzone_at_top (oe_structure)
  div.o_wsale_products_grid_before_rail
    [catégories] [clear filters] [products_attributes_filters — vide, peuplé en JS]
    [price filter]
    sidebar_dropzone_at_bottom (oe_structure) ← notre injection
```

### US-041b — Pages auteurs et éditeurs ✅

**Fichiers modifiés :**
- `comic_shop/controllers/main.py` : 4 nouvelles routes :
  - `GET /shop/auteurs` → liste des auteurs (tous rôles) groupés par partenaire avec nb albums et rôles.
    Le controller construit un dict `{partner_id: {partner, roles: set, nb_albums, role_labels}}` trié par nom.
  - `GET /shop/auteurs/<int:auteur_id>` → albums groupés par rôle (`by_role` dict) pour cet auteur.
  - `GET /shop/editeurs` → liste des éditeurs déduite des séries ayant des albums avec produits.
    Construit un dict `{editeur_id: {editeur, nb_series, nb_albums}}`.
  - `GET /shop/editeurs/<int:editeur_id>` → séries de cet éditeur avec tomes disponibles.
  - Constante `_ROLE_LABELS` au niveau module pour la traduction des rôles (scenariste → Scénariste…).
- `comic_shop/views/website_sale_shop_templates.xml` : 4 nouveaux templates QWeb :
  - `shop_auteurs_page` : grille Bootstrap card + avatar initiale si pas de photo.
  - `shop_auteur_detail_page` : en-tête auteur (avatar, site web) + albums groupés par rôle.
  - `shop_editeurs_page` : liste cards éditeurs avec pays, nb séries, nb albums.
  - `shop_editeur_detail_page` : en-tête éditeur (pays, site web) + séries avec grilles de tomes.
  - Mise à jour `shop_serie_detail_page` : badge éditeur cliquable → `/shop/editeurs/<id>`.
- `comic_shop/views/website_sale_templates.xml` (page produit) :
  - Série → lien `/shop/series/<id>`.
  - Éditeur → lien `/shop/editeurs/<id>`.
  - Auteurs → liens `/shop/auteurs/<id>` avec rôles en français (dict inline QWeb).

---

## 2026-05-20 — US-041 Navigation webshop par série / auteur / genre

## 2026-05-20 — US-041 Navigation webshop par série / auteur / genre

### US-041 — Navigation BD dans le webshop

**Fichiers créés :**
- `comic_shop/views/website_sale_shop_templates.xml` — 3 templates QWeb :
  - `shop_bd_sidebar_filters` : hérite `website_sale.products_attributes`, injecte des selects
    Série / Genre / Auteur / Type à la fin de la sidebar via `<xpath expr="." position="inside">`.
    Les selects déclenchent un `this.form.submit()` et sont donc dans le même formulaire GET
    que les filtres natifs Odoo (attributs produit). Un lien "Parcourir par série" est ajouté sous les filtres.
  - `shop_series_page` : page `/shop/series` — grille kanban Bootstrap des séries ayant au moins
    un tome avec produit (couverture 280px, badges genre/type, compteur de tomes).
  - `shop_serie_detail_page` : page `/shop/series/<id>` — en-tête série + grille des tomes disponibles
    avec prix et bouton "Voir" vers le produit Odoo.

**Fichiers modifiés :**
- `comic_shop/controllers/main.py` :
  - `shop()` override : injecte `bd_series`, `bd_genres`, `bd_auteurs`, `bd_types` +
    valeurs sélectionnées dans le qcontext. Post-filtre le recordset `products` via `.filtered()`
    quand un paramètre GET BD est présent (`bd_serie_id`, `bd_genre`, `bd_auteur`, `bd_type`).
    Note : la pagination Odoo reflète le count pré-filtre (limitation V1 acceptable).
  - Nouvelle route `GET /shop/series` → `ComicShopController.shop_series()`
  - Nouvelle route `GET /shop/series/<int:serie_id>` → `ComicShopController.shop_serie_detail()`
- `comic_shop/views/website_sale_templates.xml` :
  - Ajout du breadcrumb `Boutique > [Nom série] > Tome X` au-dessus des badges dans le template
    `product_bd_title_badges` (hérite `website_sale.product_title`, ancre `//h1` position after).
    Le lien série pointe vers `/shop/series/<serie.id>`.
- `comic_shop/__manifest__.py` : ajout de `views/website_sale_shop_templates.xml` dans `data`.

**Décisions techniques :**
- Filtres sidebar dans `website_sale.products_attributes` (position inside) : partage le formulaire
  GET natif donc les filtres BD et les filtres attributs Odoo coexistent dans la même soumission.
- Route `/shop/series/<int:serie_id>` (ID entier) plutôt que slug Odoo : `comic.serie` n'hérite
  pas `website.published.mixin`, donc pas de slug natif disponible.
- Post-filtrage dans le controller (`.filtered()`) plutôt qu'override de `_get_search_domain()`
  (signature instable entre versions Odoo 19).

---

## 2026-05-18 (suite) — Correctif Odoo 19 `models.Constraint`

### Correctif — Remplacement de `_sql_constraints`

Warning rencontré au chargement :

`Model attribute '_sql_constraints' is no longer supported, please define models.Constraint on the model.`

**Cause :** `comic_shop/models/comic_customer_album.py` utilisait encore l'ancienne API `_sql_constraints` pour l'unicité `(partner_id, album_id)`.

**Fix appliqué :**

- `comic_shop/models/comic_customer_album.py` : remplacement par l'API Odoo 19 :

```python
_unique_partner_album = models.Constraint(
    'UNIQUE(partner_id, album_id)',
    "Ce client possède déjà une entrée pour cet album dans sa bibliothèque.",
)
```

- `CLAUDE.md` : ajout de l'incompatibilité Odoo 19 dans la référence rapide.

Validation :

- `python3 -m py_compile comic_shop/models/comic_customer_album.py` OK
- Recherche globale : plus aucun `_sql_constraints` dans les fichiers Python

---

## 2026-05-18 (suite) — Correctif US-040 XPaths website_sale Odoo 19

### Correctif — Enrichissement page produit BD

Erreur rencontrée au chargement de `comic_shop` :

`Element '<xpath expr="//h1">' cannot be located in parent view`

**Cause :** `comic_shop/views/website_sale_templates.xml` héritait de `website_sale.product` et cherchait directement `//h1`. En Odoo 19, le titre produit est rendu par le sous-template `website_sale.product_title`; le `<h1>` n'est donc pas présent directement dans la vue parent `website_sale.product`.

**Fix appliqué :**

- `comic_shop/views/website_sale_templates.xml` :
  - séparation de l'injection badges dans un nouveau template `product_bd_title_badges` qui hérite de `website_sale.product_title`;
  - remplacement de l'ancre `//div[hasclass('js_product')]` par `//div[@id='product_details']`;
  - remplacement de l'ancre `//div[@id='wrap']` par `//section[@id='product_detail']`;
  - correction de l'éditeur affiché : `comic_album.serie_id.editeur_id` au lieu de `comic_album.editeur_id`, champ inexistant sur `comic.album`;
  - liens des autres tomes vers `product_tmpl_id.website_url` au lieu d'une URL backend `/web#...`;
  - images des autres tomes servies via `product.template.image_512`, accessible côté webshop.
- `comic_shop/controllers/main.py` :
  - ajout de valeurs par défaut `comic_album=False`, `comic_other_tomes=[]`, `comic_in_library=False` pour éviter un rendu QWeb fragile sur les produits non-BD.

Validation :

- XPaths vérifiés contre le template officiel Odoo 19 `addons/website_sale/views/templates.xml`.
- `xmllint --noout comic_shop/views/website_sale_templates.xml` OK
- `python3 -m py_compile comic_shop/controllers/main.py` OK

---

## 2026-05-18 (suite) — Correctif US-039 `has_product` searchable

### Correctif — Filtre "Sans produit shop" sur `comic.customer.album`

Erreur rencontrée au chargement de `comic_shop` :

`Unsearchable field "has_product" in path "has_product" in domain of <filter name="sans_produit">`

**Cause :** la vue search `comic_shop/views/comic_customer_album_views.xml` filtre sur `has_product`, mais le champ calculé dans `comic_shop/models/comic_customer_album.py` n'était pas stocké en base. Un champ computed non stocké sans méthode `search` n'est pas utilisable dans un domaine de recherche Odoo.

**Fix appliqué :**

- `comic_shop/models/comic_customer_album.py` : ajout de `store=True` et `index=True` sur `has_product`.
- Le filtre `sans_produit` reste donc fonctionnel sans modifier l'UX prévue par l'US-039.

Validation :

- `python3 -m py_compile comic_shop/models/comic_customer_album.py` OK
- `xmllint --noout comic_shop/views/comic_customer_album_views.xml` OK

---

## 2026-05-18 (suite) — Correctif Odoo 19 vue héritée `comic_shop`

### Correctif — Sélecteur `string` interdit dans une vue héritée

Erreur rencontrée au chargement de `comic_shop` :

`View inheritance may not use attribute 'string' as a selector`

**Cause :** `comic_shop/views/comic_album_views.xml` ajoutait l'onglet "Shop" avec le raccourci d'héritage :

```xml
<page string="Synopsis" position="after">
```

Odoo 19 refuse désormais `string` comme sélecteur dans les vues héritées, car le libellé est traduisible et donc instable.

**Fix appliqué :**

- `comic_shop/views/comic_album_views.xml` : remplacement du sélecteur `page string="Synopsis"` par un XPath stable basé sur le champ enfant `synopsis` :

```xml
<xpath expr="//notebook/page[field[@name='synopsis']]" position="after">
```

- `CLAUDE.md` : ajout de cette incompatibilité dans la référence rapide Odoo 19.
- `CLAUDE.md` : correction de la référence de handoff `CHANGES.md` → `CHANGE.md`.

Validation :

- `xmllint --noout comic_shop/views/comic_album_views.xml` OK
- Recherche globale des fichiers XML : plus aucun héritage XML ne cible un élément via `string` + `position`

---

## 2026-05-18 — US-035 Scaffold comic_shop + mise à jour CLAUDE.md

### CLAUDE.md — Mise à jour pour refléter l'état réel du projet
- Correction nom module : `comic_collection` → `comics_collections` (avec "s") partout
- Suppression du dossier `addons/` fictif — les modules sont à la racine du projet
- Ajout `comic_bdgest` dans la structure (coexiste avec `comic_datasource`)
- Précision : `comic_import` n'est pas un module séparé, wizard intégré dans `comics_collections`
- Ajout section identifiants XML (préfixe `comics_collections.` obligatoire)
- Ajout section incompatibilités Odoo 19 (Many2many, groupes, vues search, cache Docker)
- Ajout tableau des crons configurés
- Correction modèle Claude : `claude-sonnet-4-6`

### US-035 — Scaffold du module `comic_shop`

Fichiers créés dans `comic_shop/` :
```
comic_shop/
├── __init__.py
├── __manifest__.py                 dépendances : comics_collections, sale, website,
│                                   website_sale, point_of_sale, portal
├── models/__init__.py              vide — prêt pour US-036+
├── wizards/__init__.py             vide — prêt pour US-044+
├── security/
│   ├── comic_shop_security.xml     groupe group_shop_manager (syntaxe Odoo 19 : privilege_id)
│   │                               implique comics_collections.group_comic_manager
│   └── ir.model.access.csv         header seul (aucun modèle propre à ce stade)
└── data/
    └── comic_shop_data.xml         noupdate=1 : product.category "Bandes Dessinées"
                                    + product.pricelist "Tarif Bandes Dessinées" (EUR)
```

Décisions techniques :
- `application = False` : comic_shop enrichit comics_collections, ne crée pas de nouvelle app
- `noupdate="1"` sur les données de base pour éviter l'écrasement lors des mises à jour
- Catégorie module séparée "Comic Shop" (sequence 101) pour isoler le groupe dans l'UI utilisateur

### US-036 — Lien `comic.album` → `product.template`

Fichiers créés :
- `comic_shop/models/comic_album.py` — `_inherit = 'comic.album'`
  - Champ `product_tmpl_id` (Many2one → product.template, ondelete='set null')
  - `action_create_product()` : crée product.template pré-rempli (nom, catégorie BD, image, barcode ISBN), ouvre le formulaire produit
  - `action_view_product()` : ouvre le formulaire du produit lié
  - `action_unlink_product()` : retire le lien dans les deux sens (album + produit)
  - `_get_product_name()` : construit "Série — Titre (T{N})"
- `comic_shop/models/product_template.py` — `_inherit = 'product.template'`
  - Champ `comic_album_id` (Many2one → comic.album, ondelete='set null')
- `comic_shop/views/comic_album_views.xml` — héritage `view_comic_album_form`
  - Bouton "Voir le produit" (fa-shopping-cart) — visible si lié, accessible à tous
  - Bouton "Créer produit" (fa-plus-circle) — visible si non lié, group_comic_manager
  - Bouton "Dissocier" (fa-chain-broken) — visible si lié, group_comic_manager, confirm dialog

Décisions techniques :
- `ondelete='set null'` sur les deux Many2one : suppression d'un côté n'affecte pas l'autre
- Lien bidirectionnel géré manuellement via les actions (pas de compute) pour rester simple
- `type: 'consu'` sur le produit créé (consommable, pas de gestion de stock par défaut)

### US-037 — Synchronisation album ↔ produit

Fichiers modifiés :
- `comic_shop/models/comic_album.py`
  - Champ `sync_product` (Boolean, défaut True) : active/désactive la synchro auto
  - `_sync_to_product()` : helper central — copie nom, image_1920, barcode, description_sale (synopsis html → texte via `html2plaintext`)
  - `action_create_product()` refactorisé : délègue à `_sync_to_product()` après création
  - `action_resync_product()` : force la synchro complète (ignore `sync_product`)
  - `write()` override : si `isbn` change et `sync_product=True`, met à jour `barcode` du produit lié
- `comic_shop/views/comic_album_views.xml`
  - Bouton "Resynchroniser" (fa-refresh) ajouté dans le `button_box` (managers, visible si produit lié)
  - Onglet "Shop" ajouté après "Synopsis" : affiche `product_tmpl_id` (readonly) + `sync_product` + explication textuelle (visible seulement si produit lié, managers)

Décisions techniques :
- Synchro unidirectionnelle album → produit : le commerçant peut surcharger le produit sans risque
- `html2plaintext` (odoo.tools) pour convertir le synopsis HTML en texte brut pour `description_sale`
- L'onglet "Shop" est invisible si aucun produit n'est lié (évite de polluer l'UI des collectionneurs sans shop)

### US-039 — Modèle `comic.customer.album`

Fichiers créés :
- `comic_shop/models/comic_customer_album.py` — nouveau modèle `comic.customer.album`
  - Champs : partner_id, album_id, source, etat_lecture, dans_collection, dans_wishlist,
    note, commentaire, date_ajout, sale_order_line_id
  - `models.Constraint` : unicité (partner_id, album_id)
  - `has_product` (Boolean, computed+stored via `@api.depends('album_id.product_tmpl_id')`)
- `comic_shop/views/comic_customer_album_views.xml`
  - Vue list, form et search
  - Action `action_comic_customer_album`
  - Menu "Comic Shop" racine (group_shop_manager) + sous-menu "Bibliothèques clients"
- `comic_shop/security/ir.model.access.csv` — 3 lignes d'accès :
  - group_shop_manager : CRUD complet
  - group_comic_user : lecture/écriture/création (pas de suppression)
  - base.group_portal : lecture/écriture/création (pas de suppression)
- `comic_shop/security/comic_shop_security.xml` — 3 record rules :
  - comic_user : domain `partner_id = user.partner_id`
  - portal : domain `partner_id = user.partner_id`
  - shop_manager : domain `(1, '=', 1)` (tout voir)

Décisions techniques :
- `ondelete='cascade'` sur partner_id (si le client est supprimé, sa bibliothèque l'est aussi)
- `ondelete='restrict'` sur album_id (on ne peut pas supprimer un album présent dans une bibliothèque)
- Les utilisateurs portail ne peuvent pas supprimer leurs entrées (perm_unlink=0) — protection contre les pertes accidentelles

### US-040 — Fiche produit webshop enrichie BD

Fichiers créés :
- `comic_shop/controllers/__init__.py` + `main.py`
  - Classe `ComicShopController(WebsiteSale)` — hérite du controller website_sale
  - Override `product()` : si `product.comic_album_id` existe, ajoute au qcontext :
    - `comic_album` : l'album lié
    - `comic_other_tomes` : albums de la même série ayant un produit (triés par tome)
    - `comic_in_library` : booléen, True si le visiteur connecté a cet album en bibliothèque
  - Guard `hasattr(response, 'qcontext')` pour ne pas planter si le rendu est différent
- `comic_shop/views/website_sale_templates.xml`
  - Hérite `website_sale.product`, toutes les injections wrappées en `t-if="comic_album"`
  - XPath 1 — après `<h1>` : badge "Tome X — Série Y" (bg-primary) + badge "Dans votre bibliothèque" (bg-success, si `comic_in_library`)
  - XPath 2 — après `div.js_product` : section "Informations sur l'album" (série, tome, ISBN, parution, pages, éditeur, auteurs+rôles, synopsis HTML)
  - XPath 3 — dans `div#wrap` : section "Les autres tomes de la série" (grille Bootstrap responsive, lien vers page produit, miniature couverture via `/web/image/`)

⚠️ **À valider sur Odoo 19 réel** : les XPaths `div.js_product` et `div#wrap` sont conservateurs mais peuvent nécessiter un ajustement selon la version exacte du template `website_sale.product` en Odoo 19. Si la page produit est rendue en OWL, le controller override peut ne pas fonctionner — à tester.

Non implémenté : "Couverture haute résolution avec zoom au clic" — la couverture standard du produit (`image_1920`) est utilisée par website_sale nativement.

---

## 2026-05-15

### Incompatibilités Odoo 19 découvertes et corrigées

Odoo 19 a supprimé ou renommé plusieurs champs qui existaient en 17/18.
Ces erreurs bloquaient l'installation/mise à jour des modules.

#### `comics_collections/security/comic_security.xml`

| Champ supprimé                 | Raison                | Fix appliqué  |
| ------------------------------ | --------------------- | ------------- |
| `category_id` sur `res.groups` | Supprimé en Odoo 19   | Champ retiré  |
| `users` sur `res.groups`       | Renommé en `user_ids` | Champ corrigé |

**Nouvelle architecture Odoo 19 pour les groupes de sécurité :**

```
ir.module.category  ←  res.groups.privilege  ←  res.groups
                          (nouveau modèle)
```

Ajout d'un enregistrement `res.groups.privilege` (id: `privilege_comic_collection`)
qui lie la catégorie aux groupes, et ajout de `privilege_id` sur chaque groupe.
Les groupes apparaissent maintenant dans le formulaire utilisateur sous
la section "Bandes Dessinées" avec sélection "Aucun accès / Utilisateur / Gestionnaire".

Syntaxe Odoo 19 pour les Many2many dans XML :

```xml
<!-- ✅ Odoo 19 -->
<field name="implied_ids" eval="[Command.link(ref('base.group_user'))]"/>
<field name="user_ids" eval="[Command.link(ref('base.user_root'))]"/>

<!-- ❌ Odoo ≤18 (ne fonctionne plus) -->
<field name="implied_ids" eval="[(4, ref('base.group_user'))]"/>
<field name="users" eval="[(4, ref('base.user_root'))]"/>
```

#### `comics_collections/views/comic_serie_views.xml` et `comic_album_views.xml`

| Attributs supprimés                                    | Fix                                    |
| ------------------------------------------------------ | -------------------------------------- |
| `<group expand="0" string="...">` dans les vues search | Remplacé par `<group name="group_by">` |

`expand` et `string` ne sont plus des attributs valides sur `<group>` selon le RNG Odoo 19.

#### `comics_collections/views/comic_menu.xml`

Mauvais préfixe de module sur toutes les références :

- `comic_collection.group_comic_user` → `comics_collections.group_comic_user`
- `comic_collection.group_comic_manager` → `comics_collections.group_comic_manager`
- `web_icon="comic_collection,..."` → `web_icon="comics_collections,..."`

#### `comics_collections/security/ir.model.access.csv`

Ajout du préfixe de module manquant sur `group_id:id` :

- `group_comic_user` → `comics_collections.group_comic_user`
- `group_comic_manager` → `comics_collections.group_comic_manager`

#### `comic_bdgest/views/comic_album_inherit_views.xml`

| Champ renommé                       | Fix                               |
| ----------------------------------- | --------------------------------- |
| `groups_id` sur `ir.actions.server` | Renommé en `group_ids` en Odoo 19 |

---

### Nouvelles fonctionnalités — US-017 (cases manquantes)

#### Wizard d'enrichissement BDGest (US-017 → bouton ISBN + action batch)

Fichiers créés dans `comic_bdgest/` :

```
comic_bdgest/
├── wizards/
│   ├── __init__.py                          (nouveau)
│   └── comic_bdgest_enrich_wizard.py        (nouveau)
├── models/
│   └── comic_album.py                       (nouveau — inherit comic.album)
├── views/
│   ├── comic_bdgest_enrich_wizard_views.xml (nouveau)
│   └── comic_album_inherit_views.xml        (nouveau)
└── security/
    └── ir.model.access.csv                  (nouveau)
```

Fichiers modifiés dans `comic_bdgest/` :

- `__init__.py` — ajout `from . import wizards`
- `models/__init__.py` — ajout `from . import comic_album`
- `__manifest__.py` — ajout des nouveaux fichiers dans `data`

**Modèles transients créés :**

- `comic.bdgest.enrich.wizard` — wizard de recherche/import (2 états: search / results)
- `comic.bdgest.result.line` — ligne de résultat dans le wizard

**Méthodes ajoutées sur `comic.album` (via inherit) :**

- `action_enrich_from_bdgest()` — ouvre le wizard (bouton formulaire)
- `action_batch_enrich_from_bdgest()` — enrichissement batch par ISBN (action liste)
- `_bdgest_import_from_id(bdgest_album_id, ...)` — fetch + apply détail BDGest
- `_bdgest_apply_detail(detail, scraper)` — mappe un dict BDGest sur les champs Odoo

**Flux ISBN (bouton formulaire) :**

1. Wizard s'ouvre avec l'ISBN pré-rempli
2. "Rechercher" → search/albums?RechISBN=... → 1er résultat → get_album_detail → import direct → fermeture (pas d'étape de sélection)

**Flux titre :**

1. Saisie du titre → liste de résultats → sélection manuelle → import

**Flux batch (action liste, multi-sélection) :**

- Traite chaque album ayant un ISBN, affiche notification résumée

---

### Correction du scraper BDGest

`comic_bdgest/scraper/bdgest_scraper.py`

| Avant (cassé)                        | Après                                            |
| ------------------------------------ | ------------------------------------------------ |
| Endpoint : `/recherche-albums.html`  | `/search/albums`                                 |
| Paramètre titre : `RechAlbumTitre`   | `RechTitre`                                      |
| Paramètre ISBN : `RechAlbumEan`      | `RechISBN`                                       |
| Paramètre auteur : `RechAlbumAuteur` | `RechAuteur`                                     |
| Pas de CSRF token                    | `csrf_token_bel` extrait via `_get_csrf_token()` |

Ajouts :

- `_search_params(**criteria)` — construit les paramètres avec tous les champs vides requis + CSRF
- `_get_csrf_token()` — GET sur la page de recherche, extrait le token `<input name="csrf_token_bel">`, mis en cache par session
- `search_by_isbn()` retourne maintenant le **détail complet** (2 requêtes : search + album page) et non plus le résultat partiel

⚠️ **Note** : après modification d'un `.py`, supprimer les `__pycache__` si Odoo est en Docker avec volume monté :

```bash
find /chemin/module -name "__pycache__" -exec rm -rf {} +
```

---

## État actuel des modules (2026-05-15)

### `comics_collections`

- ✅ Installé et fonctionnel en Odoo 19
- ✅ Groupes de sécurité visibles dans le formulaire utilisateur
- ✅ Droits d'accès corrects sur tous les modèles
- ✅ Menus fonctionnels (Bandes Dessinées > Ma Collection, Catalogues, Configuration)

### `comic_bdgest`

- ✅ Installé et fonctionnel en Odoo 19
- ✅ Bouton "Enrichir depuis BDGest" dans le formulaire album (à côté de l'ISBN)
- ✅ Action "Enrichir depuis BDGest" dans le menu Action de la vue liste
- ⚠️ Le parser HTML (`bdgest_parser.py`) a été conçu pour l'ancienne URL — à valider sur la nouvelle structure HTML de `/search/albums`
- ⏳ Module destiné à être remplacé par `comic_datasource` (non encore implémenté)

### `partner_vcard_import`

- Non modifié dans cette session

---

## 2026-05-15 (suite) — Restructuration architecture multi-sources

### Documentation : migration `comic_bdgest` → `comic_datasource`

**Fichiers modifiés :**

- `comics_collections/CLAUDE.md`
- `comics_collections/USER_STORIES.md`

**Changements dans `CLAUDE.md` :**

| Section             | Changement                                                             |
| ------------------- | ---------------------------------------------------------------------- |
| Dépendances Python  | Ajout `xmltodict`                                                      |
| APIs externes       | Nouveau tableau (Google Books, Open Library, BnF SRU, BDGest)          |
| Module 2            | Renommé `comic_bdgest` → `comic_datasource`                            |
| Structure `addons/` | Mise à jour avec sous-dossiers `sources/`, `aggregator.py`, `wizards/` |
| Règles Claude       | Ajout règles 11, 12, 13 (légalité APIs, clés Google, priorité BnF)     |

**Nouvelle architecture `comic_datasource` (cascade de sources) :**

1. Google Books API → synopsis, couverture HD, métadonnées générales
2. Open Library API → couverture alternative, auteurs, éditions
3. BnF SRU API → données officielles BD francophones
4. BDGest scraping → fallback uniquement avec avertissement légal

**Changements dans `USER_STORIES.md` :**

| Changement     | Détail                                                                                        |
| -------------- | --------------------------------------------------------------------------------------------- |
| En-tête        | Ajout note sur source de rédaction                                                            |
| EPIC 3         | Réécrit intégralement : était BDGest-only (US-017→022), maintenant multi-sources (US-017→025) |
| Renumérotation | US-023→US-026 … US-030→US-033 (décalage +3 pour toutes les US post-EPIC 3)                    |
| Phases         | "Phase 3 IA" renommée "Phase 4a IA" ; ajout Phase 3 Datasource                                |
| Tableau récap  | Mis à jour avec nouvelles priorités MoSCoW                                                    |

**Nouvelles US (EPIC 3 — multi-sources) :**

- US-017 : Configuration sources de données (Google Books API key, BDGest credentials)
- US-018 : Enrichissement ISBN via aggregator (cascade automatique)
- US-019 : Wizard recherche multi-sources (affichage source par champ)
- US-020 : Import couverture depuis URL source
- US-021 : Scraping BDGest (fallback, avec disclaimer légal)
- US-022 : Import série complète BDGest
- US-023 : Source BnF SRU (données officielles FR)
- US-024 : Source Open Library
- US-025 : Tests et monitoring sources

> ⚠️ **À implémenter** : Le module `comic_datasource` est documenté mais pas encore créé.
> Le module `comic_bdgest` existant reste installé en attendant.

---

## Référence rapide — Incompatibilités Odoo 19 vs 17/18

| Modèle              | Champ                   | Changement                                                              |
| ------------------- | ----------------------- | ----------------------------------------------------------------------- |
| `res.groups`        | `category_id`           | **Supprimé** — utiliser `res.groups.privilege`                          |
| `res.groups`        | `users`                 | **Renommé** en `user_ids`                                               |
| `ir.actions.server` | `groups_id`             | **Renommé** en `group_ids`                                              |
| Vues search         | `<group expand string>` | `expand` et `string` **supprimés** — utiliser `<group name="group_by">` |
| XML Many2many       | `(4, ref(...))`         | Remplacer par `Command.link(ref(...))` (recommandé)                     |

---

---

## 2026-05-15 (suite 2) — US-017 : Infrastructure `comic_datasource`

### Nouveau module `comic_datasource/`

Fichiers créés :

```
comic_datasource/
├── __manifest__.py          (dépend de comics_collections)
├── __init__.py
├── aggregator.py            (ComicDataAggregator)
├── sources/
│   ├── __init__.py
│   ├── base.py              (BaseComicSource + ComicSourceResult)
│   ├── google_books.py      (GoogleBooksSource)
│   ├── open_library.py      (OpenLibrarySource)
│   ├── bnf.py               (BnfSource — SRU API + xmltodict)
│   └── bdgest.py            (BdgestSource — fallback scraping, désactivé par défaut)
├── wizards/__init__.py      (stub — implémenté en US-023)
├── tests/
│   ├── __init__.py
│   ├── test_sources.py      (tests unitaires avec mocks HTTP)
│   └── test_aggregator.py   (tests de fusion + priorités)
├── security/ir.model.access.csv
├── data/comic_datasource_config.xml   (params par défaut)
└── views/                   (stubs — implémentés en US-023/024)
```

**`BaseComicSource` (sources/base.py) :**

- Classe abstraite avec `search_by_isbn()` et `search_by_title()` à implémenter
- `ComicSourceResult` (dataclass) : modèle normalisé commun à toutes les sources
- Champs : title, serie_name, tome, isbn, date_parution, date_depot_legal, nb_pages, editeur, auteurs, synopsis, cover_url, cover_url_small, source, source_id, raw

**Cascade de sources par défaut :** Google Books → Open Library → BnF SRU → BDGest

**Règles de fusion dans `ComicDataAggregator` :**

- synopsis : Google > BnF > BDGest > Open Library
- date_depot_legal : BnF uniquement (source officielle)
- cover_url : Google Large > Open Library L > BDGest
- auteurs : source avec la liste la plus complète
- Cache session pour éviter les appels répétés

**BDGest désactivé par défaut** (`comic.bdgest_enabled = False`) — opt-in légal requis.

**Tests :** 17 tests unitaires (mocks HTTP, pas d'accès réseau requis) — syntaxe validée.
À lancer dans Docker : `odoo-bin test -d <db> --test-tags /comic_datasource`

---

## 2026-05-15 (suite 3) — US-018 : Google Books API dans Paramètres Odoo

### Fichiers modifiés/créés dans `comic_datasource/`

| Fichier                                   | Action  | Description                                                |
| ----------------------------------------- | ------- | ---------------------------------------------------------- |
| `models/__init__.py`                      | créé    | Import `res_config_settings`                               |
| `models/res_config_settings.py`           | créé    | Extend `res.config.settings`                               |
| `sources/google_books.py`                 | modifié | Ajout `GoogleBooksQuotaError` + gestion HTTP 403           |
| `aggregator.py`                           | modifié | Re-raise `GoogleBooksQuotaError` (non silencé)             |
| `views/comic_datasource_config_views.xml` | modifié | Vue Paramètres Odoo 19 (`<app>` + `<block>` + `<setting>`) |
| `__init__.py`                             | modifié | Ajout `from . import models`                               |
| `__manifest__.py`                         | modifié | `external_dependencies` + `models` dans `data`             |

**Nouveaux champs `res.config.settings` :**

- `comic_google_books_api_key` → `ir.config_parameter` `comic.google_books_api_key`
- `comic_bdgest_enabled` → `comic.bdgest_enabled`
- `comic_bdgest_login` / `comic_bdgest_password`

**Bouton "Tester la connexion Google Books" :**

- Appel direct à l'API avec l'ISBN Astérix T1 comme test
- Retourne une notification verte si OK
- `UserError` explicite pour HTTP 429 (quota) et HTTP 403 (clé invalide)

**Structure vue Odoo 19 :** `inherit_id = base.res_config_settings_view_form` + `xpath //form` + balise `<app name="comic_datasource">` (pattern identique à `website`, `base_setup`, etc.)

---

## 2026-05-15 (suite 4) — US-023 : Wizard de recherche et import unifié

### Nouveaux fichiers dans `comic_datasource/`

| Fichier                                          | Description                                          |
| ------------------------------------------------ | ---------------------------------------------------- |
| `wizards/comic_datasource_search_wizard.py`      | Deux TransientModels                                 |
| `models/comic_album.py`                          | Inherit `comic.album` → `action_search_datasource()` |
| `views/comic_datasource_wizard_views.xml`        | Vue wizard 3 états                                   |
| `views/comic_datasource_album_inherit_views.xml` | Bouton stat dans le form album                       |
| `views/comic_datasource_menu.xml`                | Menu "Rechercher des BD"                             |

**Modèles :**

- `comic.datasource.search.wizard` — wizard principal (états: search / results / done)
- `comic.datasource.result.line` — lignes de résultats (cover_data Binary, source badge)

**Flux ISBN :** `action_search()` → `aggregator.search(isbn=...)` → 1 ligne fusionnée
**Flux titre :** `action_search()` → `aggregator.search_list(title=...)` → N lignes par source

**Logique import (`_import_line`) :**

- Find-or-create `comic.editeur`, `comic.serie`, `res.partner` (auteurs)
- Si ISBN déjà en base : mise à jour (pas duplication)
- Téléchargement couverture HD au moment de l'import
- Dates converties str `YYYY-MM-DD` → `date`

**Points Odoo 19 spécifiques :**

- `invisible="state != 'results'"` (Python, pas domain)
- `env[...]` interdit dans les vues → champ `bdgest_enabled` computed sur le wizard
- `role="status"` requis sur `div.alert-info`
- `button_box` absent de la vue album → inséré via `xpath` avant `oe_title`
- Action liste liée via `binding_model_id` + `binding_view_types="list"`

_Maintenu par sessions — ajouter une entrée datée à chaque modification significative._

---

## 2026-05-16 (suite) — Correctifs post-déploiement

### Correctif — Conflit button_box entre `comics_collections` et `comic_datasource`

**Problème :** Après l'ajout du `button_box` dans le formulaire album (US-011), le bouton "Rechercher sur les sources" de `comic_datasource` avait disparu.

**Cause :** `comic_datasource_album_inherit_views.xml` injectait son propre `<div class="oe_button_box">` via `xpath before oe_title`. Avec un `button_box` déjà présent dans la vue de base, Odoo se retrouvait avec deux `div.oe_button_box` et le rendu du second était ignoré.

**Fix — `comic_datasource/views/comic_datasource_album_inherit_views.xml` :**

```xml
<!-- Avant (cassé) -->
<xpath expr="//div[hasclass('oe_title')]" position="before">
    <div name="button_box" class="oe_button_box"> ... </div>
</xpath>

<!-- Après (correct) -->
<xpath expr="//div[@name='button_box']" position="inside">
    <button name="action_search_datasource" .../>
</xpath>
```

**Règle à retenir :** Quand un `button_box` existe déjà dans la vue parente, les modules héritiers doivent cibler `//div[@name='button_box']` avec `position="inside"` — jamais créer un nouveau `div.oe_button_box`.

---

### Correctif — `__pycache__` Docker périmé (RPC_ERROR sur les nouvelles méthodes)

**Problème récurrent :** Après chaque ajout de méthode Python, Odoo retourne `action_xxx is not a valid action` lors de la mise à jour via l'UI.

**Cause :** Docker avec volumes bind-mounted compile les `.py` en `.pyc` dans `__pycache__`. Si le timestamp ou l'inode du fichier ne change pas côté container, Python utilise le `.pyc` périmé qui ne contient pas les nouvelles méthodes. La validation XML des vues échoue alors car elle vérifie l'existence des méthodes sur le modèle chargé.

**Fix systématique :**

```bash
find /Users/phde/Projects/odoo/<module> -name "__pycache__" -type d -exec rm -rf {} +
docker exec odoo-web odoo -u <module> -d odoo \
  --db_host postgres-Odoo --db_port 5432 \
  --db_user odoo --db_password odoo --stop-after-init
```

Concerné cette session : `action_toggle_collection`, `action_toggle_wishlist` (comics_collections), `_normalize_author_name` (import wizard).

---

### Correctif — Import auteurs : virgule persistante dans les noms

**Problème :** `"Cauvin, Raoul"` restait `"Cauvin, Raoul"` après import CSV au lieu de devenir `"Raoul Cauvin"`.

**Cause :** Le `__pycache__` Docker contenait la version de `comic_import_wizard.py` sans `_normalize_author_name()`. La méthode était dans le `.py` mais pas dans le `.pyc` utilisé par le container.

**Code ajouté (commit `60177f5`) :**

```python
@staticmethod
def _normalize_author_name(name):
    if ',' in name:
        parts = name.split(',', 1)
        last, first = parts[0].strip(), parts[1].strip()
        if first:
            return '%s %s' % (first, last)
    return name

@staticmethod
def _split_names(value):
    return [
        ComicImportWizard._normalize_author_name(name.strip())
        for name in re.split(r'[;\n|]+', str(value or ''))
        if name.strip()
    ]
```

Fix après purge du `__pycache__` et redémarrage Odoo.

---

### Feat — Retour à la fiche album/série après fermeture du wizard datasource

**Problème UX :** Après la mise à jour via datasource (album ou série), fermer le wizard ramenait à la liste au lieu de rester sur la fiche d'origine.

**Fix — méthode `action_close_and_return()` ajoutée sur les deux wizards :**

`comic_datasource/wizards/comic_datasource_search_wizard.py` :

```python
def action_close_and_return(self):
    if self.album_id:
        return {'type': 'ir.actions.act_window',
                'res_model': 'comic.album', 'res_id': self.album_id.id,
                'view_mode': 'form', 'target': 'current'}
    return {'type': 'ir.actions.act_window_close'}
```

`comic_datasource/wizards/comic_serie_update_wizard.py` :

```python
def action_close_and_return(self):
    return {'type': 'ir.actions.act_window',
            'res_model': 'comic.serie', 'res_id': self.serie_id.id,
            'view_mode': 'form', 'target': 'current'}
```

**Vues mises à jour :** `special="cancel"` remplacé par `name="action_close_and_return" type="object"` dans `comic_datasource_wizard_views.xml` et `comic_datasource_serie_inherit_views.xml`.

**Comportement :**

- Wizard album (ouvert depuis fiche album) → Fermer → retour à la fiche album
- Wizard album (ouvert depuis menu) → Fermer → ferme le dialog
- Wizard série → Fermer → retour à la fiche série

---

## 2026-05-16 — US-033, US-008b, US-011 + fix import auteurs

### US-033 ✅ — Documentation publication Odoo Apps

| Fichier                                            | Action                                                                       |
| -------------------------------------------------- | ---------------------------------------------------------------------------- |
| `comics_collections/static/description/index.html` | Créé — page HTML store avec screenshots `overview.png` et `v2.png`           |
| `comics_collections/README.rst`                    | Créé — format OCA : description, installation, configuration, usage, roadmap |

Le scanner Odoo Apps (même que pour `partner_vcard_import`) exige `static/description/index.html` — sans ce fichier le module est refusé à la publication.

### US-008b (partiel) — Menu Auteurs

| Fichier                        | Action                                                                                                |
| ------------------------------ | ----------------------------------------------------------------------------------------------------- |
| `models/res_partner.py`        | Créé — inherit `res.partner`, ajout `auteur_album_line_ids` (One2many vers `comic.album.auteur.line`) |
| `models/__init__.py`           | Modifié — import `res_partner`                                                                        |
| `views/comic_auteur_views.xml` | Créé — action `action_comic_auteurs` : `res.partner` filtré sur `auteur_album_line_ids != False`      |
| `views/comic_menu.xml`         | Modifié — menu _Catalogues → Auteurs_ (sequence 10, avant Éditeurs)                                   |
| `__manifest__.py`              | Modifié — ajout `views/comic_auteur_views.xml` dans `data`                                            |

Le filtre sur `auteur_album_line_ids != False` fonctionne grâce au One2many déclaré sur `res.partner` — Odoo traduit en EXISTS SQL automatiquement.

### US-011 ✅ — Formulaire album enrichi

| Fichier                       | Action                                                             |
| ----------------------------- | ------------------------------------------------------------------ |
| `views/comic_album_views.xml` | Modifié — button_box, onglet Synopsis, Ma Collection allégée       |
| `models/comic_album.py`       | Modifié — `action_toggle_collection()`, `action_toggle_wishlist()` |

Détails :

- `button_box` avec deux stat buttons : **En collection** (`fa-book`) et **Wishlist** (`fa-heart`), visibles en haut de fiche sans cliquer sur un onglet
- Les deux boutons appellent `action_toggle_collection()` / `action_toggle_wishlist()` qui font `self.field = not self.field`
- `dans_collection` et `dans_wishlist` supprimés de l'onglet "Ma Collection" (maintenant dans button_box)
- Onglet "IA" renommé **"Synopsis"** (plus honnête sans le module `comic_ai`)
- `note` gardé comme Float avec label `"Note (/5)"` — widget étoiles reporté

⚠️ **Erreur rencontrée :** `action_toggle_collection is not a valid action on comic.album` lors de la mise à jour Odoo via l'UI. Cause : le `__pycache__` Docker contenait une version périmée de `comic_album.py` sans les nouvelles méthodes. Fix : supprimer les `__pycache__` puis relancer `odoo -u comics_collections` via Docker.

### Fix import — Normalisation des noms d'auteurs

| Fichier                          | Action                                                             |
| -------------------------------- | ------------------------------------------------------------------ |
| `wizards/comic_import_wizard.py` | Modifié — `_normalize_author_name()` + `_split_names()` mis à jour |

`_normalize_author_name(name)` : si le nom contient une virgule, suppose le format `"Famille, Prénom"` et retourne `"Prénom Famille"`. Exemples : `"Van Hamme, Jean"` → `"Jean Van Hamme"`, `"Goscinny, René"` → `"René Goscinny"`. Noms sans virgule inchangés.

### CLAUDE.md — Règles de handoff entre sessions

Ajout d'une section **📋 Suivi de projet** avec les règles obligatoires :

- Cocher les cases `USER_STORIES.md` dès qu'une US est terminée
- Ajouter une entrée datée dans `CHANGES.md` à la fin de chaque session

---

## 2026-05-15 (suite 5) — US-023 complété + Epic 5 (Vues avancées)

### US-023 — Conflits de titres dans le wizard de résultats

**`comic_datasource/views/comic_datasource_wizard_views.xml`**

- Ajout de `decoration-danger="title_conflict"` et `decoration-warning="is_duplicate and not title_conflict"` sur la liste de résultats
- Nouvelles colonnes `existing_title` et `title_action` (visibles uniquement si `title_conflict`)
- Bannière d'avertissement : "⚠️ Certains titres diffèrent de la version en base" (masquée si `not has_title_conflicts`)
- Ajout de `has_title_conflicts` dans le bloc de champs cachés

---

### Nouveau — Wizard mise à jour des albums d'une série depuis les sources

**Fichiers créés dans `comic_datasource/` :**

| Fichier                                          | Description                                                      |
| ------------------------------------------------ | ---------------------------------------------------------------- |
| `models/comic_serie.py`                          | Inherit `comic.serie` → `action_update_albums_from_datasource()` |
| `wizards/comic_serie_update_wizard.py`           | TransientModel `comic.serie.update.wizard`                       |
| `views/comic_datasource_serie_inherit_views.xml` | Bouton dans le form Serie + vue wizard                           |

**`comic_serie_update_wizard.py` :**

- États : `confirm` / `done`
- `action_run()` : itère `serie_id.album_ids.sorted('tome')`, cherche par ISBN ou titre via aggregator
- `_apply_data()` : met à jour synopsis, nb_pages, isbn (si manquant), date_parution, date_depot_legal, couverture (via `requests`), auteurs manquants
- `_best_match()` : résultat dont le tome correspond, ou premier résultat en fallback
- `_build_report()` : HTML ✅/⏭️/❌ par album
- Classe `_FakeAgg` : enveloppe les résultats de recherche par titre dans la même interface que les résultats ISBN

**Vue wizard :**

- État `confirm` : message informatif + bouton "Lancer la mise à jour"
- État `done` : rapport HTML inline + bouton "Fermer"
- Bouton dans le form série via `xpath` avant `oe_title` → `button_box` avec icône `fa-refresh`

---

### US-025 — Génération automatique des liens d'achat (depuis ISBN)

**`comics_collections/models/comic_album.py`**

Nouveaux champs :

- `url_fnac_be = fields.Char(string='Lien FNAC.be')`
- `has_cover = fields.Boolean(compute='_compute_has_cover', store=True)` (utilisé par les kanbans)

Templates de liens :

```python
_PURCHASE_LINK_TEMPLATES = {
    'url_club_be':   'https://www.librairieclub.be/c/search?filter=search({isbn})&page=1&page_size=24&sort=RelevanceClub&sort_type=desc',
    'url_amazon_be': 'https://www.amazon.com.be/s?k={isbn}',
    'url_fnac_be':   'https://www.fnac.be/SearchResult/ResultList.aspx?Search={isbn}&sft=2',
}
```

- `create()` surchargé avec `@api.model_create_multi` → `setdefault()` pour ne pas écraser les liens existants à l'import CSV
- `@api.onchange('isbn')` → remplit les champs vides dans l'interface form
- `action_generate_purchase_links()` : régénère les 3 liens depuis l'ISBN courant
- `action_open_club_be()`, `action_open_amazon_be()` : `ir.actions.act_url` avec `target: 'new'`

**`comics_collections/views/comic_album_views.xml`** :

- Nouvel onglet "Liens d'achat" avec les 3 URL (`widget="url"`)
- Bouton "Régénérer les liens" (masqué si pas d'ISBN)

---

### Epic 5 — Vues avancées (US-009, US-010)

#### Infrastructure SCSS

**`comics_collections/static/src/scss/comics_theme.scss`** (nouveau)

Design system : INK `#022E51`, CREAM `#f3eee4`, ACCENT `#B74803`, STAR `#CC6D3D`, polices Instrument Serif + Instrument Sans.

Composants CSS :

- `.o_comic_album_card` — carte 200px avec hover
- `.o_comic_cover` — zone couverture 200×270px
- `.o_comic_cover_placeholder` — 8 palettes de couleurs (`.o_comic_pal_0` … `.o_comic_pal_7`), layout éditorial (bande, titre série, séparateur, titre, numéro tome)
- `.o_comic_reading_badge` — badges `.o_badge_lu` / `.o_badge_en_cours` / `.o_badge_non_lu`
- `.o_comic_stars` — étoiles pleines/vides
- `.o_comic_serie_card` — carte série avec couverture 120px, badge statut, barre de progression
- Scoping via `.o_kanban_view.o_comic_kanban_albums` et `.o_kanban_view.o_comic_kanban_series` + `!important` (libsass)

#### Correctif — Polices Google Fonts (render-blocking)

**Problème :** `@import url('https://fonts.googleapis.com/...')` dans un fichier CSS compilé dans le bundle Odoo bloque le rendu entier de l'interface si Google Fonts CDN est lent ou inaccessible.

**Fix :**

- Suppression de `comics_fonts.css` des assets
- Création de `comics_collections/views/comic_fonts_template.xml` : hérite `web.layout`, injecte dans `<head>` des balises `<link rel="preconnect">` + `<link rel="stylesheet">` non-bloquantes

#### US-010 — Kanban Albums

**`comics_collections/views/comic_album_views.xml`** :

- Nouvelle vue kanban `view_comic_album_kanban` (`class="o_comic_kanban_albums"`)
- Couverture ou placeholder avec palette selon `id % 8`
- Étoiles : `t-foreach="[1, 2, 3, 4, 5]"` avec `s <= (record.note.raw_value || 0)`
- Badge état lecture : `t-attf-class="o_comic_reading_badge o_badge_#{record.etat_lecture.raw_value}"`
- Cœur wishlist : `♥` si `dans_wishlist`
- `action_comic_album` → `view_mode: kanban,list,form`
- Nouvelle action `action_comic_wishlist` (`domain: dans_wishlist = True`)

#### US-009 — Kanban Séries

**`comics_collections/views/comic_serie_views.xml`** :

- Nouvelle vue kanban `view_comic_serie_kanban` (`class="o_comic_kanban_series"`)
- Barre de progression : `Math.round(nb_possedes / nb_total * 100)%`
- Badge statut dans la couverture
- `action_comic_serie` → `view_mode: kanban,list,form`

#### Menu Wishlist

**`comics_collections/views/comic_menu.xml`** :

- Ajout menu "Wishlist" (sequence 25) pointant vers `action_comic_wishlist`

#### `comics_collections/models/comic_serie.py`

- `has_cover = fields.Boolean(compute='_compute_has_cover', store=True)` (utilisé dans le kanban série)

---

### Correctif Odoo 19 — Template kanban `card`

**Problème :** `KanbanArchParser.parse: Missing 'card' template` — Odoo 19 (OWL) impose `t-name="card"` au lieu de `t-name="kanban-box"` (Odoo ≤18).

**Fix :** `replace_all=true` sur `comic_album_views.xml` et `comic_serie_views.xml`.

---

### `__manifest__.py` mis à jour

```python
'data': [
    ...
    'views/comic_fonts_template.xml',
],
'assets': {
    'web.assets_backend': [
        'comics_collections/static/src/scss/comics_theme.scss',
    ],
},
```

---

## 2026-05-16 (suite 2) — US-034, US-014, US-024 + cosmétique kanban + cron

### US-034 ✅ — Détection des tomes manquants

**Fichiers créés dans `comic_datasource/` :**

| Fichier                                      | Description                                                              |
| -------------------------------------------- | ------------------------------------------------------------------------ |
| `wizards/comic_serie_missing_wizard.py`      | Wizard `comic.serie.missing.wizard` + `comic.serie.missing.line`         |
| `views/comic_serie_missing_wizard_views.xml` | Vues form wizard (états confirm/results/done)                            |
| `security/ir.model.access.csv`               | Droits ajoutés pour les deux nouveaux TransientModel                     |
| `data/comic_serie_cron.xml`                  | Cron hebdomadaire `ir_cron_check_missing_volumes` (désactivé par défaut) |

**Modifications :**

- `comic_datasource/models/comic_serie.py` : ajout `action_search_missing_volumes()` + `_cron_check_missing_volumes()`
- `comic_datasource/views/comic_datasource_serie_inherit_views.xml` : bouton "Tomes manquants" dans `button_box`
- `comics_collections/models/comic_serie.py` : champ `a_suivre = fields.Boolean` + `first_album_cover_id = fields.Many2one` (computed stored)
- `comics_collections/views/comic_serie_views.xml` : filtre "À suivre", fallback couverture kanban (has_cover → first_album_cover_id → placeholder)

**Logique de recherche :**

- Google Books : `_fetch_google_all()` — sonde `totalItems`, pagine par 40 jusqu'au cap 200
- BnF : `search_by_serie()` avec `bib.serie adj` + fallback `bib.title any` si < 5 résultats, `_paginate_query()` pour pagination complète
- Stubs pour les tomes attendus si `nb_albums_total` est renseigné

**Cron `ir_cron_check_missing_volumes` :**

- Appelle `model._cron_check_missing_volumes()` sur `comic.serie`
- Parcourt toutes les séries `a_suivre=True`, instancie le wizard en code, exécute `action_search()` puis `action_add_to_wishlist()`
- `active=False` par défaut — à activer dans Configuration > Crons

**Correctifs BnF :**

- Bug `max_records` vs `page_size` : l'appel `source.search_by_serie(serie_name, max_records=40)` passait un kwarg inconnu → TypeError silencieuse → 0 résultats. Fix : appel sans kwarg.
- `bib.serie adj` ne tag pas tous les albums → fallback `bib.title any` si < 5 résultats.

---

### US-014 ✅ — Wishlist

- `comics_collections/models/comic_album.py` : `action_mark_acquired()` → `dans_collection=True, dans_wishlist=False`
- `comics_collections/views/comic_album_views.xml` :
  - `view_comic_album_wishlist_list` : colonnes Club.be, Amazon.be, Fnac.be (widget url) + bouton Acquérir
  - `view_comic_album_kanban_wishlist_btn` : héritage xpath — bouton "Acquérir" conditionnel dans kanban
  - `action_comic_wishlist` : domain `dans_wishlist=True`, `context={'group_by': 'serie_id'}`, `view_id` pointant sur la liste dédiée

**Erreur rencontrée :** `ir.actions.act_window.view` unique constraint — Odoo auto-crée ces records au premier install, INSERT → violation. Solution : utiliser `view_id` sur l'action + héritage xpath pour le kanban, pas de records `ir.actions.act_window.view` séparés.

---

### US-024 ✅ — Configuration des sources

- `comic_datasource/models/res_config_settings.py` : `comic_openlibrary_enabled`, `comic_bnf_enabled`, `comic_bdgest_delay`
- `comic_datasource/views/comic_datasource_config_views.xml` : toggles Open Library, BnF, champ délai BDGest conditionnel
- `comic_datasource/data/comic_datasource_config.xml` : valeurs par défaut (`openlibrary=True`, `bnf=True`, `bdgest_delay=2`)
- `comic_datasource/sources/open_library.py` : `is_available()` lit `comic.openlibrary_enabled`
- `comic_datasource/sources/bnf.py` : `is_available()` lit `comic.bnf_enabled`
- `comic_datasource/sources/bdgest.py` : `_get_delay()` lit `comic.bdgest_delay`, minimum 2s

---

## 2026-05-16 (suite 3) — Correctifs sources, UX liste albums, cron enrichissement, audit

### Correctifs BnF — requête trop large

**`comic_datasource/sources/bnf.py`**

- `bib.title any` → `bib.title adj` dans le fallback de `search_by_serie()` : `any` = logique OR sur chaque mot → 2,4 millions de résultats pour "Complainte des Landes perdues". `adj` = phrase exacte.
- `_paginate_query()` : ajout param `max_results=200` + `batch_size = min(page_size, max_results - len(results))` pour éviter de télécharger des millions de records.
- `search_by_serie()` : signature `page_size=50, max_results=200`.

### Correctif Google Books — retry sur erreur 5xx

**`comic_datasource/sources/google_books.py`**

- `_fetch()` : retry automatique (3 tentatives) avec backoff exponentiel (2s, 4s, 8s) sur HTTP 500/502/503/504.
- Abandon propre après 3 tentatives → retourne `None` sans exception.

### Correctif cron — `numbercall` supprimé (Odoo 19)

**`comic_datasource/data/comic_serie_cron.xml`** : champ `numbercall` retiré (champ inexistant en Odoo 19 → `ValueError: Invalid field`).

### Déduplication tomes manquants — 3 couches + `isbn_unverified`

**`comic_datasource/wizards/comic_serie_missing_wizard.py`**

- Ajout `_normalize_isbn()` (ISBN-10 → ISBN-13, suppression tirets/espaces).
- Ajout `_normalize_title()` (minuscules, suppression ponctuation).
- `action_search()` : déduplication en 3 couches :
  1. Tome dans `existing_tomes` (inchangé)
  2. ISBN normalisé dans `existing_isbns` (normalisé) + vérification globale DB via `search_read` groupé
  3. Chevauchement de mots (≥60%) pour candidats sans ISBN
- Candidats sans ISBN marqués `isbn_unverified=True` → ligne surlignée en orange dans le wizard.
- Nouveau champ `isbn_unverified` sur `ComicSerieMissingLine`.
- Vue wizard : `decoration-warning="isbn_unverified"` + colonne "⚠️" optionnelle.

### Cron enrichissement quotidien des albums

**`comic_datasource/models/comic_album.py`**

- `_apply_datasource_data(data)` : logique de mise à jour extraite du wizard (synopsis, pages, ISBN, dates, couverture, auteurs) — centralisée sur le modèle, appelée par le wizard ET le cron.
- `_cron_update_albums(batch_size=30)` : enrichit les albums incomplets (sans synopsis OU couverture OU ISBN), priorise `dans_collection`, limite à 30 par run.

**`comic_datasource/wizards/comic_serie_update_wizard.py`** : `_apply_data()` supprimée, remplacée par appel à `album._apply_datasource_data(data)`.

**`comic_datasource/data/comic_serie_cron.xml`** : second cron `ir_cron_update_albums` — quotidien, `active=False` par défaut.

### UX — Vue Albums dans la fiche Série

**`comics_collections/views/comic_serie_views.xml`**

- `dans_collection` → `widget="boolean_toggle"` dans la liste Albums de l'onglet.
- `etat_lecture` remplacé par 3 boutons cycle (un seul clic : Non lu → En cours → Lu → Non lu) :
  - Gris "Non lu" / Orange "En cours" / Vert "Lu ✓"
  - `etat_lecture` chargé via `column_invisible="True"`.
- Colonne `a_suivre` avec `widget="boolean_toggle"` ajoutée à la vue liste des séries.

**`comics_collections/models/comic_album.py`** : méthode `action_cycle_etat_lecture()` (cycle `non_lu → en_cours → lu → non_lu`).

### Audit pré-GitHub — sécurité

- **Doublon `action_comic_album`** supprimé de `comic_album_views.xml` (lignes 274-278 en double → violation contrainte unique Odoo à l'install).
- **`.claude/settings.local.json`** dé-tracké (`git rm --cached`) : contenait credentials dev localhost `admin/admin`.
- **`.gitignore`** : ajout `.claude/` pour éviter tout futur commit de settings Claude Code locaux.
- Clé Google Books API : jamais committée (`Clés API` dans `.gitignore` depuis le début). ✅

> À mettre à jour à chaque adaptation du module.

## 2026-05-15

- Alignement documentaire du projet sur Odoo 19.
- Ajout du wizard `comic.import.wizard`.
- Ajout du téléchargement de modèles CSV et XLSX pour l'import albums.
- Ajout du flux d'import complet : upload, mapping, prévisualisation, import et rapport d'erreurs CSV.
- Support de l'export `Albums_Collection_En_Ligne.xlsx` au format compact `N°` / `Contenu`.
- Correction de l'import Excel : prise en charge des fichiers `.xls` si `xlrd` est disponible côté serveur.
- Correction de l'import XLSX : conversion des dates Excel numériques en dates `YYYY-MM-DD`.
- Correction de l'import auteurs : les virgules ne séparent plus les auteurs afin de préserver les noms contenant une virgule.

```

```

## 2026-05-23 — US-058 Cleanup UI : onglets, menus, fix sync pochettes

### US-058 — Cleanup formulaires + menus

**Référénces dans des onglets** — champs techniques déplacés hors des en-têtes de formulaire :
- `comics_collections/views/comic_serie_views.xml` : `bdgest_id` + `bedetheque_url` déplacés dans un onglet "Références" (notebook)
- `comics_collections/views/comic_work_views.xml` : `slug` + `wikidata_id` + `openlibrary_id` + `bedetheque_id` + `comicvine_id` déplacés dans onglet "Références" ; le groupe "Références externes" disparaît de l'en-tête
- `comics_collections/views/comic_edition_views.xml` : liens d'achat (`url_club_be`, `url_amazon_be`, `url_fnac_be`) déplacés dans onglet "Liens d'achat" + bouton `action_generate_purchase_links` (managers uniquement)

**Fix pochettes d'album** — cause racine : `comic_shop/views/comic_album_views.xml` n'était pas dans le manifest et pointait sur l'ancien modèle `comic.album` :
- Model corrigé : `comic.album` → `comic.edition`
- inherit_id corrigé : `view_comic_album_form` → `view_comic_edition_form`
- Record id renommé : `view_comic_album_form_shop` → `view_comic_edition_form_shop`
- Fichier ajouté dans `comic_shop/__manifest__.py` data list
- Résultat : les boutons "Créer produit", "Resynchroniser" et "Dissocier" sont maintenant fonctionnels sur la fiche album (comic.edition)

**Menu website** — `comic_shop/data/comic_shop_data.xml` :
- Bloc `noupdate="1"` séparé du bloc menus (`noupdate="0"`)
- Menu `menu_bd_catalogue` renommé "Ma Collection" avec URL `/my/library`
- Sous-menus Séries/Auteurs/Maisons d'édition supprimés du XML ; sur instance existante, les supprimer manuellement via Site Web > Menus
