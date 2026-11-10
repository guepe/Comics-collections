from odoo import _, api, fields, models
from odoo.tools import is_html_empty
from odoo.exceptions import AccessError, UserError


def _open_ai_wizard(record, field_name):
    """Ouvre l'assistant IA (génération / traduction) sur ``record`` (gestionnaires)."""
    record.ensure_one()
    if not record.env.user.has_group("comics_collections.group_comic_manager"):
        raise AccessError(_("L'assistant IA est réservé aux gestionnaires de la collection."))
    if not record.id:
        raise UserError(_("Enregistrez d'abord la fiche."))
    mode = record.env.context.get("comic_ai_mode") or "synopsis"
    wizard = record.env["comic.ai.wizard"].create({field_name: record.id, "mode": mode})
    return wizard._reopen()


class ResPartner(models.Model):
    _inherit = "res.partner"

    # US-091 : biographie de l'auteur (rédigée ou générée par IA, à relire)
    comic_bio = fields.Html(string="Biographie")
    comic_bio_auto = fields.Boolean(
        string="Biographie générée automatiquement",
        readonly=True,
        copy=False,
        help="Texte écrit par la tâche de fond IA ; à relire. Décoché dès qu'il est modifié.",
    )

    has_comic_bio = fields.Boolean(compute="_compute_has_comic_bio")

    @api.depends("comic_bio")
    def _compute_has_comic_bio(self):
        for record in self:
            record.has_comic_bio = not is_html_empty(record.comic_bio)

    def write(self, vals):
        if "comic_bio" in vals and not self.env.context.get("comic_ai_auto_text"):
            vals = dict(vals, comic_bio_auto=False)
        return super().write(vals)

    def action_open_ai_wizard(self):
        return _open_ai_wizard(self, "partner_id")
