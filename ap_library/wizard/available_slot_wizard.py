from odoo import models, fields, api
from datetime import timedelta

class AvailableSlotWizard(models.TransientModel):
    _name = "available.slot.wizard"
    _description = "Available Slot Wizard"

    booking_id = fields.Many2one("booking.history")
    slot_message = fields.Html(readonly=True)


    def _generate_available_slots(self):
        booking = self.booking_id
        conflicts = booking._get_overlapping_bookings().sorted(
            key=lambda r: r.booking_date
        )

        available_slots = []
        current_start = booking.booking_date

        for conflict in conflicts:
            if current_start < conflict.booking_date:
                available_slots.append(
                    (current_start, conflict.booking_date)
                )
            current_start = conflict.expiry_date

        if current_start < booking.expiry_date:
            available_slots.append(
                (current_start, booking.expiry_date)
            )

        return available_slots

    # DEFAULT GET (SHOW IN WIZARD)


    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)

        booking = self.env['booking.history'].browse(
            self.env.context.get('default_booking_id')
        )

        res['booking_id'] = booking.id

        slots = self._context.get('available_slots') or []

        if not slots:
            wizard_temp = self.new({'booking_id': booking.id})
            slots = wizard_temp._generate_available_slots()

        message = "<p><b>Below slots are available between this period:</b></p><ul>"

        for start, end in slots:
            message += f"<li>{start} between {end}</li>"

        message += "</ul>"

        res['slot_message'] = message
        return res

    # NOTIFY USER
  

    def action_notify_user(self):
        self.ensure_one()

        booking = self.booking_id
        slots = self._generate_available_slots()

        formatted_slots = ""
        for start, end in slots:
            formatted_slots += f"<li>{start} between {end}</li>"

        booking.available_slot_html = formatted_slots
        booking.status = 'pending'

        template = self.env.ref(
            'wk_library_management.email_template_booking_notify',
            False
        )

        if template:
            template.send_mail(booking.id, force_send=True)

        return {'type': 'ir.actions.act_window_close'}