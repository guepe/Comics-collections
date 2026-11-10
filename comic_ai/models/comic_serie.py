from odoo import _, models
from odoo.exceptions import AccessError, UserError


class ComicSerie(models.Model):
    _name = "comic.serie"
    _inherit = ["comic.serie", "comic.ai.synopsis.auto.mixin"]

    def action_open_ai_wizard(self):
        """Ouvre l'assistant IA (synopsis / traduction) sur cette série (gestionnaires)."""
        self.ensure_one()
        if not self.env.user.has_group("comics_collections.group_comic_manager"):
            raise AccessError(_("L'assistant IA est réservé aux gestionnaires de la collection."))
        if not self.id:
            raise UserError(_("Enregistrez d'abord la fiche."))
        mode = self.env.context.get("comic_ai_mode") or "synopsis"
        wizard = self.env["comic.ai.wizard"].create({"serie_id": self.id, "mode": mode})
        return wizard._reopen()
