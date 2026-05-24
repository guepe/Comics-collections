"""
Migration 19.0.1.0.0 → 19.0.2.0.0
comic.customer.album : album_id (→ comic.album) → edition_id (→ comic.edition)

Prérequis : la migration comics_collections 19.0.2.0.0 a déjà créé
les enregistrements comic.work et comic.edition depuis comic_album.
"""
import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    if not version:
        return

    # Vérifier que la colonne album_id existe encore (sinon déjà migré)
    cr.execute("""
        SELECT COUNT(*) FROM information_schema.columns
        WHERE table_name = 'comic_customer_album'
          AND column_name = 'album_id'
    """)
    if not cr.fetchone()[0]:
        _logger.info("Migration customer.album : colonne album_id absente, rien à faire.")
        return

    # Vérifier que comic_album existe (source)
    cr.execute("""
        SELECT COUNT(*) FROM information_schema.tables
        WHERE table_name = 'comic_album'
    """)
    if not cr.fetchone()[0]:
        _logger.warning("Migration customer.album : table comic_album absente, impossible de migrer.")
        return

    cr.execute("""
        UPDATE comic_customer_album ca
        SET edition_id = e.id
        FROM comic_album a
        JOIN comic_work w
            ON w.serie_id = a.serie_id
           AND w.tome = COALESCE(a.tome, 0)
        JOIN comic_edition e
            ON e.work_id = w.id
        WHERE ca.album_id = a.id
          AND (ca.edition_id IS NULL OR ca.edition_id = 0)
    """)
    updated = cr.rowcount
    _logger.info("Migration customer.album : %d enregistrement(s) mis à jour.", updated)

    # Supprimer les orphelins sans correspondance (album supprimé entre-temps)
    cr.execute("""
        DELETE FROM comic_customer_album
        WHERE (edition_id IS NULL OR edition_id = 0)
          AND album_id IS NOT NULL
    """)
    deleted = cr.rowcount
    if deleted:
        _logger.warning(
            "Migration customer.album : %d enregistrement(s) orphelin(s) supprimé(s) "
            "(album source introuvable dans comic_work/edition).",
            deleted,
        )
