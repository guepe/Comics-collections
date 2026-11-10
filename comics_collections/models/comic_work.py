import difflib
import logging
import re
import unicodedata
from datetime import timedelta

from markupsafe import Markup

from odoo import SUPERUSER_ID, api, fields, models
from odoo.exceptions import UserError, ValidationError

from ..utils.normalize import normalize_title

_logger = logging.getLogger(__name__)

# Fenêtre « nouveauté » par défaut (jours), surchargée par ``comic.new_release_days``
DEFAULT_NEW_RELEASE_DAYS = 90


def _score_pair(same_serie, tome_a, titre_norm_a, serie_norm_a, tome_b, titre_norm_b, serie_norm_b):
    """Return (score, reason) for a pair of works.

    same_serie   — bool, True when both belong to the exact same serie record
    serie_norm_* — normalized serie name (empty string if no serie)
    titre_norm_* — normalized title
    """
    if same_serie and tome_a and tome_b and tome_a == tome_b:
        return 1.0, "conflit_certain"

    if not titre_norm_a or not titre_norm_b:
        return 0.0, ""

    titre_ratio = difflib.SequenceMatcher(None, titre_norm_a, titre_norm_b).ratio()

    if titre_ratio >= 0.85 and same_serie:
        return 0.9, "doublon_probable"

    if titre_ratio >= 0.85:
        if not serie_norm_a and not serie_norm_b:
            return round(titre_ratio, 3), "doublon_possible"
        if serie_norm_a and serie_norm_b:
            serie_ratio = difflib.SequenceMatcher(None, serie_norm_a, serie_norm_b).ratio()
            if serie_ratio >= 0.85:
                return round((titre_ratio + serie_ratio) / 2, 3), "doublon_possible"

    return 0.0, ""


