Sell comic books online and at the counter, and give customers their own
library on the portal. Extends ``comics_collections`` and ``comic_datasource``.

**Product synchronisation**

A ``comic.edition`` can be linked to a ``product.template`` (*Créer produit*).
Name (``Série — Titre (T1)``), cover, description and barcode (ISBN-13) follow the
edition, and are resynchronised when the series, the album or an ISBN changes.
A barcode typed by hand is kept, and *Available in POS* is only set when the
product is created. Products can be bulk-created from a series for all editions
that have an ISBN. An ``uninstall_hook`` cleans up shop-specific data.

**Webshop pages**

``/shop/series``, ``/shop/auteurs`` and ``/shop/editeurs`` browse the comics on
sale (published and active products only), with filters on series type. An
author page only exists for partners credited on an album on sale.

**Customer library** (``/my/library``)

Each customer keeps their own library (``comic.customer.album``, the personal
library of ``comics_collections``): *Ma collection* and *Ma wishlist*, reading
status, star rating and comments, a dashboard (``/my/library/dashboard``), with pagination and
sorting. Albums bought outside the shop are added by ISBN or title search
(local catalogue + online sources); cover downloads are restricted to the known
source hosts. Putting an owned album in the wishlist keeps it in the collection;
adding it to the collection removes it from the wishlist. A customer can share
their wishlist through a secret, revocable link (``/wishlist/<token>``): a
read-only page with covers and links to the albums on sale, nothing else.

**Purchases**

Confirmed sale orders and paid POS orders add the albums to the buyer's library
(source *Acheté ici*), unless the customer switched this off on their library page.
Cancelled orders and POS refunds remove the entries they created.

**Moderation of portal records**

Series, albums and publishers created from the portal are flagged *À valider*
and a review activity is scheduled for a manager. Managers validate them, or
refuse them — as a duplicate of an existing album (the customer's library entry
and ISBN are moved onto it) or as incorrect (removed) — and the customer is
notified. Products cannot be created for albums awaiting validation.
