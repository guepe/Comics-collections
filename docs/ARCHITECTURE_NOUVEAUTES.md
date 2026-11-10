# Outil « Nouveautés BD » — Rapport d'architecture (étapes 1 à 3)

> Rédigé le 2026-11-05. **Aucun code de scraping n'est écrit** : ce document attend ta validation.
> Les tests réseau mentionnés ont été faits le 2026-11-05 avec un simple `curl` (User-Agent
> `ComicsCollectionBot/0.1`), une requête par page, 2 s entre les requêtes.

---

## Étape 1 — Analyse du module existant

### 1.1 Version d'Odoo

| Module               | `version`    | Dépendances                                       |
| -------------------- | ------------ | ------------------------------------------------- |
| `comics_collections` | `19.0.2.0.0` | `base`, `mail`, `contacts`                        |
| `comic_datasource`   | `19.0.1.0.0` | `comics_collections`                              |
| `comic_shop`         | `19.0.2.0.0` | `comics_collections`, website/sale/POS…           |

→ **Odoo 19.0** partout.

⚠️ **Écart avec `CLAUDE.md`** : le dossier `comic_bdgest/` est **vide** (retiré dans le commit
`1fd4595 retrait de comic_bdgest`) et `comic_datasource/sources/` ne contient **pas** de
`bdgest.py`. Le fallback BDGest décrit dans `CLAUDE.md` n'existe donc plus dans le code.

### 1.2 Modèles : un « album » est réparti sur 4 niveaux

Il n'y a pas de modèle « album » unique. Un album BD correspond à la chaîne
`comic.serie` → `comic.work` → `comic.edition` → `comic.isbn`.

**`comic.serie`** (`comics_collections/models/comic_serie.py`) — mail.thread
| Champ | Type | Remarque |
|---|---|---|
| `name` | Char, requis | |
| `name_normalise` | Char compute/store/index | `normalize_title(name)` |
| `type` | Selection | `bd` / `manga` / `comics` / `one_shot` |
| `statut` | Selection | `en_cours` / `terminee` / `abandonnee` |
| `genre_id` | Many2one `comic.genre` | |
| `editeur_id` | Many2one `comic.editeur` | |
| `image_couverture` | Image | |
| `synopsis` | Html | |
| `bdgest_id`, `bedetheque_url` | Integer, Char | |
| `a_suivre` | Boolean | **utile pour filtrer les nouveautés** |
| `work_ids` | One2many `comic.work` | |

**`comic.work`** (« Album / Tome » côté utilisateur) — mail.thread
| Champ | Type | Remarque |
|---|---|---|
| `serie_id` | Many2one `comic.serie` | |
| `titre_canonique` | Char, **requis** | |
| `tome` | Integer | **UNIQUE(serie_id, tome)** |
| `slug`, `titre_normalise` | Char | |
| `wikidata_id`, `openlibrary_id`, `bedetheque_id`, `comicvine_id` | Char | identifiants externes |
| `auteur_line_ids` | One2many `comic.work.auteur.line` | |
| `edition_ids` | One2many `comic.edition` | |
| + champs relayés depuis l'édition principale (couverture, éditeur, date, ISBN, liens…) | | |

**`comic.work.auteur.line`** : `work_id`, `partner_id` → `res.partner` (requis), `role` ∈
`scenariste` / `dessinateur` / `coloriste` / `encreur` / `traducteur` / `autre`.

