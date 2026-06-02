================
Comic Datasource
================

Multi-source data enrichment connector for comic book editions.
Automatically fetches metadata, covers and authors from Google Books, Open Library,
BnF (French National Library) and BDGest.

**Table of contents**

.. contents::
   :local:

Features
========

- **Aggregated search** — A single wizard searches all enabled sources in priority order
  and merges the results field by field. First non-empty value wins, with field-specific
  overrides (e.g. BnF wins for *date_dépôt_légal*; Google wins for synopsis).

- **Source cascade** — ``Google Books → Open Library → BnF SRU → BDGest``

- **Cover retrieval** — Fetches the best available cover image (Google extraLarge >
  Open Library L > BDGest).

- **Missing-tome detection** — A wizard compares the editions already in a series against
  data returned by the sources and lists tomes that are absent from your catalogue.

- **Serie update wizard** — Batch-enrich all incomplete editions in a series in one click.

- **Scheduled enrichment** — Two optional cron jobs (disabled by default):

  * *Daily*: enrich editions missing synopsis, cover or ISBN.
  * *Weekly*: detect missing tomes across all series.

- **Search result line model** — ``comic.datasource.result.line`` stores each source hit
  so you can compare and select the best match before importing.

Sources
=======

+-------------+-----------------------+-------------------+
| Source      | Authentication        | Rate limit        |
+=============+=======================+===================+
| Google Books| Free API key (optional)| 1 000 req/day    |
+-------------+-----------------------+-------------------+
| Open Library| None                  | Unlimited         |
+-------------+-----------------------+-------------------+
| BnF SRU     | None                  | Unlimited         |
+-------------+-----------------------+-------------------+
| BDGest      | Optional login        | 2 s delay enforced|
+-------------+-----------------------+-------------------+

Configuration
=============

1. Go to **Comics → Configuration → Data Sources**.
2. Optionally enter a **Google Books API key** to raise the daily quota to 1 000 requests.
3. Enable or disable individual sources with the toggle buttons.
4. Toggle **BDGest** separately — scraping is opt-in for legal compliance.
5. Activate the scheduled cron jobs if you want automatic enrichment.

Usage
=====

**Enrich a single edition**

Open any edition (``comic.edition``) and click **Enrich from online sources**.
The wizard searches by ISBN first, then by title. Select the best result and confirm.

**Detect missing tomes**

Open a series and click **Detect missing tomes**.
The wizard lists tomes found online but absent from your catalogue.
Check the ones you want and click **Add to wishlist**.

**Batch update a series**

Open a series and click **Update all editions**.
All editions missing data will be enriched automatically.

Installation
============

Python dependencies (install on the Odoo server):

.. code-block:: bash

   pip install requests beautifulsoup4 lxml xmltodict

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
