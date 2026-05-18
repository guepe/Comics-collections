# DESIGN SPECS — Comic Collection
> Source : Claude Design handoff (mai 2026). Variante choisie : **A — Sobre éditorial**.
> À utiliser pour la Phase 4 (interface complète).

---

## Palette

| Token | Valeur | Usage |
|---|---|---|
| `INK` | `#022E51` | Sidebar bg, texte fort, titres |
| `INK_2` | `#2a4a6a` | Texte secondaire |
| `INK_3` | `#6f88a4` | Texte muet, labels, métadonnées |
| `CREAM` | `#f3eee4` | Fond de l'app (content area) |
| `PAPER` | `#ffffff` | Cartes, topbar, filter bar |
| `ACCENT` | `#B74803` | CTA, badge actif, barre de progression |
| `STAR` | `#CC6D3D` | Étoiles de notation |
| `SOFT` | `#A3B4C8` | Tonalité bordure |
| `BORDER` | `rgba(2,46,81,0.10)` | Bordures légères |
| `BORDER_STRONG` | `rgba(2,46,81,0.20)` | Bordures marquées |

---

## Typographie

| Rôle | Police | Taille | Poids |
|---|---|---|---|
| Titre h1 (Topbar) | `Instrument Serif` | 26px | 400 |
| Titre carte album | `Instrument Serif` | 14px | 400 |
| Titre section Sidebar | `Instrument Sans` | 10px | 600 / letterspacing 0.14em |
| Texte nav Sidebar | `Instrument Sans` | 13px | 400 / 500 actif |
| Nom série (petites caps) | `Instrument Sans` | 9px | 600 / letterspacing 0.12em / uppercase |
| Métadonnées (tome, année) | `Instrument Sans` | 10px | 400 / tabular-nums |
| Bouton CTA | `Instrument Sans` | 12px | 600 |

> Google Fonts : `https://fonts.googleapis.com/css2?family=Instrument+Sans:wght@400;500;600&family=Instrument+Serif&display=swap`

---

## Layout — AppShell (1440×900)

```
┌──────────────────────────────────────────────────────┐
│  Sidebar 232px  │  Topbar 64px                        │
│                 ├─────────────────────────────────────┤
│                 │  FilterBar 48px                     │
│                 ├─────────────────────────────────────┤
│                 │                                     │
│                 │  Content area (padding 20px 28px)   │
│                 │  Fond CREAM                         │
│                 │                                     │
└──────────────────────────────────────────────────────┘
```

---

## Sidebar (232px)

- **Fond** : `INK` (`#022E51`)
- **Logo** : "Ma Collection / Bandes dessinées" avec icône orange `ACCENT`
- **Sections** :
  - *Ma collection* : Séries (count), Albums (count), Prêts (badge rouge nb retard), Wishlist (count)
  - *Catalogues* : Auteurs, Éditeurs, Genres
  - *Outils* : Import, Statistiques, Paramètres
- **Item actif** : `rgba(255,255,255,0.08)` bg + texte `#fbf7ef`
- **Item inactif** : texte `rgba(251,247,239,0.65)`
- **Profil** (bas) : avatar initiales + nom + email

---

## Topbar (64px)

- **Fond** : `PAPER`
- **Breadcrumb** : `INK_3` 11px → `INK_2` avec chevron SVG
- **H1** : `Instrument Serif` 26px `INK` + count `INK_3` 13px
- **Recherche** : input 220px, fond `#f3f6fa`, placeholder `INK_2`
- **View switcher** : kanban / list / form — actif fond `CREAM`
- **CTA** : "Nouvel album" — fond `ACCENT`, blanc, 12px 600

---

## FilterBar (48px)

- **Fond** : `PAPER`
- **Chip actif** : fond `#fde6d2`, texte `ACCENT`, bordure `#f5cfa2`
- **Chip inactif** : fond `#eef1f5`, texte `INK_2`, bordure `BORDER`
- **Bouton "+ Ajouter"** : tirets `BORDER_STRONG`
- **Groupé par / Tri** : `INK_3` + valeur `INK_2` 500 + chevron

---

## Carte Album — Style A (sobre éditorial)

```
┌──────────────────────┐  200px
│                      │
│     Couverture       │  270px (SVG éditorial)
│     stylisée         │
│                      │
├──────────────────────┤
│ SÉRIE (small caps)   │  9px, INK_3, 0.12em
│ Titre de l'album     │  14px Serif, INK, h=34px max
│ T.24 · 1979   ★★★★☆ │  10px INK_3 + étoiles
└──────────────────────┘  14px padding
```

