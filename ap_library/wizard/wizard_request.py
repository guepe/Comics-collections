from odoo import models, api, fields
from odoo.exceptions import ValidationError

class BookIssuedWizard(models.TransientModel):
    _name="book.issue.wizard"
    _description="Book Issue Wizard"


    book_from=fields.Datetime(string="Book From",default=fields.Datetime.now)
    till_date=fields.Datetime(string="Till Date",default=fields.Datetime.now)

    assign_to = fields.Many2one("res.users", required=True)

    book_id=fields.Many2one("book.books",required=True)

    def action_confirm_request(self):
        self.ensure_one()

        if self.till_date < self.book_from:
            raise ValidationError("Till Date must be after Book From!.")
        
        self.env['booking.history'].create(
            {
                'book_id':self.book_id.id,
                'assign_to':self.assign_to.id,
                'booking_date':self.book_from,
                'expiry_date':self.till_date,
                'status':'pending',
            }
        )
