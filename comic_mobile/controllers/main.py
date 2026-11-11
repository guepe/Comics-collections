"""App mobile (PWA) : page autonome, manifeste web."""

import json

from markupsafe import Markup

from odoo import http
from odoo.http import request

APP_URL = "/comics/app"


class ComicMobile(http.Controller):
    @http.route([APP_URL, f"{APP_URL}/<path:subpath>"], type="http", auth="user", sitemap=False)
    def comic_mobile_app(self, subpath=None, **kwargs):
        """Page de l'app : réservée aux utilisateurs BD (les autres retournent dans Odoo)."""
        if not request.env.user.has_group("comics_collections.group_comic_user"):
            return request.redirect("/odoo")
        session_info = request.env["ir.http"].session_info()
        return request.render(
            "comic_mobile.index",
            {
                "session_info": session_info,
                # JSON sûr dans une balise <script> (« </ » échappé)
                "session_info_json": Markup(json.dumps(session_info).replace("</", "<\\/")),
                "app_url": APP_URL,
            },
            headers={"Cache-Control": "no-store"},
        )

    @http.route("/comic_mobile/manifest.webmanifest", type="http", auth="public", sitemap=False)
    def comic_mobile_manifest(self, **kwargs):
        """Manifeste web : nom, icônes, plein écran (installation sur l'écran d'accueil)."""
        env = request.env
        manifest = {
            "name": env._("My Comics"),
            "short_name": env._("Comics"),
            "description": env._("My comic collection"),
            "start_url": APP_URL,
            "scope": APP_URL,
            "display": "standalone",
            "orientation": "portrait",
            "background_color": "#f3eee4",
            "theme_color": "#022E51",
            "icons": [
                {"src": "/comic_mobile/static/img/icon-192.png", "sizes": "192x192", "type": "image/png"},
                {"src": "/comic_mobile/static/img/icon-512.png", "sizes": "512x512", "type": "image/png"},
            ],
        }
        return request.make_response(
            json.dumps(manifest, ensure_ascii=False),
            headers=[("Content-Type", "application/manifest+json; charset=utf-8")],
        )
