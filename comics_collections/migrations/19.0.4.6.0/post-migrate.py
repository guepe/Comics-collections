"""Statut de série « Inconnu » (19.0.4.6.0).

Jusqu'ici, toute série était créée « En cours » par défaut, sans que personne ne l'ait
vérifié : ni l'import ni les sources de données ne renseignent le statut. Les séries
« En cours » dont le statut n'a jamais été modifié (aucune trace de suivi) passent à
« Inconnu », pour que les filtres « En cours » / « Terminées » aient un sens et que
l'IA (comic_ai) puisse proposer le vrai statut.
"""

from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    if not version:
        return
    env = api.Environment(cr, SUPERUSER_ID, {})
    field = env["ir.model.fields"]._get("comic.serie", "statut")
    changed = env["mail.tracking.value"].search([("field_id", "=", field.id)]).mail_message_id
    touched = set(changed.filtered(lambda m: m.model == "comic.serie").mapped("res_id"))
    series = (
        env["comic.serie"]
        .with_context(active_test=False, tracking_disable=True)
        .search([("statut", "=", "en_cours"), ("id", "not in", list(touched))])
    )
    series.write({"statut": "inconnu"})
