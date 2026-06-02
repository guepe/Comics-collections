Go to **Comics → Configuration → Data Sources** to configure the module.

1. Optionally enter a **Google Books API key** to raise the daily quota to
   1 000 requests (free key at `console.cloud.google.com
   <https://console.cloud.google.com>`_). Without a key, requests are limited
   to ~100/day in anonymous mode.
2. Enable or disable **Open Library** and **BnF** with the toggle buttons.
   Both are enabled by default.
3. Activate the **scheduled cron jobs** if you want automatic enrichment:

   - *Daily*: enriches editions missing synopsis, cover or ISBN.
   - *Weekly*: detects missing tomes across all series.

   Both cron jobs are disabled by default to avoid unexpected API traffic.
