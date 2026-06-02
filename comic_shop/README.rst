==========
Comic Shop
==========

Sell comic books online and manage your customers' reading libraries.
Extends ``comics_collections`` with product synchronisation, a webshop, a POS
integration and a customer portal library.

**Table of contents**

.. contents::
   :local:

Features
========

**Product synchronisation**

- Each ``comic.edition`` can be linked to a ``product.template``.
- A *Sync to shop* button creates or updates the product from edition metadata
  (title, cover, description, price).
- Bulk product creation is available directly from the series form view.
- An ``uninstall_hook`` cleans up shop-specific fields when the module is removed.

**Webshop**

- Browse comics by series, genre or author on a dedicated shop page (``/shop``).
- Product pages display the comic cover, synopsis, volume number, authors and links
  to external retailers.
- Search and filtering by genre and series are available out of the box.

**Customer portal library** (``/my/library``)

- Authenticated customers can maintain a personal reading library:
  ``comic.customer.album`` records track each album's ownership status, reading state,
  rating and notes.
- Albums can be marked as *In collection*, *In wishlist* or both.
- Customers can rate albums (0–5 stars) and add free-text comments.
- The portal displays albums grouped by series with cover thumbnails.

**Point of Sale integration**

- POS category and barcode fields are synchronised from the edition's ISBN.
- Comic products are available in the POS interface (``available_in_pos = True``).

**Sale order integration**

- ``comic.sale.order`` extends ``sale.order`` to automatically create
  ``comic.customer.album`` records when an order is confirmed.

Data Model
==========

::

    comic.edition
      └── product_tmpl_id → product.template   (added by this module)

    comic.customer.album
      partner_id, edition_id, work_id (compute)
      source, etat_lecture, dans_collection, dans_wishlist
      note, commentaire, date_ajout

    comic.sale.order                            (_inherit sale.order)

Configuration
=============

1. Install ``comic_shop`` on top of ``comics_collections`` and ``comic_datasource``.
2. Go to **Comics → Configuration → Shop Settings** and configure the default
   product category and POS category for comic books.
3. Use **Comics → Series → [a series] → Create products** to bulk-create webshop
   products for all editions in a series.

Usage
=====

**Link an edition to the webshop**

1. Open an edition record.
2. Click **Sync to shop** (or **Create product** if none exists yet).
3. The product is created in the e-commerce catalogue and can be published
   from the website backend.

**Customer portal**

Customers access their library at ``/my/library`` after logging in.
They can add albums manually or receive them automatically when they purchase
through the webshop.

**Point of Sale**

Comic products appear in the POS interface. Scanning an ISBN barcode selects
the correct product automatically.

Installation
============

Depends on: ``comics_collections``, ``comic_datasource``, ``sale``, ``website``,
``website_sale``, ``point_of_sale``, ``portal``.

These are all standard Odoo 19 modules — no extra Python packages required.

Known Issues / Roadmap
=======================

- POS integration is partial: sales are recorded but the POS receipt template
  does not yet display comic-specific fields.
- The AI synopsis generation module (``comic_ai``) is not yet implemented.

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
