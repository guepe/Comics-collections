from odoo import _, models
from odoo.exceptions import UserError


class ComicWork(models.Model):
    _inherit = "comic.work"

    def action_complete_from_sources(self):
        """Fiche album : complète l'édition principale depuis les sources (champs vides seulement)."""
        self.ensure_one()
        if not self.primary_edition_id:
            raise UserError(_("Cet album n'a pas encore d'édition à compléter."))
        return self.primary_edition_id.action_complete_from_sources()
