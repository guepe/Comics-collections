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
