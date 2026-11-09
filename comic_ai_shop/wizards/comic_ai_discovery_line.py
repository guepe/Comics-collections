from odoo import models


class ComicAiDiscoveryLine(models.TransientModel):
    _inherit = "comic.ai.discovery.line"

    def _create_catalog_entry(self, serie):
        """Portal: the missing series / volume 1 go through the moderated circuit.

        Fiches créées « à valider » et signalées au gestionnaire du shop, comme un
        album proposé depuis « Ajouter une BD » (comic.edition._create_from_portal_data).
        """
        self.ensure_one()
        if not self.wizard_id.portal:
            return super()._create_catalog_entry(serie)
        data = {
            "title": self.verified_title or (serie.name if serie else self.name),
            "serie_name": serie.name if serie else self.name,
            "editeur_name": self.verified_editeur or "",
            "isbn": self._valid_isbn(),
            "tome": 1,
            "cover_url": "",
        }
        return self.env["comic.edition"].sudo()._create_from_portal_data(data, self.wizard_id.partner_id)
