from odoo import fields, models


class ComicAiSynopsisAutoMixin(models.AbstractModel):
    """Case « synopsis généré automatiquement » (US-090), décochée dès qu'on retouche le synopsis."""

    _name = "comic.ai.synopsis.auto.mixin"
    _description = "Synopsis généré automatiquement (IA)"

    synopsis_auto = fields.Boolean(
        string="Synopsis généré automatiquement",
        readonly=True,
        copy=False,
        help="Synopsis écrit par la tâche de fond IA ; à relire. Décoché dès qu'il est modifié.",
    )

    def write(self, vals):
        if "synopsis" in vals and not self.env.context.get("comic_ai_auto_text"):
            vals = dict(vals, synopsis_auto=False)
        return super().write(vals)
