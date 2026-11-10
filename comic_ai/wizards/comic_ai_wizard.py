"""Assistant IA d'une fiche album / édition / série (US-027 synopsis, US-028 traduction).

L'assistant porte sur une seule fiche : une édition (``edition_id`` ; depuis un album :
son édition principale) ou une série (``serie_id``) pour le synopsis, un auteur
(``partner_id``, champ ``comic_bio``) ou un éditeur (``editeur_id``, champ
``comic_histoire``) pour la biographie / l'histoire de la maison (US-091).

Flux : choix du mode et de la langue → Générer (appel IA, prévisualisation dans le
wizard) → Appliquer / Régénérer / Annuler. Un synopsis existant n'est jamais écrasé
sans la case « Remplacer le synopsis existant ».
"""

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError
from odoo.tools import html2plaintext, is_html_empty, plaintext2html

from ..models.comic_ai_service import LANGS

ROLE_LABELS = {
    "scenariste": "scénario",
    "dessinateur": "dessin",
    "coloriste": "couleurs",
    "encreur": "encrage",
    "traducteur": "traduction",
    "autre": "autre",
}


# Champ texte écrit par l'assistant, selon le modèle de la fiche
TEXT_FIELDS = {
    "comic.edition": "synopsis",
    "comic.serie": "synopsis",
    "res.partner": "comic_bio",
    "comic.editeur": "comic_histoire",
}


def text_to_html(text):
    """Texte brut IA → HTML propre : échappement, paragraphes (ligne vide), ``<br>``."""
    text = (text or "").replace("\r\n", "\n").strip()
    return plaintext2html(text) if text else ""


