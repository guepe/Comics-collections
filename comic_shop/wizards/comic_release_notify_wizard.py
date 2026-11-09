from markupsafe import Markup, escape

from odoo import _, api, fields, models


class ComicReleaseNotifyWizard(models.TransientModel):
    """Aperçu puis envoi de l'email « disponible » aux clients (US-069)."""

    _name = "comic.release.notify.wizard"
    _description = "Prévenir les clients d'une mise en vente"

    edition_ids = fields.Many2many("comic.edition", string="Albums mis en vente")
    recipient_count = fields.Integer(string="Clients prévenus", compute="_compute_recipients")
    recipient_partner_ids = fields.Many2many("res.partner", string="Destinataires", compute="_compute_recipients")
    summary_html = fields.Html(string="Résumé", compute="_compute_recipients", sanitize=False)
    preview_subject = fields.Char(string="Objet", compute="_compute_preview")
    preview_body = fields.Html(string="Aperçu", compute="_compute_preview", sanitize=False)

    @api.depends("edition_ids")
    def _compute_recipients(self):
        for wizard in self:
            partners = self.env["res.partner"]
            counted = {}  # album -> clients déjà comptés (une fois par album)
            rows = []
            for edition in wizard.edition_ids:
                work = edition.work_id
                recipients = edition._get_release_recipients() - counted.get(work, partners)
                if not recipients:
                    continue
                counted[work] = counted.get(work, partners) | recipients
                partners |= recipients
                rows.append(
                    Markup("<tr><td>%s</td><td class='text-end'>%s</td></tr>") % (work.display_name, len(recipients))
                )
            wizard.recipient_partner_ids = partners
            wizard.recipient_count = len(partners)
            wizard.summary_html = (
                Markup(
                    "<table class='table table-sm mb-0'><thead><tr><th>%s</th>"
                    "<th class='text-end'>%s</th></tr></thead><tbody>%s</tbody></table>"
                )
                % (_("Album"), _("Clients"), Markup("").join(rows))
                if rows
                else escape(_("Aucun client à prévenir."))
            )

    @api.depends("edition_ids")
    def _compute_preview(self):
        template = self.env.ref("comic_shop.mail_template_comic_release_available")
        for wizard in self:
            edition = wizard.edition_ids.filtered(lambda e: e._get_release_recipients())[:1]
            if not edition:
                wizard.preview_subject = False
                wizard.preview_body = False
                continue
            wizard.preview_subject = template._render_field("subject", edition.ids)[edition.id]
            wizard.preview_body = template._render_field("body_html", edition.ids)[edition.id]

    def action_send(self):
        self.ensure_one()
        count = self.edition_ids._send_release_notification()
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "message": _("%(count)s client(s) prévenu(s) par email.", count=count),
                "type": "success",
                "sticky": False,
                "next": {"type": "ir.actions.act_window_close"},
            },
        }
