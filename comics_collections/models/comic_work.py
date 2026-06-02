import difflib
import re

from odoo import _, api, fields, models
from odoo.exceptions import UserError

from ..utils.normalize import normalize_title


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
    _description = "Œuvre BD (titre canonique)"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _rec_name = "titre_canonique"
    _order = "serie_id, tome"

    serie_id = fields.Many2one("comic.serie", string="Série", ondelete="restrict", index=True, tracking=True)
    titre_canonique = fields.Char(string="Titre canonique", required=True, tracking=True)
    tome = fields.Integer(tracking=True)
    slug = fields.Char(string="Slug URL", index=True, copy=False)
    titre_normalise = fields.Char(
        string="Titre normalisé",
        compute="_compute_titre_normalise",
        store=True,
        index=True,
    )

    # Références externes
    wikidata_id = fields.Char(string="Wikidata ID")
    openlibrary_id = fields.Char(string="Open Library ID")
    bedetheque_id = fields.Char(string="Bedetheque ID")
    comicvine_id = fields.Char(string="Comicvine ID")

    auteur_line_ids = fields.One2many("comic.work.auteur.line", "work_id", string="Auteurs")
    edition_ids = fields.One2many("comic.edition", "work_id", string="Éditions")
    active = fields.Boolean(default=True)

    nb_editions = fields.Integer(string="Nb éditions", compute="_compute_nb_editions", store=True)
    nb_auteurs = fields.Integer(string="Nb auteurs", compute="_compute_nb_auteurs", store=True)

    _unique_serie_tome = models.Constraint(
        "UNIQUE(serie_id, tome)",
        "Un tome de cette série existe déjà. Chaque numéro de tome doit être unique par série.",
    )

    # ── Édition principale — façade "album tout-en-un" ───────────────────────

    primary_edition_id = fields.Many2one(
        "comic.edition",
        string="Édition principale",
        compute="_compute_primary_edition_id",
        store=True,
        index=True,
    )

    # Champs délégués à l'édition principale (écriture transparente)
    image_couverture = fields.Image(
        string="Couverture",
        related="primary_edition_id.image_couverture",
        readonly=False,
    )
    editeur_id = fields.Many2one(
        "comic.editeur",
        string="Éditeur",
        related="primary_edition_id.editeur_id",
        readonly=False,
    )
    langue = fields.Selection(
        related="primary_edition_id.langue",
        string="Langue",
        readonly=False,
    )
    format = fields.Selection(
        related="primary_edition_id.format",
        string="Format",
        readonly=False,
    )
    nb_pages = fields.Integer(
        string="Nombre de pages",
        related="primary_edition_id.nb_pages",
        readonly=False,
    )
    date_parution = fields.Date(
        string="Date de parution",
        related="primary_edition_id.date_parution",
        readonly=False,
    )
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
        string="Lien Club.be",
        readonly=False,
    )
    url_amazon_be = fields.Char(
        related="primary_edition_id.url_amazon_be",
        string="Lien Amazon.be",
        readonly=False,
    )
    url_fnac_be = fields.Char(
        related="primary_edition_id.url_fnac_be",
        string="Lien FNAC.be",
        readonly=False,
    )

    # ── Computes ─────────────────────────────────────────────────────────────

    @api.depends("edition_ids")
    def _compute_primary_edition_id(self):
        for rec in self:
            rec.primary_edition_id = rec.edition_ids[:1] if rec.edition_ids else False

    @api.depends("edition_ids")
    def _compute_nb_editions(self):
        for rec in self:
            rec.nb_editions = len(rec.edition_ids)

    @api.depends("auteur_line_ids")
    def _compute_nb_auteurs(self):
        for rec in self:
            rec.nb_auteurs = len(rec.auteur_line_ids)

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
            tome = f" T{rec.tome:02d}" if rec.tome else ""
            sep = " — " if (serie or tome) and rec.titre_canonique else ""
            rec.display_name = f"{serie}{tome}{sep}{rec.titre_canonique}".strip()

    # ── Création + édition par défaut ────────────────────────────────────────

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get("slug"):
                vals["slug"] = self._generate_slug(vals)
        records = super().create(vals_list)
        # Skip auto-edition during data/demo file loading (install_mode) — the XML
        # provides explicit editions. Only auto-create in interactive/API context.
        if not self.env.context.get("install_mode"):
            for record in records:
                if not record.edition_ids:
                    self.env["comic.edition"].create(
                        {
                            "work_id": record.id,
                            "langue": "fr",
                            "format": "cartonne",
                        }
                    )
        return records

    # ── Actions ───────────────────────────────────────────────────────────────

    def action_view_editions(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": f"Éditions — {self.display_name}",
            "res_model": "comic.edition",
            "view_mode": "list,form",
            "domain": [("work_id", "=", self.id)],
            "context": {"default_work_id": self.id},
        }

    def action_generate_purchase_links(self):
        self.ensure_one()
        if self.primary_edition_id:
            self.primary_edition_id.action_generate_purchase_links()

    # ── Slug ──────────────────────────────────────────────────────────────────

    def _generate_slug(self, vals):
        serie_slug = ""
        if vals.get("serie_id"):
            serie = self.env["comic.serie"].browse(vals["serie_id"])
            serie_slug = re.sub(r"[^a-z0-9]+", "-", serie.name.lower()).strip("-")
        tome = vals.get("tome", 0)
        base = f"{serie_slug}-t{tome:02d}" if serie_slug else f"t{tome:02d}"
        slug = base
        n = 1
        while self.search_count([("slug", "=", slug)]):
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
                raise UserError(
                    _(
                        "Titre dupliqué détecté : « %(other)s » (Tome %(tome)s) existe "
                        "déjà dans cette série avec un titre identique après normalisation.\n"
                        "Si ce sont deux éditions différentes du même album, ouvrez l'album "
                        "existant et ajoutez une édition depuis l'onglet « Éditions multiples ».",
                        other=duplicate.display_name,
                        tome=duplicate.tome,
                    )
                )

    def _merge_into(self, target_work):
        """Transfer all editions and auteur lines to target_work, then archive self."""
        self.ensure_one()
        if self.id == target_work.id:
            raise UserError(_("Impossible de fusionner un album avec lui-même."))

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
            body=_(
                "Fusion : « %(source)s » (ID %(sid)s) intégré ici. "
                "%(n)d édition(s) transférée(s). L'album source a été archivé.",
                source=self.display_name,
                sid=self.id,
                n=editions_count,
            )
        )
        self.with_context(skip_dedup_check=True).write({"active": False})
        return target_work


class ComicWorkAuteurLine(models.Model):
    _name = "comic.work.auteur.line"
    _description = "Auteur d'une œuvre BD"

    work_id = fields.Many2one("comic.work", string="Œuvre", required=True, ondelete="cascade", index=True)
    partner_id = fields.Many2one("res.partner", string="Auteur", required=True)
    role = fields.Selection(
        [
            ("scenariste", "Scénariste"),
            ("dessinateur", "Dessinateur"),
            ("coloriste", "Coloriste"),
            ("encreur", "Encreur"),
            ("traducteur", "Traducteur"),
            ("autre", "Autre"),
        ],
        string="Rôle",
        required=True,
        default="dessinateur",
    )