- **Carte** : fond `PAPER`, bordure `BORDER`, `border-radius: 4px`
- **Grille** : `repeat(5, 1fr)`, gap `16px`

---

## Couverture SVG (Cover component)

Format **100% × 100%** du conteneur. Composition :
- Bande accent (6px) en haut — couleur `pal[2]` (accent)
- Nom série — 8px 600 uppercase, `pal[1]` (fg), `opacity: 0.75`
- Filet fin 1px séparation — `pal[1]` `opacity: 0.35`
- Titre centré (max 3 lignes, 14 chars/ligne) — `Instrument Serif` 21px (ou 17px si 3 lignes), `pal[1]`
- Numéro de tome en bas — "TOME" 7px + chiffre 28px Serif couleur `pal[2]`
- Filet bas 1px — `pal[1]` `opacity: 0.25`

Palette par série (`[bg, fg, accent]`) :

| Série | bg | fg | accent |
|---|---|---|---|
| Astérix | `#f4c842` | `#1a1a1a` | `#c5341d` |
| Tintin | `#f5e6c8` | `#c5341d` | `#1a3a8a` |
| Blacksad | `#1a1a1a` | `#f0e0c0` | `#c5341d` |
| Largo Winch | `#0a1f3d` | `#e8b339` | `#c5341d` |
| Lanfeust | `#5b2a8a` | `#f0c8ff` | `#ffd700` |
| Spirou | `#c5301f` | `#fdf5e6` | `#1a1a1a` |
| Lucky Luke | `#e8c478` | `#5a3416` | `#c5341d` |
| XIII | `#16171b` | `#c5341d` | `#e0dcd0` |
| Thorgal | `#1a4a6a` | `#f0e0c0` | `#b8a060` |
| Yoko Tsuno | `#e8a4c8` | `#143a4a` | `#00a4a4` |
| Schtroumpfs | `#3f86d4` | `#ffffff` | `#f4c842` |
| Gaston | `#fdf5e6` | `#1a1a1a` | `#1aa050` |

---

## Badges état de lecture

| État | bg | fg | dot |
|---|---|---|---|
| `lu` | `#e0efe2` | `#1f6a3a` | `#2d9550` |
| `en_cours` | `#fde6c8` | `#9c5410` | `#e8901a` |
| `non_lu` | `#ece8df` | `#5a544c` | `#8a8278` |

---

## Étoiles (Stars)

- 5 étoiles SVG path `M6 1l1.5 3.2 3.5 0.4 -2.6 2.4 0.7 3.4L6 8.7 2.9 10.4l0.7 -3.4L1 4.6l3.5 -0.4z`
- Pleine : `STAR` (`#CC6D3D`)
- Vide : `rgba(0,0,0,0.12)`
- Taille : 9px (carte) / 11px (wishlist)

---

## Carte Wishlist

Même structure que carte A + :
- **Cœur** (top-left) : cercle 22px fond `ACCENT`, icône cœur blanc
- **Prix** : `INK` 11px 600, top-right de la zone info
- **Boutons Club.be / Amazon** : `flex 1`, hauteur 24px, bordure `BORDER`, fond `PAPER`, point coloré (orange `#e8901a` / vert `#1aa050`)

### Bandeau stats Wishlist

Fond `PAPER`, bordure `BORDER`, borderRadius 6px, padding 16/22px :
- Albums à acquérir, Séries concernées, Valeur estimée, Disponible Club.be
- Valeurs : `Instrument Serif` 26px `INK`
- Bouton "Exporter" : outline `BORDER_STRONG`
- Bouton "Marquer comme acquis" : `ACCENT`

---

## Screens à implémenter en Phase 4

| Écran | US | Statut design |
|---|---|---|
| Kanban Albums (style A) | US-009, US-010 | ✅ Validé |
| Wishlist | US-014 | ✅ Validé |
| Menus complets + navigation | US-008b | ✅ Validé (sidebar) |
| Formulaire album enrichi | US-011 | À designer |
| Dashboard statistiques | US-013 | À designer |
| Filtres avancés | US-012 | ✅ Validé (filter bar) |

---

## Notes d'implémentation Odoo

- Les vues Kanban Odoo utilisent des templates QWeb — adapter le `Cover` en HTML/CSS statique (pas de SVG React)
- `Instrument Sans` + `Instrument Serif` à charger via `web.assets_frontend` ou `web.assets_backend`
- Les couleurs `CREAM`, `INK`, `ACCENT` à centraliser dans un fichier SCSS custom
- Les badges état → utiliser les `decoration-*` attributes d'Odoo ou des champs `html_class` computed
- La barre de progression série → widget `progressbar` natif Odoo avec `max_value`
