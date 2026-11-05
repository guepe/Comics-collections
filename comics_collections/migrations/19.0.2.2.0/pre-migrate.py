"""
Migration 19.0.2.1.0 → 19.0.2.2.0

Le suivi des séries devient propre à chaque utilisateur : le booléen stocké
comic.serie.a_suivre est remplacé par le Many2many suivi_user_ids, et
a_suivre devient un champ calculé non stocké.

SQL brut justifié : la colonne a_suivre doit être renommée avant le
chargement du registre, sinon ses valeurs seraient perdues (l'ORM ne la gère
plus). Le post-migrate reporte ensuite ces valeurs dans suivi_user_ids.
"""

import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    if not version:
        return
    cr.execute(
        """
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'comic_serie' AND column_name = 'a_suivre'
        """
    )
    if not cr.fetchone():
        return
    cr.execute(
        """
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'comic_serie' AND column_name = 'a_suivre_legacy'
        """
    )
    if cr.fetchone():
        cr.execute("ALTER TABLE comic_serie DROP COLUMN a_suivre")
        return
    cr.execute("ALTER TABLE comic_serie RENAME COLUMN a_suivre TO a_suivre_legacy")
    _logger.info("comic.serie : colonne a_suivre renommée en a_suivre_legacy")
