"""
Migration → 19.0.4.0.0 (US-088 : suivi automatique des séries commencées)

Chaque utilisateur interne actif suit désormais les séries dont il possède au moins un
album. On rattrape l'existant : pour chaque utilisateur qui possède des albums
(dans_collection), il suit les séries de ces albums, sauf s'il s'en est exclu.
Idempotent : un utilisateur qui suit déjà une série n'est pas compté.
"""

import logging

from odoo import SUPERUSER_ID, api

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    entries = env["comic.customer.album"].search([("dans_collection", "=", True)])
    added = 0
    for user in entries.partner_id.user_ids.filtered(lambda u: u.active and not u.share):
        series = entries.filtered(lambda e, u=user: e.partner_id == u.partner_id).work_id.serie_id
        to_follow = series.filtered(lambda s, u=user: u not in s.suivi_user_ids and u not in s.suivi_exclu_user_ids)
        if to_follow:
            to_follow._auto_follow(user)
            added += len(to_follow)
    _logger.info("comic.serie : %d suivi(s) de série ajouté(s) pour les propriétaires d'albums", added)
