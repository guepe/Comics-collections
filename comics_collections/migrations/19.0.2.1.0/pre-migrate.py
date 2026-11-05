"""
Migration 19.0.2.0.0 → 19.0.2.1.0

La contrainte UNIQUE(serie_id, tome) est remplacée par un index unique
partiel (serie_id, tome) WHERE tome > 0, pour autoriser plusieurs albums
sans numéro (hors-série) dans une même série.

SQL brut justifié : suppression d'une contrainte DB obsolète avant que
l'ORM ne crée le nouvel index.
"""

import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    if not version:
        return
    cr.execute("ALTER TABLE comic_work DROP CONSTRAINT IF EXISTS comic_work_unique_serie_tome")
    cr.execute("DELETE FROM ir_model_constraint WHERE name = 'comic_work_unique_serie_tome'")
    _logger.info("comic.work : contrainte UNIQUE(serie_id, tome) remplacée par un index partiel (tome > 0)")
