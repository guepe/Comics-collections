Menus are under **Bandes Dessinées**:

1. **Ma Collection → Tableau de bord** — statistics of your own collection.
2. **Ma Collection → Séries** — create series; the *Albums* smart button lists their tomes.
3. **Ma Collection → Albums / Tomes** — your albums (*Ma collection* filter on by
   default; remove it, or use *Catalogues → Tous les albums*, to see the whole
   shared catalogue), grouped by series; filters *Prêtés*, *Note ≥ 3★ / 4★*, group by
   genre or series type; *Marquer comme lu / en cours* from the action menu.
   Create an album with its series, tome number, title, publisher, authors and
   ISBN in a single form.
4. **Ma Collection → Ma bibliothèque** — your library entries: collection,
   wishlist, reading status, star rating, comments.
5. **Ma Collection → Prêts** — record a loan, then click *Retourner* when the
   album comes back. Use the *En retard* filter to find overdue loans.
6. **Ma Collection → Import CSV/Excel** — upload a file, check the column mapping,
   choose the policy for existing albums and run the import.
7. **Catalogues → Auteurs / Éditeurs / Genres** — reference data. Open an author or
   a publisher to see all the series and albums linked to them.
8. **Configuration → Doublons potentiels** (managers) — review detected duplicate
   pairs, merge or ignore them.
9. **Configuration → Référentiel avancé → Éditions** (managers) — edition-level
   records, for albums published in several versions.

**Data model overview**::

    comic.serie
      └──< comic.work                    (album / tome)
             ├──< comic.work.auteur.line (partner_id + role)
             └──< comic.edition
                    └──< comic.isbn      (EAN-13, unique)

    comic.customer.album                 (personal library, unique per partner + edition)
    comic.pret                           (loan, private to its creator)
    comic.dedup.pair                     (detected duplicate pair)
