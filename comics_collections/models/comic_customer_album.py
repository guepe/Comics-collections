"""Bibliothèque personnelle : ce que chaque utilisateur possède, souhaite, lit et note.

Le catalogue (séries, albums, éditions) est partagé ; la possession est propre à chacun
(un enregistrement par couple partenaire / édition). Le module comic_shop étend ce modèle
avec les achats (commande, caisse) et l'expose aux clients sur le portail.
"""

import datetime
import logging
from collections import defaultdict

from psycopg2 import errors as pg_errors

from odoo import api, fields, models

_logger = logging.getLogger(__name__)

TOP_SERIES_LIMIT = 5
RECENT_LIMIT = 5


class ComicCustomerAlbum(models.Model):
    _name = "comic.customer.album"
    _description = "Bibliothèque personnelle — album"
    _order = "partner_id, edition_id"
    _rec_name = "edition_id"

    partner_id = fields.Many2one(
        "res.partner",
        string="Propriétaire",
        required=True,
        ondelete="cascade",
        index=True,
        default=lambda self: self.env.user.partner_id,
    )
    edition_id = fields.Many2one(
        "comic.edition",
        string="Album",
        required=True,
        ondelete="restrict",
        index=True,
    )
    source = fields.Selection(
        [
            ("achete_ailleurs", "Acheté ailleurs"),
            ("cadeau", "Cadeau"),
            ("inconnu", "Inconnu"),
        ],
        default="inconnu",
    )
    etat_lecture = fields.Selection(
        [
            ("non_lu", "Non lu"),
            ("en_cours", "En cours"),
            ("lu", "Lu"),
        ],
        string="État de lecture",
        default="non_lu",
    )
    dans_collection = fields.Boolean(string="Dans la collection", default=True)
    dans_wishlist = fields.Boolean(string="En wishlist", default=False)
    note = fields.Float(digits=(2, 1))
    commentaire = fields.Text()
    date_ajout = fields.Date(
        string="Date d'ajout",
        default=lambda self: datetime.date.today(),
    )
    work_id = fields.Many2one(
        "comic.work",
        string="Titre",
        compute="_compute_work_id",
        store=True,
        index=True,
    )

    _unique_partner_edition = models.Constraint(
        "UNIQUE(partner_id, edition_id)",
        "Cet album figure déjà dans cette bibliothèque.",
    )

    @api.depends("edition_id.work_id")
    def _compute_work_id(self):
        for rec in self:
            rec.work_id = rec.edition_id.work_id if rec.edition_id else False

    # ── Création / mise à jour idempotente ──────────────────────────────────

    @api.model
    def _upsert(self, partner, edition, vals):
        """Create or update the (partner, edition) entry. Returns (record, created).

        Protégé contre la violation de UNIQUE(partner_id, edition_id) si une autre
        transaction crée la même entrée en parallèle : on ne fait jamais échouer
        l'opération appelante (paiement caisse, confirmation de commande).
        """
        domain = [("partner_id", "=", partner.id), ("edition_id", "=", edition.id)]
        record = self.search(domain, limit=1)
        if record:
            record.write(vals)
            return record, False
        try:
            with self.env.cr.savepoint():
                record = self.create({**vals, "partner_id": partner.id, "edition_id": edition.id})
            return record, True
        except pg_errors.UniqueViolation:
            _logger.info("Bibliothèque : entrée %s/%s créée en parallèle", partner.id, edition.id)
            record = self.search(domain, limit=1)
            if record:
                record.write(vals)
            return record, False

    # ── Statistiques (tableau de bord back-office et portail) ───────────────

    @api.model
    def _get_collection_stats(self, partner, include_loans=False):
        """Return the collection statistics of ``partner`` as a plain dict.

        Seule source de vérité des tableaux de bord : le back-office (comics_collections)
        et le portail (comic_shop) ne font qu'afficher ce résultat.
        """
        entries = self.sudo().search([("partner_id", "=", partner.id)])
        owned = entries.filtered("dans_collection")

        # Séries : complètes = tous les tomes numérotés connus au catalogue sont possédés
        owned_by_serie = defaultdict(set)
        for entry in owned:
            work = entry.work_id
            if work.serie_id and work.tome > 0:
                owned_by_serie[work.serie_id].add(work.tome)
        series = owned.work_id.serie_id
        completes = 0
        for serie in series:
            known = set(serie.work_ids.filtered(lambda w: w.tome > 0).mapped("tome"))
            if known and known <= owned_by_serie.get(serie, set()):
                completes += 1

        # Répartition par genre (via la série)
        genre_counts = defaultdict(int)
        for entry in owned:
            genre = entry.work_id.serie_id.genre_id
            genre_counts[genre.name if genre else "Sans genre"] += 1
        by_genre = sorted(genre_counts.items(), key=lambda item: (-item[1], item[0]))

        # Répartition par état de lecture (dans l'ordre de la sélection)
        labels = dict(self._fields["etat_lecture"]._description_selection(self.env))
        by_reading = [(key, labels[key], len(owned.filtered(lambda e, k=key: e.etat_lecture == k))) for key in labels]

        # Top séries par note moyenne (albums notés uniquement)
        notes = defaultdict(list)
        for entry in entries.filtered(lambda e: e.note > 0 and e.work_id.serie_id):
            notes[entry.work_id.serie_id].append(entry.note)
        top_series = sorted(
            (
                {"id": serie.id, "name": serie.name, "note": round(sum(vals) / len(vals), 1), "count": len(vals)}
                for serie, vals in notes.items()
            ),
            key=lambda row: (-row["note"], -row["count"], row["name"]),
        )[:TOP_SERIES_LIMIT]

        recent = [
            {
                "id": entry.id,
                "work_id": entry.work_id.id,
                "name": entry.work_id.display_name or entry.edition_id.display_name,
                "date": entry.date_ajout,
            }
            for entry in owned.sorted(lambda e: (e.date_ajout or datetime.date.min, e.id), reverse=True)[:RECENT_LIMIT]
        ]

        stats = {
            "nb_albums": len(owned),
            "nb_wishlist": len(entries.filtered("dans_wishlist")),
            "nb_series": len(series),
            "series_completes": completes,
            "series_en_cours": len(series) - completes,
            "by_genre": by_genre,
            "by_reading": by_reading,
            "top_series": top_series,
            "recent": recent,
        }
        if include_loans:
            stats["loans_late"] = self.env["comic.pret"].search_count(
                [("create_uid", "=", self.env.uid), ("en_retard", "=", True)]
            )
        return stats
