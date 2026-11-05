import logging

from odoo import _, fields, models

_logger = logging.getLogger(__name__)


class ComicWork(models.Model):
    _inherit = "comic.work"

    a_valider = fields.Boolean(
        string="À valider",
        default=False,
        tracking=True,
        index=True,
        copy=False,
        help="Album proposé par un client depuis le portail, à contrôler avant mise en vente.",
    )
    portal_partner_id = fields.Many2one(
        "res.partner",
        string="Proposé par",
        readonly=True,
        copy=False,
        ondelete="set null",
    )

    def action_valider_portail(self):
        """Validate albums proposed from the portal."""
        self.write({"a_valider": False})
        return True

    def _get_shop_manager_users(self):
        group = self.env.ref("comic_shop.group_shop_manager", raise_if_not_found=False)
        if not group:
            return self.env["res.users"]
        group = group.sudo()
        users = group.all_user_ids if "all_user_ids" in group._fields else group.user_ids
        return users.filtered(lambda u: u.active and not u.share)

    def _schedule_portal_validation_activity(self):
        """Schedule one To-Do per album for a shop manager (silently skipped if none)."""
        managers = self._get_shop_manager_users()
        if not managers:
            return
        manager = managers.sorted("id")[0]
        summary = _("Album proposé par un client à valider")
        for work in self.sudo():
            if work.activity_ids.filtered(lambda a, s=summary: a.summary == s):
                continue
            try:
                with self.env.cr.savepoint():
                    work.activity_schedule(
                        "mail.mail_activity_data_todo",
                        summary=summary,
                        note=_("Proposé depuis le portail par %s.", work.portal_partner_id.display_name or "-"),
                        user_id=manager.id,
                    )
            except Exception as exc:  # pylint: disable=broad-except
                # La notification ne doit jamais bloquer l'ajout côté client
                _logger.warning("Portal validation activity not scheduled for work %s: %s", work.id, exc)

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
