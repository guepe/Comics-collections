**Link an edition to the webshop**

1. Open an edition record.
2. Click **Sync to shop** (or **Create product** if none exists yet).
3. The product is created in the e-commerce catalogue and can be published
   from the website backend.

**Customer portal**

Customers access their library at ``/my/library`` after logging in.
They can add albums manually (searching by ISBN or title) or receive them
automatically when purchasing through the webshop or at the Point of Sale.

**Point of Sale**

Comic products appear in the POS interface. Scanning an ISBN barcode selects
the correct product automatically. If a customer is identified at checkout, a
``comic.customer.album`` record is created automatically for the purchased edition.

**Data model**::

    comic.edition
      └── product_tmpl_id → product.template

    comic.customer.album
      partner_id, edition_id, work_id (compute)
      source, etat_lecture, dans_collection, dans_wishlist
      note, commentaire, date_ajout
