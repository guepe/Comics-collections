from odoo import models


class ComicWork(models.Model):
    _inherit = 'comic.work'

    def _set_etat_lecture(self, etat):
        partner_id = self.env.user.partner_id.id
        CustomerAlbum = self.env['comic.customer.album']
        for work in self:
            edition = work.primary_edition_id
            if not edition:
                continue
            ca = CustomerAlbum.search([
                ('partner_id', '=', partner_id),
                ('edition_id', '=', edition.id),
            ], limit=1)
            if ca:
                ca.etat_lecture = etat
            else:
                CustomerAlbum.create({
                    'partner_id': partner_id,
                    'edition_id': edition.id,
                    'etat_lecture': etat,
                    'dans_collection': True,
                })

    def action_mark_lu(self):
        self._set_etat_lecture('lu')

    def action_mark_en_cours(self):
        self._set_etat_lecture('en_cours')

    def action_mark_non_lu(self):
        self._set_etat_lecture('non_lu')
