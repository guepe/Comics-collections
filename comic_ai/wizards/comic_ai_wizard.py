"""Assistant IA d'une fiche album / édition (US-027 synopsis, US-028 traduction).

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


def text_to_html(text):
    """Texte brut IA → HTML propre : échappement, paragraphes (ligne vide), ``<br>``."""
    text = (text or "").replace("\r\n", "\n").strip()
    return plaintext2html(text) if text else ""


class ComicAiWizard(models.TransientModel):
    _name = "comic.ai.wizard"
    _description = "Assistant IA : synopsis et traduction"

    edition_id = fields.Many2one("comic.edition", string="Édition", required=True, readonly=True, ondelete="cascade")
    work_id = fields.Many2one(related="edition_id.work_id", string="Album")
    mode = fields.Selection(
        [("synopsis", "Générer le synopsis"), ("translate", "Traduire le synopsis")],
        string="Action",
        required=True,
        default="synopsis",
    )
    lang = fields.Selection(
        LANGS, string="Langue du synopsis", required=True, default=lambda self: self._default_lang()
    )
    source_synopsis = fields.Html(related="edition_id.synopsis", string="Synopsis actuel")
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
    destination_synopsis = fields.Html(string="Synopsis existant", compute="_compute_destination")
    destination_has_synopsis = fields.Boolean(compute="_compute_destination")
    state = fields.Selection([("draft", "Paramètres"), ("preview", "Prévisualisation")], default="draft")
    generated_text = fields.Text(string="Nouveau synopsis", help="Modifiable avant application.")
    provider = fields.Char(readonly=True)
    model_name = fields.Char(string="Modèle", readonly=True)
    replace_confirmed = fields.Boolean(string="Remplacer le synopsis existant")

    # ── Valeurs par défaut / calculs ─────────────────────────────────────────

    @api.model
    def _default_lang(self):
        return self.env["comic.ai.service"]._get_default_lang()

    @api.depends("edition_id")
    def _compute_target_lang(self):
        default = self._default_lang()
        codes = [code for code, _label in LANGS]
        for wiz in self:
            # Par défaut : langue de génération, sinon la première autre que celle de l'édition
            source = wiz.edition_id.langue
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

    @api.depends("mode", "translate_destination", "target_edition_id", "edition_id.synopsis")
    def _compute_destination(self):
        for wiz in self:
            dest = wiz.edition_id
            if wiz.mode == "translate" and wiz.translate_destination == "target" and wiz.target_edition_id:
                dest = wiz.target_edition_id
            wiz.destination_edition_id = dest
            wiz.destination_synopsis = dest.synopsis
            wiz.destination_has_synopsis = not is_html_empty(dest.synopsis)

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

    def _build_prompt(self):
        self.ensure_one()
        service = self.env["comic.ai.service"]
        values = self._album_values()
        current = "" if is_html_empty(self.edition_id.synopsis) else html2plaintext(self.edition_id.synopsis).strip()
        if self.mode == "translate":
            if not current:
                raise UserError(_("Cette édition n'a pas de synopsis à traduire."))
            source = self.edition_id.langue
            return service._render_prompt(
                "translate",
                langue_cible=service._lang_name(self.target_lang),
                langue_source=service._lang_name(source) if source in dict(LANGS) else _("non précisée"),
                synopsis=current,
                titre=values["titre"],
                serie=values["serie"],
            )
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
        """Écrit le texte (converti en HTML) sur l'édition de destination + trace chatter."""
        self.ensure_one()
        self._check_manager()
        if self.state != "preview" or not (self.generated_text or "").strip():
            raise UserError(_("Générez d'abord un texte à appliquer."))
        dest = self.destination_edition_id
        if not is_html_empty(dest.synopsis) and not self.replace_confirmed:
            raise UserError(
                _(
                    "L'édition « %s » a déjà un synopsis : cochez « Remplacer le synopsis existant » "
                    "pour confirmer son remplacement.",
                    dest.display_name,
                )
            )
        dest.synopsis = text_to_html(self.generated_text)
        if self.mode == "translate":
            label = _(
                "Synopsis traduit par IA (%(source)s → %(target)s)",
                source=self.edition_id.langue or "?",
                target=self.target_lang,
            )
        else:
            label = _("Synopsis généré par IA (%s)", self.lang)
        self.env["comic.ai.service"]._post_trace(dest, label, {"provider": self.provider, "model": self.model_name})
        return {"type": "ir.actions.act_window_close"}
