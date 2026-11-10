import time

import requests
from odoo import api, fields, models
from odoo.exceptions import UserError


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    # ── Google Books ──────────────────────────────────────────────────────────
    comic_google_books_api_key = fields.Char(
        string="Google Books API key",
        config_parameter="comic.google_books_api_key",
        help="Free API key to create on console.cloud.google.com. "
        "Without a key, a reduced shared anonymous quota applies; with a key, 1000 requests/day.",
    )

    # ── Open Library / BnF (activées par défaut) ─────────────────────────────
    # Pas de `config_parameter=` : Odoo supprime le paramètre quand la case est
    # décochée, et les sources (défaut "True") restaient alors actives.
    # On stocke explicitement "True" / "False" (voir get_values / set_values).
    comic_openlibrary_enabled = fields.Boolean(
        string="Enable Open Library",
        help="Source of covers and metadata. Free, no API key required.",
    )
    comic_bnf_enabled = fields.Boolean(
        string="Enable BnF (Bibliothèque nationale de France)",
        help="Official legal deposit data for French-language comics. Free, no API key required.",
    )

    _SOURCE_TOGGLES = {
        "comic_openlibrary_enabled": "comic.openlibrary_enabled",
        "comic_bnf_enabled": "comic.bnf_enabled",
    }

    @api.model
    def get_values(self):
        res = super().get_values()
        icp = self.env["ir.config_parameter"].sudo()
        for field_name, key in self._SOURCE_TOGGLES.items():
            res[field_name] = icp.get_param(key, "True") != "False"
        return res

    def set_values(self):
        res = super().set_values()
        icp = self.env["ir.config_parameter"].sudo()
        for field_name, key in self._SOURCE_TOGGLES.items():
            icp.set_param(key, "True" if self[field_name] else "False")
        return res

    # ── Actions ───────────────────────────────────────────────────────────────

    def action_test_google_books(self):
        """Teste la connexion Google Books et retourne une notification."""
        self.ensure_one()
        api_key = self.env["ir.config_parameter"].sudo().get_param("comic.google_books_api_key", "")
        url = "https://www.googleapis.com/books/v1/volumes"
        # ISBN de test : Astérix T1
        params = {"q": "isbn:9782012101340"}
        if api_key:
            params["key"] = api_key

        retries = 3
        backoff = 2
        for attempt in range(retries):
            try:
                resp = requests.get(url, params=params, timeout=10)
            except Exception as e:
                raise UserError(
                    self.env._(
                        "Unable to reach Google Books: %(error)s\nCheck your internet connection.",
                        error=e,
                    )
                ) from e

            if resp.status_code in (500, 502, 503, 504) and attempt < retries - 1:
                time.sleep(backoff * (2**attempt))
                continue
            break

        if resp.status_code == 403:
            raise UserError(
                self.env._(
                    "Google Books: access denied (HTTP 403).\n"
                    "Check that the API key is valid and that "
                    '"Books API" is enabled in the Google Cloud console.'
                )
            )
        if resp.status_code == 429:
            raise UserError(
                self.env._(
                    "Google Books: quota exceeded (HTTP 429).\n"
                    "You have reached the free request limit. "
                    "Add an API key in Settings > Comic Books > "
                    "Data Sources to increase the quota (1000 req/day)."
                )
            )
        if resp.status_code != 200:
            raise UserError(
                self.env._(
                    "Google Books: unexpected error HTTP %(status)s (after %(retries)s attempt(s)).",
                    status=resp.status_code,
                    retries=retries,
                )
            )

        data = resp.json()
        total = data.get("totalItems", 0)
        mode = self.env._("with API key") if api_key else self.env._("anonymous mode")

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": self.env._("Google Books — Connection OK"),
                "message": self.env._(
                    "✅ %(total)s result(s) found (%(mode)s). The Google Books source is operational.",
                    total=total,
                    mode=mode,
                ),
                "type": "success",
                "sticky": False,
            },
        }
