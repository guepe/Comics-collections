Manage a comic book (*bande dessinée*) collection in Odoo 19.
Series, albums, authors, publishers, loans and duplicates — in one place.

The catalogue (series, albums, editions, ISBN) is **shared** by all comic users;
what each user owns is tracked in a **personal library** (``comic.customer.album``),
and loans are private to the lender. The module works on its own, at home;
``comic_shop`` offers the same library to shop customers on the portal.

**Key features**

- **Series & Albums** — Albums (tomes) are grouped by series. Tome ``0`` means
  *unnumbered / hors-série*: a series may hold several of them, while numbered
  tomes are unique per series. Each album carries its edition metadata (publisher,
  publication date, language, format, cover, synopsis, page count) and purchase
  links (Club.be, Amazon.be, FNAC.be).

- **Personal library & dashboard** — Collection, wishlist, reading status and a
  star rating per album and per user. *Ma Collection → Tableau de bord* shows owned
  albums, wishlist, complete / ongoing series, breakdowns by genre and reading status,
  best-rated series, recent additions and overdue loans. Optional purchase price
  and estimated value per album give the collection's total value; the collection
  exports to CSV and to a PDF inventory (e.g. for insurance).

- **New-release alerts** — When a tome released less than 90 days ago (or not yet
  released) is added to a followed series — by the missing-tome detection of
  ``comic_datasource`` — its followers get an Odoo notification (inbox or e-mail,
  per user preference). *Ajouter à ma wishlist* on the album adds it in one click.
  The window is the ``comic.new_release_days`` system parameter.

- **Followed series** — Each user can follow series independently
  (*Suivie* toggle), which drives the missing-tome detection of ``comic_datasource``.

- **Authors** — Authors are standard ``res.partner`` records linked to albums with a
  role (scénariste, dessinateur, coloriste, encreur, traducteur, autre). The contact
  form shows a *Bandes dessinées* tab and smart buttons listing every series and
  album the author worked on.

- **Publishers & Genres** — ``comic.editeur`` and ``comic.genre``. The publisher form
  lists its series and albums (through the editions it published).

- **ISBN management** — EAN-13 / ISBN-10 validation, ISBN-10 → ISBN-13 conversion,
  global uniqueness. An edition can carry several ISBN records.

- **Loans (Prêts)** — Who borrowed which album, with default dates (today, +30 days),
  a *Retourner* button, overdue highlighting, a check against lending the same
  album twice, and a daily reminder activity for overdue loans.

- **CSV / TSV / XLS / XLSX import** — Column mapping step, *update* or *skip* policy
  for existing albums, series matched on their normalised name, cover download
  from a URL column, and an error/warning report with the real file line numbers.

- **Deduplication** — Blocked scan (normalised title keys + ``difflib`` ratio,
  threshold 0.85) producing scored duplicate pairs; merge in either direction
  (A → B or B → A) or ignore a pair.

- **Purchase links cron** — Weekly scheduled action filling missing purchase links
  for editions that have an ISBN.

- **Chatter & tracking** — Series, albums, editions and loans inherit
  ``mail.thread`` and ``mail.activity.mixin``.
