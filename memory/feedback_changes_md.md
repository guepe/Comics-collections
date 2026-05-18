---
name: feedback-changes-md
description: Toujours mettre à jour CHANGE.md après chaque session ou groupe de modifications significatives
metadata:
  type: feedback
---

Après chaque session de travail (ou groupe de modifications significatives), ajouter une entrée datée dans `CHANGE.md` à la racine du projet.

**Why:** Instruction ferme de l'utilisateur — le journal des modifications doit rester à jour pour assurer la continuité entre les sessions.

**How to apply:** Format à respecter :
```
## YYYY-MM-DD (suite N) — Titre court

### US-XXX — Titre
Fichiers modifiés/créés, description des changements.

### Correctif — Titre
Description du bug et du fix.
```
Inclure : fichiers créés/modifiés, méthodes ajoutées, bugs corrigés, décisions techniques, erreurs rencontrées et leurs solutions.
Ne pas résumer ce qui est déjà dans USER_STORIES — aller dans le détail technique.
