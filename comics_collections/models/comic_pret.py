from datetime import timedelta

from odoo import api, fields, models
from odoo.exceptions import ValidationError

DEFAULT_LOAN_DAYS = 30


class ComicPret(models.Model):
    _name = "comic.pret"
    _description = "Comic album loan"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "date_pret desc"

    edition_id = fields.Many2one("comic.edition", string="Album", required=True, ondelete="restrict", tracking=True)
    partner_id = fields.Many2one("res.partner", string="Lent to", required=True, tracking=True)
    date_pret = fields.Date(string="Loan date", default=fields.Date.context_today, tracking=True)
    date_retour_prevue = fields.Date(
        string="Expected return date",
        default=lambda self: fields.Date.context_today(self) + timedelta(days=DEFAULT_LOAN_DAYS),
        tracking=True,
    )
    date_retour_effective = fields.Date(string="Actual return date", tracking=True)
    retourne = fields.Boolean(string="Returned", tracking=True)
    en_retard = fields.Boolean(string="Overdue", compute="_compute_en_retard", search="_search_en_retard")
    notes = fields.Text()

    # ── Retard ───────────────────────────────────────────────────────────────

    @api.depends("retourne", "date_retour_prevue")
    def _compute_en_retard(self):
        today = fields.Date.context_today(self)
        for pret in self:
            pret.en_retard = bool(not pret.retourne and pret.date_retour_prevue and pret.date_retour_prevue < today)

    def _search_en_retard(self, operator, value):
        if operator not in ("=", "!=") or not isinstance(value, bool):
            raise NotImplementedError(self.env._('Unsupported operator for "Overdue".'))
        domain = [
            ("retourne", "=", False),
            ("date_retour_prevue", "<", fields.Date.context_today(self)),
        ]
        positive = (operator == "=") == value
        return domain if positive else ["!", "&", *domain]

    # ── Cohérence retourne / date de retour ──────────────────────────────────

    @api.model
    def _normalize_return_vals(self, vals):
        """Keep `retourne` and `date_retour_effective` consistent:
        - retourné sans date → date du jour ;
        - date de retour saisie → retourné ;
        - « non retourné » → date de retour effacée."""
        if vals.get("date_retour_effective"):
            vals["retourne"] = True
        elif vals.get("retourne") and "date_retour_effective" not in vals:
            vals["date_retour_effective"] = fields.Date.context_today(self)
        elif "retourne" in vals and not vals["retourne"]:
            vals["date_retour_effective"] = False
        return vals

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            self._normalize_return_vals(vals)
        return super().create(vals_list)

    def write(self, vals):
        return super().write(self._normalize_return_vals(dict(vals)))

    @api.onchange("retourne")
    def _onchange_retourne(self):
        if self.retourne and not self.date_retour_effective:
            self.date_retour_effective = fields.Date.context_today(self)
        elif not self.retourne:
            self.date_retour_effective = False

    # ── Contraintes ──────────────────────────────────────────────────────────

    @api.constrains("date_pret", "date_retour_prevue", "date_retour_effective")
    def _check_dates(self):
        for pret in self:
            if pret.date_pret and pret.date_retour_prevue and pret.date_retour_prevue < pret.date_pret:
                raise ValidationError(self.env._("The expected return date cannot be earlier than the loan date."))
            if pret.date_pret and pret.date_retour_effective and pret.date_retour_effective < pret.date_pret:
                raise ValidationError(self.env._("The actual return date cannot be earlier than the loan date."))

    @api.constrains("edition_id", "retourne")
    def _check_not_already_lent(self):
        """Un même prêteur ne peut pas prêter deux fois en même temps le même album.
        (Catalogue partagé : deux collectionneurs différents peuvent prêter chacun leur exemplaire.)"""
        for pret in self.filtered(lambda p: not p.retourne):
            other = self.search(
                [
                    ("id", "!=", pret.id),
                    ("edition_id", "=", pret.edition_id.id),
                    ("create_uid", "=", pret.create_uid.id),
                    ("retourne", "=", False),
                ],
                limit=1,
            )
            if other:
                raise ValidationError(
                    self.env._(
                        '"%(album)s" is already lent to %(partner)s and has not been returned.',
                        album=pret.edition_id.display_name,
                        partner=other.partner_id.display_name,
                    )
                )

    # ── Actions ──────────────────────────────────────────────────────────────

    def action_retourner(self):
        self.filtered(lambda p: not p.retourne).write({"retourne": True})
        return True

    # ── Cron : rappel des retards ────────────────────────────────────────────

    @api.model
    def _cron_remind_overdue(self):
        """Crée une activité « À faire » pour le prêteur sur chaque prêt en retard
        (une seule activité ouverte par prêt)."""
        todo = self.env.ref("mail.mail_activity_data_todo", raise_if_not_found=False)
        for pret in self.search([("en_retard", "=", True)]):
            if pret.activity_ids:
                continue
            pret.activity_schedule(
                activity_type_id=todo.id if todo else False,
                summary=self.env._("Overdue loan: get the album back"),
                note=self.env._(
                    '"%(album)s" lent to %(partner)s was due back on %(date)s.',
                    album=pret.edition_id.display_name,
                    partner=pret.partner_id.display_name,
                    date=pret.date_retour_prevue,
                ),
                user_id=pret.create_uid.id or self.env.uid,
            )
