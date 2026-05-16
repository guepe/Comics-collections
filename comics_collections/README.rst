================
Comic Collection
================

**Gérez votre collection de bandes dessinées dans Odoo 19.**

.. image:: https://img.shields.io/badge/licence-LGPL--3-blue.png
   :target: http://www.gnu.org/licenses/lgpl-3.0-standalone.html
   :alt: License: LGPL-3

.. image:: https://img.shields.io/badge/odoo-19.0-purple.png
   :alt: Odoo 19.0

Description
===========

Ce module permet de gérer une collection personnelle de bandes dessinées
directement dans Odoo 19.

Fonctionnalités :

* **Séries et albums** avec couvertures, synopsis, auteurs, éditeurs
* **Vues Kanban** avec grille de couvertures et barre de progression des séries
* **Wishlist** pour les tomes à acquérir
* **État de lecture** (Non lu / En cours / Lu) et **note** par album
* **Enrichissement automatique** depuis Google Books (ISBN ou titre), Open Library, BnF
* **Import CSV/XLS/XLSX** avec wizard de mapping et rapport d'erreurs
* **Liens d'achat** auto-générés vers Club.be, Amazon.be et FNAC.be
* Auteurs liés aux contacts Odoo natifs (``res.partner``)
* Gestion des genres, éditeurs, et historique via chatter

Installation
============

1. Copier le module ``comics_collections`` dans votre répertoire ``addons``
2. Mettre à jour la liste des modules dans Odoo
3. Installer *Comic Collection* depuis le menu Apps

Pour utiliser l'enrichissement depuis Google Books :

* Créer une clé API gratuite sur `console.cloud.google.com <https://console.cloud.google.com>`_
* La saisir dans *Configuration → Paramètres → Sources de données BD*

Aucune dépendance Python supplémentaire n'est requise pour le module de base.

Le module ``comic_datasource`` (optionnel) ajoute le wizard de recherche
multi-sources et l'enrichissement automatique depuis les APIs externes.

Configuration
=============

Après installation :

1. Accéder à **Bandes Dessinées → Configuration** (groupe Gestionnaire)
2. Configurer la clé API Google Books si souhaité
3. Créer vos premiers genres et éditeurs (ou utiliser les données de démonstration)

Groupes de sécurité
-------------------

* **Utilisateur BD** : accès en lecture/écriture à sa propre collection
* **Gestionnaire BD** : accès complet + configuration

Usage
=====

**Ajouter une série :**

* *Ma Collection → Séries → Nouveau*
* Ou importer depuis le wizard *Rechercher des BD* (module ``comic_datasource``)

**Importer une collection existante :**

* *Ma Collection → Import CSV/Excel*
* Télécharger le modèle de fichier, le remplir, l'uploader

**Gérer la wishlist :**

* Cocher *Dans ma wishlist* sur un album
* Accéder à la vue dédiée *Wishlist* dans le menu

Roadmap
=======

* Module IA (génération de synopsis via Claude / OpenAI)
* Gestion des prêts
* Dashboard statistiques

Bug Tracker
===========

Les bugs peuvent être signalés sur le dépôt GitHub du projet.

Credits
=======

Authors
-------

* Belspace

Maintainers
-----------

* Belspace (sales@belspace.net)

This module is maintained by Belspace.
