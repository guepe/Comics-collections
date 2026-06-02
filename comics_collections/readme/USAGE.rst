1. Go to **Comics** in the main menu.
2. Create series under **Comics → Series**.
3. Add albums (tomes) under a series via the *Albums* tab or from **Comics → Albums**.
4. Editions (publisher-level metadata: ISBN, date, format) live under
   **Configuration → Advanced → Editions**.
5. Import a spreadsheet via **Comics → Import → Import from file**.
6. Review potential duplicates via **Comics → Deduplication**.

**Data model overview**::

    comic.serie
      └──< comic.work          (album / tome)
             ├──< comic.work.auteur.line   (partner_id + role)
             └──< comic.edition
                    └──< comic.isbn        (EAN-13, unique)

    comic.pret                 (loan record)
    comic.dedup.pair           (detected duplicate pair)
