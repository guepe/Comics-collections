Menus are under **Bandes Dessinées**:

1. **Ma Collection → Tableau de bord** — statistics of your own collection,
   collection value, *Exporter (CSV)* and *Inventaire (PDF)* buttons.
2. **Ma Collection → Mes séries** — the series you own albums of, or follow; creating
   a series follows it. The *Albums* smart button lists their tomes; the form shows
   all the authors of its albums with their roles.
3. **Ma Collection → Mes albums** — a cover gallery by default (list view available) of only your albums (creating one here adds it to
   your collection), grouped by series; filters *Prêtés*, *Note ≥ 3★ / 4★*, group by
   genre or series type; *Marquer comme lu / en cours* and *Ajouter à ma wishlist*
   from the action menu. Create an album with its series, tome number, title,
   publisher, authors and ISBN in a single form. On a phone, the ISBN fields show a
   camera button to scan the barcode.
4. **Ma Collection → Ma wishlist** — missing tomes of followed series and manual
   wishes, grouped by series: *Je l'ai*, *Ignorer ce tome*, *Retirer* (for a missing
   tome: stop following the series).
5. **Ma Collection → Ma bibliothèque** — a cover gallery by default (series, tome,
   stars, reading status, wishlist) of your library entries: collection,
   wishlist, reading status, star rating, comments, purchase price and estimated
   value (the *Print* menu offers the PDF inventory).
6. **Ma Collection → Prêts** — record a loan, then click *Retourner* when the
   album comes back. Use the *En retard* filter to find overdue loans.
7. **Ma Collection → Import CSV/Excel** — upload a file, check the column mapping,
   choose the policy for existing albums and run the import.
8. **Catalogues → Auteurs / Éditeurs / Genres** — reference data. Open an author or
   a publisher to see all the series and albums linked to them, and the co-authors
   the author has often worked with.
9. **Configuration → Doublons potentiels** (managers) — review detected duplicate
   pairs, merge or ignore them.
10. **Configuration → Référentiel avancé** (managers) — *Tous les albums*, *Toutes
    les séries* (the full shared catalogue) and *Éditions*.

**Data model overview**::

    comic.serie
      └──< comic.work                    (album / tome)
             ├──< comic.work.auteur.line (partner_id + role)
             └──< comic.edition
                    └──< comic.isbn      (EAN-13, unique)

    comic.customer.album                 (personal library, unique per partner + edition)
    comic.pret                           (loan, private to its creator)
    comic.dedup.pair                     (detected duplicate pair)
