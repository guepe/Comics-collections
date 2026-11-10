# Releases — Comic Collection

Deux dépôts, même procédure : public `guepe/Comics-collections` (modules gratuits, LGPL-3) et
privé `guepe/Comics-collections-pro` (modules payants, OPL-1).

## Branches

| Branche    | Rôle                                                                  |
| ---------- | --------------------------------------------------------------------- |
| `19.0-dev` | Développement : tous les commits et push du quotidien.                |
| `19.0`     | Versions publiées uniquement : lue par l'Odoo Apps Store et le staging. |

Les deux branches lancent la CI (tests + pre-commit). La CI du dépôt privé récupère la même
branche du dépôt public (`19.0-dev` ↔ `19.0-dev`, `19.0` ↔ `19.0`).

Les mots-clés `Closes #n` des commits ferment les issues quand le commit arrive sur `19.0`
(branche par défaut), c'est-à-dire **à la release**.

## Versions

- Chaque module garde sa version dans son manifest (`19.0.X.Y.Z`) : la monter dès qu'un module
  change (correctif → Z, fonctionnalité → Y, rupture / migration lourde → X).
- Chaque release pose **un tag par dépôt** : `v19.0.X.Y.Z` (numérotation propre au dépôt). Le
  message du tag liste les modules et leurs versions, puis les entrées de `CHANGE.md` depuis la
  release précédente ; le workflow `release.yml` en fait la GitHub Release.

## Publier

Depuis la racine du dépôt à publier, sur `19.0-dev`, tout commité et poussé, CI verte :

```bash
python3 ../Comics-collections/tools/release.py 19.0.1.1.0           # vérifications (dry-run)
python3 ../Comics-collections/tools/release.py 19.0.1.1.0 --apply   # publie
```

(dans le dépôt public : `python3 tools/release.py …`)

Le script refuse de publier si : la branche n'est pas `19.0-dev`, l'arbre n'est pas propre ou pas
à jour avec `origin`, `19.0` ne peut pas avancer en fast-forward, la CI du commit n'est pas verte,
un module modifié n'a pas monté sa version, ou `CHANGE.md` n'a pas de nouvelle entrée. Il pousse
ensuite le commit sur `19.0` sans changer de branche locale (les dossiers montés dans Docker ne
bougent pas) et pousse le tag.

Une évolution qui touche les deux dépôts se publie dans l'ordre : **public d'abord**, puis privé.

## Après une release

- **Staging** : `git pull` de `19.0` dans les deux dépôts, puis
  `odoo -d <base> -u <modules> --stop-after-init` et redémarrage.
- **Odoo Apps Store** : apps.odoo.com relit la branche `19.0` des dépôts enregistrés (le dépôt
  privé y est relié par une clé SSH de déploiement fournie par le site).
