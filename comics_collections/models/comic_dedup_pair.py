import difflib
import logging
from collections import defaultdict

from odoo import _, api, fields, models

from ..utils.normalize import normalize_title
from .comic_work import _score_pair

_logger = logging.getLogger(__name__)

# Seuil de similarité utilisé par _score_pair (titres et noms de série).
# Sert ici de borne pour les préfiltres quick_ratio / real_quick_ratio.
DEDUP_RATIO_THRESHOLD = 0.85
# Longueur du préfixe normalisé utilisé pour le blocking titre / série.
BLOCKING_PREFIX_LEN = 4


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

    def _merge_wizard_action(self, source, target):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Fusionner deux albums"),
            "res_model": "comic.work.merge.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_source_work_id": source.id,
                "default_target_work_id": target.id,
                "default_pair_id": self.id,
            },
        }

    def action_open_merge_wizard(self):
        """Fusionner A → B : A est archivé, B est conservé."""
        self.ensure_one()
        return self._merge_wizard_action(self.work_a_id, self.work_b_id)

    def action_open_merge_wizard_reverse(self):
        """Fusionner B → A : B est archivé, A est conservé."""
        self.ensure_one()
        return self._merge_wizard_action(self.work_b_id, self.work_a_id)

    @api.model
    def _cleanup_for_works(self, works):
        """Supprime toutes les paires (ignorées ou non) impliquant ces albums."""
        if not works:
            return
        self.search(["|", ("work_a_id", "in", works.ids), ("work_b_id", "in", works.ids)]).unlink()

    # ── Scan ─────────────────────────────────────────────────────────────────

    @api.model
    def _blocking_keys(self, row):
        """Clés de bucket d'un album (ligne issue de _load_scan_rows).

        - ``("s", serie_id)`` : albums de la même série ;
        - ``("t", titre[:4], serie[:4])`` : titres normalisés ET noms de série
          normalisés partageant leurs 4 premiers caractères (séries proches,
          ou albums sans série entre eux).
        """
        keys = []
        if row["serie_id"]:
            keys.append(("s", row["serie_id"]))
        if row["titre"]:
            keys.append(
                (
                    "t",
                    row["titre"][:BLOCKING_PREFIX_LEN],
                    row["serie_norm"][:BLOCKING_PREFIX_LEN],
                )
            )
        return keys

    @api.model
    def _iter_blocked_pairs(self, rows):
        """Génère les couples (row_a, row_b) partageant un bucket, sans doublon."""
        buckets = defaultdict(list)
        for row in rows:
            for key in self._blocking_keys(row):
                buckets[key].append(row)
        seen = set()
        for bucket in buckets.values():
            if len(bucket) < 2:
                continue
            for i, ra in enumerate(bucket):
                for rb in bucket[i + 1 :]:
                    key = (min(ra["id"], rb["id"]), max(ra["id"], rb["id"]))
                    if key in seen:
                        continue
                    seen.add(key)
                    yield ra, rb

    @api.model
    def _load_scan_rows(self):
        """Lit en masse les albums actifs et le nom normalisé de leur série."""
        works = self.env["comic.work"].search_read(
            [("active", "=", True)],
            ["titre_normalise", "titre_canonique", "tome", "serie_id"],
        )
        serie_ids = list({w["serie_id"][0] for w in works if w["serie_id"]})
        serie_norms = {
            s["id"]: s["name_normalise"] or ""
            for s in self.env["comic.serie"].search_read([("id", "in", serie_ids)], ["name_normalise"])
        }
        rows = []
        for w in works:
            serie_id = w["serie_id"][0] if w["serie_id"] else False
            rows.append(
                {
                    "id": w["id"],
                    "tome": w["tome"],
                    "titre": w["titre_normalise"] or normalize_title(w["titre_canonique"]),
                    "serie_id": serie_id,
                    "serie_norm": serie_norms.get(serie_id, "") if serie_id else "",
                }
            )
        return rows

    @staticmethod
    def _may_reach_threshold(a, b):
        """Bornes supérieures bon marché de SequenceMatcher.ratio()."""
        matcher = difflib.SequenceMatcher(None, a, b)
        return matcher.real_quick_ratio() >= DEDUP_RATIO_THRESHOLD and matcher.quick_ratio() >= DEDUP_RATIO_THRESHOLD

    @api.model
    def _score_rows(self, ra, rb):
        """Score d'un couple : même résultat que _score_pair, avec préfiltres."""
        same_serie = bool(ra["serie_id"] and ra["serie_id"] == rb["serie_id"])
        conflict = bool(same_serie and ra["tome"] and ra["tome"] == rb["tome"])
        if not conflict:
            if not ra["titre"] or not rb["titre"]:
                return 0.0, ""
            if not self._may_reach_threshold(ra["titre"], rb["titre"]):
                return 0.0, ""
            if not same_serie and ra["serie_norm"] and rb["serie_norm"]:
                if not self._may_reach_threshold(ra["serie_norm"], rb["serie_norm"]):
                    return 0.0, ""
        return _score_pair(
            same_serie,
            ra["tome"],
            ra["titre"],
            ra["serie_norm"],
            rb["tome"],
            rb["titre"],
            rb["serie_norm"],
        )

    @api.model
    def action_scan_all(self):
        """Scan all active works for duplicates and (re-)populate pairs.

        Blocking : seuls les albums d'un même bucket (même série, ou titres et
        séries partageant leurs 4 premiers caractères normalisés) sont comparés.
        """
        # Remove non-ignored pairs, and any pair pointing to an archived album
        self.search(
            [
                "|",
                "|",
                ("ignored", "=", False),
                ("work_a_id.active", "=", False),
                ("work_b_id.active", "=", False),
            ]
        ).unlink()

        # Build ignored pair keys so we don't re-create them
        ignored_keys = {
            (min(p["work_a_id"][0], p["work_b_id"][0]), max(p["work_a_id"][0], p["work_b_id"][0]))
            for p in self.search_read([("ignored", "=", True)], ["work_a_id", "work_b_id"])
        }

        new_pairs = []
        for ra, rb in self._iter_blocked_pairs(self._load_scan_rows()):
            key = (min(ra["id"], rb["id"]), max(ra["id"], rb["id"]))
            if key in ignored_keys:
                continue
            score, reason = self._score_rows(ra, rb)
            if score >= 0.7:
                new_pairs.append(
                    {
                        "work_a_id": key[0],
                        "work_b_id": key[1],
                        "score": score,
                        "reason": reason,
                        "ignored": False,
                    }
                )

        try:
            with self.env.cr.savepoint():
                self.create(new_pairs)
        except Exception:
            _logger.debug("Bulk dedup pair creation failed, falling back to one by one")
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
