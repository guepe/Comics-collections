from odoo import fields, models

from .res_partner import DEFAULT_DISCOVERY_DAILY_LIMIT


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    comic_ai_discovery_daily_limit = fields.Integer(
        string="Découvertes IA par client et par jour",
        default=DEFAULT_DISCOVERY_DAILY_LIMIT,
        config_parameter="comic_ai.discovery_daily_limit",
        help="Nombre maximal de recherches « Découvrir de nouvelles BD » par client du portail et "
        "par jour (0 : désactivé sur le portail).",
    )
