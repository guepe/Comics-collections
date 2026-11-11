"""Données de l'app mobile (PWA) : collection, série, wishlist et scan ISBN.

Toutes les méthodes travaillent pour l'utilisateur connecté (sa bibliothèque
``comic.customer.album``, ses séries suivies, sa wishlist) et renvoient des
dictionnaires simples, prêts pour l'application OWL. Les droits d'accès et
règles d'enregistrement des modèles de ``comics_collections`` s'appliquent : un
utilisateur sans droits BD reçoit une erreur d'accès.
"""

from collections import OrderedDict

from odoo import api, fields, models
from odoo.exceptions import UserError

COLLECTION_PAGE = 60
READING_STATES = ("non_lu", "en_cours", "lu")
COVER_SIZE = "320x0"


class ComicMobileApi(models.AbstractModel):
    _name = "comic.mobile.api"
    _description = "Comics mobile app — data API"

    # ── Outils ────────────────────────────────────────────────────────────

    @api.model
    def _partner(self):
        return self.env.user.partner_id

    @api.model
    def _cover_url(self, edition):
        """URL de la couverture de ``edition`` (False s'il n'y en a pas)."""
        if not edition:
            return False
        light = edition.with_context(bin_size=True)
        if not light.image_couverture:
            return False
        unique = fields.Datetime.to_string(edition.write_date or fields.Datetime.now()).replace(" ", "T")
        return f"/web/image/comic.edition/{edition.id}/image_couverture/{COVER_SIZE}?unique={unique}"

    @api.model
    def _entries_by_work(self, works):
        """Entrées de bibliothèque de l'utilisateur pour ``works`` : {work_id: entrée}.

        Si plusieurs éditions d'un même album sont présentes, on garde celle possédée.
        """
        entries = self.env["comic.customer.album"].search(
            [("partner_id", "=", self._partner().id), ("work_id", "in", works.ids)]
        )
        result = {}
        for entry in entries:
            current = result.get(entry.work_id.id)
            if not current or (entry.dans_collection and not current.dans_collection):
                result[entry.work_id.id] = entry
        return result

    @api.model
    def _album_vals(self, work, entry=None):
        edition = entry.edition_id if entry else work.primary_edition_id
        owned = bool(entry and entry.dans_collection)
        return {
            # Clé unique côté app : un même album peut être possédé en plusieurs éditions
            "key": f"e{entry.id}" if entry else f"w{work.id}",
            "work_id": work.id,
            "edition_id": edition.id or False,
            "serie_id": work.serie_id.id or False,
            "serie": work.serie_id.name or "",
            "tome": work.tome or 0,
            "title": work.titre_canonique or "",
            "cover": self._cover_url(edition) or self._cover_url(work.primary_edition_id),
            "owned": owned,
            "wished": bool(entry and entry.dans_wishlist and not entry.dans_collection),
            "reading": entry.etat_lecture if owned else False,
            "rating": int(round(entry.note or 0)) if owned else 0,
        }

    @api.model
    def _authors(self, works, limit=3):
        names = []
        for line in works.auteur_line_ids.sorted(lambda li: (li.work_id.tome or 0, li.id)):
            name = line.partner_id.name
            if name and name not in names:
                names.append(name)
        return names[:limit]

    @api.model
    def _serie_strip(self, serie, works=None):
        """Tomes numérotés de la série avec leur état pour l'utilisateur."""
        works = (works or serie.work_ids).filtered(lambda w: w.tome and w.tome > 0).sorted("tome")
        entries = self._entries_by_work(works)
        strip = []
        for work in works:
            entry = entries.get(work.id)
            strip.append({"tome": work.tome, "work_id": work.id, "owned": bool(entry and entry.dans_collection)})
        return strip

    # ── Accueil ───────────────────────────────────────────────────────────

    @api.model
    def mobile_get_summary(self):
        """Compteurs affichés dans les en-têtes de l'app."""
        partner = self._partner()
        owned = self.env["comic.customer.album"].search(
            [("partner_id", "=", partner.id), ("dans_collection", "=", True)]
        )
        wishlist = self.env["comic.wishlist.item"].search([("user_id", "=", self.env.uid)])
        return {
            "user": self.env.user.name,
            "albums": len(owned),
            "series": len(owned.work_id.serie_id),
            "missing": len(wishlist.filtered(lambda i: i.type == "manque")),
            "wishes": len(wishlist.filtered(lambda i: i.type == "souhait")),
        }

    # ── Ma collection ─────────────────────────────────────────────────────

    @api.model
    def mobile_get_collection(self, reading="all", search="", offset=0, limit=COLLECTION_PAGE):
        """Albums possédés, triés par série et tome, filtrés par état de lecture et texte."""
        domain = [("partner_id", "=", self._partner().id), ("dans_collection", "=", True)]
        if reading in READING_STATES:
            domain.append(("etat_lecture", "=", reading))
        search = (search or "").strip()
        if search:
            domain += [
                "|",
                "|",
                ("edition_id", "ilike", search),
                ("work_id.auteur_line_ids.partner_id.name", "ilike", search),
                ("edition_id.isbn_ids.isbn_10", "ilike", search),
            ]
        Album = self.env["comic.customer.album"]
        total = Album.search_count(domain)
        entries = Album.search(domain, order="work_id, id", offset=offset, limit=limit)
        return {
            "total": total,
            "albums": [self._album_vals(entry.work_id, entry) for entry in entries if entry.work_id],
        }

    # ── Série ─────────────────────────────────────────────────────────────

    @api.model
    def mobile_get_serie(self, serie_id):
        serie = self.env["comic.serie"].browse(int(serie_id)).exists()
        if not serie:
            raise UserError(self.env._("This series no longer exists."))
        works = serie.work_ids.sorted(lambda w: (w.tome or 0, w.id))
        entries = self._entries_by_work(works)
        albums = []
        for work in works:
            vals = self._album_vals(work, entries.get(work.id))
            vals["missing"] = not vals["owned"] and bool(work.tome)
            albums.append(vals)
        owned = [a for a in albums if a["owned"]]
        statut = dict(serie._fields["statut"]._description_selection(self.env)).get(serie.statut, "")
        return {
            "id": serie.id,
            "name": serie.name,
            "genre": serie.genre_id.name or "",
            "status": statut,
            "publisher": serie.editeur_id.name or "",
            "authors": self._authors(works),
            "followed": self.env.user in serie.suivi_user_ids,
            "cover": next((a["cover"] for a in albums if a["cover"]), False),
            "owned": len(owned),
            "read": len([a for a in owned if a["reading"] == "lu"]),
            "total": len([a for a in albums if a["tome"]]) or len(albums),
            "albums": albums,
        }

    @api.model
    def mobile_set_follow(self, serie_id, follow):
        """Suivre / ne plus suivre une série (désabonnement mémorisé, comme dans le cœur)."""
        serie = self.env["comic.serie"].browse(int(serie_id)).exists()
        if not serie:
            raise UserError(self.env._("This series no longer exists."))
        serie.check_access("read")
        serie.with_context(active_test=False).a_suivre = bool(follow)
        return {"followed": self.env.user in serie.suivi_user_ids}

    # ── Ma wishlist ───────────────────────────────────────────────────────

    @api.model
    def mobile_get_wishlist(self):
        """Manques des séries suivies et souhaits, groupés par série."""
        items = self.env["comic.wishlist.item"].search([("user_id", "=", self.env.uid)], order="serie_id, tome, id")
        today = fields.Date.context_today(self)
        groups = OrderedDict()
        for item in items:
            key = item.serie_id.id or 0
            if key not in groups:
                groups[key] = {
                    "serie_id": item.serie_id.id or False,
                    "serie": item.serie_id.name or self.env._("Without series"),
                    "items": [],
                }
            vals = self._album_vals(item.work_id)
            vals.update(
                {
                    "key": f"i{item.id}",
                    "type": item.type,
                    "date": fields.Date.to_string(item.date_parution) if item.date_parution else False,
                    "year": item.date_parution.year if item.date_parution else False,
                    "upcoming": bool(item.date_parution and item.date_parution > today),
                }
            )
            groups[key]["items"].append(vals)
        series = self.env["comic.serie"].browse([k for k in groups if k])
        strips = {serie.id: self._serie_strip(serie) for serie in series}
        for key, group in groups.items():
            strip = strips.get(key, [])
            group["owned"] = len([t for t in strip if t["owned"]])
            group["total"] = len(strip)
        return {
            "missing": len(items.filtered(lambda i: i.type == "manque")),
            "wishes": len(items.filtered(lambda i: i.type == "souhait")),
            "groups": list(groups.values()),
        }

    # ── Scan ISBN ─────────────────────────────────────────────────────────

    @api.model
    def mobile_scan(self, isbn):
        """Résultat d'un scan : owned / wished / missing (album connu non possédé) / unknown."""
        code = "".join(ch for ch in str(isbn or "") if ch.isdigit() or ch in "Xx").upper()
        if len(code) not in (10, 13):
            raise UserError(self.env._("“%(code)s” is not a valid ISBN.", code=isbn))
        field = "isbn_13" if len(code) == 13 else "isbn_10"
        record = self.env["comic.isbn"].search([(field, "=", code)], limit=1)
        if not record or not record.edition_id.work_id:
            return {"status": "unknown", "isbn": code}
        return self._scan_result(record.edition_id.work_id, record.edition_id, code)

    @api.model
    def _scan_result(self, work, edition=None, isbn=""):
        entry = self._entries_by_work(work).get(work.id)
        vals = self._album_vals(work, entry)
        if edition and not entry:
            vals["edition_id"] = edition.id
            vals["cover"] = self._cover_url(edition) or vals["cover"]
        if vals["owned"]:
            status = "owned"
        elif vals["wished"]:
            status = "wished"
        else:
            status = "missing"
        strip = self._serie_strip(work.serie_id) if work.serie_id else []
        owned_tomes = [t["tome"] for t in strip if t["owned"]]
        edition = edition or work.primary_edition_id
        vals.update(
            {
                "status": status,
                "isbn": isbn,
                "authors": self._authors(work),
                "publisher": edition.editeur_id.name or "",
                "year": edition.date_parution.year if edition.date_parution else False,
                "strip": strip,
                "serie_owned": len(owned_tomes),
                "serie_total": len(strip),
                "is_next": bool(work.tome and owned_tomes and work.tome == max(owned_tomes) + 1),
            }
        )
        return vals

    # ── Actions ───────────────────────────────────────────────────────────

    @api.model
    def mobile_add(self, work_id, target, edition_id=False):
        """Ajoute l'album à la collection (``target='collection'``) ou à la wishlist."""
        work = self.env["comic.work"].browse(int(work_id)).exists()
        if not work:
            raise UserError(self.env._("This album no longer exists."))
        edition = self.env["comic.edition"].browse(int(edition_id or 0)).exists()
        if not edition or edition.work_id != work:
            edition = work.primary_edition_id
        if not edition:
            raise UserError(self.env._("This album has no edition yet."))
        Album = self.env["comic.customer.album"]
        partner = self._partner()
        if target == "collection":
            Album._upsert(partner, edition, {"dans_collection": True, "dans_wishlist": False})
        elif target == "wishlist":
            entry = self._entries_by_work(work).get(work.id)
            if not (entry and entry.dans_collection):
                Album._upsert(partner, edition, {"dans_wishlist": True, "dans_collection": False})
        else:
            raise UserError(self.env._("Unknown destination."))
        return self._scan_result(work, edition)

    @api.model
    def mobile_set_reading(self, work_id, reading):
        """Change l'état de lecture d'un album possédé."""
        if reading not in READING_STATES:
            raise UserError(self.env._("Unknown reading status."))
        work = self.env["comic.work"].browse(int(work_id)).exists()
        entry = self._entries_by_work(work).get(work.id) if work else None
        if not (entry and entry.dans_collection):
            raise UserError(self.env._("This album is not in your collection."))
        entry.etat_lecture = reading
        return self._album_vals(work, entry)
