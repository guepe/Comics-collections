import base64
import datetime
import logging
import re

import requests as http_requests

from urllib.parse import urljoin, urlparse

from odoo import http, _
from odoo.exceptions import UserError, ValidationError
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal, pager as portal_pager
from odoo.addons.comic_datasource.aggregator import ComicDataAggregator
from odoo.addons.comics_collections.models.comic_isbn import ComicIsbn

_logger = logging.getLogger(__name__)

# Valeurs acceptées depuis le portail (un client ne peut pas se déclarer "achete_ici")
_PORTAL_SOURCES = ("achete_ailleurs", "cadeau", "inconnu")
_ETATS_LECTURE = ("non_lu", "en_cours", "lu")
# Destination d'un album ajouté depuis le portail
_ADD_TARGETS = ("collection", "wishlist")
_LIBRARY_PAGE_SIZE = 24

# Hôtes autorisés pour le téléchargement des couvertures (anti-SSRF)
_COVER_ALLOWED_HOSTS = (
    "books.google.com",
    "books.googleusercontent.com",
    "covers.openlibrary.org",
    "archive.org",
    "catalogue.bnf.fr",
    "gallica.bnf.fr",
)
_COVER_MAX_BYTES = 5 * 1024 * 1024


def _clean_isbn(raw):
    """Return a valid ISBN-13 (ISBN-10 converted), or empty string."""
    digits = re.sub(r"[\s\-]", "", raw or "").upper()
    if len(digits) == 10 and ComicIsbn._validate_isbn10(digits):
        base = "978" + digits[:9]
        total = sum(int(d) * (1 if i % 2 == 0 else 3) for i, d in enumerate(base))
        return base + str((10 - total % 10) % 10)
    if len(digits) == 13 and ComicIsbn._validate_ean13(digits):
        return digits
    return ""


def _cover_url_allowed(url):
    try:
        parsed = urlparse(url)
    except ValueError:
        return False
    host = (parsed.hostname or "").lower()
    return parsed.scheme in ("http", "https") and any(
        host == allowed or host.endswith("." + allowed) for allowed in _COVER_ALLOWED_HOSTS
    )


def _download_cover(url):
    """Download a cover from an allowed host; return base64 bytes or None."""
    try:
        resp = None
        for _hop in range(4):  # redirections suivies manuellement, hôte revérifié à chaque saut
            if not _cover_url_allowed(url):
                _logger.warning("Cover URL refused (host not allowed): %s", url)
                return None
            resp = http_requests.get(url, timeout=10, stream=True, allow_redirects=False)
            if resp.is_redirect:
                url = urljoin(url, resp.headers.get("Location", ""))
                resp.close()
                continue
            break
        if resp is None or resp.status_code != 200 or not resp.headers.get("Content-Type", "").startswith("image/"):
            return None
        content = resp.raw.read(_COVER_MAX_BYTES + 1, decode_content=True)
        if len(content) > _COVER_MAX_BYTES or len(content) <= 100:
            return None
        return base64.b64encode(content)
    except Exception as exc:
        _logger.warning("Cover download failed: %s", exc)
        return None


