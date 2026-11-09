**Put an album on sale**

1. Open an edition and click *Créer produit* (or *Resynchroniser* to
   refresh an existing product). From a series, *À publier* creates the products
   of all its editions that have an ISBN.
2. Set the price and publish the product from the website backend.
3. Tell the customers: when customers follow the series or have the album in their
   wishlist, the edition shows *N client(s) attendent cet album* → *Prévenir les
   clients*. The wizard shows how many customers will be notified, the recipients
   and a preview of the email, then sends it (once per album and customer, trace in
   the edition chatter). *Publier les albums* on a series opens the same wizard;
   *Prévenir les clients (mise en vente)* is also in the action menu of series and
   editions.

**Point of Sale**

Scanning an ISBN selects the product. When a customer is set on the order, the
album is added to their library at payment.

**Customer portal**

Customers open *Ma Bibliothèque BD* (``/my/library``) from their portal, filter
collection / wishlist, update reading status and star rating, open their
*Tableau de bord BD* (``/my/library/dashboard``), share their wishlist
(*Partager ma wishlist* → link to copy, revocable), and add albums with
*Ajouter une BD* (the *Scanner* button reads the ISBN barcode with the phone
camera; HTTPS is required, manual entry stays available). *Mes séries*
(``/my/library/series``) lists the followed series and those of the library, with
*Suivre la série* / *Série suivie* buttons, also shown on the shop series page and on
an album of the library. The *Ajouter automatiquement mes achats à ma bibliothèque*
switch disables the automatic addition of their purchases.

**Moderation**

*Comic Shop → À valider (portail)* lists the albums created by customers: use
*Valider*, or *Refuser* to open the refusal wizard (duplicate of an existing
album, or incorrect record, with an optional message to the customer).
*Comic Shop → Bibliothèques clients* lists all customer library entries.

**Data model**::

    comic.edition
      └── product_tmpl_id → product.template

    comic.customer.album        (defined in comics_collections, extended here)
      + source « achete_ici », sale_order_line_id, pos_order_line_id
      + auto_created, has_product
