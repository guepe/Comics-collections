from odoo import api, fields, models

from odoo.tools import is_html_empty

from .res_partner import _open_ai_wizard


class ComicEditeur(models.Model):
    _inherit = "comic.editeur"

    # US-091 : histoire de la maison d'édition (rédigée ou générée par IA, à relire)
    comic_histoire = fields.Html(string="Histoire de la maison")
    comic_histoire_auto = fields.Boolean(
        string="Histoire générée automatiquement",
        readonly=True,
        copy=False,
        help="Texte écrit par la tâche de fond IA ; à relire. Décoché dès qu'il est modifié.",
    )

    has_comic_histoire = fields.Boolean(compute="_compute_has_comic_histoire")

    @api.depends("comic_histoire")
    def _compute_has_comic_histoire(self):
        for record in self:
            record.has_comic_histoire = not is_html_empty(record.comic_histoire)

    def write(self, vals):
        if "comic_histoire" in vals and not self.env.context.get("comic_ai_auto_text"):
            vals = dict(vals, comic_histoire_auto=False)
        return super().write(vals)

    def action_open_ai_wizard(self):
        return _open_ai_wizard(self, "editeur_id")
