import operator as py_operator
import string
from collections import defaultdict

from odoo import SUPERUSER_ID, Command, api, fields, models

from ..utils.normalize import normalize_title

# Barre alphabétique de « Mes séries » : « # » regroupe chiffres et symboles.
NAME_INITIALS = [("#", "#")] + [(letter, letter) for letter in string.ascii_uppercase]

# Opérateurs acceptés par les recherches sur les compteurs « mes … ».
COUNT_OPERATORS = {
    "=": py_operator.eq,
    "!=": py_operator.ne,
    ">": py_operator.gt,
    ">=": py_operator.ge,
    "<": py_operator.lt,
    "<=": py_operator.le,
}


class ComicSerie(models.Model):
    _name = "comic.serie"
    _description = "Comic series"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "name"

    name = fields.Char(string="Title", required=True, tracking=True)
    name_normalise = fields.Char(
        string="Normalized title",
        compute="_compute_name_normalise",
        store=True,
        index=True,
    )
    type = fields.Selection(
        [
            ("bd", "Comic book"),
            ("manga", "Manga"),
            ("comics", "Comics"),
            ("one_shot", "One-shot"),
        ],
        default="bd",
        tracking=True,
    )
    statut = fields.Selection(
        [
            ("en_cours", "Ongoing"),
            ("terminee", "Completed"),
            ("abandonnee", "Discontinued"),
        ],
        string="Status",
        default="en_cours",
        tracking=True,
    )
    genre_id = fields.Many2one("comic.genre", string="Genre")
    editeur_id = fields.Many2one("comic.editeur", string="Publisher")
    image_couverture = fields.Image(string="Cover")
    synopsis = fields.Html()
    bdgest_id = fields.Integer(string="BDGest ID", aggregator=False)
    bedetheque_url = fields.Char(string="Bedetheque URL")
    work_ids = fields.One2many("comic.work", "serie_id", string="Albums")
    # Auteurs de tous les albums de la série (sans doublon), avec leurs rôles
    auteur_ids = fields.Many2many("res.partner", string="Authors", compute="_compute_auteurs")
    auteur_names = fields.Char(string="Authors (roles)", compute="_compute_auteurs")
    nb_works_total = fields.Integer(string="Total volumes", compute="_compute_works", store=True)
    suivi_user_ids = fields.Many2many(
        "res.users",
        "comic_serie_suivi_user_rel",
        "serie_id",
        "user_id",
        string="Followed by",
    )
    # Utilisateurs qui se sont désabonnés explicitement : le suivi automatique
    # (création de la série, album possédé) ne les réabonne plus (US-088).
    suivi_exclu_user_ids = fields.Many2many(
        "res.users",
        "comic_serie_suivi_exclu_user_rel",
        "serie_id",
        "user_id",
        string="No longer following",
    )
    # Catalogue partagé : le suivi est propre à chaque utilisateur. Ce booléen
    # non stocké reflète l'utilisateur courant (présence dans suivi_user_ids).
    a_suivre = fields.Boolean(
        string="Followed",
        compute="_compute_a_suivre",
        inverse="_inverse_a_suivre",
        search="_search_a_suivre",
    )
    first_edition_cover_id = fields.Many2one(
        "comic.edition",
        compute="_compute_first_edition_cover",
        store=True,
    )
    active = fields.Boolean(default=True)
    has_cover = fields.Boolean(compute="_compute_has_cover", store=True)
    # Initiale du titre normalisé (articles ôtés) : barre alphabétique (searchpanel).
    name_initial = fields.Selection(
        NAME_INITIALS,
        string="Initial",
        compute="_compute_name_initial",
        store=True,
        index=True,
    )

    # ── Ma collection : compteurs de l'utilisateur connecté (non stockés) ────
    # Catalogue partagé, collection privée : chaque utilisateur voit ses propres chiffres.
    my_owned_count = fields.Integer(
        string="My albums",
        compute="_compute_my_counts",
        search="_search_my_owned_count",
        help="Albums of this series in my collection.",
    )
    my_read_count = fields.Integer(
        string="Read",
        compute="_compute_my_counts",
        search="_search_my_read_count",
        help="Albums of this series in my collection that I have read.",
    )
    my_unread_count = fields.Integer(
        string="Unread",
        compute="_compute_my_counts",
        search="_search_my_unread_count",
        help="Albums of this series in my collection that I have not read yet.",
    )
    my_lent_count = fields.Integer(
        string="Lent",
        compute="_compute_my_counts",
        search="_search_my_lent_count",
        help="My loans of albums of this series that have not been returned yet.",
    )
    my_missing_count = fields.Integer(
        string="Missing",
        compute="_compute_my_counts",
        search="_search_my_missing_count",
        help="Numbered volumes of this series that I do not own (volumes marked "
        '"ignore" in my wishlist are not counted).',
    )
    my_rating = fields.Float(
        string="My rating",
        digits=(2, 1),
        compute="_compute_my_counts",
        help="Average rating (0-5) of the albums of this series I have rated.",
    )

    @api.depends("name")
    def _compute_name_normalise(self):
        for rec in self:
            rec.name_normalise = normalize_title(rec.name)

    @api.depends("suivi_user_ids")
    @api.depends_context("uid")
    def _compute_a_suivre(self):
        user = self.env.user
        for rec in self:
            rec.a_suivre = user in rec.suivi_user_ids

    def _inverse_a_suivre(self):
        user = self.env.user
        # Réabonnement : on suit et on lève l'exclusion. Désabonnement : on ne suit plus
        # et on mémorise l'exclusion, pour que le suivi automatique ne réabonne pas.
        to_follow = self.filtered(
            lambda s: s.a_suivre and (user not in s.suivi_user_ids or user in s.suivi_exclu_user_ids)
        )
        # Seul un utilisateur qui suivait est exclu : un formulaire de création envoie
        # a_suivre=False sans que ce soit un désabonnement.
        to_unfollow = self.filtered(lambda s: not s.a_suivre and user in s.suivi_user_ids)
        if to_follow:
            to_follow.write(
                {"suivi_user_ids": [Command.link(user.id)], "suivi_exclu_user_ids": [Command.unlink(user.id)]}
            )
        if to_unfollow:
            to_unfollow.write(
                {"suivi_user_ids": [Command.unlink(user.id)], "suivi_exclu_user_ids": [Command.link(user.id)]}
            )

    def _auto_follow(self, users):
        """Make ``users`` follow the series of ``self`` (automatic follow, US-088).

        Ignore les utilisateurs inactifs, partagés (portail) et ceux qui se sont
        désabonnés de la série (suivi_exclu_user_ids). Écriture en sudo : le suivi
        automatique découle d'une autre action (création, possession).
        """
        users = users.filtered(lambda u: u.active and not u.share)
        if not users:
            return
        for serie in self.sudo():
            to_add = users - serie.suivi_user_ids - serie.suivi_exclu_user_ids
            if to_add:
                serie.write({"suivi_user_ids": [Command.link(uid) for uid in to_add.ids]})

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        # Le créateur réel suit sa série ; pas le superutilisateur ni le chargement de données.
        if not self.env.su and self.env.uid != SUPERUSER_ID and not self.env.context.get("install_mode"):
            records._auto_follow(self.env.user)
        return records

    def _search_a_suivre(self, operator, value):
        # Odoo 19 normalise '=' / '!=' en 'in' / 'not in' avant l'appel ;
        # on accepte les deux formes.
        if operator in ("=", "!="):
            values = {bool(value)}
        elif operator in ("in", "not in"):
            values = {bool(v) for v in value}
        else:
            return NotImplemented
        if operator in ("!=", "not in"):
            values = {True, False} - values
        followed = [("suivi_user_ids", "in", self.env.user.id)]
        not_followed = [("suivi_user_ids", "not in", self.env.user.id)]
        if values == {True, False}:
            return []
        if values == {True}:
            return followed
        if values == {False}:
            return not_followed
        return [("id", "=", False)]

    @api.depends("name_normalise")
    def _compute_name_initial(self):
        for rec in self:
            first = (rec.name_normalise or "")[:1].upper()
            rec.name_initial = first if first in string.ascii_uppercase else "#"

    # ── Compteurs « ma collection » ─────────────────────────────────────────

    def _my_collection_counts(self, serie_ids=None):
        """Return ``{serie_id: {...counts}}`` for the current user.

        Une requête par source (bibliothèque, tomes numérotés, prêts), quel que soit
        le nombre de séries. ``serie_ids=None`` : toutes les séries (recherche).
        """
        user = self.env.user
        serie_domain = [] if serie_ids is None else [("serie_id", "in", list(serie_ids))]
        counts = defaultdict(lambda: {"owned": 0, "read": 0, "unread": 0, "lent": 0, "missing": 0, "rating": 0.0})

        entries = (
            self.env["comic.customer.album"]
            .sudo()
            .search_fetch(
                [("partner_id", "=", user.partner_id.id), ("serie_id", "!=", False), *serie_domain],
                ["serie_id", "work_id", "dans_collection", "etat_lecture", "note", "ignore_wishlist"],
            )
        )
        owned = defaultdict(set)
        read = defaultdict(set)
        not_missing = defaultdict(set)  # possédés ou ignorés (« ne pas acheter »)
        notes = defaultdict(list)
        for entry in entries:
            sid, wid = entry.serie_id.id, entry.work_id.id
            if entry.dans_collection:
                owned[sid].add(wid)
                not_missing[sid].add(wid)
                if entry.etat_lecture == "lu":
                    read[sid].add(wid)
            elif entry.ignore_wishlist:
                not_missing[sid].add(wid)
            if entry.note > 0:
                notes[sid].append(entry.note)

        numbered = defaultdict(set)
        works = self.env["comic.work"].sudo().search_fetch([("tome", ">", 0), *serie_domain], ["serie_id"])
        for work in works:
            numbered[work.serie_id.id].add(work.id)

        loans = (
            self.env["comic.pret"]
            .sudo()
            .search_fetch(
                [
                    ("create_uid", "=", user.id),
                    ("retourne", "=", False),
                    ("edition_id.work_id.serie_id", "!=", False),
                    *([] if serie_ids is None else [("edition_id.work_id.serie_id", "in", list(serie_ids))]),
                ],
                ["edition_id"],
            )
        )
        for loan in loans:
            counts[loan.edition_id.work_id.serie_id.id]["lent"] += 1

        for sid in set(owned) | set(notes) | set(numbered):
            row = counts[sid]
            row["owned"] = len(owned[sid])
            row["read"] = len(read[sid])
            row["unread"] = len(owned[sid] - read[sid])
            row["missing"] = len(numbered[sid] - not_missing[sid])
            if notes[sid]:
                row["rating"] = round(sum(notes[sid]) / len(notes[sid]), 1)
        return counts

    @api.depends_context("uid")
    @api.depends("work_ids.tome")
    def _compute_my_counts(self):
        counts = self._my_collection_counts([sid for sid in self.ids if sid])
        for serie in self:
            row = counts.get(serie.id) or {}
            serie.my_owned_count = row.get("owned", 0)
            serie.my_read_count = row.get("read", 0)
            serie.my_unread_count = row.get("unread", 0)
            serie.my_lent_count = row.get("lent", 0)
            serie.my_missing_count = row.get("missing", 0)
            serie.my_rating = row.get("rating", 0.0)

    def _search_my_count(self, key, operator, value):
        """Domain on a ``my_*_count`` field, evaluated for the current user.

        Seules les séries à compteur non nul sont calculées ; les autres valent 0.
        Si 0 satisfait la condition, on exclut les séries qui ne la satisfont pas.
        """
        if operator in ("in", "not in"):
            values = {int(v or 0) for v in value}
            matches = (lambda c: c in values) if operator == "in" else (lambda c: c not in values)
        elif operator in COUNT_OPERATORS:
            matches = lambda c: COUNT_OPERATORS[operator](c, int(value or 0))  # noqa: E731
        else:
            return NotImplemented
        counts = {sid: row[key] for sid, row in self._my_collection_counts().items() if row[key]}
        if matches(0):
            return [("id", "not in", [sid for sid, count in counts.items() if not matches(count)])]
        return [("id", "in", [sid for sid, count in counts.items() if matches(count)])]

    def _search_my_owned_count(self, operator, value):
        return self._search_my_count("owned", operator, value)

    def _search_my_read_count(self, operator, value):
        return self._search_my_count("read", operator, value)

    def _search_my_unread_count(self, operator, value):
        return self._search_my_count("unread", operator, value)

    def _search_my_lent_count(self, operator, value):
        return self._search_my_count("lent", operator, value)

    def _search_my_missing_count(self, operator, value):
        return self._search_my_count("missing", operator, value)

    # ── Suivi depuis les lignes « Mes séries » / « Albums manquants » ───────

    def action_toggle_follow(self):
        """Badge « Followed » / bouton « Follow » : bascule le suivi de l'utilisateur."""
        for serie in self:
            serie.a_suivre = not serie.a_suivre
        return True

    def action_stop_following(self):
        """« Stop following » (albums manquants) : désabonnement mémorisé, puis rechargement."""
        self.a_suivre = False
        return {"type": "ir.actions.client", "tag": "soft_reload"}

    def action_view_my_missing(self):
        """« See » : ma wishlist, filtrée sur cette série."""
        self.ensure_one()
        action = self.env["ir.actions.act_window"]._for_xml_id("comics_collections.action_comic_wishlist")
        action["context"] = {
            "create": False,
            "edit": False,
            "delete": False,
            "search_default_serie_id": self.id,
        }
        return action

    @api.depends("image_couverture")
    def _compute_has_cover(self):
        for rec in self:
            rec.has_cover = bool(rec.image_couverture)

    @api.depends("work_ids.edition_ids.image_couverture", "work_ids.tome")
    def _compute_first_edition_cover(self):
        for serie in self:
            edition = False
            for work in serie.work_ids.sorted("tome"):
                ed = work.edition_ids.filtered("image_couverture")
                if ed:
                    edition = ed[0]
                    break
            serie.first_edition_cover_id = edition

    @api.depends("work_ids.auteur_line_ids.partner_id", "work_ids.auteur_line_ids.role", "work_ids.active")
    def _compute_auteurs(self):
        role_labels = dict(self.env["comic.work.auteur.line"]._fields["role"]._description_selection(self.env))
        for serie in self:
            roles_by_partner = {}
            for line in serie.work_ids.filtered("active").auteur_line_ids.sorted(lambda li: (li.tome or 0, li.id)):
                roles = roles_by_partner.setdefault(line.partner_id, [])
                label = role_labels.get(line.role, line.role)
                if label and label not in roles:
                    roles.append(label)
            serie.auteur_ids = self.env["res.partner"].union(*roles_by_partner)
            serie.auteur_names = " · ".join(
                f"{partner.name} ({', '.join(roles)})" if roles else partner.name
                for partner, roles in roles_by_partner.items()
            )

    @api.depends("work_ids")
    def _compute_works(self):
        for serie in self:
            serie.nb_works_total = len(serie.work_ids)

    @api.model
    def _action_open_series(self, series, title):
        """Liste des séries données (fiches auteur / éditeur)."""
        return {
            "type": "ir.actions.act_window",
            "name": self.env._("Series — %s", title),
            "res_model": "comic.serie",
            "view_mode": "list,kanban,form",
            "domain": [("id", "in", series.ids)],
            "context": {"create": False},
        }

    def action_view_works(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": self.env._("Albums — %s", self.name),
            "res_model": "comic.work",
            "view_mode": "list,kanban,form",
            "views": [
                (self.env.ref("comics_collections.view_comic_work_list_serie").id, "list"),
                (False, "kanban"),
                (False, "form"),
            ],
            "domain": [("serie_id", "=", self.id)],
            # Ouvert depuis « Mes séries » : un album créé ici entre dans la collection.
            "context": {
                "default_serie_id": self.id,
                **({"comic_auto_own": True} if self.env.context.get("comic_auto_own") else {}),
            },
        }
