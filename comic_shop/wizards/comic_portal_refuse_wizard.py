from markupsafe import Markup

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class ComicPortalRefuseWizard(models.TransientModel):
    _name = "comic.portal.refuse.wizard"
    _description = "Refus d'un album proposé depuis le portail"

    work_id = fields.Many2one("comic.work", string="Album proposé", required=True, readonly=True)
    portal_partner_id = fields.Many2one(related="work_id.portal_partner_id", string="Proposé par")
    motif = fields.Selection(
        [
            ("doublon", "Doublon d'un album existant"),
            ("incorrect", "Fiche incorrecte"),
        ],
        string="Motif",
        required=True,
        default="doublon",
    )
    target_work_id = fields.Many2one(
        "comic.work",
        string="Album existant",
        domain="[('id', '!=', work_id), ('a_valider', '=', False)]",
        help="L'entrée de bibliothèque du client est reportée sur cet album.",
    )
    message = fields.Text(
        string="Message au client",
        help="Ajouté à la notification envoyée au client (facultatif).",
    )

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        if not res.get("work_id") and self.env.context.get("active_model") == "comic.work":
            res["work_id"] = self.env.context.get("active_id")
        return res

    def action_refuse(self):
        self.ensure_one()
        work = self.work_id.sudo()
        if not work.a_valider:
            raise UserError(_("Cet album n'est plus à valider."))
        if self.motif == "doublon" and not self.target_work_id:
            raise UserError(_("Choisissez l'album existant dont celui-ci est le doublon."))

        # Tout lire AVANT de supprimer : l'assistant (many2one requis vers l'album) est
        # supprimé en cascade avec l'album.
        motif, target, message = self.motif, self.target_work_id.sudo(), self.message
        partner = work.portal_partner_id
        title = work.display_name
        serie, editeurs = work.serie_id, work.edition_ids.editeur_id
        albums = self.env["comic.customer.album"].sudo().search([("edition_id", "in", work.edition_ids.ids)])

        target_name = target.display_name
        if motif == "doublon":
            self._transfer_to_target(work, albums, target)
        else:
            albums.unlink()
        work.edition_ids.isbn_ids.unlink()
        work.unlink()
        self._cleanup_orphans(serie, editeurs)
        self._notify_partner(partner, title, motif, target_name, message)
        return {"type": "ir.actions.act_window_close"}

    @api.model
    def _transfer_to_target(self, work, albums, target):
        """Move library entries (and a missing ISBN) onto the existing album."""
        target_edition = target.primary_edition_id
        if not target_edition:
            raise UserError(_("L'album existant n'a pas d'édition."))
        Album = self.env["comic.customer.album"].sudo()
        for album in albums:
            existing = Album.search(
                [("partner_id", "=", album.partner_id.id), ("edition_id", "=", target_edition.id)], limit=1
            )
            if existing:
                album.unlink()  # le client possède déjà l'album existant
            else:
                album.edition_id = target_edition
        isbns = work.edition_ids.isbn_ids
        if isbns and not target_edition.isbn_ids:
            isbns.write({"edition_id": target_edition.id})

    @api.model
    def _cleanup_orphans(self, serie, editeurs):
        """Delete the série / éditeurs created from the portal that nothing uses anymore."""
        serie = serie.sudo().exists()
        if serie and serie.a_valider and not serie.with_context(active_test=False).work_ids:
            serie.unlink()
        for editeur in editeurs.sudo().exists().filtered("a_valider"):
            used = self.env["comic.edition"].sudo().with_context(active_test=False).search_count(
                [("editeur_id", "=", editeur.id)]
            ) or self.env["comic.serie"].sudo().with_context(active_test=False).search_count(
                [("editeur_id", "=", editeur.id)]
            )
            if not used:
                editeur.unlink()

    @api.model
    def _notify_partner(self, partner, title, motif, target_name, message):
        if not partner:
            return
        if motif == "doublon":
            body = Markup(_("<p>Votre proposition « %(title)s » existait déjà dans notre catalogue : "
                            "elle a été rattachée à « %(target)s » dans votre bibliothèque.</p>")) % {
                "title": title,
                "target": target_name,
            }
        else:
            body = Markup(_("<p>Votre proposition « %(title)s » n'a pas pu être ajoutée à notre "
                            "catalogue et a été retirée de votre bibliothèque.</p>")) % {"title": title}
        if message:
            body += Markup("<p>%s</p>") % message
        partner.sudo().message_post(
            body=body,
            subject=_("Votre proposition d'album"),
            partner_ids=partner.ids,
            message_type="comment",
            subtype_xmlid="mail.mt_comment",
        )
