from odoo import api, fields, models


class ComicEditeur(models.Model):
    _name = "comic.editeur"
    _description = "Comic publisher"
    _order = "name"

    name = fields.Char(required=True)
    partner_id = fields.Many2one("res.partner", string="Contact")
    pays_id = fields.Many2one("res.country", string="Country")
    site_web = fields.Char(string="Website")
    bdgest_editeur_id = fields.Integer(string="BDGest ID", aggregator=False)

    serie_ids = fields.One2many("comic.serie", "editeur_id", string="Series (main publisher)")
    edition_ids = fields.One2many("comic.edition", "editeur_id", string="Editions")
    comic_work_ids = fields.Many2many("comic.work", string="Albums", compute="_compute_catalogue")
    comic_serie_ids = fields.Many2many("comic.serie", string="Series", compute="_compute_catalogue")
    comic_work_count = fields.Integer(string="Number of albums", compute="_compute_catalogue")
    comic_serie_count = fields.Integer(string="Number of series", compute="_compute_catalogue")

    @api.depends("edition_ids.work_id.serie_id", "serie_ids")
    def _compute_catalogue(self):
        """Albums publiés par l'éditeur (via leurs éditions) et séries correspondantes,
        y compris les séries dont il est l'éditeur principal."""
        for editeur in self:
            works = editeur.edition_ids.work_id
            series = editeur.serie_ids | works.serie_id
            editeur.comic_work_ids = works.sorted(lambda w: (w.serie_id.name or "", w.tome, w.id))
            editeur.comic_serie_ids = series.sorted(lambda s: (s.name or "", s.id))
            editeur.comic_work_count = len(works)
            editeur.comic_serie_count = len(series)

    def action_view_comic_works(self):
        self.ensure_one()
        return self.env["comic.work"]._action_open_works(self.comic_work_ids, self.display_name)

    def action_view_comic_series(self):
        self.ensure_one()
        return self.env["comic.serie"]._action_open_series(self.comic_serie_ids, self.display_name)