class ComicWork(models.Model):
    _name = "comic.work"
    _description = "Comic work (canonical title)"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _rec_name = "titre_canonique"
    # Recherche « Album » / « Titre » : titre de l'album ou nom de la série
    _rec_names_search = ["titre_canonique", "serie_id.name"]
    _order = "serie_id, tome"

    serie_id = fields.Many2one("comic.serie", string="Series", ondelete="restrict", index=True, tracking=True)
    titre_canonique = fields.Char(string="Canonical title", required=True, tracking=True)
    tome = fields.Integer(string="Volume", tracking=True, aggregator=False)
    slug = fields.Char(string="URL slug", index=True, copy=False)
    titre_normalise = fields.Char(
        string="Normalized title",
        compute="_compute_titre_normalise",
        store=True,
        index=True,
    )

    # Références externes
    wikidata_id = fields.Char(string="Wikidata ID")
    openlibrary_id = fields.Char(string="Open Library ID")
    bedetheque_id = fields.Char(string="Bedetheque ID")
    comicvine_id = fields.Char(string="Comicvine ID")

    auteur_line_ids = fields.One2many("comic.work.auteur.line", "work_id", string="Authors")
    edition_ids = fields.One2many("comic.edition", "work_id", string="Editions")
    active = fields.Boolean(default=True)
    release_notified = fields.Boolean(
        string="New release notified",
        copy=False,
        help='True once the "new volume" alert has been sent to the followers of the series '
        "(or skipped for lack of followers): the album is never processed again.",
    )

    # Regroupements de la recherche (genre / type portés par la série)
    genre_id = fields.Many2one(related="serie_id.genre_id", store=True, string="Genre", index=True)
    serie_type = fields.Selection(related="serie_id.type", store=True, string="Series type")

    nb_editions = fields.Integer(string="Number of editions", compute="_compute_nb_editions", store=True)
    nb_auteurs = fields.Integer(string="Number of authors", compute="_compute_nb_auteurs", store=True)
    auteur_names = fields.Char(string="Authors", compute="_compute_auteur_names")

    # Unicité limitée aux tomes numérotés : tome = 0 (hors-série, album sans
    # numéro) peut exister plusieurs fois dans une même série.
    _unique_serie_tome_numbered = models.UniqueIndex(
        "(serie_id, tome) WHERE tome > 0",
        "A volume of this series already exists. Each volume number must be unique per series.",
    )

    # ── Édition principale — façade "album tout-en-un" ───────────────────────

    primary_edition_id = fields.Many2one(
        "comic.edition",
        string="Main edition",
        compute="_compute_primary_edition_id",
        store=True,
        index=True,
    )

    # Champs délégués à l'édition principale (écriture transparente)
    image_couverture = fields.Image(
        string="Cover",
        related="primary_edition_id.image_couverture",
        readonly=False,
    )
    editeur_id = fields.Many2one(
        "comic.editeur",
        string="Publisher",
        related="primary_edition_id.editeur_id",
        readonly=False,
    )
    langue = fields.Selection(
        related="primary_edition_id.langue",
        string="Language",
        readonly=False,
    )
    format = fields.Selection(
        related="primary_edition_id.format",
        string="Format",
        readonly=False,
    )
    nb_pages = fields.Integer(
        string="Number of pages",
        related="primary_edition_id.nb_pages",
        readonly=False,
    )
    date_parution = fields.Date(
        string="Release date",
        related="primary_edition_id.date_parution",
        readonly=False,
    )
    # Bibliothèque de l'utilisateur courant (bouton « Ajouter à ma wishlist », #7)
    in_my_collection = fields.Boolean(string="In my collection", compute="_compute_my_library")
    in_my_wishlist = fields.Boolean(string="In my wishlist", compute="_compute_my_library")
    synopsis = fields.Html(
        string="Synopsis",
        related="primary_edition_id.synopsis",
        readonly=False,
    )
    isbn_ids = fields.One2many(
        related="primary_edition_id.isbn_ids",
        string="ISBNs",
        readonly=False,
    )
    url_club_be = fields.Char(
        related="primary_edition_id.url_club_be",
        string="Club.be link",
        readonly=False,
    )
    url_amazon_be = fields.Char(
        related="primary_edition_id.url_amazon_be",
        string="Amazon.be link",
        readonly=False,
    )
    url_fnac_be = fields.Char(
        related="primary_edition_id.url_fnac_be",
        string="FNAC.be link",
        readonly=False,
    )

    # ── Computes ─────────────────────────────────────────────────────────────

    @api.depends("edition_ids")
    def _compute_primary_edition_id(self):
        # Édition principale = la première créée (stable). Avant : edition_ids[:1] suivait
        # l'ordre par date de parution et changeait dès qu'une édition plus ancienne arrivait.
        for rec in self:
            rec.primary_edition_id = rec.edition_ids.sorted("id")[:1]

    @api.depends_context("uid")
    @api.depends(
        "edition_ids.customer_album_ids.partner_id",
        "edition_ids.customer_album_ids.dans_collection",
        "edition_ids.customer_album_ids.dans_wishlist",
    )
    def _compute_my_library(self):
        """Album possédé / souhaité par l'utilisateur courant (une de ses éditions)."""
        partner = self.env.user.partner_id
        entries = self.env["comic.customer.album"].search(
            [("partner_id", "=", partner.id), ("edition_id.work_id", "in", [i for i in self.ids if i])]
        )
        owned = set(entries.filtered("dans_collection").edition_id.work_id.ids)
        wished = set(entries.filtered(lambda e: e.dans_wishlist and not e.dans_collection).edition_id.work_id.ids)
        for work in self:
            work.in_my_collection = work.id in owned
            work.in_my_wishlist = work.id in wished

    @api.depends("edition_ids")
    def _compute_nb_editions(self):
        for rec in self:
            rec.nb_editions = len(rec.edition_ids)

    @api.depends("auteur_line_ids")
    def _compute_nb_auteurs(self):
        for rec in self:
            rec.nb_auteurs = len(rec.auteur_line_ids)

    @api.depends("auteur_line_ids.partner_id.name")
    def _compute_auteur_names(self):
        for rec in self:
            rec.auteur_names = ", ".join(dict.fromkeys(rec.auteur_line_ids.partner_id.mapped("name")))

    @api.depends("titre_canonique")
    def _compute_titre_normalise(self):
        for rec in self:
            rec.titre_normalise = normalize_title(rec.titre_canonique)

    @api.model
    def _name_search(self, name="", domain=None, operator="ilike", limit=100, order=None):
        # If the input looks like an ISBN (digits/dashes, 10-17 chars), search via isbn first
        isbn_clean = re.sub(r"[^0-9X]", "", (name or "").upper())
        if len(isbn_clean) >= 10:
            isbn_domain = [("edition_ids.isbn_ids.isbn_13", "ilike", isbn_clean)]
            works = self.search((domain or []) + isbn_domain, limit=limit, order=order)
            if works:
                return works
        return super()._name_search(name, domain=domain, operator=operator, limit=limit, order=order)

    def _compute_display_name(self):
        for rec in self:
            serie = rec.serie_id.name if rec.serie_id else ""
            tome = " " + self.env._("Vol. %s", f"{rec.tome:02d}") if rec.tome else ""
            sep = " — " if (serie or tome) and rec.titre_canonique else ""
            rec.display_name = f"{serie}{tome}{sep}{rec.titre_canonique}".strip()

    # ── Création + édition par défaut ────────────────────────────────────────

    # Champs de la façade « album » stockés sur l'édition principale
    _EDITION_FIELDS = (
        "image_couverture",
        "editeur_id",
        "langue",
        "format",
        "nb_pages",
        "date_parution",
        "synopsis",
        "isbn_ids",
        "url_club_be",
        "url_amazon_be",
        "url_fnac_be",
    )

    @api.model_create_multi
    def create(self, vals_list):
        # Les champs d'édition saisis à la création (éditeur, ISBN, couverture…) ne
        # peuvent pas passer par le related : l'édition n'existe pas encore. On les
        # retire ici et on les donne à l'édition créée juste après.
        edition_vals_list = []
        for vals in vals_list:
            if not vals.get("slug"):
                vals["slug"] = self._generate_slug(vals)
            edition_vals_list.append({f: vals.pop(f) for f in self._EDITION_FIELDS if f in vals})
        records = super().create(vals_list)
        install_mode = self.env.context.get("install_mode")
        for record, edition_vals in zip(records, edition_vals_list):
            edition_vals = {k: v for k, v in edition_vals.items() if v}
            if record.edition_ids:
                if edition_vals:
                    record.primary_edition_id.write(edition_vals)
            elif edition_vals or not install_mode:
                # install_mode (données XML/démo) : les éditions sont fournies explicitement
                self.env["comic.edition"].create(
                    {"work_id": record.id, "langue": "fr", "format": "cartonne", **edition_vals}
                )
        if self.env.context.get("comic_auto_own"):
            # Créé depuis « Mes albums » / « Mes séries » (US-087) : création = possession.
            Album = self.env["comic.customer.album"]
            partner = self.env.user.partner_id
            for record in records.filtered("primary_edition_id"):
                Album._upsert(partner, record.primary_edition_id, {"dans_collection": True})
        return records

    def write(self, vals):
        res = super().write(vals)
        if ("serie_id" in vals or "tome" in vals) and "slug" not in vals:
            # Le slug dépend de la série et du tome : on le régénère s'ils changent.
            for record in self:
                slug = record._generate_slug(
                    {"serie_id": record.serie_id.id, "tome": record.tome},
                    exclude_id=record.id,
                )
                if slug != record.slug:
                    super(ComicWork, record).write({"slug": slug})
        return res

    # ── Suppression ──────────────────────────────────────────────────────────

    def _get_unlink_blockers(self):
        """Messages expliquant pourquoi ces albums ne peuvent pas être supprimés.
        Étendu par les modules qui référencent les éditions (ex. comic_shop)."""
        blockers = []
        prets = self.env["comic.pret"].sudo().search([("edition_id", "in", self.edition_ids.ids)])
        if prets:
            blockers.append(self.env._("%(count)s loan(s) involve these albums (delete them first).", count=len(prets)))
        albums = self.env["comic.customer.album"].sudo().search_count([("edition_id", "in", self.edition_ids.ids)])
        if albums:
            blockers.append(self.env._("%(count)s library entry(ies) contain these albums.", count=albums))
        return blockers

    @api.ondelete(at_uninstall=False)
    def _unlink_except_blocked(self):
        blockers = self._get_unlink_blockers()
        if blockers:
            raise UserError(self.env._("Cannot delete:") + "\n- " + "\n- ".join(blockers))

    def unlink(self):
        # Contrôle explicite AVANT de toucher aux éditions (sinon un prêt lèverait une
        # erreur SQL brute) ; il est aussi rejoué par l'ORM via @api.ondelete.
        self._unlink_except_blocked()
        # L'édition est liée en ondelete="restrict" : on supprime d'abord les éditions
        # (créées automatiquement avec l'album), puis l'album lui-même.
        self.edition_ids.unlink()
        return super().unlink()

    # ── Bibliothèque personnelle : état de lecture ───────────────────────────

    def _set_etat_lecture(self, etat):
        """Set the reading state in the current user's library (adds the album if needed)."""
        partner = self.env.user.partner_id
        CustomerAlbum = self.env["comic.customer.album"]
        for work in self:
            edition = work.primary_edition_id
            if not edition:
                continue
            CustomerAlbum._upsert(partner, edition, {"etat_lecture": etat})

    def action_mark_lu(self):
        self._set_etat_lecture("lu")

    def action_mark_en_cours(self):
        self._set_etat_lecture("en_cours")

    def action_mark_non_lu(self):
        self._set_etat_lecture("non_lu")

    # ── Alerte nouveautés sur les séries suivies (US-068) ────────────────────

    @api.model
    def _get_new_release_days(self):
        """Fenêtre « nouveauté » en jours (paramètre ``comic.new_release_days``, 90 par défaut)."""
        raw = self.env["ir.config_parameter"].sudo().get_param("comic.new_release_days")
        try:
            days = int(raw)
        except (TypeError, ValueError):
            return DEFAULT_NEW_RELEASE_DAYS
        return days if days >= 0 else DEFAULT_NEW_RELEASE_DAYS

    def _is_new_release(self, days=None):
        """Vrai si l'album paraît dans le futur ou a paru dans les N derniers jours.

        Sans date de parution connue, l'album n'est jamais considéré comme une nouveauté.
        """
        self.ensure_one()
        if not self.date_parution:
            return False
        if days is None:
            days = self._get_new_release_days()
        today = fields.Date.context_today(self)
        # Couvre aussi les dates futures (>= aujourd'hui - N)
        return self.date_parution >= today - timedelta(days=days)

    def _is_automated_user(self):
        """Contexte cron : superutilisateur ou OdooBot (``base.user_root``)."""
        user = self.env.user
        root = self.env.ref("base.user_root", raise_if_not_found=False)
        return user.id == SUPERUSER_ID or (root and user == root)

    def _new_release_message_body(self):
        self.ensure_one()
        tome = " " + self.env._("Vol. %s", self.tome) if self.tome else ""
        return Markup(
            self.env._(
                "New volume in a series you follow: <strong>%(serie)s%(tome)s</strong> — %(title)s "
                "(released on %(date)s)."
            )
        ) % {
            "serie": self.serie_id.name,
            "tome": tome,
            "title": self.titre_canonique,
            "date": self.date_parution.strftime("%d/%m/%Y"),
        }

    def _notify_new_release(self):
        """Prévient les abonnés de la série de chaque nouveau tome (une seule fois par album).

        Destinataires : partenaires des utilisateurs internes actifs qui suivent la série, sauf
        l'utilisateur courant (il vient d'ajouter le tome) hors contexte cron.
        """
        days = self._get_new_release_days()
        exclude_current = not self._is_automated_user()
        to_flag = self.browse()
        for work in self:
            if work.release_notified or not work.serie_id or not work._is_new_release(days):
                continue
            # Utilisateurs internes seulement : les clients du portail (comic_shop) sont
            # prévenus par email à la mise en vente, pas à la mise en catalogue.
            users = work.serie_id.sudo().suivi_user_ids.filtered(lambda u: u.active and not u.share)
            if exclude_current:
                users -= self.env.user
            partners = users.partner_id
            if partners:
                work.message_post(
                    body=work._new_release_message_body(),
                    message_type="notification",
                    subtype_xmlid="mail.mt_comment",
                    partner_ids=partners.ids,
                    # Seuls les abonnés de la série sont prévenus, pas les abonnés de l'album
                    notify_skip_followers=True,
                )
                _logger.info("Nouveauté « %s » notifiée à %d abonné(s).", work.display_name, len(partners))
            to_flag |= work
        if to_flag:
            to_flag.write({"release_notified": True})
        return to_flag

    def action_add_to_my_wishlist(self):
        """Place l'édition principale de chaque album dans la wishlist de l'utilisateur.

        Un album déjà possédé (``dans_collection``) n'est jamais déclassé en wishlist.
        """
        partner = self.env.user.partner_id
        CustomerAlbum = self.env["comic.customer.album"]
        added = 0
        for work in self:
            edition = work.primary_edition_id
            if not edition:
                continue
            existing = CustomerAlbum.search(
                [("partner_id", "=", partner.id), ("edition_id", "=", edition.id)],
                limit=1,
            )
            if existing and existing.dans_collection:
                continue
            CustomerAlbum._upsert(partner, edition, {"dans_wishlist": True, "dans_collection": False})
            added += 1
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": self.env._("Wishlist"),
                "message": self.env._("%(count)s album(s) added to your wishlist.", count=added),
                "type": "success" if added else "info",
                "sticky": False,
            },
        }

    # ── Actions ───────────────────────────────────────────────────────────────

    def action_view_editions(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": self.env._("Editions — %s", self.display_name),
            "res_model": "comic.edition",
            "view_mode": "list,form",
            "domain": [("work_id", "=", self.id)],
            "context": {"default_work_id": self.id},
        }

    @api.model
    def _action_open_works(self, works, title):
        """Liste des albums donnés, groupée par série (fiches auteur / éditeur)."""
        return {
            "type": "ir.actions.act_window",
            "name": self.env._("Albums — %s", title),
            "res_model": "comic.work",
            "view_mode": "list,kanban,form",
            "views": [
                (self.env.ref("comics_collections.view_comic_work_list").id, "list"),
                (False, "kanban"),
                (False, "form"),
            ],
            "domain": [("id", "in", works.ids)],
            "context": {"create": False},
        }

    def action_generate_purchase_links(self):
        self.ensure_one()
        if self.primary_edition_id:
            self.primary_edition_id.action_generate_purchase_links()

    # ── Slug ──────────────────────────────────────────────────────────────────

    @staticmethod
    def _slugify(text):
        """Translittère (NFKD, sans diacritiques) puis remplace le reste par des tirets."""
        text = unicodedata.normalize("NFKD", text or "")
        text = "".join(c for c in text if not unicodedata.combining(c))
        return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")

    def _generate_slug(self, vals, exclude_id=None):
        serie_slug = ""
        if vals.get("serie_id"):
            serie = self.env["comic.serie"].browse(vals["serie_id"])
            serie_slug = self._slugify(serie.name)
        tome = vals.get("tome") or 0
        base = f"{serie_slug}-t{tome:02d}" if serie_slug else f"t{tome:02d}"
        slug = base
        n = 1
        exclude_domain = [("id", "!=", exclude_id)] if exclude_id else []
        while self.search_count([("slug", "=", slug)] + exclude_domain):
            slug = f"{base}-{n}"
            n += 1
        return slug

    # ── Moteur de déduplication ───────────────────────────────────────────────

    def _find_duplicate_candidates(self, serie_id, tome, titre, exclude_self=True):
        """Return list of dicts {work, score, reason} for potential duplicates.

        Score levels:
            1.0  conflit_certain  — exact (serie_id, tome) match
            0.9  doublon_probable — same serie + similar title (≥ 0.85)
            0.7+ doublon_possible — similar serie + similar title (both ≥ 0.85)
        """
        titre_norm = normalize_title(titre)
        serie_norm = ""
        if serie_id:
            serie = self.env["comic.serie"].browse(serie_id)
            serie_norm = serie.name_normalise or normalize_title(serie.name)

        domain = [("active", "=", True)]
        if exclude_self and self.ids:
            domain.append(("id", "not in", self.ids))

        candidates = []
        for work in self.search(domain):
            same_serie = bool(serie_id and work.serie_id.id == serie_id)
            score, reason = _score_pair(
                same_serie,
                tome,
                titre_norm,
                serie_norm,
                work.tome,
                work.titre_normalise or "",
                work.serie_id.name_normalise or "",
            )
            if score > 0:
                candidates.append({"work": work, "score": score, "reason": reason})

        return sorted(candidates, key=lambda x: x["score"], reverse=True)

    @api.constrains("serie_id", "titre_canonique")
    def _check_title_duplicate(self):
        for rec in self:
            if self.env.context.get("skip_dedup_check"):
                continue
            titre_norm = normalize_title(rec.titre_canonique)
            if not titre_norm or not rec.serie_id:
                continue
            duplicate = self.search(
                [
                    ("id", "!=", rec.id),
                    ("serie_id", "=", rec.serie_id.id),
                    ("titre_normalise", "=", titre_norm),
                    ("active", "=", True),
                ],
                limit=1,
            )
            if duplicate:
                raise ValidationError(
                    self.env._(
                        'Duplicate title detected: "%(other)s" (Volume %(tome)s) already exists '
                        "in this series with an identical title after normalization.\n"
                        "If these are two different editions of the same album, open the existing "
                        'album and add a version from the "Other versions" tab.',
                        other=duplicate.display_name,
                        tome=duplicate.tome,
                    )
                )

    def _merge_into(self, target_work):
        """Transfer all editions and auteur lines to target_work, then archive self."""
        self.ensure_one()
        if self.id == target_work.id:
            raise UserError(self.env._("Cannot merge an album with itself."))

        editions_count = len(self.edition_ids)

        # Customer albums follow their editions automatically via FK
        self.edition_ids.write({"work_id": target_work.id})

        # Transfer auteur lines, skipping partners already on target
        existing_partners = target_work.auteur_line_ids.mapped("partner_id")
        for line in self.auteur_line_ids:
            if line.partner_id not in existing_partners:
                line.write({"work_id": target_work.id})
            else:
                line.unlink()

        target_work.message_post(
            body=self.env._(
                'Merge: "%(src)s" (ID %(sid)s) merged into this album. '
                "%(n)d edition(s) transferred. The source album has been archived.",
                src=self.display_name,
                sid=self.id,
                n=editions_count,
            )
        )
        self.with_context(skip_dedup_check=True).write({"active": False})
        # The source is archived: every dedup pair involving it is now obsolete
        self.env["comic.dedup.pair"].sudo()._cleanup_for_works(self)
        return target_work


class ComicWorkAuteurLine(models.Model):
    _name = "comic.work.auteur.line"
    _description = "Comic work author"

    work_id = fields.Many2one("comic.work", string="Album", required=True, ondelete="cascade", index=True)
    partner_id = fields.Many2one("res.partner", string="Author", required=True)
    serie_id = fields.Many2one(related="work_id.serie_id", store=True, string="Series")
    tome = fields.Integer(related="work_id.tome", store=True, string="Volume", aggregator=False)
    role = fields.Selection(
        [
            ("scenariste", "Writer"),
            ("dessinateur", "Artist"),
            ("coloriste", "Colorist"),
            ("encreur", "Inker"),
            ("traducteur", "Translator"),
            ("autre", "Other"),
        ],
        required=True,
        default="dessinateur",
    )

    @api.model_create_multi
    def create(self, vals_list):
        lines = super().create(vals_list)
        # Tout partenaire crédité sur un album devient « Auteur BD ».
        partners = lines.partner_id.filtered(lambda p: not p.is_comic_author)
        if partners:
            partners.sudo().write({"is_comic_author": True})
        return lines
