Go to **Bandes Dessinées → Configuration → Sources de données** (or
*Settings → Bandes Dessinées*):

1. Optionally enter a **Google Books API key** to raise the daily quota (free key
   at `console.cloud.google.com <https://console.cloud.google.com>`_), then use
   *Tester la connexion Google Books*.
2. Enable or disable **Open Library** and **BnF**. Both are enabled by default.
3. To change the source priority, edit the ``comic.datasource_order`` system
   parameter (JSON list, default ``["google", "openlibrary", "bnf"]``).
4. Activate the **scheduled actions** if you want automatic enrichment
   (*Settings → Technical → Automation → Scheduled Actions*):

   - *BD — Enrichissement quotidien des éditions incomplètes*;
   - *BD — Détection hebdomadaire des tomes manquants* (followed series only).

   Both are disabled by default to avoid unexpected API traffic.
