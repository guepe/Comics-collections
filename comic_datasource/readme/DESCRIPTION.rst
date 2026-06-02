Multi-source data enrichment connector for comic book editions.
Automatically fetches metadata, covers and authors from Google Books, Open Library
and BnF (French National Library).

**Source cascade** — ``Google Books → Open Library → BnF SRU``

A single wizard searches all enabled sources in priority order and merges the results
field by field. First non-empty value wins, with field-specific overrides
(e.g. BnF wins for *date_dépôt_légal*; Google wins for synopsis and covers).

**Available sources**

+-------------+------------------------+------------------+
| Source      | Authentication         | Rate limit       |
+=============+========================+==================+
| Google Books| Free API key (optional)| 1 000 req/day    |
+-------------+------------------------+------------------+
| Open Library| None                   | Unlimited        |
+-------------+------------------------+------------------+
| BnF SRU     | None                   | Unlimited        |
+-------------+------------------------+------------------+

**Additional features**

- **Cover retrieval** — Fetches the best available cover image (Google extraLarge >
  Open Library L).
- **Missing-tome detection** — Compares editions in a series against online sources
  and lists tomes absent from your catalogue.
- **Serie update wizard** — Batch-enrich all incomplete editions in a series in one click.
- **Scheduled enrichment** — Two optional cron jobs (disabled by default):
  daily enrichment of incomplete editions, weekly detection of missing tomes.
