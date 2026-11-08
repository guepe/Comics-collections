"""Export CSV de la bibliothèque personnelle (US-071)."""

import csv
import io

from odoo import fields, http
from odoo.http import request

CSV_HEADER = [
    "Série",
    "Tome",
    "Titre",
    "ISBN",
    "Éditeur",
    "État de lecture",
    "Collection",
    "Wishlist",
    "Note",
    "Prix d'achat",
    "Valeur estimée",
    "Date d'ajout",
]


def _amount(value, digits=2):
    """Decimal with a dot separator, empty when not filled in (0)."""
    return f"{value:.{digits}f}" if value else ""


class ComicCollectionExport(http.Controller):
    @http.route("/comics/collection/export.csv", type="http", auth="user", methods=["GET"])
    def export_collection_csv(self, **kwargs):
        Album = request.env["comic.customer.album"]
        entries = Album.search(
            [
                ("partner_id", "=", request.env.user.partner_id.id),
                "|",
                ("dans_collection", "=", True),
                ("dans_wishlist", "=", True),
            ]
        ).sorted(lambda e: (e.work_id.serie_id.name or "", e.work_id.tome or 0, e.work_id.titre_canonique or ""))
        reading_labels = dict(Album._fields["etat_lecture"]._description_selection(request.env))

        buffer = io.StringIO()
        writer = csv.writer(buffer, delimiter=";", lineterminator="\r\n")
        writer.writerow(CSV_HEADER)
        for entry in entries:
            work = entry.work_id
            edition = entry.edition_id
            writer.writerow(
                [
                    work.serie_id.name or "",
                    work.tome or "",
                    work.titre_canonique or edition.display_name,
                    edition.isbn_ids.filtered("isbn_13")[:1].isbn_13 or "",
                    edition.editeur_id.name or "",
                    reading_labels.get(entry.etat_lecture, ""),
                    "Oui" if entry.dans_collection else "Non",
                    "Oui" if entry.dans_wishlist else "Non",
                    _amount(entry.note, 1),
                    _amount(entry.prix_achat),
                    _amount(entry.valeur_estimee),
                    fields.Date.to_string(entry.date_ajout) if entry.date_ajout else "",
                ]
            )

        content = buffer.getvalue().encode("utf-8-sig")
        filename = f"ma_collection_{fields.Date.context_today(Album)}.csv"
        return request.make_response(
            content,
            headers=[
                ("Content-Type", "text/csv; charset=utf-8"),
                ("Content-Disposition", f'attachment; filename="{filename}"'),
                ("Content-Length", str(len(content))),
            ],
        )
