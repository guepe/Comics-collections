import requests
from odoo import api, fields, models
from odoo.exceptions import UserError


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    # ── Google Books ──────────────────────────────────────────────────────────
    comic_google_books_api_key = fields.Char(
        string='Clé API Google Books',
        config_parameter='comic.google_books_api_key',
        help='Clé API gratuite à créer sur console.cloud.google.com. '
             'Sans clé, les requêtes sont limitées à ~100/jour.',
    )

    # ── Open Library (activé par défaut) ─────────────────────────────────────
    comic_openlibrary_enabled = fields.Boolean(
        string='Activer Open Library',
        config_parameter='comic.openlibrary_enabled',
        help='Source de couvertures et métadonnées. Gratuite, sans clé API.',
    )

    # ── BnF SRU (activée par défaut) ─────────────────────────────────────────
    comic_bnf_enabled = fields.Boolean(
        string='Activer BnF (Bibliothèque nationale de France)',
        config_parameter='comic.bnf_enabled',
        help='Données officielles de dépôt légal pour les BD francophones. Gratuite, sans clé API.',
    )

    # ── BDGest (opt-in) ───────────────────────────────────────────────────────
    comic_bdgest_enabled = fields.Boolean(
        string='Activer BDGest (scraping)',
        config_parameter='comic.bdgest_enabled',
        help='BDGest est un fallback de scraping. '
             'Son utilisation est soumise aux CGU de bedetheque.com.',
    )
    comic_bdgest_login = fields.Char(
        string='Login BDGest',
        config_parameter='comic.bdgest_login',
    )
    comic_bdgest_password = fields.Char(
        string='Mot de passe BDGest',
        config_parameter='comic.bdgest_password',
    )
    comic_bdgest_delay = fields.Integer(
        string='Délai entre requêtes BDGest (secondes)',
        config_parameter='comic.bdgest_delay',
        help='Délai minimum entre deux requêtes BDGest. Minimum 2 secondes (CGU).',
    )

    # ── Actions ───────────────────────────────────────────────────────────────

    def action_test_google_books(self):
        """Teste la connexion Google Books et retourne une notification."""
        self.ensure_one()
        api_key = self.env['ir.config_parameter'].sudo().get_param(
            'comic.google_books_api_key', ''
        )
        url = 'https://www.googleapis.com/books/v1/volumes'
        # ISBN de test : Astérix T1
        params = {'q': 'isbn:9782012101340'}
        if api_key:
            params['key'] = api_key

        try:
            resp = requests.get(url, params=params, timeout=10)
        except Exception as e:
            raise UserError(
                f'Impossible de contacter Google Books : {e}\n'
                'Vérifiez votre connexion internet.'
            )

        if resp.status_code == 403:
            raise UserError(
                'Google Books : accès refusé (HTTP 403).\n'
                'Vérifiez que la clé API est valide et que '
                '"Books API" est activée dans la console Google Cloud.'
            )
        if resp.status_code == 429:
            raise UserError(
                'Google Books : quota dépassé (HTTP 429).\n'
                'Vous avez atteint la limite de requêtes gratuite. '
                'Ajoutez une clé API pour augmenter le quota (1000 req/jour).'
            )
        if resp.status_code != 200:
            raise UserError(
                f'Google Books : erreur inattendue HTTP {resp.status_code}.'
            )

        data = resp.json()
        total = data.get('totalItems', 0)
        mode = 'avec clé API' if api_key else 'mode anonyme'

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Google Books — Connexion OK',
                'message': f'✅ {total} résultat(s) trouvé(s) ({mode}). '
                           f'La source Google Books est opérationnelle.',
                'type': 'success',
                'sticky': False,
            },
        }
