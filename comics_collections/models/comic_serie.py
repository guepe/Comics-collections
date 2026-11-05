from odoo import Command, api, fields, models

from ..utils.normalize import normalize_title


class ComicSerie(models.Model):
    _name = "comic.serie"
    _description = "Série de bandes dessinées"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "name"

    name = fields.Char(string="Titre", required=True, tracking=True)
    name_normalise = fields.Char(
        string="Titre normalisé",
        compute="_compute_name_normalise",
        store=True,
        index=True,
    )
    type = fields.Selection(
        [
            ("bd", "Bande dessinée"),
            ("manga", "Manga"),
            ("comics", "Comics"),
            ("one_shot", "One-shot"),
        ],
        default="bd",
        tracking=True,
    )
    statut = fields.Selection(
        [
            ("en_cours", "En cours"),
            ("terminee", "Terminée"),
            ("abandonnee", "Abandonnée"),
        ],
        default="en_cours",
        tracking=True,
    )
    genre_id = fields.Many2one("comic.genre", string="Genre")
    editeur_id = fields.Many2one("comic.editeur", string="Éditeur")
    image_couverture = fields.Image(string="Couverture")
    synopsis = fields.Html()
    bdgest_id = fields.Integer(string="ID BDGest")
    bedetheque_url = fields.Char(string="URL Bedetheque")
    work_ids = fields.One2many("comic.work", "serie_id", string="Albums")
    nb_works_total = fields.Integer(string="Tomes au total", compute="_compute_works", store=True)
    suivi_user_ids = fields.Many2many(
        "res.users",
        "comic_serie_suivi_user_rel",
        "serie_id",
        "user_id",
        string="Suivie par",
    )
    # Catalogue partagé : le suivi est propre à chaque utilisateur. Ce booléen
    # non stocké reflète l'utilisateur courant (présence dans suivi_user_ids).
    a_suivre = fields.Boolean(
        string="À suivre",
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
        to_follow = self.filtered(lambda s: s.a_suivre and user not in s.suivi_user_ids)
        to_unfollow = self.filtered(lambda s: not s.a_suivre and user in s.suivi_user_ids)
        if to_follow:
            to_follow.write({"suivi_user_ids": [Command.link(user.id)]})
        if to_unfollow:
            to_unfollow.write({"suivi_user_ids": [Command.unlink(user.id)]})

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

    @api.depends("work_ids")
    def _compute_works(self):
        for serie in self:
            serie.nb_works_total = len(serie.work_ids)

    def action_view_works(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": f"Albums — {self.name}",
            "res_model": "comic.work",
            "view_mode": "list,kanban,form",
            "views": [
                (self.env.ref("comics_collections.view_comic_work_list_serie").id, "list"),
                (False, "kanban"),
                (False, "form"),
            ],
            "domain": [("serie_id", "=", self.id)],
            "context": {"default_serie_id": self.id},
        }