class ComicAiWizard(models.TransientModel):
    _name = "comic.ai.wizard"
    _description = "Assistant IA : synopsis et traduction"

    edition_id = fields.Many2one("comic.edition", string="Édition", readonly=True, ondelete="cascade")
    serie_id = fields.Many2one("comic.serie", string="Série", readonly=True, ondelete="cascade")
    partner_id = fields.Many2one("res.partner", string="Auteur", readonly=True, ondelete="cascade")
    editeur_id = fields.Many2one("comic.editeur", string="Éditeur", readonly=True, ondelete="cascade")
    work_id = fields.Many2one(related="edition_id.work_id", string="Album")
    mode = fields.Selection(
        [("synopsis", "Générer le texte"), ("translate", "Traduire le texte")],
        string="Action",
        required=True,
        default="synopsis",
    )
    lang = fields.Selection(LANGS, string="Langue du texte", required=True, default=lambda self: self._default_lang())
    source_synopsis = fields.Html(string="Texte actuel", compute="_compute_source_synopsis")
    target_lang = fields.Selection(
        LANGS, string="Langue cible", compute="_compute_target_lang", store=True, readonly=False
    )
    target_edition_id = fields.Many2one(
        "comic.edition",
        string="Édition dans la langue cible",
        compute="_compute_target_edition_id",
        help="Autre édition du même album dans la langue cible, si elle existe.",
    )
    translate_destination = fields.Selection(
        [
            ("current", "Remplacer le synopsis de cette édition"),
            ("target", "L'écrire sur l'édition de la langue cible"),
        ],
        string="Appliquer la traduction",
        compute="_compute_translate_destination",
        store=True,
        readonly=False,
    )
    destination_edition_id = fields.Many2one("comic.edition", string="Édition modifiée", compute="_compute_destination")
    destination_synopsis = fields.Html(string="Texte existant", compute="_compute_destination")
    destination_has_synopsis = fields.Boolean(compute="_compute_destination")
    state = fields.Selection([("draft", "Paramètres"), ("preview", "Prévisualisation")], default="draft")
    generated_text = fields.Text(string="Nouveau texte", help="Modifiable avant application.")
    provider = fields.Char(readonly=True)
    model_name = fields.Char(string="Modèle", readonly=True)
    replace_confirmed = fields.Boolean(string="Remplacer le texte existant")

    _check_target = models.Constraint(
        "CHECK(num_nonnulls(edition_id, serie_id, partner_id, editeur_id) = 1)",
        "L'assistant IA porte sur une seule fiche (édition, série, auteur ou éditeur).",
    )

    # ── Valeurs par défaut / calculs ─────────────────────────────────────────

    def _source_record(self):
        """Fiche dont on lit le texte : série, édition, auteur ou éditeur."""
        self.ensure_one()
        return self.serie_id or self.edition_id or self.partner_id or self.editeur_id

    @staticmethod
    def _text(record):
        return record[TEXT_FIELDS[record._name]] if record else False

    @api.depends("edition_id.synopsis", "serie_id.synopsis", "partner_id.comic_bio", "editeur_id.comic_histoire")
    def _compute_source_synopsis(self):
        for wiz in self:
            wiz.source_synopsis = wiz._text(wiz._source_record())

    @api.model
    def _default_lang(self):
        return self.env["comic.ai.service"]._get_default_lang()

    @api.depends("edition_id")
    def _compute_target_lang(self):
        default = self._default_lang()
        codes = [code for code, _label in LANGS]
        for wiz in self:
            # Par défaut : langue de génération, sinon la première autre que celle de l'édition
            source = wiz.edition_id.langue if wiz.edition_id else False
            wiz.target_lang = wiz.target_lang or (
                default if default != source else next(c for c in codes if c != source)
            )

    @api.depends("edition_id", "target_lang")
    def _compute_target_edition_id(self):
        for wiz in self:
            others = wiz.edition_id.work_id.edition_ids - wiz.edition_id
            wiz.target_edition_id = others.filtered(lambda e, lang=wiz.target_lang: e.langue == lang).sorted("id")[:1]

    @api.depends("target_edition_id")
    def _compute_translate_destination(self):
        for wiz in self:
            wiz.translate_destination = "target" if wiz.target_edition_id else "current"

    def _destination_record(self):
        """Fiche sur laquelle le texte sera écrit (série, édition ou édition de la langue cible)."""
        self.ensure_one()
        if not self.edition_id:
            return self._source_record()
        if self.mode == "translate" and self.translate_destination == "target" and self.target_edition_id:
            return self.target_edition_id
        return self.edition_id

    @api.depends(
        "mode",
        "translate_destination",
        "target_edition_id",
        "edition_id.synopsis",
        "serie_id.synopsis",
        "partner_id.comic_bio",
        "editeur_id.comic_histoire",
    )
    def _compute_destination(self):
        for wiz in self:
            dest = wiz._destination_record()
            wiz.destination_edition_id = dest if dest._name == "comic.edition" else False
            wiz.destination_synopsis = wiz._text(dest)
            wiz.destination_has_synopsis = not is_html_empty(wiz._text(dest))

    @api.onchange("mode", "lang", "target_lang")
    def _onchange_reset_preview(self):
        # Changer d'action ou de langue invalide l'aperçu affiché.
        if self.state == "preview":
            self.state = "draft"
            self.generated_text = False
            self.replace_confirmed = False

    # ── Prompts ──────────────────────────────────────────────────────────────

    def _album_values(self):
        self.ensure_one()
        edition, work = self.edition_id, self.edition_id.work_id
        auteurs = ", ".join(
            f"{line.partner_id.name} ({ROLE_LABELS.get(line.role, line.role)})" for line in work.auteur_line_ids
        )
        return {
            "titre": work.titre_canonique,
            "serie": work.serie_id.name or "—",
            "tome": str(work.tome) if work.tome else "—",
            "auteurs": auteurs or "—",
            "editeur": edition.editeur_id.name or "—",
        }

    def _serie_values(self):
        self.ensure_one()
        serie = self.serie_id
        works = serie.work_ids.filtered("active").sorted(lambda w: (w.tome or 0, w.id))
        auteurs = []
        for line in works.auteur_line_ids:
            label = f"{line.partner_id.name} ({ROLE_LABELS.get(line.role, line.role)})"
            if label not in auteurs:
                auteurs.append(label)
        tomes = "\n".join(
            f"- T{w.tome} : {w.titre_canonique}" if w.tome else f"- {w.titre_canonique}" for w in works[:12]
        )
        return {
            "serie": serie.name,
            "type": dict(serie._fields["type"]._description_selection(self.env)).get(serie.type, "—"),
            "statut": dict(serie._fields["statut"]._description_selection(self.env)).get(serie.statut, "—"),
            "genre": serie.genre_id.name or "—",
            "editeur": serie.editeur_id.name or "—",
            "auteurs": ", ".join(auteurs[:8]) or "—",
            "nb_tomes": str(len(works)),
            "tomes": tomes or "—",
        }

    def _author_values(self):
        """Bibliographie connue de l'auteur : rôles, séries (éditeurs, années), co-auteurs."""
        self.ensure_one()
        partner = self.partner_id
        lines = partner.auteur_work_line_ids.filtered(lambda li: li.work_id.active)
        role_labels = dict(lines._fields["role"]._description_selection(self.env))
        roles = sorted({role_labels.get(li.role, li.role) for li in lines})
        series_rows = []
        for serie in lines.work_id.serie_id.sorted("name")[:15]:
            works = lines.work_id.filtered(lambda w, s=serie: w.serie_id == s)
            years = sorted({w.date_parution.year for w in works if w.date_parution})
            span = f", {years[0]}–{years[-1]}" if len(years) > 1 else (f", {years[0]}" if years else "")
            editeur = serie.editeur_id.name or works.primary_edition_id.editeur_id[:1].name or "—"
            series_rows.append(f"- {serie.name} ({len(works)} album(s), {editeur}{span})")
        coauthors = {}
        for work in lines.work_id:
            for other in work.auteur_line_ids.partner_id - partner:
                coauthors[other.name] = coauthors.get(other.name, 0) + 1
        top = sorted(coauthors.items(), key=lambda item: -item[1])[:8]
        return {
            "nom": partner.name,
            "roles": ", ".join(roles) or "—",
            "series": "\n".join(series_rows) or "—",
            "coauteurs": ", ".join(f"{name} ({count})" for name, count in top) or "—",
        }

    def _editeur_values(self):
        """Catalogue connu de l'éditeur : pays, site, séries et auteurs principaux."""
        self.ensure_one()
        editeur = self.editeur_id
        works = editeur.edition_ids.work_id.filtered("active")
        series = (editeur.serie_ids | works.serie_id).sorted("name")
        authors = {}
        for work in works:
            for partner in work.auteur_line_ids.partner_id:
                authors[partner.name] = authors.get(partner.name, 0) + 1
        top = sorted(authors.items(), key=lambda item: -item[1])[:10]
        years = sorted({e.date_parution.year for e in editeur.edition_ids if e.date_parution})
        return {
            "nom": editeur.name,
            "pays": editeur.pays_id.name or "—",
            "site": editeur.site_web or "—",
            "series": ", ".join(series[:20].mapped("name")) or "—",
            "nb_albums": str(len(works)),
            "annees": f"{years[0]}–{years[-1]}" if years else "—",
            "auteurs": ", ".join(f"{name} ({count})" for name, count in top) or "—",
        }

    def _build_prompt(self):
        self.ensure_one()
        service = self.env["comic.ai.service"]
        source_record = self._source_record()
        source_text = self._text(source_record)
        current = "" if is_html_empty(source_text) else html2plaintext(source_text).strip()
        if self.mode == "translate":
            if not current:
                if self.edition_id or self.serie_id:
                    raise UserError(_("Cette fiche n'a pas de synopsis à traduire."))
                raise UserError(_("Cette fiche n'a pas de texte à traduire."))
            source = self.edition_id.langue if self.edition_id else False
            if not self.edition_id:
                titre, serie = _("(texte de la fiche)"), source_record.display_name
            else:
                values = self._album_values()
                titre, serie = values["titre"], values["serie"]
            return service._render_prompt(
                "translate",
                langue_cible=service._lang_name(self.target_lang),
                langue_source=service._lang_name(source) if source in dict(LANGS) else _("non précisée"),
                synopsis=current,
                titre=titre,
                serie=serie,
            )
        if self.partner_id:
            return service._render_prompt(
                "author_bio",
                langue=service._lang_name(self.lang),
                bio_existante=current or "—",
                **self._author_values(),
            )
        if self.editeur_id:
            return service._render_prompt(
                "editeur_histoire",
                langue=service._lang_name(self.lang),
                histoire_existante=current or "—",
                **self._editeur_values(),
            )
        if self.serie_id:
            return service._render_prompt(
                "serie_synopsis",
                langue=service._lang_name(self.lang),
                synopsis_existant=current or "—",
                **self._serie_values(),
            )
        values = self._album_values()
        return service._render_prompt(
            "synopsis", langue=service._lang_name(self.lang), synopsis_existant=current or "—", **values
        )

    # ── Actions ──────────────────────────────────────────────────────────────

    def _check_manager(self):
        if not self.env.user.has_group("comics_collections.group_comic_manager"):
            raise AccessError(_("L'assistant IA est réservé aux gestionnaires de la collection."))

    def _reopen(self):
        return {
            "type": "ir.actions.act_window",
            "name": _("Assistant IA"),
            "res_model": self._name,
            "res_id": self.id,
            "view_mode": "form",
            "target": "new",
        }

    def action_generate(self):
        """Génère (ou régénère) le texte et l'affiche dans le wizard, resté ouvert."""
        self.ensure_one()
        self._check_manager()
        result = self.env["comic.ai.service"]._generate(self._build_prompt(), max_tokens=1024, effort="low")
        self.write(
            {
                "generated_text": result["text"],
                "provider": result["provider"],
                "model_name": result["model"],
                "state": "preview",
            }
        )
        return self._reopen()

    def action_apply(self):
        """Écrit le texte (converti en HTML) sur la fiche de destination + trace chatter."""
        self.ensure_one()
        self._check_manager()
        if self.state != "preview" or not (self.generated_text or "").strip():
            raise UserError(_("Générez d'abord un texte à appliquer."))
        dest = self._destination_record()
        field_name = TEXT_FIELDS[dest._name]
        if not is_html_empty(dest[field_name]) and not self.replace_confirmed:
            if field_name == "synopsis":
                message = _(
                    "L'édition « %s » a déjà un synopsis : cochez « Remplacer le synopsis existant » "
                    "pour confirmer son remplacement.",
                    dest.display_name,
                )
            else:
                message = _(
                    "« %s » a déjà un texte : cochez « Remplacer le texte existant » pour confirmer son remplacement.",
                    dest.display_name,
                )
            raise UserError(message)
        if dest._name == "res.partner":
            # Le gestionnaire BD (vérifié ci-dessus) n'a pas le droit d'écrire sur les contacts :
            # seule la biographie est écrite, en sudo (l'auteur du message chatter reste l'utilisateur).
            dest = dest.sudo()
        dest[field_name] = text_to_html(self.generated_text)
        kind = {
            "res.partner": _("Biographie"),
            "comic.editeur": _("Histoire de la maison"),
        }.get(dest._name, _("Synopsis"))
        if self.mode == "translate":
            source = (self.edition_id.langue if self.edition_id else False) or "?"
            if dest._name in ("res.partner", "comic.editeur"):
                label = _(
                    "%(kind)s traduite par IA (%(source)s → %(target)s)",
                    kind=kind,
                    source=source,
                    target=self.target_lang,
                )
            else:
                label = _("Synopsis traduit par IA (%(source)s → %(target)s)", source=source, target=self.target_lang)
        elif dest._name in ("res.partner", "comic.editeur"):
            label = _("%(kind)s générée par IA (%(lang)s) — à relire", kind=kind, lang=self.lang)
        else:
            label = _("Synopsis généré par IA (%s)", self.lang)
        self.env["comic.ai.service"]._post_trace(dest, label, {"provider": self.provider, "model": self.model_name})
        return {"type": "ir.actions.act_window_close"}
