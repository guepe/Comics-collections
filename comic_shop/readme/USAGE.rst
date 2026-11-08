**Put an album on sale**

1. Open an edition and click *Créer produit* (or *Resynchroniser* to
   refresh an existing product). From a series, *À publier* creates the products
   of all its editions that have an ISBN.
2. Set the price and publish the product from the website backend.

**Point of Sale**

Scanning an ISBN selects the product. When a customer is set on the order, the
album is added to their library at payment.

**Customer portal**

Customers open *Ma Bibliothèque BD* (``/my/library``) from their portal, filter
collection / wishlist, update reading status and star rating, open their
*Tableau de bord BD* (``/my/library/dashboard``), share their wishlist
(*Partager ma wishlist* → link to copy, revocable), and add albums with
*Ajouter une BD*. The *Ajouter automatiquement mes achats à ma bibliothèque*
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
