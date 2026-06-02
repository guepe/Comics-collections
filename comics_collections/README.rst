================
Comic Collection
================

Manage your comic book collection in Odoo 19.
Track series, albums, authors, publishers, loans and duplicates — all in one place.

.. image:: https://img.shields.io/badge/licence-LGPL--3-blue.png
   :target: http://www.gnu.org/licenses/lgpl-3.0-standalone.html
   :alt: License: LGPL-3

.. image:: https://img.shields.io/badge/odoo-19.0-purple.png
   :alt: Odoo 19.0

**Table of contents**

.. contents::
   :local:

Features
========

- **Series & Albums** — Organise your collection by series and individual albums (tomes).
  Each album holds edition metadata: publisher, publication date, language, format,
  cover image, synopsis, page count and purchase links (Club.be, Amazon.be, FNAC.be).

- **Authors** — Link authors to albums with their role: *scénariste*, *dessinateur*,
  *coloriste* or *autre*. Authors are stored as standard ``res.partner`` records and
  benefit from the full Odoo contact management.

- **Publishers & Genres** — Dedicated models for publishers (``comic.editeur``) and
  genres (``comic.genre``) with full list views and easy assignment on series.

- **ISBN management** — EAN-13 / ISBN-10 validation with uniqueness constraint.
  Each edition can carry multiple ISBN records (``comic.isbn``).

- **Loans (Prêts)** — Track who borrowed which album, expected and effective return dates.
  Overdue loans are highlighted automatically.

- **CSV / XLS / XLSX import wizard** — Import large collections from spreadsheets.
  A column-mapping step lets you adapt any file layout to the Odoo schema, with a
  detailed error report for rows that failed.

- **Deduplication** — Automatic detection of probable duplicates based on title
  similarity (``difflib.SequenceMatcher``, threshold 0.85). A merge wizard lets you
  pick the canonical record and archive the duplicate.

- **Purchase links cron** — Weekly scheduled action fills missing purchase-link URLs
  for all editions that have an ISBN.

- **Chatter & tracking** — ``comic.work`` and ``comic.edition`` inherit
  ``mail.thread`` and ``mail.activity.mixin`` for full change history.

Security Groups
===============

+-------------------------+----------------------------------------------+
| Group                   | Access                                       |
+=========================+==============================================+
| Comic User              | Read/write on own records                    |
+-------------------------+----------------------------------------------+
| Comic Manager           | Full access + configuration menu             |
+-------------------------+----------------------------------------------+

Configuration
=============

No specific configuration is required after installation. The module ships with
default genre data and an optional demo dataset.

To adjust the weekly purchase-links cron, go to
**Technical → Automation → Scheduled Actions** and edit
*Comic — Fill missing purchase links*.

Usage
=====

1. Go to **Comics** in the main menu.
2. Create series under **Comics → Series**.
3. Add albums (tomes) under a series via the *Albums* tab or from **Comics → Albums**.
4. Editions (publisher-level metadata: ISBN, date, format) live under
   **Configuration → Advanced → Editions**.
5. Import a spreadsheet via **Comics → Import → Import from file**.
6. Review potential duplicates via **Comics → Deduplication**.

Data Model
==========

::

    comic.serie
      └──< comic.work          (album / tome)
             ├──< comic.work.auteur.line   (partner_id + role)
             └──< comic.edition
                    └──< comic.isbn        (EAN-13, unique)

    comic.pret                 (loan record)
    comic.dedup.pair           (detected duplicate pair)

Known Issues / Roadmap
=======================

- AI-assisted synopsis generation (``comic_ai`` module) is not yet implemented.
- Portal browsing and customer library are provided by the ``comic_shop`` module.
- Multi-language title normalisation currently covers FR, NL and EN articles only.

Bug Tracker
===========

Please report issues at https://github.com/your-org/Comics-collections/issues.

Credits
=======

Authors
-------

* Belspace

Maintainers
-----------

* Belspace — sales@belspace.net
