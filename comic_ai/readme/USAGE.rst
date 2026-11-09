**Discover new comics (AI taste profile)**

*Bandes Dessinées → Ma Collection → Découvrir de nouvelles BD* opens a wizard:

1. The taste profile lists the series of the albums you rated 4★ or more in your
   library. Remove or add series, then click *Obtenir des suggestions*. An empty
   profile gives a clear message (rate at least one album 4★).
2. The AI (prompt ``comic_ai/prompts/discovery.txt``) suggests 10 to 15 series you do
   not know yet: title, author(s), genre and a short reason, in the default
   generation language. The series already in your collection or wishlist (owned,
   wished or followed series) are excluded, in the prompt and again afterwards
   (normalized title comparison).
3. *Vérifier* searches the series on the data sources (Google Books, Open Library,
   BnF) and shows what was found (publisher, ISBN of volume 1, authors): a guard
   against hallucinated titles.
4. Tick the suggestions you like and click *Ajouter à ma wishlist*: the first volume
   of a series already in the catalogue is added to your wishlist; otherwise the
   series and its volume 1 are created (with the ISBN and publisher found by the
   verification, if any).

Provider errors (invalid key, timeout, quota, unreadable answer) are shown as clear
messages. With *comic_shop*, the module *comic_ai_shop* offers the same discovery to
the customers of the portal library.
