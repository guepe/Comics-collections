"""
Migration 19.0.2.x → 19.0.3.0.0

Le modèle comic.customer.album (bibliothèque personnelle) passe de comic_shop dans
comics_collections. Même modèle, même table : seuls les identifiants XML changent de
module. Sans cette réattribution, la mise à jour de comic_shop supprimerait ses
identifiants devenus « orphelins » (modèle, champs, contrainte), donc les colonnes
voire la table.

SQL brut justifié : ir_model_data doit être réattribué avant le chargement du
registre ; l'ORM n'offre pas d'API pour déplacer un identifiant XML entre modules.
Idempotent : un identifiant déjà présent côté comics_collections n'est pas touché.
"""

import logging

_logger = logging.getLogger(__name__)

# Champs qui descendent dans comics_collections (les autres restent dans comic_shop :
# sale_order_line_id, pos_order_line_id, auto_created, has_product).
CORE_FIELDS = (
    "id",
    "display_name",
    "create_uid",
    "create_date",
    "write_uid",
    "write_date",
    "partner_id",
    "edition_id",
    "source",
    "etat_lecture",
    "dans_collection",
    "dans_wishlist",
    "note",
    "commentaire",
    "date_ajout",
    "work_id",
)

CORE_SELECTIONS = (
    "source__achete_ailleurs",
    "source__cadeau",
    "source__inconnu",
    "etat_lecture__non_lu",
    "etat_lecture__en_cours",
    "etat_lecture__lu",
)

OTHER_XMLIDS = (
    "model_comic_customer_album",
    "constraint_comic_customer_album_unique_partner_edition",
    "field_comic_edition__customer_album_ids",
    "access_comic_customer_album_user",
    "rule_customer_album_user",
    "view_comic_customer_album_list",
    "view_comic_customer_album_form",
    "view_comic_customer_album_search",
    "action_work_mark_lu",
    "action_work_mark_en_cours",
    "action_work_mark_non_lu",
)


def _xmlids_to_move():
    names = list(OTHER_XMLIDS)
    names += [f"field_comic_customer_album__{name}" for name in CORE_FIELDS]
    names += [f"selection__comic_customer_album__{name}" for name in CORE_SELECTIONS]
    return names


def migrate(cr, version):
    if not version:
        return
    names = _xmlids_to_move()
    cr.execute(
        """
        UPDATE ir_model_data imd
           SET module = 'comics_collections'
         WHERE imd.module = 'comic_shop'
           AND imd.name = ANY(%s)
           AND NOT EXISTS (
                SELECT 1 FROM ir_model_data core
                 WHERE core.module = 'comics_collections' AND core.name = imd.name
           )
        """,
        (names,),
    )
    _logger.info("comic.customer.album : %s identifiant(s) XML réattribué(s) à comics_collections", cr.rowcount)
