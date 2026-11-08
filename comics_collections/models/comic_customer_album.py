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
from odoo.exceptions import UserError
from odoo.tools import format_amount

_logger = logging.getLogger(__name__)

TOP_SERIES_LIMIT = 5
RECENT_LIMIT = 5
NOTE_ETOILES = [
    ("0", "Pas de note"),
    ("1", "1 étoile"),
    ("2", "2 étoiles"),
    ("3", "3 étoiles"),
    ("4", "4 étoiles"),
    ("5", "5 étoiles"),
]


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
    ignore_wishlist = fields.Boolean(
        string="Ignoré dans la wishlist",
        default=False,
        help="Tome manquant d'une série suivie que l'utilisateur ne veut pas (« ne pas acheter ») : "
        "il n'apparaît plus dans les manques de sa wishlist.",
    )
    note = fields.Float(digits=(2, 1))
    note_etoiles = fields.Selection(
        NOTE_ETOILES,
        string="Note (étoiles)",
        compute="_compute_note_etoiles",
        inverse="_inverse_note_etoiles",
        readonly=False,
        help="Saisie en étoiles de la note ; la note décimale reste la seule valeur enregistrée.",
    )
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
    genre_id = fields.Many2one(related="work_id.genre_id", store=True, string="Genre")
    currency_id = fields.Many2one(
        "res.currency",
        string="Devise",
        compute="_compute_currency_id",
        help="Devise de la société courante, utilisée pour le prix d'achat et la valeur estimée.",
    )
    prix_achat = fields.Monetary(string="Prix d'achat", currency_field="currency_id")
    valeur_estimee = fields.Monetary(string="Valeur estimée", currency_field="currency_id")

    _unique_partner_edition = models.Constraint(
        "UNIQUE(partner_id, edition_id)",
        "Cet album figure déjà dans cette bibliothèque.",
    )

    @api.depends("edition_id.work_id")
    def _compute_work_id(self):
        for rec in self:
            rec.work_id = rec.edition_id.work_id if rec.edition_id else False

    @api.depends_context("company")
    def _compute_currency_id(self):
        self.currency_id = self.env.company.currency_id

    @api.depends("note")
    def _compute_note_etoiles(self):
        for rec in self:
            rec.note_etoiles = str(min(5, max(0, round(rec.note or 0.0))))

    def _inverse_note_etoiles(self):
        for rec in self:
            rec.note = float(rec.note_etoiles or 0)

    # ── Suivi automatique des séries commencées (US-088) ────────────────────

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        records.filtered("dans_collection")._auto_follow_series()
        return records

    def write(self, vals):
        res = super().write(vals)
        if vals.get("dans_collection"):
            self._auto_follow_series()
        return res

    def _auto_follow_series(self):
        """Internal users of the owner follow the series of the owned albums.

        Les clients portail ne sont pas concernés (suivi_user_ids = utilisateurs BD
        internes) ; _auto_follow écarte aussi inactifs et désabonnés.
        """
        users_by_serie = defaultdict(lambda: self.env["res.users"])
        for rec in self.sudo():
            serie = rec.work_id.serie_id
            users = rec.partner_id.user_ids.filtered(lambda u: not u.share)
            if serie and users:
                users_by_serie[serie] |= users
        for serie, users in users_by_serie.items():
            serie._auto_follow(users)

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

        # Wishlist (US-089) : souhaits manuels + manques des séries suivies. Les manques
        # n'existent que pour les utilisateurs internes (le suivi porte sur res.users) :
        # un partenaire portail sans utilisateur interne ne compte que ses souhaits.
        # Même règle que la vue comic.wishlist.item : en wishlist ET hors collection
        nb_souhaits = len(entries.filtered(lambda e: e.dans_wishlist and not e.dans_collection))
        internal_users = partner.sudo().user_ids.filtered(lambda u: not u.share)
        nb_manques = (
            self.env["comic.wishlist.item"]
            .sudo()
            .search_count([("type", "=", "manque"), ("user_id", "in", internal_users.ids)])
            if internal_users
            else 0
        )

        stats = {
            "nb_albums": len(owned),
            "nb_souhaits": nb_souhaits,
            "nb_manques": nb_manques,
            "nb_wishlist": nb_souhaits + nb_manques,
            "nb_series": len(series),
            "series_completes": completes,
            "series_en_cours": len(series) - completes,
            "by_genre": by_genre,
            "by_reading": by_reading,
            "top_series": top_series,
            "recent": recent,
            # Valeur de la collection (US-071) : montants facultatifs, 0 = non renseigné
            "total_prix_achat": sum(owned.mapped("prix_achat")),
            "total_valeur": sum(owned.mapped("valeur_estimee")),
            "nb_values": len(owned.filtered(lambda e: e.prix_achat or e.valeur_estimee)),
        }
        if include_loans:
            stats["loans_late"] = self.env["comic.pret"].search_count(
                [("create_uid", "=", self.env.uid), ("en_retard", "=", True)]
            )
        return stats

    @api.model
    def get_dashboard_data(self):
        """Return the current user's statistics, JSON-serializable, for the OWL dashboard.

        Simple mise en forme de ``_get_collection_stats`` : dates ISO, répartitions en
        dicts avec un pourcentage déjà calculé (le JS ne fait qu'afficher).
        """
        stats = self._get_collection_stats(self.env.user.partner_id, include_loans=True)
        total = stats["nb_albums"]

        def percent(count):
            return round(100.0 * count / total, 1) if total else 0.0

        currency = self.env.company.currency_id
        return {
            **stats,
            "has_values": bool(stats["nb_values"]),
            "total_prix_achat_display": format_amount(self.env, stats["total_prix_achat"], currency),
            "total_valeur_display": format_amount(self.env, stats["total_valeur"], currency),
            "by_genre": [
                {"label": label, "count": count, "percent": percent(count)} for label, count in stats["by_genre"]
            ],
            "by_reading": [
                {"key": key, "label": label, "count": count, "percent": percent(count)}
                for key, label, count in stats["by_reading"]
            ],
            "recent": [
                {**row, "date": fields.Date.to_string(row["date"]) if row["date"] else False} for row in stats["recent"]
            ],
        }

    # ── Inventaire PDF (US-071) ─────────────────────────────────────────────

    @api.model
    def action_print_my_inventory(self):
        """Return the inventory report action on the current user's collection."""
        entries = self.search([("partner_id", "=", self.env.user.partner_id.id), ("dans_collection", "=", True)])
        if not entries:
            raise UserError(self.env._("Votre collection est vide : aucun album à inventorier."))
        return self.env.ref("comics_collections.action_report_comic_collection_inventory").report_action(entries)

    def _get_inventory_data(self):
        """Group ``self`` by series for the inventory report, with subtotals and totals."""
        groups = defaultdict(self.browse)
        for entry in self:
            groups[entry.work_id.serie_id] |= entry

        def tome_key(entry):
            return (entry.work_id.tome or 0, entry.work_id.titre_canonique or "", entry.id)

        series = []
        for serie, entries in sorted(groups.items(), key=lambda item: (not item[0], item[0].name or "")):
            lines = [
                {
                    "tome": entry.work_id.tome or "",
                    "titre": entry.work_id.titre_canonique or entry.edition_id.display_name,
                    "isbn": entry.edition_id.isbn_ids.filtered("isbn_13")[:1].isbn_13 or "",
                    "etat_lecture": dict(self._fields["etat_lecture"]._description_selection(self.env)).get(
                        entry.etat_lecture, ""
                    ),
                    "note": entry.note,
                    "prix_achat": entry.prix_achat,
                    "valeur_estimee": entry.valeur_estimee,
                }
                for entry in entries.sorted(tome_key)
            ]
            series.append(
                {
                    "name": serie.name or self.env._("Sans série"),
                    "lines": lines,
                    "count": len(lines),
                    "prix_achat": sum(entries.mapped("prix_achat")),
                    "valeur_estimee": sum(entries.mapped("valeur_estimee")),
                }
            )
        return {
            "series": series,
            "owners": ", ".join(self.partner_id.mapped("name")),
            "count": len(self),
            "prix_achat": sum(self.mapped("prix_achat")),
            "valeur_estimee": sum(self.mapped("valeur_estimee")),
            "currency": self.env.company.currency_id,
        }
