==============================
Comic Collection — BDGest Connector
==============================

Enriches comic book editions by scraping BDGest / Bedetheque.
Provides album search by ISBN or title, detail import and batch enrichment.

.. warning::

   This module performs web scraping of BDGest. Use it only if you have a legal right
   to do so under their terms of service. A mandatory 2-second delay between requests
   is enforced to avoid overloading the server.

**Table of contents**

.. contents::
   :local:

Features
========

- **Search by ISBN** — Looks up an album on BDGest using its EAN-13. If found, imports
  title, series, volume number, authors, publisher and cover image directly into the
  edition record.

- **Search by title** — Returns a list of matching albums on BDGest. The user selects
  the correct match and confirms the import.

- **Batch enrichment** — Select multiple editions in the list view and use the
  *Enrich from BDGest* action to process them all in sequence (2 s delay between calls).

- **BDGest result line model** — ``comic.bdgest.result.line`` stores each search hit so
  you can review and pick the best match.

- **Parser unit tests** — Offline HTML parsing tests included in ``tests/`` (no network
  calls required).

Architecture
============

::

    comic_bdgest/
    ├── scraper/
    │   ├── bdgest_scraper.py   # HTTP client + session management
    │   └── bdgest_parser.py    # BeautifulSoup HTML parser
    ├── models/
    │   └── comic_edition.py    # _inherit comic.edition — adds enrich actions
    └── wizards/
        └── comic_bdgest_enrich_wizard.py

The scraper raises typed exceptions (``BdgestError``, ``BdgestTimeoutError``,
``BdgestBlockedError``, ``BdgestNotFoundError``) so callers can handle each case
appropriately.

Configuration
=============

No API key required. Optionally enable BDGest in **Comics → Configuration → Data Sources**
(the toggle is in the ``comic_datasource`` module settings).

Usage
=====

**Single edition**

1. Open an edition record.
2. Click **Search on BDGest**.
3. Search by ISBN (auto-filled if available) or enter a title.
4. Select the correct album from the result list.
5. Click **Import**.

**Batch enrichment**

1. Go to **Comics → Configuration → Advanced → Editions**.
2. Select one or more editions.
3. Choose **Action → Enrich from BDGest** in the action menu.

Installation
============

Python dependencies:

.. code-block:: bash

   pip install requests beautifulsoup4 lxml

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
