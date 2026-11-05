from odoo import api, models


class ComicIsbn(models.Model):
    _inherit = "comic.isbn"

    # Un ISBN créé / modifié / supprimé directement (portail, import, enrichissement)
    # ne passe pas par comic.edition.write : on resynchronise le code-barres produit ici.

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        records.edition_id._auto_sync_products()
        return records

    def write(self, vals):
        editions = self.edition_id
        res = super().write(vals)
        (editions | self.edition_id)._auto_sync_products()
        return res

    def unlink(self):
        editions = self.edition_id
        res = super().unlink()
        editions.exists()._auto_sync_products()
        return res
