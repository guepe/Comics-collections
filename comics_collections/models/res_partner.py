from odoo import api, fields, models

from ..utils.author_tables import authors_table


class ResPartner(models.Model):
    _inherit = "res.partner"

    auteur_work_line_ids = fields.One2many(
        "comic.work.auteur.line",
        "partner_id",
        string="Rôles BD",
    )
    is_comic_author = fields.Boolean(
        string="Auteur BD",
        default=False,
        index=True,
        help="Coché automatiquement dès que le contact est crédité sur un album, "
        "ou à la création depuis le menu Auteurs.",
    )
    comic_work_ids = fields.Many2many(
        "comic.work",
        string="Albums BD",
        compute="_compute_comic_bibliography",
    )
    comic_serie_ids = fields.Many2many(
        "comic.serie",
        string="Séries BD",
        compute="_compute_comic_bibliography",
    )
    comic_work_count = fields.Integer(string="Nb albums BD", compute="_compute_comic_bibliography")
    comic_serie_count = fields.Integer(string="Nb séries BD", compute="_compute_comic_bibliography")

    # « A souvent travaillé avec » : co-auteurs, par nombre d'albums en commun (US-091)
    comic_coauthors_html = fields.Html(
        string="A souvent travaillé avec", compute="_compute_comic_coauthors", sanitize=False
    )

    @api.depends("auteur_work_line_ids.work_id.auteur_line_ids.partner_id")
    def _compute_comic_coauthors(self):
        for partner in self:
            works_by_partner = {}
            for work in partner.auteur_work_line_ids.work_id:
                for other in work.auteur_line_ids.partner_id - partner:
                    works_by_partner[other] = works_by_partner.get(other, self.env["comic.work"]) | work
            partner.comic_coauthors_html = authors_table(
                self.env,
                {other: len(works) for other, works in works_by_partner.items()},
                works_by_partner,
                self.env._("Aucun co-auteur connu."),
                self.env._("Albums ensemble"),
            )

    @api.depends("auteur_work_line_ids.work_id.serie_id")
    def _compute_comic_bibliography(self):
        """Albums et séries auxquels le contact a participé (tous rôles confondus)."""
        for partner in self:
            works = partner.auteur_work_line_ids.work_id
            series = works.serie_id
            partner.comic_work_ids = works.sorted(lambda w: (w.serie_id.name or "", w.tome, w.id))
            partner.comic_serie_ids = series.sorted(lambda s: (s.name or "", s.id))
            partner.comic_work_count = len(works)
            partner.comic_serie_count = len(series)

    def action_view_comic_works(self):
        self.ensure_one()
        return self.env["comic.work"]._action_open_works(self.comic_work_ids, self.display_name)

    def action_view_comic_series(self):
        self.ensure_one()
        return self.env["comic.serie"]._action_open_series(self.comic_serie_ids, self.display_name)
