# CHANGE.md

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
