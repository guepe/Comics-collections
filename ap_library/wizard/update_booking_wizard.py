from odoo import models, fields, api


class UpdateBookingWizard(models.TransientModel):
    _name = "update.booking.wizard"
    _description = "Update Booking Wizard"

    partner_id = fields.Many2one(
        "res.partner",
        string="Customer",
        readonly=True
    )

    booking_id = fields.Many2one(
        "booking.history",
        string="Booking",
        required=True,
        domain="[('partner_id','=',partner_id), ('status','in',['pending','draft'])]"
    )

    start_date = fields.Date(string="Start Date")
    end_date = fields.Date(string="End Date")

    @api.onchange('booking_id')
    def _onchange_booking(self):
        """Auto fill dates when booking selected"""
        if self.booking_id:
            self.start_date = self.booking_id.booking_date
            self.end_date = self.booking_id.expiry_date

    def action_update_booking(self):
        """Update booking duration"""
        self.ensure_one()

        if self.booking_id:
            self.booking_id.write({
                'booking_date': self.start_date,
                'expiry_date': self.end_date,
            })