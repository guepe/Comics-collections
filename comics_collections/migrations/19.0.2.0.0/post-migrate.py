"""
Migration 19.0.1.0.0 → 19.0.2.0.0
Transfère comic.album → comic.work + comic.edition + comic.isbn
et comic.album.auteur.line → comic.work.auteur.line
"""
import logging

from odoo import SUPERUSER_ID, api

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    if not version:
        return

    cr.execute("""
        SELECT COUNT(*) FROM information_schema.tables
        WHERE table_name = 'comic_album'
    """)
    if not cr.fetchone()[0]:
        _logger.info("Migration: table comic_album absente, rien à faire.")
        return

    cr.execute("SELECT COUNT(*) FROM comic_album")
    if not cr.fetchone()[0]:
        _logger.info("Migration: table comic_album vide, rien à migrer.")
        return

    env = api.Environment(cr, SUPERUSER_ID, {})
    album_to_edition = _migrate_albums(cr, env)
    _migrate_prets(cr, album_to_edition)


def _get_existing_columns(cr, table):
    cr.execute("""
        SELECT column_name FROM information_schema.columns
        WHERE table_name = %s
    """, (table,))
    return {row[0] for row in cr.fetchall()}


def _migrate_albums(cr, env):
    """Retourne un dict {album_id: edition_id} pour la migration des prêts."""
    existing = _get_existing_columns(cr, 'comic_album')
    _logger.info("Colonnes disponibles dans comic_album : %s", sorted(existing))

    # Colonnes obligatoires + colonnes optionnelles selon le schéma réel
    required_cols = ['id', 'name', 'serie_id', 'tome', 'active']
    optional_cols = [
        'isbn', 'date_parution', 'date_depot_legal', 'nb_pages',
        'image_couverture', 'synopsis',
        'url_club_be', 'url_amazon_be', 'url_fnac_be', 'bdgest_album_id',
        'product_tmpl_id',
    ]
    select_cols = required_cols + [c for c in optional_cols if c in existing]

    cr.execute(
        f"SELECT {', '.join(select_cols)} FROM comic_album ORDER BY id"  # noqa: S608
    )
    albums = cr.dictfetchall()

    auteurs_by_album = {}
    cr.execute("""
        SELECT COUNT(*) FROM information_schema.tables
        WHERE table_name = 'comic_album_auteur_line'
    """)
    if cr.fetchone()[0]:
        cr.execute("""
            SELECT album_id, partner_id, role
            FROM comic_album_auteur_line
            ORDER BY album_id, id
        """)
        for row in cr.dictfetchall():
            auteurs_by_album.setdefault(row['album_id'], []).append(row)

    Work = env['comic.work']
    Edition = env['comic.edition']
    Isbn = env['comic.isbn']
    AuteurLine = env['comic.work.auteur.line']

    album_to_edition = {}
    migrated = skipped = 0
    total = len(albums)

    for album in albums:
        album_id = album['id']

        # Idempotence : chercher par (serie_id, tome) — la vraie contrainte UNIQUE
        domain = [('tome', '=', album['tome'] or 0)]
        if album['serie_id']:
            domain.append(('serie_id', '=', album['serie_id']))
        else:
            domain.append(('serie_id', '=', False))
        existing = Work.search(domain, limit=1)

        if existing:
            # Work déjà présent : relier le produit si manquant
            work = existing
            if album.get('product_tmpl_id') and existing.primary_edition_id:
                ed = existing.primary_edition_id
                if not ed.product_tmpl_id:
                    ed.product_tmpl_id = album['product_tmpl_id']
                album_to_edition[album_id] = ed.id
            elif existing.primary_edition_id:
                album_to_edition[album_id] = existing.primary_edition_id.id
            skipped += 1
        else:
            # comic.work — nouveau
            work_vals = {
                'titre_canonique': album['name'],
                'serie_id': album['serie_id'],
                'tome': album['tome'] or 0,
                'active': album['active'],
            }
            if album.get('bdgest_album_id'):
                work_vals['bedetheque_id'] = str(album['bdgest_album_id'])
            work = Work.create(work_vals)

        # comic.work.auteur.line — seulement si work nouvellement créé
        if not existing:
            for auteur in auteurs_by_album.get(album_id, []):
                AuteurLine.create({
                    'work_id': work.id,
                    'partner_id': auteur['partner_id'],
                    'role': auteur['role'],
                })

        # comic.edition
        edition_vals = {'work_id': work.id, 'active': album['active']}
        for fld in ('date_parution', 'date_depot_legal', 'nb_pages', 'synopsis',
                    'url_club_be', 'url_amazon_be', 'url_fnac_be'):
            if album.get(fld):
                edition_vals[fld] = album[fld]
        if album.get('image_couverture'):
            edition_vals['image_couverture'] = album['image_couverture']
        if album.get('product_tmpl_id'):
            edition_vals['product_tmpl_id'] = album['product_tmpl_id']
        edition = Edition.create(edition_vals)

        # comic.isbn
        if album.get('isbn'):
            isbn_clean = album['isbn'].replace('-', '').replace(' ', '')
            if len(isbn_clean) == 13 and isbn_clean.isdigit():
                try:
                    Isbn.create({'edition_id': edition.id, 'isbn_13': isbn_clean})
                except Exception as exc:
                    _logger.warning("Album %d — ISBN '%s' ignoré : %s", album_id, isbn_clean, exc)
            else:
                _logger.warning("Album %d — ISBN '%s' invalide, ignoré.", album_id, album['isbn'])

        album_to_edition[album_id] = edition.id
        migrated += 1

        if migrated % 100 == 0:
            _logger.info("Migration albums : %d/%d traités…", migrated, total)

    _logger.info(
        "Migration albums terminée : %d migrés, %d déjà présents.",
        migrated, skipped,
    )
    return album_to_edition


def _migrate_prets(cr, album_to_edition):
    """Relie comic.pret.edition_id depuis l'ancien album_id si la colonne existe encore."""
    cr.execute("""
        SELECT COUNT(*) FROM information_schema.columns
        WHERE table_name = 'comic_pret' AND column_name = 'album_id'
    """)
    if not cr.fetchone()[0]:
        _logger.info("Migration prêts : colonne album_id absente, rien à faire.")
        return

    updated = 0
    for album_id, edition_id in album_to_edition.items():
        cr.execute("""
            UPDATE comic_pret
            SET edition_id = %s
            WHERE album_id = %s
              AND (edition_id IS NULL OR edition_id = 0)
        """, (edition_id, album_id))
        updated += cr.rowcount

    _logger.info("Migration prêts : %d prêt(s) mis à jour.", updated)
