from odoo import _, models
from odoo.exceptions import AccessError, UserError


class ComicEdition(models.Model):
    _inherit = "comic.edition"

    def action_open_ai_wizard(self):
        """Ouvre l'assistant IA (synopsis / traduction) sur cette édition (gestionnaires)."""
        self.ensure_one()
        if not self.env.user.has_group("comics_collections.group_comic_manager"):
            raise AccessError(_("L'assistant IA est réservé aux gestionnaires de la collection."))
        if not self.id:
            raise UserError(_("Enregistrez d'abord la fiche."))
        mode = self.env.context.get("comic_ai_mode") or "synopsis"
        wizard = self.env["comic.ai.wizard"].create({"edition_id": self.id, "mode": mode})
        return wizard._reopen()
