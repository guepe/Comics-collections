from . import models
from . import controllers
from . import wizards


def post_init_hook(env):
    """Réinstallation : recrée les liens produit ↔ édition coupés par uninstall_hook."""
    env["product.template"]._comic_relink_editions()


def uninstall_hook(env):
    """Nullify cross-module FK links so comics_collections data is preserved on uninstall."""
    env.cr.execute("UPDATE comic_edition SET product_tmpl_id = NULL WHERE product_tmpl_id IS NOT NULL")
    env.cr.execute("UPDATE product_template SET comic_edition_id = NULL WHERE comic_edition_id IS NOT NULL")
    # Menus « Ma collection » recopiés par Odoo sur chaque site (sans identifiant XML)
    env["website.menu"].search([("url", "in", ["/my/library", "/my/library/dashboard", "/my/library/add"])]).unlink()
