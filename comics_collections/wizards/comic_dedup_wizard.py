from odoo import fields, models
from odoo.exceptions import UserError


class ComicWorkMergeWizard(models.TransientModel):
    _name = "comic.work.merge.wizard"
    _description = "Merge two comic albums"

    source_work_id = fields.Many2one(
        "comic.work",
        required=True,
        string="Source album (will be archived)",
        domain=[("active", "=", True)],
    )
    target_work_id = fields.Many2one(
        "comic.work",
        required=True,
        string="Target album (will be kept)",
        domain=[("active", "=", True)],
    )
    pair_id = fields.Many2one("comic.dedup.pair", string="Duplicate pair")

    nb_editions_source = fields.Integer(related="source_work_id.nb_editions", string="Editions to transfer")
    nb_auteurs_source = fields.Integer(related="source_work_id.nb_auteurs", string="Authors to transfer")

    def action_confirm_merge(self):
        self.ensure_one()
        if self.source_work_id == self.target_work_id:
            raise UserError(self.env._("Source and target must be two different albums."))

        self.source_work_id._merge_into(self.target_work_id)

        # _merge_into already removed the pairs of the archived source; the
        # selected pair may still exist if it did not involve the source.
        if self.pair_id.exists():
            self.pair_id.unlink()

        return {
            "type": "ir.actions.act_window",
            "res_model": "comic.work",
            "res_id": self.target_work_id.id,
            "view_mode": "form",
            "target": "current",
        }
