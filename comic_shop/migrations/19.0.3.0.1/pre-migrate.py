"""
Migration 19.0.3.0.0 → 19.0.3.0.1

Le menu du site « Ma collection » (menu_bd_catalogue) n'était plus rattaché à aucun site :
Odoo ne recopie un menu sur chaque site qu'à sa création. On supprime l'ancien menu
(et ses éventuelles copies / sous-menus) pour que le chargement des données le recrée,
recopié sur chaque site.

SQL brut justifié : suppression avant le chargement des données du module (le registre
n'est pas encore prêt), pour forcer la recréation de l'enregistrement.
"""

import logging

_logger = logging.getLogger(__name__)

LIBRARY_URLS = ("/my/library", "/my/library/dashboard", "/my/library/add")


def migrate(cr, version):
    if not version:
        return
    cr.execute(
        "SELECT res_id FROM ir_model_data WHERE module = 'comic_shop' AND name = 'menu_bd_catalogue'",
    )
    ids = [row[0] for row in cr.fetchall()]
    cr.execute("SELECT id FROM website_menu WHERE url IN %s", (LIBRARY_URLS,))
    ids += [row[0] for row in cr.fetchall()]
    if ids:
        # Les sous-menus suivent (parent_id ondelete cascade)
        cr.execute("DELETE FROM website_menu WHERE id IN %s", (tuple(set(ids)),))
    cr.execute(
        "DELETE FROM ir_model_data WHERE module = 'comic_shop' AND model = 'website.menu' AND name IN %s",
        (
            (
                "menu_bd_catalogue",
                "website_menu_ma_collection",
                "website_menu_ma_bibliotheque",
                "website_menu_tableau_de_bord",
                "website_menu_ajouter_bd",
            ),
        ),
    )
    _logger.info("Menu du site « Ma collection » : %s ancien(s) menu(s) supprimé(s), recréation", len(set(ids)))
