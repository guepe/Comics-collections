from odoo import models, fields, api

class BookingConflictWizard(models.TransientModel):
    _name = "booking.conflict.wizard"
    _description = "Booking Conflict Wizard"

    booking_id = fields.Many2one("booking.history")
    conflict_ids = fields.Many2many("booking.history", string="Conflicting Bookings")

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        booking = self.env['booking.history'].browse(self.env.context.get('default_booking_id'))
        conflicts = booking._get_overlapping_bookings()
        res['conflict_ids'] = [(6, 0, conflicts.ids)]
        return res

    # CHECK AVAILABLE SLOTS
   

    def action_check_available_slots(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Available Slots',
            'res_model': 'available.slot.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_booking_id': self.booking_id.id
            }
        }
    
    warning_message = fields.Html(
        default="""
        <div style="background-color:#ffe6e6;
                    border:1px solid #ff4d4d;
                    padding:8px;
                    font-weight:bold;
                    color:#cc0000;">
            Books are already allocated between the below slots
        </div>
        """
    )