**`comic.edition`** (`comics_collections/models/comic_edition.py`) — mail.thread
| Champ | Type |
|---|---|
| `work_id` | Many2one `comic.work`, requis |
| `editeur_id` | Many2one `comic.editeur` |
| `date_parution`, `date_depot_legal` | Date |
| `langue` | Selection `fr`/`nl`/`en`/`de`/`autre` |
| `format` | Selection `broche`/`cartonne`/`integrale`/`collector`/`numerique`/`autre` |
| `image_couverture` | Image |
| `synopsis` | Html |
| `nb_pages` | Integer |
| `url_club_be`, `url_amazon_be`, `url_fnac_be` | Char (générés depuis l'ISBN) |
| `isbn_ids` | One2many `comic.isbn` |
| `product_tmpl_id`, `sync_product` | ajoutés par `comic_shop` |

**`comic.isbn`** : `edition_id`, `isbn_13` (EAN-13 validé, **UNIQUE**), `isbn_10`.
Normalisation (suppression tirets/espaces) dans `create`/`write`.

**`comic.editeur`** : `name`, `partner_id`, `pays_id`, `site_web`, `bdgest_editeur_id`.
**`comic.genre`** : `name`, `description`, `color`.

### 1.3 Ce qui manque pour tes données cibles

| Donnée souhaitée | Où dans Odoo | Statut |
|---|---|---|
| ISBN-13 | `comic.isbn.isbn_13` | ✅ |
| Titre / série / tome | `comic.work` / `comic.serie` | ✅ |
| Scénaristes / dessinateurs / coloristes | `comic.work.auteur.line` | ✅ |
| Éditeur | `comic.editeur` | ✅ |
| Date de parution, nb pages, synopsis | `comic.edition` | ✅ |
| Image de couverture | `comic.edition.image_couverture` | ✅ (binaire, pas d'URL stockée) |
| **Prix** | — | ❌ **aucun champ prix sur `comic.edition`**. Seul `product.template.list_price` (via `comic_shop`) existe ; la colonne `prixachat` de l'assistant d'import est ignorée. |
| **URL produit éditeur** | — | ❌ pas de champ générique (seulement Club/Amazon/Fnac) |
| **Provenance / date de mise à jour** | — | ❌ (le chatter trace les modifs, mais rien de structuré) |

### 1.4 Mécanismes d'import existants

1. **`comic.import.wizard`** (`comics_collections/wizards/comic_import_wizard.py`, ~1450 lignes)
   - Formats CSV / XLS / XLSX, étapes *upload → mapping → prévisualisation → terminé*.
   - Politique `update` (mettre à jour si l'ISBN existe) ou `create`.
   - Logique `_import_row` : recherche de l'édition **par ISBN** (`comic.isbn`), sinon
     `_find_work` (série+tome, puis série+titre, puis titre), get-or-create de la série,
     de l'éditeur, du genre et des auteurs **par nom exact**.
   - **Pas de JSON** aujourd'hui.
2. **`comic_datasource`**
   - `ComicDataAggregator` : cascade Google Books → Open Library → BnF, résultat normalisé.
   - `comic.edition._apply_datasource_data(data)` : applique un dict normalisé (synopsis,
     pages, dates, ISBN, **téléchargement de la couverture depuis une URL**, auteurs).
   - Crons (désactivés par défaut) : enrichissement quotidien des éditions incomplètes,
     détection hebdomadaire des tomes manquants (`comic.serie._cron_check_missing_volumes`).
   - Les classes `sources/*.py` **n'importent pas Odoo** (`env` est optionnel) : elles sont
     réutilisables telles quelles dans un script externe.

**Conclusion étape 1** : le dict normalisé de `comic_datasource` et `_import_row` couvrent déjà
80 % du besoin. Le nouvel outil doit **produire ce même vocabulaire** pour que l'import réutilise
le code existant.

---

## Étape 2 — Format JSON

### 2.1 Principes

- Noms de champs **identiques** à ceux de l'assistant d'import et du dict `comic_datasource`
  (`serie_name`, `titre_canonique`, `tome`, `editeur`, `date_parution`, `nb_pages`…).
- **Une entrée = une édition**, clé `isbn_13` (dédoublonnage).
- Relations exprimées **par nom** (comme l'import existant), avec identifiants externes
  optionnels quand une source en fournit.
- Texte brut pour le synopsis (l'import le convertit en Html échappé).
- Fichier versionné (`schema_version`) et validé par un JSON Schema avant export.

### 2.2 Schéma proposé

```json
{
  "schema_version": "1.0",
  "generated_at": "2026-11-05T09:30:00+01:00",
  "generator": "comic-nouveautes/0.1",
  "albums": [
    {
      "isbn_13": "9782800123456",
      "isbn_10": null,

      "titre_canonique": "Le Retour du Marsupilami",
      "serie_name": "Marsupilami",
      "tome": 34,
      "type": "bd",

      "editeur": "Dupuis",
      "collection": null,
      "date_parution": "2026-11-14",
      "langue": "fr",
      "format": "cartonne",
      "nb_pages": 48,
      "prix": { "montant": 12.50, "devise": "EUR", "pays": "BE" },

      "auteurs": [
        { "name": "Prénom Nom", "role": "scenariste" },
        { "name": "Prénom Nom", "role": "dessinateur" },
        { "name": "Prénom Nom", "role": "coloriste" }
      ],

      "synopsis": "Texte brut…",

      "couverture": {
        "url": "https://…/cover-large.jpg",
        "url_small": "https://…/cover-small.jpg",
        "fichier": "covers/9782800123456.jpg",
        "sha1": "…"
      },
      "url_produit": "https://www.dupuis.com/…",

      "ids_externes": { "bnf_ark": "ark:/12148/…", "google_books": "…", "openlibrary": "OL…M" },

      "statut_parution": "a_paraitre",
      "sources": [
        { "site": "dupuis", "type": "decouverte", "url": "https://…", "vu_le": "2026-11-05T09:12:00+01:00" },
        { "site": "bnf", "type": "enrichissement", "url": "https://catalogue.bnf.fr/…", "vu_le": "2026-11-05T09:14:00+01:00" }
      ],
      "provenance_champs": { "synopsis": "dupuis", "auteurs": "bnf", "nb_pages": "bnf", "prix": "dupuis" },

      "first_seen": "2026-10-20T08:00:00+02:00",
      "updated_at": "2026-11-05T09:14:00+01:00",
      "content_hash": "sha1 des champs métier, pour ne réimporter que ce qui a changé"
    }
  ]
}
```

Valeurs autorisées alignées sur Odoo : `role` ∈ les 6 valeurs de `comic.work.auteur.line`,
`langue` et `format` ∈ les sélections de `comic.edition`, `type` ∈ celles de `comic.serie`.

### 2.3 Relations

| Relation | Résolution à l'import | Création si absent ? |
|---|---|---|
| **Série** | match sur `name_normalise` = `normalize_title(serie_name)` (plus robuste que le match exact actuel du wizard) | Oui, mais **marquée « à vérifier »** (ex. activité mail) |
| **Album (work)** | 1) ISBN existant → édition connue ; 2) `(serie, tome)` ; 3) `(serie, titre_normalise)` ; 4) `_find_duplicate_candidates` pour signaler un doublon probable | Oui |
| **Éditeur** | nom normalisé + petite table d'alias (`"Éditions Dupuis"`, `"Dupuis SA"` → `Dupuis`) | Oui |
| **Auteurs** | `res.partner` par nom normalisé « Prénom Nom » (les sources donnent souvent « Nom, Prénom ») | Oui |
| Tome absent (hors-série, intégrale) | `tome: null` → pas de conflit avec UNIQUE(serie_id, tome) | — |

À noter : aujourd'hui le wizard cherche les partenaires par nom **exact** et `_apply_datasource_data`
par **`ilike`** (risque d'attacher le mauvais auteur). L'import JSON devrait utiliser une seule
fonction de résolution, partagée.

### 2.4 Couverture

**Recommandation : URL dans le JSON + cache fichier local optionnel, jamais de base64 dans le JSON.**

- base64 : un JSON de 300 nouveautés ferait 50–150 Mo, illisible, et les diffs sont inutilisables.
- URL seule : simple, et `_apply_datasource_data` sait déjà télécharger une URL. Risque : l'URL
  expire (fréquent sur les sites éditeurs).
- URL + `couverture.fichier` (dossier `covers/` à côté du JSON, nommé par ISBN) + `sha1` :
  l'import prend le fichier s'il est fourni (upload d'un ZIP JSON + covers), sinon l'URL.
  Le `sha1` évite de réécrire une image identique.

### 2.5 Prix — décision à prendre

Aucun champ n'accueille le prix. Options :
1. **Ajouter `prix_editeur` (Monetary) + `currency_id` sur `comic.edition`** — recommandé ;
   `comic_shop` peut ensuite proposer ce prix comme `list_price` par défaut à la création du produit.
2. Écrire directement `product.template.list_price` — mélange prix public éditeur et prix de vente
   de ta boutique : déconseillé.
3. Garder le prix dans le JSON seulement.

Attention : les sites éditeurs affichent le **prix public France** ; le prix belge peut différer
(d'où `prix.pays`).

---

## Étape 3 — Architecture de l'outil

### 3.1 Vue d'ensemble

```
            ┌─────────────── Phase 1 : DÉCOUVERTE ───────────────┐
 config ──► │ dupuis │ dargaud │ lombard │ glenat │ casterman │…  │──► candidats
            └──── 1 adaptateur / site, isolé (try/except) ───────┘    {site, url, titre, isbn?}
                                     │
                                     ▼
            ┌──────────── Phase 2 : ENRICHISSEMENT PAR ISBN ─────────┐
            │ a. page produit éditeur (JSON-LD / HTML) si ISBN absent │
            │ b. BnF SRU → Google Books → Open Library                 │
            │    (réutilise comic_datasource/sources/*.py)            │
            └─────────────────────────────────────────────────────────┘
                                     │
                                     ▼
            fusion par champ (priorités) ─► dédoublonnage ISBN-13 ─► validation ─► JSON (+ covers/)
                                     ▲
                       état local SQLite (déjà vus, hash, dates)
```

### 3.2 Arborescence proposée

```
tools/nouveautes/                 # hors des modules Odoo, pas d'import odoo
├── pyproject.toml                # requests, beautifulsoup4, lxml, requests-cache, xmltodict, jsonschema
├── config.toml                   # sites actifs, délais, clé Google Books, filtres
├── nouveautes/
│   ├── cli.py                    # `nouveautes run|discover|enrich|export|status`
│   ├── http.py                   # session unique : UA honnête, robots.txt, rate-limit par hôte,
│   │                             # retries/backoff, cache HTTP (ETag/Last-Modified)
│   ├── discovery/
│   │   ├── base.py               # DiscoveryAdapter.discover() -> list[Candidate]
│   │   ├── mediaparticipations.py# Dupuis, Dargaud, Le Lombard (même groupe, à confirmer si même gabarit)
│   │   ├── glenat.py
│   │   └── casterman.py
│   ├── enrich/
│   │   ├── product_page.py       # parse JSON-LD schema.org/Book puis repli HTML
│   │   └── apis.py               # wrapper sur comic_datasource/sources (BnF, Google, OL)
│   ├── merge.py                  # priorités par champ, provenance_champs
│   ├── state.py                  # SQLite : isbn, first_seen, last_enriched, hash, statut
│   ├── export.py                 # JSON + JSON Schema
│   └── schema/album.schema.json
└── tests/fixtures/               # pages HTML figées pour tester chaque adaptateur hors ligne
```

Réutilisation de `comic_datasource/sources/*.py` : ces classes n'importent pas Odoo, mais
`comic_datasource/__init__.py` importe les modèles Odoo. Deux options : charger le sous-package
`sources` directement par chemin, ou (plus propre) en faire une petite lib partagée. À trancher
à l'implémentation ; la clé Google Books viendra alors de `config.toml` au lieu de
`ir.config_parameter`.

### 3.3 Règles de fusion (proposition)

| Champ | Priorité |
|---|---|
| `isbn_13`, `titre_canonique`, `date_parution`, `prix`, `url_produit`, couverture | **site éditeur** (source de référence pour les albums à paraître) |
| `auteurs` + rôles | BnF (rôles UNIMARC fiables) > éditeur > Google |
| `nb_pages` | BnF > éditeur > Google > OL |
| `serie_name`, `tome` | éditeur > BnF > `parse_bd_title` |
| `synopsis` | éditeur > Google |

Remarque réaliste : pour des albums **à paraître**, la BnF et Google Books n'ont souvent **pas
encore** de notice. Les pages éditeurs seront donc la source principale au départ ; les API
complètent les albums déjà parus (rôles des auteurs, pages, dépôt légal). D'où la ré-interrogation
périodique ci-dessous.

### 3.4 Incrémental et cache

- **État SQLite** : un ISBN déjà enrichi n'est re-téléchargé que si
  `statut_parution = a_paraitre` (re-vérification hebdomadaire jusqu'à parution + 30 jours),
  ou si des champs manquent encore, ou sur `--force`.
- **Cache HTTP** (`requests-cache`, SQLite) avec ETag / Last-Modified : les listes de nouveautés
  ne sont re-téléchargées que si elles ont changé.
- Export : JSON complet + option `--since` pour n'exporter que les albums modifiés
  (`content_hash` différent).

### 3.5 Robustesse et politesse

- Chaque adaptateur tourne dans son propre `try/except` ; un site en erreur produit une ligne
  dans le rapport final (`site, nb candidats, erreurs`) et un code de sortie non nul, sans
  bloquer les autres.
- **Alerte « 0 résultat »** : un site qui renvoyait 20 albums et en renvoie 0 a probablement changé
  de gabarit.
- `robots.txt` lu et respecté (y compris les paramètres d'URL interdits), délai ≥ 2 s par hôte,
  User-Agent honnête du type `ComicsCollectionBot/0.1 (+contact)`, pas de requêtes parallèles
  sur un même hôte.
- Pas de contournement de protection anti-bot : un 403 / captcha = site désactivé, pas de
  Playwright pour forcer le passage.

### 3.6 Faisabilité par site

| Site | Page nouveautés | Rendu | robots.txt (pour `*`) | Protection | Verdict |
|---|---|---|---|---|---|
| **Dupuis** | `/catalogue/FR/parutions.html` → 200, 13 ISBN dans le HTML | serveur + JSON-LD | aucune restriction, sitemap fourni | aucune vue | ✅ **garder** |
| **Dargaud** | `/nouveautes-prochaines-sorties-bd` (+ `/bd-a-paraitre`) → 200, 15 ISBN | serveur (Drupal) | seulement les fichiers internes Drupal | aucune vue | ✅ **garder** |
| **Le Lombard** | `/bd/nouveautes` → 200, 22 ISBN | serveur + JSON-LD | pas de règle `*` ; bloque nommément les robots IA (GPTBot, ClaudeBot…) | reCAPTCHA présent (formulaires) | ✅ **garder**, avec prudence (voir ci-dessous) |
| **Glénat** | `/bd/nouveautes/` (+ `/bd/a-paraitre/`) → 200, 59 ISBN | Next.js : données dans `__NEXT_DATA__` (JSON, en fait le plus simple à lire) ; page lourde (1,7 Mo) | interdit les paramètres `sort_by`, `f[0]`, `mode`, `index`… | aucune vue | ✅ **garder**, sans ces paramètres |
| **Casterman** | non trouvée ; accueil 200 au 1er essai puis délais dépassés | à déterminer | `*` autorisé hors filtres de catalogue | connexions instables, peut-être limitation | ⚠️ **à re-tester** avant de décider |
| **Slumberland** | `www.slumberland.be` : DNS en échec (SERVFAIL) depuis cette machine | — | — | — | ❓ **à vérifier** : quelle URL utilises-tu ? Intérêt réel : multi-éditeurs + **prix belges** |
| **BDGest / Bedetheque** | `bedetheque.com` → **403 Cloudflare** ; `bdgest.com` → 200 | serveur | `Content-Signal: ai-train=no, use=reference` | Cloudflare | ❌ **écarter** de l'automatisation (tu as déjà retiré `comic_bdgest`) |
| **Fnac.be** | `robots.txt` et accueil → **403** | — | illisible (403) | anti-bot actif | ❌ **écarter** |

Points d'attention :
- **Dupuis, Dargaud et Le Lombard appartiennent au même groupe (Média-Participations)** :
  si leurs gabarits sont proches, un adaptateur paramétré suffit.
- Le Lombard (et Casterman) bloquent explicitement les robots d'IA. Ton script n'en est pas un
  (usage personnel, pas d'entraînement), mais le message est clair : volume minimal, délai
  généreux, UA honnête.
- **CGU non lues dans cette passe** : à vérifier pour chaque site retenu avant l'implémentation.
- Les sites éditeurs couvrent leurs propres albums : sans Slumberland (ou équivalent), les
  « petits » éditeurs (Delcourt, Soleil, Futuropolis, Bamboo…) manquent. On peut en ajouter
  au cas par cas, ou passer par la recherche BnF par date pour les séries suivies.

### 3.7 Intégration avec Odoo : trois options

| | a) Script → JSON → import dans le module | b) Script → push direct (API externe) | c) Scraping dans le module (cron) |
|---|---|---|---|
| **Avantages** | Découplé : un site qui casse ne touche pas Odoo ; JSON relisible avant import ; testable hors ligne ; réutilise l'import ISBN existant ; tourne sur ton Mac sans toucher au VPS | Zéro étape manuelle ; données à jour en continu | Tout dans Odoo, planifié, visible dans l'interface ; aucune machine externe |
| **Inconvénients** | Étape manuelle (upload) ou script d'upload à ajouter ; deux formats à maintenir (schéma + import) | Nécessite une clé API et l'accès réseau au VPS ; logique de résolution série/auteur dupliquée hors d'Odoo (ou appel de méthodes serveur) ; XML-RPC / JSON-RPC sont **dépréciés depuis Odoo 19** au profit de l'API JSON-2 ; pas de relecture avant écriture | Scraping lent (2 s/requête) dans un worker Odoo → timeouts de cron, workers bloqués ; dépendances à ajouter à l'image Docker du VPS ; un changement de site produit des erreurs dans Odoo ; mise à jour = redéploiement du module |

**Recommandation : (a)**, en deux temps :
1. Script externe → `nouveautes.json` (+ `covers/`).
2. Côté Odoo, un **assistant d'import JSON** qui réutilise `_import_row` / `_apply_datasource_data`
   et alimente de préférence un **modèle de transit `comic.nouveaute`** (états : *nouveau /
   importé / ignoré*, avec lien vers l'édition créée) plutôt que de créer directement les
   séries et albums. Ainsi les données scrapées, de qualité variable, ne polluent pas le
   catalogue, et tu peux filtrer sur les séries `a_suivre`.

Le package étant en Python pur, il pourra plus tard être appelé par un cron (c) ou
pousser via l'API JSON-2 (b) sans réécriture.

---

## Étape 3 bis — Outil standalone sur la base de Pompe-Recettes (ajout du 2026-11-05)

Contrainte précisée : l'outil doit rester **standalone**, hors du dépôt Odoo. Le projet
`/Users/phde/Projects/Pompe-Recettes` (Python 3.11, ~3 000 lignes) suit déjà le même flux :
*URL de départ → découverte de liens → extraction structurée → export (Markdown / JSON / Notion)*.

### Ce qui est réutilisable

| Brique Pompe-Recettes | Réutilisation pour les BD |
|---|---|
| `project_config.py` (config TOML + surcharge CLI) | ✅ telle quelle (motif) |
| `crawl_progress.py` (reprise d'un crawl, URLs vues, file d'attente) | ✅ base de l'état incrémental, à indexer par ISBN en plus de l'URL |
| `cli.py` → `find_candidate_links`, parcours en largeur limité par `max_pages` | ✅ pour la découverte sur les pages nouveautés |
| `site_overrides.py` → motif « un extracteur par site » + lecture JSON-LD (`extract_recipe_from_ld_json`) | ✅ même motif ; JSON-LD `Book` au lieu de `Recipe` |
| `notion_export/` (création de pages, dédoublonnage par URL source) | 🎁 bonus possible : une base Notion « Nouveautés BD » |
| `models.Recipe`, `recipe-scrapers`, `localize.py`, `ingredient_filter.py`, `markdown.py` | ❌ spécifique aux recettes |

### Ce qui manque ou va à l'encontre des contraintes BD

- `fetcher.py` envoie un **User-Agent de navigateur Chrome** : contraire au « User-Agent honnête ».
- Aucune lecture de `robots.txt`, **aucun délai** entre requêtes.
- `crawl_workers` télécharge **en parallèle sur le même hôte** (`ThreadPoolExecutor`) : incompatible
  avec 1 requête / 2 s par site.
- Pas de clé métier (le dédoublonnage Notion se fait par URL, pas par ISBN), pas
  d'enrichissement par API, pas de fusion multi-sources.
- `cli.py` (923 lignes) est entièrement typé `Recipe` : on ne peut pas y « brancher » les BD
  sans le rendre générique.

### Options

1. **Ajouter les BD dans le package `pompe_recettes`** : rapide, mais mélange deux domaines dans
   un `cli.py` déjà gros. ❌
2. **Même dépôt, deux packages + un noyau commun** — recommandé :
   ```
   Pompe-Recettes/  (renommable en « Pompe »)
   └── src/
       ├── pompe_core/      # fetcher poli (UA honnête, robots.txt, délai par hôte, cache HTTP),
       │                    # config TOML, état de progression, helpers JSON-LD, découverte de liens
       ├── pompe_recettes/  # inchangé au départ, migré vers pompe_core plus tard
       └── pompe_bd/        # adaptateurs éditeurs, enrichissement BnF/Google/OL,
                            # fusion par ISBN, export JSON (+ Notion en option)
   ```
   Deux commandes : `pompe-recettes` et `pompe-bd`. Les recettes continuent de fonctionner ;
   le nouveau fetcher poli leur profitera ensuite.
3. **Nouveau projet séparé** en recopiant les motifs : le plus propre côté isolation, mais on
   duplique config, progression et fetcher. Acceptable si tu préfères ne pas toucher aux recettes.

Pour l'enrichissement, les classes `comic_datasource/sources/*.py` (BnF, Google Books,
Open Library) seraient **copiées** dans `pompe_bd` (elles n'importent pas Odoo) : l'outil ne
dépend alors plus du tout du dépôt Odoo, et le contrat entre les deux reste le JSON de l'étape 2.

⚠️ Pompe-Recettes a des **modifications non commitées** (filtre d'ingrédients, `cli.py`,
`project_config.py`, README) : à commiter avant toute restructuration.

---

## Décisions à prendre avant d'implémenter

1. **Prix** : ajouter `prix_editeur` + `currency_id` sur `comic.edition` ? (recommandé)
2. **Transit** : passer par un modèle `comic.nouveaute` à valider, ou importer directement dans le catalogue ?
3. **Sites** : confirmer Dupuis, Dargaud, Le Lombard, Glénat ; Casterman et Slumberland après re-test (quelle URL Slumberland ?).
4. **Périmètre** : toutes les nouveautés, ou seulement celles des séries `a_suivre` (+ auteurs suivis) ?
5. **Emplacement** : standalone confirmé → option 2 de l'étape 3 bis (package `pompe_bd` + noyau `pompe_core` dans Pompe-Recettes) ou nouveau projet séparé ?
6. Mettre à jour `CLAUDE.md` pour retirer `comic_bdgest` / le fallback BDGest, qui n'existent plus ?
