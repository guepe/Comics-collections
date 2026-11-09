from odoo import fields, models

DEFAULT_DISCOVERY_DAILY_LIMIT = 5


class ResPartner(models.Model):
    _inherit = "res.partner"

    comic_ai_discovery_date = fields.Date(
        string="Découverte IA — dernier jour d'utilisation",
        groups="base.group_system",
        copy=False,
    )
    comic_ai_discovery_count = fields.Integer(
        string="Découverte IA — appels du jour",
        groups="base.group_system",
        copy=False,
    )

    def _comic_ai_discovery_limit(self):
        raw = self.env["ir.config_parameter"].sudo().get_param("comic_ai.discovery_daily_limit")
        try:
            return max(0, int(raw)) if raw not in (None, False, "") else DEFAULT_DISCOVERY_DAILY_LIMIT
        except (TypeError, ValueError):
            return DEFAULT_DISCOVERY_DAILY_LIMIT

    def _comic_ai_discovery_remaining(self):
        """Number of AI discovery calls still allowed today from the portal."""
        self.ensure_one()
        partner = self.sudo()
        today = fields.Date.context_today(partner)
        used = partner.comic_ai_discovery_count if partner.comic_ai_discovery_date == today else 0
        return max(0, self._comic_ai_discovery_limit() - used)

    def _comic_ai_discovery_consume(self):
        self.ensure_one()
        partner = self.sudo()
        today = fields.Date.context_today(partner)
        if partner.comic_ai_discovery_date == today:
            partner.comic_ai_discovery_count += 1
        else:
            partner.write({"comic_ai_discovery_date": today, "comic_ai_discovery_count": 1})
