from odoo import _, models
from odoo.exceptions import UserError


class ComicWork(models.Model):
    _inherit = "comic.work"

    def action_open_ai_wizard(self):
        """Assistant IA de l'album : agit sur son édition principale."""
        self.ensure_one()
        if not self.primary_edition_id:
            raise UserError(_("Cet album n'a pas encore d'édition : renseignez d'abord ses informations."))
        return self.primary_edition_id.action_open_ai_wizard()
