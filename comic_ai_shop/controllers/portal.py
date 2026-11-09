"""Portail : « Découvrir de nouvelles BD » (US-029) sur /my/library/discover.

Même logique que l'assistant back-office (comic.ai.discovery.wizard), utilisé en sudo
et toujours pour le partenaire courant : l'assistant force son partenaire à la
création et la session ne retient que l'identifiant de l'assistant du client.
Le nombre d'appels IA par client et par jour est limité (comic_ai.discovery_daily_limit).
"""

import logging

from odoo import Command, _, http
from odoo.exceptions import UserError
from odoo.http import request

_logger = logging.getLogger(__name__)

SESSION_KEY = "comic_ai_discovery_wizard_id"
DISCOVER_URL = "/my/library/discover"


def _int_list(values):
    ids = []
    for value in values:
        try:
            ids.append(int(value))
        except (TypeError, ValueError):
            continue
    return ids


class ComicAiDiscoverPortal(http.Controller):

    # ── Helpers ────────────────────────────────────────────────────────────

    @staticmethod
    def _flash(kind, message):
        request.session["comic_library_flash"] = {"type": kind, "message": message}

    @staticmethod
    def _current_wizard():
        """The discovery wizard of the current customer kept in session, or an empty recordset."""
        Wizard = request.env["comic.ai.discovery.wizard"].sudo()
        wizard_id = request.session.get(SESSION_KEY)
        if not wizard_id:
            return Wizard
        try:
            wizard = Wizard.browse(int(wizard_id)).exists()
        except (TypeError, ValueError):
            return Wizard
        if not wizard or wizard.partner_id != request.env.user.partner_id or not wizard.portal:
            return Wizard
        return wizard

    @staticmethod
    def _library_series(partner):
        """Series of the customer's library, the profile candidates."""
        entries = request.env["comic.customer.album"].sudo().search([("partner_id", "=", partner.id)])
        return entries.work_id.serie_id.sorted(lambda s: (s.name or "").lower())

    # ── Page ───────────────────────────────────────────────────────────────

    @http.route(DISCOVER_URL, type="http", auth="user", website=True)
    def my_library_discover(self, **kw):
        partner = request.env.user.partner_id
        Wizard = request.env["comic.ai.discovery.wizard"].sudo()
        wizard = self._current_wizard()
        candidates = self._library_series(partner)
        if wizard:
            checked = wizard.profile_serie_ids
            candidates |= checked
        else:
            checked = Wizard._get_profile_series(partner)
        # Profil coché en tête, puis les autres séries de la bibliothèque
        candidates = checked + (candidates - checked)
        remaining = partner._comic_ai_discovery_remaining()
        return request.render(
            "comic_ai_shop.portal_library_discover",
            {
                "page_name": "library",
                "candidates": candidates,
                "checked_ids": set(checked.ids),
                "wizard": wizard,
                "lines": wizard.line_ids if wizard else [],
                "remaining": remaining,
                "daily_limit": partner._comic_ai_discovery_limit(),
                "flash": request.session.pop("comic_library_flash", None),
            },
        )

    # ── Appel IA ───────────────────────────────────────────────────────────

    @http.route(
        DISCOVER_URL + "/suggest",
        type="http",
        auth="user",
        methods=["POST"],
        website=True,
        csrf=True,
    )
    def my_library_discover_suggest(self, **post):
        partner = request.env.user.partner_id
        # Profil limité aux séries de la bibliothèque du client
        allowed = self._library_series(partner)
        wanted = set(_int_list(request.httprequest.form.getlist("serie_ids")))
        profile = allowed.filtered(lambda s: s.id in wanted)
        Wizard = request.env["comic.ai.discovery.wizard"].sudo()
        try:
            Wizard.new({"portal": True, "profile_serie_ids": [Command.set(profile.ids)]})._check_profile()
        except UserError as exc:
            self._flash("warning", exc.args[0])
            return request.redirect(DISCOVER_URL)
        if partner._comic_ai_discovery_remaining() <= 0:
            self._flash(
                "warning",
                _(
                    "Vous avez atteint la limite de %s recherches de suggestions pour aujourd'hui. " "Revenez demain !",
                    partner._comic_ai_discovery_limit(),
                ),
            )
            return request.redirect(DISCOVER_URL)
        wizard = Wizard.create({"portal": True, "profile_serie_ids": [Command.set(profile.ids)]})
        request.session[SESSION_KEY] = wizard.id
        # Chaque appel au fournisseur compte, même en cas d'erreur (coût engagé)
        partner._comic_ai_discovery_consume()
        try:
            kept = wizard._generate_suggestions()
        except UserError as exc:  # ComicAiError compris : message déjà lisible
            _logger.info("Portal discovery failed for partner %s: %s", partner.id, exc)
            self._flash("danger", _("Suggestions indisponibles : %s", exc.args[0]))
            return request.redirect(DISCOVER_URL)
        if kept:
            self._flash("success", _("%s suggestion(s) pour vous.", len(kept)))
        return request.redirect(DISCOVER_URL + "#suggestions")

    # ── Vérification et ajout en wishlist ──────────────────────────────────

    @http.route(
        DISCOVER_URL + "/verify",
        type="http",
        auth="user",
        methods=["POST"],
        website=True,
        csrf=True,
    )
    def my_library_discover_verify(self, verify_line_id=None, **post):
        wizard = self._current_wizard()
        line = wizard.line_ids.filtered(lambda line: line.id in _int_list([verify_line_id])) if wizard else None
        if not line:
            self._flash("warning", _("Suggestion introuvable : relancez une recherche."))
            return request.redirect(DISCOVER_URL)
        line._verify_on_sources()
        return request.redirect(DISCOVER_URL + "#suggestion-%s" % line.id)

    @http.route(
        DISCOVER_URL + "/add",
        type="http",
        auth="user",
        methods=["POST"],
        website=True,
        csrf=True,
    )
    def my_library_discover_add(self, **post):
        wizard = self._current_wizard()
        if not wizard:
            self._flash("warning", _("Vos suggestions ont expiré : relancez une recherche."))
            return request.redirect(DISCOVER_URL)
        wanted = set(_int_list(request.httprequest.form.getlist("line_ids")))
        lines = wizard.line_ids.filtered(lambda line: line.id in wanted and not line.added)
        if not lines:
            self._flash("warning", _("Cochez au moins une suggestion à ajouter à votre wishlist."))
            return request.redirect(DISCOVER_URL + "#suggestions")
        wizard.line_ids.write({"selected": False})
        lines.write({"selected": True})
        added = wizard._add_selected_to_wishlist()
        self._flash(
            "success",
            _(
                "%(count)s série(s) ajoutée(s) à votre wishlist : %(names)s",
                count=len(added),
                names=", ".join(added.mapped("name")),
            ),
        )
        return request.redirect("/my/library?filter=wishlist")