class ComicLibraryPortal(CustomerPortal):

    def _prepare_home_portal_values(self, counters):
        values = super()._prepare_home_portal_values(counters)
        # La carte « Ma Bibliothèque BD » affiche le nombre directement (pas de
        # data-placeholder_count) : calculé au rendu de /my (counters=[]) ou s'il est
        # demandé. Jamais renvoyé à /my/counters sans être demandé, sinon le script
        # portal_home_counters cherche un emplacement absent et plante (textContent de null).
        if counters and "library_count" not in counters:
            return values
        values["library_count"] = request.env["comic.customer.album"].search_count(
            [
                ("partner_id", "=", request.env.user.partner_id.id),
                ("dans_collection", "=", True),
            ]
        )
        return values

    # ── /my/library — index ─────────────────────────────────────────────────

    @http.route(
        ["/my/library", "/my/library/page/<int:page>"],
        type="http",
        auth="user",
        website=True,
    )
    def my_library(self, filter="all", sort="date", view="kanban", page=1, **kw):
        partner = request.env.user.partner_id
        Album = request.env["comic.customer.album"].sudo()

        domain = [("partner_id", "=", partner.id)]
        if filter == "collection":
            domain.append(("dans_collection", "=", True))
        elif filter == "wishlist":
            domain.append(("dans_wishlist", "=", True))
        elif filter == "reading":
            domain.append(("etat_lecture", "=", "en_cours"))
        else:
            filter = "all"

        records = Album.search(domain)

        if sort == "serie":
            records = records.sorted(
                key=lambda r: (r.edition_id.work_id.serie_id.name or "", r.edition_id.work_id.tome or 0)
            )
        elif sort == "title":
            records = records.sorted(key=lambda r: r.edition_id.work_id.titre_canonique or "")
        else:
            sort = "date"
            # Clé homogène : les entrées sans date d'ajout passent en dernier
            records = records.sorted(
                key=lambda r: (bool(r.date_ajout), r.date_ajout or datetime.date.min),
                reverse=True,
            )

        try:
            page = max(1, int(page))
        except (ValueError, TypeError):
            page = 1
        pager = portal_pager(
            url="/my/library",
            url_args={"filter": filter, "sort": sort, "view": view},
            total=len(records),
            page=page,
            step=_LIBRARY_PAGE_SIZE,
        )
        records = records[pager["offset"] : pager["offset"] + _LIBRARY_PAGE_SIZE]

        # Compteurs calculés sur toute la bibliothèque (indépendants du filtre / de la page)
        all_records = Album.search([("partner_id", "=", partner.id)])
        nb_series = len(all_records.mapped("edition_id.work_id.serie_id").filtered("id"))

        # Partage de la wishlist (US-073) : jeton réservé aux admins, lu en sudo
        partner_sudo = partner.sudo()
        wishlist_url = False
        if partner_sudo.comic_wishlist_shared and partner_sudo.comic_wishlist_token:
            wishlist_url = "%s/wishlist/%s" % (
                request.website.get_base_url().rstrip("/"),
                partner_sudo.comic_wishlist_token,
            )

        return request.render(
            "comic_shop.portal_library_index",
            {
                "records": records,
                # « filter » est un builtin Python : dans QWeb il masquerait la valeur
                "current_filter": filter,
                "sort": sort,
                "view_mode": view,
                "pager": pager,
                "library_empty": not all_records,
                "nb_albums": len(all_records),
                "nb_series": nb_series,
                "nb_reading": len(all_records.filtered(lambda r: r.etat_lecture == "en_cours")),
                "page_name": "library",
                "flash": request.session.pop("comic_library_flash", None),
                "wishlist_url": wishlist_url,
            },
        )

    # ── /my/library/dashboard — tableau de bord collectionneur (US-065) ──────

    @staticmethod
    def _dashboard_bars(rows, total):
        """Turn ``(label, count)`` rows into bar dicts with a width percentage.

        Les largeurs sont calculées ici (part du total des albums possédés) pour que
        le template n'ait qu'à afficher.
        """
        bars = []
        for label, count in rows:
            pct = round(count * 100.0 / total) if total else 0
            bars.append({"label": label, "count": count, "pct": pct})
        return bars

    @http.route("/my/library/dashboard", type="http", auth="user", website=True)
    def my_library_dashboard(self, **kw):
        # Prêts exclus : ils sont privés au back-office
        stats = request.env["comic.customer.album"]._get_collection_stats(request.env.user.partner_id)
        total = stats["nb_albums"]
        return request.render(
            "comic_shop.portal_library_dashboard",
            {
                "stats": stats,
                "genre_bars": self._dashboard_bars(stats["by_genre"], total),
                "reading_bars": [
                    dict(row, key=key)
                    for (key, _label, _count), row in zip(
                        stats["by_reading"],
                        self._dashboard_bars([(label, count) for _key, label, count in stats["by_reading"]], total),
                    )
                ],
                "dashboard_empty": not stats["nb_albums"] and not stats["nb_wishlist"],
                "page_name": "library_dashboard",
            },
        )

    # ── /my/library/<id> — détail ───────────────────────────────────────────

    @http.route("/my/library/<int:cust_album_id>", type="http", auth="user", website=True)
    def my_library_detail(self, cust_album_id, **kw):
        record = request.env["comic.customer.album"].sudo().browse(cust_album_id)
        if not record.exists() or record.partner_id.id != request.env.user.partner_id.id:
            return request.not_found()
        return request.render(
            "comic_shop.portal_library_detail",
            {
                "record": record,
                "page_name": "library",
            },
        )

    # ── /my/library/series — séries suivies (US-069) ────────────────────────

    @staticmethod
    def _safe_redirect(url, default="/my/library/series"):
        """Chemin local uniquement (pas de redirection ouverte)."""
        if url and url.startswith("/") and not url.startswith("//") and "\\" not in url:
            return url
        return default

    @http.route("/my/library/series", type="http", auth="user", website=True)
    def my_library_series(self, **kw):
        user = request.env.user
        Serie = request.env["comic.serie"].sudo()
        entries = request.env["comic.customer.album"].sudo().search([("partner_id", "=", user.partner_id.id)])
        library_series = entries.work_id.serie_id
        series = (Serie.search([("suivi_user_ids", "in", user.id)]) | library_series).filtered("active")
        series = series.sorted(key=lambda s: (user not in s.suivi_user_ids, (s.name or "").lower()))
        owned = {}
        for entry in entries.filtered("dans_collection"):
            serie = entry.work_id.serie_id
            if serie:
                owned.setdefault(serie.id, set()).add(entry.work_id.id)
        return request.render(
            "comic_shop.portal_library_series",
            {
                "series": series,
                "followed_ids": set(series.filtered(lambda s: user in s.suivi_user_ids).ids),
                "owned_counts": {sid: len(works) for sid, works in owned.items()},
                "page_name": "library",
                "flash": request.session.pop("comic_library_flash", None),
            },
        )

    @http.route(
        "/my/library/series/<int:serie_id>/follow",
        type="http",
        auth="user",
        methods=["POST"],
        website=True,
    )
    def my_library_series_follow(self, serie_id, follow="1", redirect=None, **post):
        """Suivre (follow=1) ou ne plus suivre (follow=0) une série, pour soi seulement."""
        serie = request.env["comic.serie"].sudo().browse(serie_id)
        if not serie.exists() or not serie.active:
            return request.not_found()
        # sudo garde l'utilisateur courant : l'inverse de a_suivre n'agit que sur lui
        serie.a_suivre = follow == "1"
        if follow == "1":
            message = _("Vous suivez « %s » : vous serez prévenu de la mise en vente des nouveaux tomes.", serie.name)
        else:
            message = _("Vous ne suivez plus « %s ».", serie.name)
        request.session["comic_library_flash"] = {"type": "success", "message": message}
        return request.redirect(self._safe_redirect(redirect))

    # ── /my/library/<id>/update — POST ─────────────────────────────────────

    @http.route(
        "/my/library/<int:cust_album_id>/update",
        type="http",
        auth="user",
        methods=["POST"],
        website=True,
        csrf=True,
    )
    def my_library_update(self, cust_album_id, **post):
        record = request.env["comic.customer.album"].sudo().browse(cust_album_id)
        if not record.exists() or record.partner_id.id != request.env.user.partner_id.id:
            return request.not_found()

        etat_lecture = post.get("etat_lecture")
        vals = {
            "etat_lecture": etat_lecture if etat_lecture in _ETATS_LECTURE else record.etat_lecture,
            "dans_collection": bool(post.get("dans_collection")),
            "dans_wishlist": bool(post.get("dans_wishlist")),
            "commentaire": post.get("commentaire", ""),
        }
        try:
            vals["note"] = max(0.0, min(5.0, float(post.get("note", 0))))
        except (ValueError, TypeError):
            _logger.debug("Invalid note value: %s", post.get("note"))

        record.sudo().write(vals)
        return request.redirect(f"/my/library/{cust_album_id}")

    # ── /my/library/<id>/remove — POST ─────────────────────────────────────

    @http.route(
        "/my/library/<int:cust_album_id>/remove",
        type="http",
        auth="user",
        methods=["POST"],
        website=True,
        csrf=True,
    )
    def my_library_remove(self, cust_album_id, **post):
        record = request.env["comic.customer.album"].sudo().browse(cust_album_id)
        if record.exists() and record.partner_id.id == request.env.user.partner_id.id:
            record.sudo().unlink()
        return request.redirect("/my/library")

    # ── /my/library/preferences — POST ─────────────────────────────────────

    @http.route(
        "/my/library/preferences",
        type="http",
        auth="user",
        methods=["POST"],
        website=True,
        csrf=True,
    )
    def my_library_preferences(self, **post):
        auto_library = bool(post.get("comic_auto_library"))
        request.env.user.partner_id.sudo().write({"comic_auto_library": auto_library})
        return request.redirect("/my/library")

    # ── Wishlist partageable (US-073) ───────────────────────────────────────

    @http.route(
        "/my/library/wishlist/share",
        type="http",
        auth="user",
        methods=["POST"],
        website=True,
        csrf=True,
    )
    def my_library_wishlist_share(self, **post):
        request.env.user.partner_id._comic_wishlist_enable()
        request.session["comic_library_flash"] = {
            "type": "success",
            "message": _("Le lien de partage de votre wishlist est prêt."),
        }
        return request.redirect("/my/library")

    @http.route(
        "/my/library/wishlist/revoke",
        type="http",
        auth="user",
        methods=["POST"],
        website=True,
        csrf=True,
    )
    def my_library_wishlist_revoke(self, **post):
        request.env.user.partner_id._comic_wishlist_revoke()
        request.session["comic_library_flash"] = {
            "type": "info",
            "message": _("Le lien de partage a été révoqué : l'ancien lien ne fonctionne plus."),
        }
        return request.redirect("/my/library")

    @staticmethod
    def _wishlist_partner(token):
        """Return the partner sharing its wishlist under ``token`` (sudo), or None."""
        if not token:
            return None
        partner = (
            request.env["res.partner"]
            .sudo()
            .search(
                [
                    ("comic_wishlist_shared", "=", True),
                    ("comic_wishlist_token", "!=", False),
                    ("comic_wishlist_token", "=", token),
                ],
                limit=1,
            )
        )
        return partner or None

    @staticmethod
    def _wishlist_entries(partner):
        return (
            request.env["comic.customer.album"]
            .sudo()
            .search([("partner_id", "=", partner.id), ("dans_wishlist", "=", True)])
            .sorted(key=lambda r: (r.edition_id.work_id.serie_id.name or "", r.edition_id.work_id.tome or 0))
        )

    @http.route(
        "/wishlist/<string:token>",
        type="http",
        auth="public",
        website=True,
        sitemap=False,
    )
    def wishlist_public(self, token, **kw):
        partner = self._wishlist_partner(token)
        if not partner:
            return request.not_found()
        # Seules des valeurs extraites (pas les enregistrements sudo) vont au template :
        # rien d'autre que série, tome, titre, couverture et lien boutique n'est exposé.
        items = []
        for entry in self._wishlist_entries(partner):
            edition = entry.edition_id
            work = edition.work_id
            product = edition.product_tmpl_id
            published = bool(product and product.is_published)
            items.append(
                {
                    "title": work.titre_canonique or "",
                    "serie": work.serie_id.name or "",
                    "tome": work.tome or 0,
                    "cover_url": (
                        "/wishlist/%s/cover/%d" % (token, entry.id)
                        if edition.image_couverture or (product and product.image_512)
                        else False
                    ),
                    "shop_url": product.website_url if published else False,
                }
            )
        owner_name = (partner.name or "").split()[0] if (partner.name or "").strip() else partner.display_name
        response = request.render(
            "comic_shop.wishlist_public_page",
            {"items": items, "owner_name": owner_name},
        )
        response.headers["X-Robots-Tag"] = "noindex"
        return response

    @http.route(
        "/wishlist/<string:token>/cover/<int:entry_id>",
        type="http",
        auth="public",
        website=True,
        sitemap=False,
    )
    def wishlist_public_cover(self, token, entry_id, **kw):
        """Serve a wishlist cover in sudo, only for an entry of the shared wishlist."""
        partner = self._wishlist_partner(token)
        if not partner:
            return request.not_found()
        entry = request.env["comic.customer.album"].sudo().browse(entry_id)
        if not entry.exists() or entry.partner_id != partner or not entry.dans_wishlist:
            return request.not_found()
        edition = entry.edition_id
        if edition.image_couverture:
            record, field = edition, "image_couverture"
        elif edition.product_tmpl_id.image_512:
            record, field = edition.product_tmpl_id, "image_512"
        else:
            return request.not_found()
        stream = request.env["ir.binary"]._get_image_stream_from(record, field, width=512, height=512)
        return stream.get_response()

    # ── /my/library/add — formulaire de recherche (étape 1) ────────────────

    @http.route("/my/library/add", type="http", auth="user", website=True)
    def my_library_add(self, **kw):
        flash = request.session.pop("comic_library_flash", None)
        return request.render(
            "comic_shop.portal_library_add",
            {
                "step": "search",
                "page_name": "library",
                "flash": flash,
            },
        )

    # ── /my/library/add/search — résultats de recherche (étape 1→2) ────────

    @http.route(
        "/my/library/add/search",
        type="http",
        auth="user",
        methods=["POST"],
        website=True,
        csrf=True,
    )
    def my_library_add_search(self, **post):
        isbn_raw = (post.get("isbn") or "").strip()
        title_raw = (post.get("title") or "").strip()

        if not isbn_raw and not title_raw:
            return request.redirect("/my/library/add")

        isbn = _clean_isbn(isbn_raw)
        results = []
        error = None

        # Local DB — ISBN exact
        if isbn:
            isbn_rec = request.env["comic.isbn"].sudo().search([("isbn_13", "=", isbn)], limit=1)
            if isbn_rec:
                results.append(self._edition_to_result(isbn_rec.edition_id, is_local=True))

        # Local DB — titre (si pas trouvé par ISBN)
        if not results and title_raw:
            works = (
                request.env["comic.work"]
                .sudo()
                .search([("titre_canonique", "ilike", title_raw)], limit=5, order="id desc")
            )
            for work in works:
                if work.edition_ids:
                    results.append(self._edition_to_result(work.edition_ids[0], is_local=True))

        # Sources externes via ComicDataAggregator
        if not results:
            try:
                agg = ComicDataAggregator(env=request.env)
                if isbn:
                    agg_result = agg.search(isbn=isbn)
                    if agg_result.data:
                        results.append(self._agg_to_result(agg_result.data, isbn))
                elif title_raw:
                    for r in agg.search_list(title=title_raw)[:6]:
                        d = self._source_result_to_result(r)
                        if d:
                            results.append(d)
            except Exception as exc:
                _logger.warning("Library add search error: %s", exc)
                error = _("La recherche externe est temporairement indisponible.")

        return request.render(
            "comic_shop.portal_library_add",
            {
                "step": "results",
                "results": results,
                "search_isbn": isbn_raw,
                "search_title": title_raw,
                "error": error,
                "page_name": "library",
            },
        )

    # ── /my/library/add/confirm — création / mise à jour (étape 2) ─────────

    @http.route(
        "/my/library/add/confirm",
        type="http",
        auth="user",
        methods=["POST"],
        website=True,
        csrf=True,
    )
    def my_library_add_confirm(self, **post):
        partner = request.env.user.partner_id
        isbn = _clean_isbn(post.get("isbn", ""))
        try:
            edition_id = int(post.get("edition_id") or 0)
        except (ValueError, TypeError):
            edition_id = 0
        source = post.get("source")
        if source not in _PORTAL_SOURCES:
            source = "inconnu"
        etat_lecture = post.get("etat_lecture")
        if etat_lecture not in _ETATS_LECTURE:
            etat_lecture = "non_lu"
        ajouter_a = post.get("ajouter_a")
        if ajouter_a not in _ADD_TARGETS:
            ajouter_a = "collection"
        force_update = bool(post.get("force_update"))

        try:
            note = max(0.0, min(5.0, float(post.get("note") or 0)))
        except (ValueError, TypeError):
            note = 0.0

        # Resolve edition
        edition = None
        if edition_id:
            rec = request.env["comic.edition"].sudo().browse(edition_id)
            if rec.exists():
                edition = rec
        if not edition and isbn:
            isbn_rec = request.env["comic.isbn"].sudo().search([("isbn_13", "=", isbn)], limit=1)
            if isbn_rec:
                edition = isbn_rec.edition_id
        if not edition:
            try:
                with request.env.cr.savepoint():
                    edition = self._create_edition_from_post(post)
            except (UserError, ValidationError) as exc:
                _logger.info("Library add: edition creation refused: %s", exc)
                request.session["comic_library_flash"] = {
                    "type": "danger",
                    "message": _("Impossible d'ajouter cet album : %s") % exc,
                }
                return request.redirect("/my/library/add")

        if not edition:
            return request.redirect("/my/library/add")

        existing = (
            request.env["comic.customer.album"]
            .sudo()
            .search(
                [
                    ("partner_id", "=", partner.id),
                    ("edition_id", "=", edition.id),
                ],
                limit=1,
            )
        )

        update_vals = {
            "source": source,
            "etat_lecture": etat_lecture,
            "dans_collection": ajouter_a == "collection",
            "dans_wishlist": ajouter_a == "wishlist",
            "note": note,
        }

        if existing and not force_update:
            return request.render(
                "comic_shop.portal_library_add",
                {
                    "step": "warning",
                    "existing": existing,
                    "edition": edition,
                    "post": post,
                    "page_name": "library",
                },
            )

        title = edition.work_id.titre_canonique or _("cet album")
        if existing:
            if existing.source == "achete_ici":
                # Un achat dans le shop ne doit pas être requalifié depuis le portail
                update_vals.pop("source")
            if ajouter_a == "wishlist":
                # Mettre en wishlist un album déjà possédé ne le retire pas de la collection
                update_vals.pop("dans_collection")
            existing.sudo().write(update_vals)
            request.session["comic_library_flash"] = {
                "type": "success",
                "message": _("« %s » a été mis à jour dans votre bibliothèque.") % title,
            }
        else:
            update_vals.update({"partner_id": partner.id, "edition_id": edition.id})
            request.env["comic.customer.album"].sudo().create(update_vals)
            request.session["comic_library_flash"] = {
                "type": "success",
                "message": _("« %s » a été ajouté à votre bibliothèque.") % title,
            }

        return request.redirect("/my/library")

    # ── Helpers ────────────────────────────────────────────────────────────

    def _edition_to_result(self, edition, is_local=True):
        work = edition.work_id
        auteurs = ", ".join(line.partner_id.name for line in work.auteur_line_ids if line.partner_id)
        isbn = edition._get_primary_isbn() or ""
        return {
            "edition_id": edition.id,
            "isbn": isbn,
            "title": work.titre_canonique or "",
            "serie_name": work.serie_id.name or "",
            "tome": work.tome or 0,
            "auteurs": auteurs,
            "editeur_name": edition.editeur_id.name or "",
            "cover_url": "",
            "is_local": is_local,
        }

    def _agg_to_result(self, data, isbn_fallback=""):
        auteurs_list = data.get("auteurs") or []
        auteurs = ", ".join(a.get("name", "") for a in auteurs_list if a.get("name"))
        return {
            "edition_id": 0,
            "isbn": data.get("isbn") or isbn_fallback,
            "title": data.get("title") or "",
            "serie_name": data.get("serie_name") or "",
            "tome": data.get("tome") or 0,
            "auteurs": auteurs,
            "editeur_name": data.get("editeur") or "",
            "cover_url": data.get("cover_url_small") or data.get("cover_url") or "",
            "is_local": False,
        }

    def _source_result_to_result(self, result):
        if not result:
            return None
        auteurs_list = result.auteurs or []
        auteurs = ", ".join(a.get("name", "") for a in auteurs_list if a.get("name"))
        return {
            "edition_id": 0,
            "isbn": result.isbn or "",
            "title": result.title or "",
            "serie_name": result.serie_name or "",
            "tome": result.tome or 0,
            "auteurs": auteurs,
            "editeur_name": result.editeur or "",
            "cover_url": getattr(result, "cover_url_small", "") or getattr(result, "cover_url", "") or "",
            "is_local": False,
        }

    def _create_edition_from_post(self, post):
        """Creates comic.work + comic.edition + comic.isbn from POST data (external result)."""
        isbn = _clean_isbn(post.get("isbn", ""))
        title = (post.get("title") or "").strip()
        serie_name = (post.get("serie_name") or "").strip()
        editeur_name = (post.get("editeur_name") or "").strip()
        cover_url = (post.get("cover_url") or "").strip()

        try:
            tome = int(post.get("tome") or 0)
        except (ValueError, TypeError):
            tome = 0

        if not title:
            return None

        data = {
            "isbn": isbn,
            "title": title,
            "serie_name": serie_name,
            "editeur_name": editeur_name,
            "cover_url": cover_url,
            "tome": tome,
        }
        # Création déléguée au modèle (testable sans HTTP) : les fiches créées
        # sont marquées « à valider » et signalées au gestionnaire du shop.
        return (
            request.env["comic.edition"]
            .sudo()
            ._create_from_portal_data(data, request.env.user.partner_id, cover_fetcher=_download_cover)
        )
