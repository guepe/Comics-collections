"""Tableaux HTML d'auteurs partagés par les fiches auteur et éditeur (US-091)."""

from markupsafe import Markup, escape

MAX_ROWS = 15


def authors_table(env, counts, works_by_partner, empty_message, count_label):
    """Tableau « auteur | nb albums | séries » trié par nombre d'albums décroissant.

    :param counts: {res.partner: nombre d'albums}
    :param works_by_partner: {res.partner: comic.work recordset} (séries affichées)
    """
    if not counts:
        return Markup('<p class="text-muted">%s</p>') % empty_message
    rows = []
    ordered = sorted(counts.items(), key=lambda item: (-item[1], (item[0].name or "").lower()))
    for partner, count in ordered[:MAX_ROWS]:
        series = works_by_partner[partner].serie_id.sorted("name")
        # Séries cliquables (fiche série) ; au-delà de 3, « … »
        links = Markup(", ").join(
            Markup('<a href="/odoo/comic.serie/%s">%s</a>') % (serie.id, serie.name) for serie in series[:3]
        )
        if len(series) > 3:
            links += Markup(" …")
        rows.append(
            Markup('<tr><td><a href="/odoo/res.partner/%s">%s</a></td><td class="text-end">%s</td><td>%s</td></tr>')
            % (partner.id, partner.name, count, links)
        )
    head = Markup(
        '<table class="table table-sm o_comic_authors_table"><thead><tr><th>%s</th>'
        '<th class="text-end">%s</th><th>%s</th></tr></thead><tbody>'
    ) % (escape(env._("Author")), escape(count_label), escape(env._("Series")))
    return head + Markup("").join(rows) + Markup("</tbody></table>")
