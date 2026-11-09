Go to *Settings → Bandes Dessinées → Intelligence artificielle*:

1. Choose the provider (Claude or OpenAI) and the default generation language.
2. Enter the API key of the provider (stored as a system parameter, never in the
   code) and, if needed, the model (default ``claude-sonnet-5-5`` /
   ``gpt-5-mini``).
3. Click *Tester la connexion IA*.

The Python libraries ``anthropic`` and ``openai`` are imported on demand: install
the one of your provider on the server (``pip install anthropic``).
