from odoo import fields, models


class ComicEditeur(models.Model):
    _inherit = "comic.editeur"

    a_valider = fields.Boolean(
        string="À valider",
        default=False,
        index=True,
        copy=False,
        help="Éditeur proposé par un client depuis le portail, à contrôler.",
    )
    portal_partner_id = fields.Many2one(
        "res.partner",
        string="Proposé par",
        readonly=True,
        copy=False,
        ondelete="set null",
    )

    def action_valider_portail(self):
        """Validate publishers proposed from the portal."""
        self.write({"a_valider": False})
        return True
