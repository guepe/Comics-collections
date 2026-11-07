Menus are under **Bandes Dessinées**:

1. **Ma Collection → Séries** — create series; the *Albums* smart button lists their tomes.
2. **Ma Collection → Albums / Tomes** — list grouped by series (kanban and form
   available); create an album with its series, tome number, title, publisher,
   authors and ISBN in a single form.
3. **Ma Collection → Prêts** — record a loan, then click *Retourner* when the
   album comes back. Use the *En retard* filter to find overdue loans.
4. **Ma Collection → Import CSV/Excel** — upload a file, check the column mapping,
   choose the policy for existing albums and run the import.
5. **Catalogues → Auteurs / Éditeurs / Genres** — reference data. Open an author or
   a publisher to see all the series and albums linked to them.
6. **Configuration → Doublons potentiels** (managers) — review detected duplicate
   pairs, merge or ignore them.
7. **Configuration → Référentiel avancé → Éditions** (managers) — edition-level
   records, for albums published in several versions.

**Data model overview**::

    comic.serie
      └──< comic.work                    (album / tome)
             ├──< comic.work.auteur.line (partner_id + role)
             └──< comic.edition
                    └──< comic.isbn      (EAN-13, unique)

    comic.pret                           (loan, private to its creator)
    comic.dedup.pair                     (detected duplicate pair)
