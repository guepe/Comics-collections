Manage your comic book collection in Odoo 19.
Track series, albums, authors, publishers, loans and duplicates — all in one place.

**Key features**

- **Series & Albums** — Organise your collection by series and individual albums (tomes).
  Each album holds edition metadata: publisher, publication date, language, format,
  cover image, synopsis, page count and purchase links (Club.be, Amazon.be, FNAC.be).

- **Authors** — Link authors to albums with their role: *scénariste*, *dessinateur*,
  *coloriste* or *autre*. Authors are stored as standard ``res.partner`` records.

- **Publishers & Genres** — Dedicated models for publishers (``comic.editeur``) and
  genres (``comic.genre``) with full list views and easy assignment on series.

- **ISBN management** — EAN-13 / ISBN-10 validation with uniqueness constraint.
  Each edition can carry multiple ISBN records (``comic.isbn``).

- **Loans (Prêts)** — Track who borrowed which album, expected and effective return dates.
  Overdue loans are highlighted automatically.

- **CSV / XLS / XLSX import wizard** — Import large collections from spreadsheets with
  a column-mapping step and a detailed error report for failed rows.

- **Deduplication** — Automatic detection of probable duplicates based on title
  similarity (``difflib.SequenceMatcher``, threshold 0.85). A merge wizard lets you
  pick the canonical record and archive the duplicate.

- **Purchase links cron** — Weekly scheduled action fills missing purchase-link URLs
  for all editions that have an ISBN.

- **Chatter & tracking** — ``comic.work`` and ``comic.edition`` inherit
  ``mail.thread`` and ``mail.activity.mixin`` for full change history.
