import datetime
import logging

from psycopg2 import errors as pg_errors

from odoo import models, fields, api

_logger = logging.getLogger(__name__)


class ComicCustomerAlbum(models.Model):
    _name = "comic.customer.album"
    _description = "Bibliothèque client — édition"
    _order = "partner_id, edition_id"
    _rec_name = "edition_id"

    partner_id = fields.Many2one(
        "res.partner",
        string="Client",
        required=True,
        ondelete="cascade",
        index=True,
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
            ("achete_ici", "Acheté ici"),
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
    sale_order_line_id = fields.Many2one(
        "sale.order.line",
        string="Ligne de commande",
        ondelete="set null",
        copy=False,
        help="Ligne de commande à l'origine de l'ajout automatique.",
    )
    pos_order_line_id = fields.Many2one(
        "pos.order.line",
        string="Ligne de caisse",
        ondelete="set null",
        copy=False,
        help="Ligne de vente en caisse à l'origine de l'ajout automatique.",
    )
    auto_created = fields.Boolean(
        string="Créé par un achat",
        copy=False,
        help="Entrée créée automatiquement par une vente (shop ou caisse). "
        "Sert à la retirer proprement en cas d'annulation ou de remboursement.",
    )

    work_id = fields.Many2one(
        "comic.work",
        string="Titre",
        compute="_compute_work_id",
        store=True,
        index=True,
    )

    @api.depends("edition_id.work_id")
    def _compute_work_id(self):
        for rec in self:
            rec.work_id = rec.edition_id.work_id if rec.edition_id else False

    has_product = fields.Boolean(
        string="Produit disponible",
        compute="_compute_has_product",
        store=True,
        index=True,
        help="True si l'édition est liée à un produit vendable dans le shop.",
    )

    _unique_partner_edition = models.Constraint(
        "UNIQUE(partner_id, edition_id)",
        "Ce client possède déjà une entrée pour cette édition dans sa bibliothèque.",
    )

    @api.depends("edition_id.product_tmpl_id")
    def _compute_has_product(self):
        for rec in self:
            rec.has_product = bool(rec.edition_id.product_tmpl_id)

    # ── Enregistrement / annulation d'achats ────────────────────────────────

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

    @api.model
    def _register_purchase(self, partner, edition, sale_line=None, pos_line=None):
        vals = {
            "source": "achete_ici",
            "dans_collection": True,
            "dans_wishlist": False,  # acheté → sort de la wishlist
        }
        if sale_line:
            vals["sale_order_line_id"] = sale_line.id
        if pos_line:
            vals["pos_order_line_id"] = pos_line.id
        record, created = self._upsert(partner, edition, vals)
        if created:
            record.auto_created = True
        return record, created

    def _revert_purchase(self):
        """Undo an automatic purchase registration (cancelled order / refund).

        Entrée créée par l'achat et jamais touchée par le client → supprimée.
        Sinon (le client l'a lue, notée, commentée, ou elle existait avant) → conservée,
        mais la source « acheté ici » n'est plus vraie : elle repasse à « inconnu ».
        """
        for rec in self:
            untouched = rec.etat_lecture == "non_lu" and not rec.note and not rec.commentaire
            if rec.auto_created and untouched:
                rec.unlink()
            else:
                rec.write(
                    {
                        "source": "inconnu" if rec.source == "achete_ici" else rec.source,
                        "sale_order_line_id": False,
                        "pos_order_line_id": False,
                        "auto_created": False,
                    }
                )
