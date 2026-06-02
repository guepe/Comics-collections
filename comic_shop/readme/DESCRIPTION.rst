Sell comic books online and manage your customers' reading libraries.
Extends ``comics_collections`` with product synchronisation, a webshop, a POS
integration and a customer portal library.

**Product synchronisation**

Each ``comic.edition`` can be linked to a ``product.template``. A *Sync to shop*
button creates or updates the product from edition metadata (title, cover, synopsis,
price). Bulk product creation is available directly from the series form view.
An ``uninstall_hook`` cleans up shop-specific fields when the module is removed.

**Webshop**

Browse comics by series, genre or author on a dedicated shop page (``/shop``).
Product pages display the cover, synopsis, volume number, authors and links to
external retailers. Search and filtering by genre and series are available out of
the box.

**Customer portal library** (``/my/library``)

Authenticated customers can maintain a personal reading library via
``comic.customer.album`` records. Albums can be marked as *In collection* or
*In wishlist*, rated (0–5 stars) and annotated with free-text comments.

**Point of Sale integration**

POS category and barcode fields are synchronised from the edition's ISBN.
Comic products are available in the POS interface (``available_in_pos = True``).
Sales at the POS automatically create ``comic.customer.album`` records when a
customer is identified.

**Sale order integration**

Confirming a sale order automatically creates ``comic.customer.album`` records
for the buyer.
