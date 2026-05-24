from . import models
from . import controllers


def uninstall_hook(env):
    """Nullify cross-module FK links so comics_collections data is preserved on uninstall."""
    env.cr.execute(
        "UPDATE comic_edition SET product_tmpl_id = NULL WHERE product_tmpl_id IS NOT NULL"
    )
    env.cr.execute(
        "UPDATE product_template SET comic_edition_id = NULL WHERE comic_edition_id IS NOT NULL"
    )
