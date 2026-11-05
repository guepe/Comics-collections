"""
Migration 19.0.2.1.0 → 19.0.2.2.0

Reporte l'ancien suivi global (colonne a_suivre_legacy) dans le Many2many
suivi_user_ids : chaque série suivie est rattachée à son créateur
(create_uid), à défaut à l'administrateur.

SQL brut justifié : lecture puis suppression de la colonne héritée, que
l'ORM ne connaît plus. L'écriture du suivi passe par l'ORM.
"""

import logging

from odoo import SUPERUSER_ID, Command, api

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    if not version:
        return
    cr.execute(
        """
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'comic_serie' AND column_name = 'a_suivre_legacy'
        """
    )
    if not cr.fetchone():
        return

    env = api.Environment(cr, SUPERUSER_ID, {})
    admin = env.ref("base.user_admin", raise_if_not_found=False)
    fallback_uid = admin.id if admin else SUPERUSER_ID

    cr.execute("SELECT id, create_uid FROM comic_serie WHERE a_suivre_legacy IS TRUE")
    rows = cr.fetchall()
    Serie = env["comic.serie"].with_context(active_test=False)
    for serie_id, create_uid in rows:
        user_id = create_uid or fallback_uid
        Serie.browse(serie_id).write({"suivi_user_ids": [Command.link(user_id)]})

    cr.execute("ALTER TABLE comic_serie DROP COLUMN a_suivre_legacy")
    _logger.info("comic.serie : %d série(s) suivie(s) migrée(s) vers suivi_user_ids", len(rows))
