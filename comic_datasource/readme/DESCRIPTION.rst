Multi-source metadata enrichment for comic book editions.
Fetches titles, series, tomes, publishers, authors, synopses, page counts and
covers from Google Books, Open Library and the BnF (Bibliothèque nationale de
France).

**Source cascade** — ``Google Books → Open Library → BnF SRU`` by default
(order stored in the ``comic.datasource_order`` system parameter). Results are
merged field by field: the first non-empty value wins.

+--------------+-------------------------+------------------------------+
| Source       | Authentication          | Rate limit                   |
+==============+=========================+==============================+
| Google Books | Free API key (optional) | ~1 000 req/day with a key    |
+--------------+-------------------------+------------------------------+
| Open Library | None                    | Unlimited                    |
+--------------+-------------------------+------------------------------+
| BnF SRU      | None                    | Unlimited                    |
+--------------+-------------------------+------------------------------+

**Enrichment rules**

- Only **empty fields** are filled: data entered by a user is never overwritten.
- Editions without ISBN are only matched by title when the normalised title is
  identical and the series / tome are consistent; otherwise nothing is applied.
- Only complete publication dates are kept: a year alone (``1995``) does not
  become a fictitious ``1995-01-01``.
- Authors are matched on their exact name (case-insensitive), preferring contacts
  already credited on an album, never companies; missing authors are created.
- When Google Books answers HTTP 429 (quota exceeded), scheduled jobs and batch
  wizards stop immediately instead of hammering the API.

**Features**

- **Compléter les infos** — one button on an album (or edition) form: looks the main
  edition up on the sources (ISBN, or strict title match), fills only the empty fields
  (cover, synopsis, pages, dates, ISBN, authors) and tells what was added.
- **Search wizard** — search the sources by ISBN or title, compare the
  results and import the selected albums into the catalogue.
- **Edition enrichment** — *Rechercher sur les sources* button on an edition.
- **Series update** — enrich all incomplete albums of a series in one click.
- **Missing tomes** — compares a series with the sources (using the number of
  published tomes when known) and lists the absent tomes, which can be added to
  the catalogue or, with ``comic_shop`` installed, to the user's wishlist.
- **Scheduled jobs** (disabled by default) — daily enrichment of incomplete
  editions, weekly missing-tome detection on followed series (batches of 20).

**Free and open source** — LGPL-3, part of the free *Comic Collection* core with
``comics_collections``. It is also required by the paid *Comic Shop* module.
