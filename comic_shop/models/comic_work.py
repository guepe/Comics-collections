from odoo import _, models


class ComicWork(models.Model):
    _inherit = "comic.work"

    def write(self, vals):
        res = super().write(vals)
        if {"titre_canonique", "tome", "serie_id"} & set(vals):
            self.edition_ids._auto_sync_products()
        return res

    def _get_unlink_blockers(self):
        blockers = super()._get_unlink_blockers()
        editions = self.edition_ids
        albums = self.env["comic.customer.album"].sudo().search_count([("edition_id", "in", editions.ids)])
        if albums:
            blockers.append(_("%(count)s entrée(s) de bibliothèque client contiennent ces albums.", count=albums))
        products = editions.product_tmpl_id.filtered("active")
        if products:
            blockers.append(
                _(
                    "%(count)s produit(s) en vente sont liés à ces albums (archivez-les ou dissociez-les d'abord).",
                    count=len(products),
                )
            )
        return blockers

    def _set_etat_lecture(self, etat):
        partner_id = self.env.user.partner_id.id
        CustomerAlbum = self.env["comic.customer.album"]
        for work in self:
            edition = work.primary_edition_id
            if not edition:
                continue
            ca = CustomerAlbum.search(
                [
                    ("partner_id", "=", partner_id),
                    ("edition_id", "=", edition.id),
                ],
                limit=1,
            )
            if ca:
                ca.etat_lecture = etat
            else:
                CustomerAlbum.create(
                    {
                        "partner_id": partner_id,
                        "edition_id": edition.id,
                        "etat_lecture": etat,
                        "dans_collection": True,
                    }
                )

    def action_mark_lu(self):
        self._set_etat_lecture("lu")

    def action_mark_en_cours(self):
        self._set_etat_lecture("en_cours")

    def action_mark_non_lu(self):
        self._set_etat_lecture("non_lu")
