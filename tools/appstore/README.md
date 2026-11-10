# Pages et captures App Store

Outils qui ont produit `static/description/` de `comics_collections` et `comic_shop`
(pages `index.html`, captures `screenshot_*.png` / `shop_*.png`, bannières `banner.png`).

- `gen_pages.py` : génère les deux `index.html` (styles en ligne, Bootstrap, Font Awesome —
  l'App Store retire `<style>` et `<script>`). `python3 tools/appstore/gen_pages.py .`
- `dataset.py`, `covers.py` : catalogue **fictif** (séries, auteurs, éditeurs, ISBN 979-10-999…)
  et couvertures générées avec Pillow — jamais d'images ni de séries réelles (droits d'auteur).
- `seed_demo.py`, `seed_fix.py` (via `shell.sh`) : remplissent une base **jetable**
  (`appstore_demo`, admin/admin, client portail camille/camille) : bibliothèque, wishlist,
  prêts, produits publiés, wishlist partagée, assistant IA en prévisualisation…
- `shots.js` (Playwright) : captures 1440×900 ; `finalize.py` : recadrage, optimisation PNG,
  bannières 1200×600.

Ne jamais lancer ces scripts sur la base `odoo` (données personnelles) : utiliser un conteneur
à part sur une base jetable (voir l'en-tête de chaque script), puis la supprimer.
