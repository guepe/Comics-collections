import logging

from odoo import _, api, fields, models

from ..utils.normalize import normalize_title

_logger = logging.getLogger(__name__)


class ComicDedupPair(models.Model):
    _name = "comic.dedup.pair"
    _description = "Paire de doublons potentiels"
    _order = "score desc, id"

    work_a_id = fields.Many2one("comic.work", required=True, ondelete="cascade", string="Album A")
    work_b_id = fields.Many2one("comic.work", required=True, ondelete="cascade", string="Album B")
    score = fields.Float(digits=(4, 3))
    reason = fields.Selection(
        [
            ("conflit_certain", "Conflit certain"),
            ("doublon_probable", "Doublon probable"),
            ("doublon_possible", "Doublon possible"),
        ],
        string="Type",
    )
    ignored = fields.Boolean(string="Ignoré", default=False)

    _unique_pair = models.Constraint(
        "UNIQUE(work_a_id, work_b_id)",
        "Cette paire est déjà enregistrée.",
    )

    # ── Actions depuis la liste ───────────────────────────────────────────────

    def action_ignore(self):
        self.write({"ignored": True})

    def action_open_merge_wizard(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "Fusionner deux albums",
            "res_model": "comic.work.merge.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_source_work_id": self.work_a_id.id,
                "default_target_work_id": self.work_b_id.id,
                "default_pair_id": self.id,
            },
        }

    # ── Scan ─────────────────────────────────────────────────────────────────

    @api.model
    def action_scan_all(self):
        """Scan all active works for duplicates and (re-)populate pairs."""
        from .comic_work import _score_pair

        # Remove all non-ignored pairs so we start fresh
        self.search([("ignored", "=", False)]).unlink()

        # Build ignored pair keys so we don't re-create them
        ignored = self.search([("ignored", "=", True)])
        ignored_keys = {(min(p.work_a_id.id, p.work_b_id.id), max(p.work_a_id.id, p.work_b_id.id)) for p in ignored}

        works = self.env["comic.work"].search([("active", "=", True)])
        work_list = list(works)
        new_pairs = []
        seen = set()

        for i, wa in enumerate(work_list):
            for wb in work_list[i + 1 :]:
                key = (min(wa.id, wb.id), max(wa.id, wb.id))
                if key in seen or key in ignored_keys:
                    continue
                seen.add(key)

                same_serie = bool(wa.serie_id and wb.serie_id and wa.serie_id.id == wb.serie_id.id)
                score, reason = _score_pair(
                    same_serie,
                    wa.tome,
                    wa.titre_normalise or normalize_title(wa.titre_canonique),
                    wa.serie_id.name_normalise or "",
                    wb.tome,
                    wb.titre_normalise or normalize_title(wb.titre_canonique),
                    wb.serie_id.name_normalise or "",
                )
                if score >= 0.7:
                    new_pairs.append(
                        {
                            "work_a_id": wa.id,
                            "work_b_id": wb.id,
                            "score": score,
                            "reason": reason,
                            "ignored": False,
                        }
                    )

        for vals in new_pairs:
            try:
                with self.env.cr.savepoint():
                    self.create(vals)
            except Exception:
                _logger.debug("Dedup pair already exists, skipping duplicate creation")

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "message": _(
                    "Analyse terminée : %(n)d paire(s) de doublons potentiels trouvée(s).",
                    n=len(new_pairs),
                ),
                "type": "success",
                "sticky": False,
            },
        }
