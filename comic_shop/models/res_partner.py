import secrets

from odoo import models, fields


class ResPartner(models.Model):
    _inherit = "res.partner"

    comic_auto_library = fields.Boolean(
        string="Ajout automatique à la bibliothèque",
        default=True,
        help="Si activé, les BD achetées dans le shop sont automatiquement ajoutées à la bibliothèque.",
    )
    # Wishlist partageable (US-073) : lus et écrits en sudo depuis le portail,
    # uniquement sur le partenaire de l'utilisateur connecté.
    comic_wishlist_shared = fields.Boolean(
        string="Wishlist BD partagée",
        help="Si activé, la wishlist BD est consultable publiquement via un lien secret.",
    )
    comic_wishlist_token = fields.Char(
        string="Jeton de partage de la wishlist",
        copy=False,
        groups="base.group_system",
    )

    def _comic_wishlist_enable(self):
        """Share the wishlist; create a token if none exists (the link is kept while shared)."""
        for partner in self.sudo():
            vals = {"comic_wishlist_shared": True}
            if not partner.comic_wishlist_token:
                vals["comic_wishlist_token"] = secrets.token_urlsafe(16)
            partner.write(vals)
        return True

    def _comic_wishlist_revoke(self):
        """Stop sharing and drop the token: a later re-share yields a new link."""
        self.sudo().write({"comic_wishlist_shared": False, "comic_wishlist_token": False})
        return True
