"""Wishlist de l'utilisateur (US-089) : manques des séries suivies + souhaits manuels.

Modèle en lecture seule adossé à une vue SQL : une ligne par (utilisateur, album).

- « Manque » : tome numéroté (> 0), actif, d'une série suivie par l'utilisateur
  (``comic.serie.suivi_user_ids``) sans aucune entrée de sa bibliothèque sur une
  édition de cet album (ni possédé, ni souhaité, ni ignoré).
- « Souhait » : entrée de la bibliothèque en wishlist et hors collection.

Les actions de ligne agissent sur la bibliothèque (``comic.customer.album``) ou sur
le suivi de la série de l'utilisateur courant, jamais sur ceux d'un autre utilisateur.
"""

from odoo import fields, models, tools
from odoo.exceptions import AccessError

# Identifiant stable d'une ligne : user_id * ID_FACTOR + work_id (bigint). Il ne
# dépend que du couple (utilisateur, album), unique dans la vue (un album est soit
# un manque, soit un souhait), et reste donc identique d'un rechargement à l'autre.
ID_FACTOR = 10**9


class ComicWishlistItem(models.Model):
    _name = "comic.wishlist.item"
    _description = "Wishlist — manque ou souhait"
    _auto = False
    # Champs techniques (create/write uid/date) repris de l'album : le widget image du
    # client web lit write_date (clé de cache), absent par défaut d'une vue _auto=False.
    _log_access = True
    _order = "serie_id, tome, work_id"
    _rec_name = "work_id"

    # Tables lues par la vue : l'ORM vide ces changements en base avant toute
    # recherche ou lecture sur ce modèle.
    _depends = {
        "comic.customer.album": [
            "partner_id",
            "edition_id",
            "work_id",
            "dans_collection",
            "dans_wishlist",
            "ignore_wishlist",
        ],
        "comic.serie": ["suivi_user_ids"],
        "comic.work": ["serie_id", "tome", "active", "primary_edition_id"],
        "comic.edition": ["work_id", "date_parution"],
        "res.users": ["partner_id", "share", "active"],
    }

    user_id = fields.Many2one("res.users", string="Utilisateur", readonly=True)
    partner_id = fields.Many2one("res.partner", string="Partenaire", readonly=True)
    work_id = fields.Many2one("comic.work", string="Titre", readonly=True)
    serie_id = fields.Many2one("comic.serie", string="Série", readonly=True)
    tome = fields.Integer(string="T°", readonly=True, aggregator=False)
    edition_id = fields.Many2one("comic.edition", string="Édition", readonly=True)
    date_parution = fields.Date(string="Parution", readonly=True)
    type = fields.Selection([("manque", "Manque"), ("souhait", "Souhait")], readonly=True)
    # Affichage seul de la couverture de l'album.
    image_couverture = fields.Binary(related="work_id.image_couverture", string="Couverture")

    def init(self):
        # Vue de reporting : exception admise à la règle « ORM uniquement ». Calculer
        # les manques en Python imposerait de croiser à chaque affichage tous les tomes
        # des séries suivies avec la bibliothèque ; la vue permet la liste groupée,
        # les filtres, la recherche et les compteurs sans code dédié.
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute(
            f"""
            CREATE OR REPLACE VIEW {self._table} AS (
                SELECT DISTINCT ON (u.id, w.id)
                    u.id::bigint * {ID_FACTOR} + w.id AS id,
                    u.id AS user_id,
                    u.partner_id AS partner_id,
                    w.id AS work_id,
                    w.serie_id AS serie_id,
                    w.tome AS tome,
                    a.edition_id AS edition_id,
                    e.date_parution AS date_parution,
                    'souhait'::varchar AS type,
                    w.create_uid AS create_uid,
                    w.create_date AS create_date,
                    w.write_uid AS write_uid,
                    w.write_date AS write_date
                FROM comic_customer_album a
                JOIN res_users u ON u.partner_id = a.partner_id
                    AND u.active AND u.share IS NOT TRUE
                JOIN comic_work w ON w.id = a.work_id
                JOIN comic_edition e ON e.id = a.edition_id
                WHERE a.dans_wishlist AND a.dans_collection IS NOT TRUE
                ORDER BY u.id, w.id, a.edition_id
            )
            UNION ALL
            (
                SELECT
                    u.id::bigint * {ID_FACTOR} + w.id AS id,
                    u.id AS user_id,
                    u.partner_id AS partner_id,
                    w.id AS work_id,
                    w.serie_id AS serie_id,
                    w.tome AS tome,
                    w.primary_edition_id AS edition_id,
                    pe.date_parution AS date_parution,
                    'manque'::varchar AS type,
                    w.create_uid AS create_uid,
                    w.create_date AS create_date,
                    w.write_uid AS write_uid,
                    w.write_date AS write_date
                FROM comic_serie_suivi_user_rel rel
                JOIN res_users u ON u.id = rel.user_id
                    AND u.active AND u.share IS NOT TRUE
                JOIN comic_work w ON w.serie_id = rel.serie_id
                    AND w.active AND w.tome > 0
                LEFT JOIN comic_edition pe ON pe.id = w.primary_edition_id
                WHERE NOT EXISTS (
                    SELECT 1
                    FROM comic_customer_album a
                    JOIN comic_edition ae ON ae.id = a.edition_id
                    WHERE a.partner_id = u.partner_id
                      AND ae.work_id = w.id
                      AND (a.dans_collection OR a.dans_wishlist OR a.ignore_wishlist)
                )
            )
            """
        )

    # ── Actions de ligne ────────────────────────────────────────────────────

    def _own_lines(self):
        """Return ``self``, refusing any line that belongs to another user."""
        if any(line.user_id != self.env.user for line in self):
            raise AccessError(self.env._("Vous ne pouvez modifier que votre propre wishlist."))
        return self

    @staticmethod
    def _reload():
        return {"type": "ir.actions.client", "tag": "soft_reload"}

    def _line_edition(self):
        self.ensure_one()
        return self.edition_id or self.work_id.primary_edition_id

    def action_open_work(self):
        """Clic sur une ligne : fiche de l'album (la wishlist n'a pas de formulaire)."""
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "res_model": "comic.work",
            "res_id": self.work_id.id,
            "view_mode": "form",
            "views": [(False, "form")],
            "target": "current",
        }

    def action_mark_owned(self):
        """« Je l'ai » : l'album passe dans la collection et sort de la wishlist."""
        Album = self.env["comic.customer.album"]
        partner = self.env.user.partner_id
        for line in self._own_lines():
            edition = line._line_edition()
            if edition:
                Album._upsert(partner, edition, {"dans_collection": True, "dans_wishlist": False})
        return self._reload()

    def action_ignore(self):
        """« Ignorer ce tome » : le manque ne sera plus proposé (« ne pas acheter »)."""
        Album = self.env["comic.customer.album"]
        partner = self.env.user.partner_id
        for line in self._own_lines().filtered(lambda line: line.type == "manque"):
            edition = line._line_edition()
            if edition:
                Album._upsert(partner, edition, {"ignore_wishlist": True, "dans_collection": False})
        return self._reload()

    def action_remove(self):
        """Retirer : souhait → hors wishlist ; manque → ne plus suivre la série."""
        lines = self._own_lines()
        wishes = lines.filtered(lambda line: line.type == "souhait")
        if wishes:
            self.env["comic.customer.album"].search(
                [
                    ("partner_id", "=", self.env.user.partner_id.id),
                    ("work_id", "in", wishes.work_id.ids),
                    ("dans_wishlist", "=", True),
                    ("dans_collection", "=", False),
                ]
            ).write({"dans_wishlist": False})
        series = lines.filtered(lambda line: line.type == "manque").serie_id
        if series:
            # Passe par l'inverse de a_suivre : ne retire que l'utilisateur courant.
            series.a_suivre = False
        return self._reload()
