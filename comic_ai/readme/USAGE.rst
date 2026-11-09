**Synopsis generation and translation** (comic managers)

1. Open an album (or an edition, in *Configuration → Référentiel avancé*) and go to
   the *Synopsis* tab. On an album, the assistant works on its main edition.
2. Click *Générer le synopsis* (or *Traduire le synopsis* when a synopsis exists).
3. In the AI assistant, choose the action:

   * *Générer le synopsis*: a short synopsis (4 to 6 sentences, no major spoiler,
     no invented facts) written from the title, series, volume, authors with their
     roles, publisher and existing synopsis, in the chosen language (default: the
     language set in the settings).
   * *Traduire le synopsis*: translation of the current synopsis into French,
     Dutch, English or German. When the album has an edition in the target
     language, choose whether to replace the synopsis of the current edition or to
     write the translation on that edition.

4. Click *Générer* (generation can take a few seconds; the screen is blocked
   meanwhile). The text is shown as a preview and can be edited.
5. *Appliquer* writes it (converted to clean HTML) on the edition, *Régénérer*
   asks the AI for a new version, *Annuler* closes without any change. If the
   edition already has a synopsis, the old and new texts are shown side by side
   and *Remplacer le synopsis existant* must be ticked before applying.

Each application is logged in the edition chatter (action, provider, model).
Provider errors (invalid key, timeout, quota…) are shown as clear messages.

The prompts are plain text files in ``comic_ai/prompts/`` (``synopsis.txt``,
``translate.txt``) and can be adjusted without touching the code.

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
