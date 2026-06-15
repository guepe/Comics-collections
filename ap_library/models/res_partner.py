from odoo import models, fields

class ResPartner(models.Model):
    _inherit = "res.partner"

    history_ids = fields.One2many(
        "booking.history",
        "partner_id",
        string="Booking History"
    )




    def action_create_booking(self):
        self.ensure_one()
        user = self.user_ids[:1]   # first related user (if exists)

        return {
            "type": "ir.actions.act_window",
            "name": "Create Booking",
            "res_model": "booking.history",
            "view_mode": "form",
            "view_id": self.env.ref(
                "wk_library_management.view_library_booking_history_form"
            ).id,
            "target": "new",   
            "context": {
                "default_partner_id": self.id,
                "default_assign_to": user.id if user else False,
            },
        }
    
    def action_open_update_booking_wizard(self):
        return {
            'name': 'Update Booking',
            'type': 'ir.actions.act_window',
            'res_model': 'update.booking.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_partner_id': self.id
            }
        }
    

    def action_download_booking_history(self):
        self.ensure_one()
        return self.env.ref('wk_library_management.partner_booking_history_report').report_action(self)