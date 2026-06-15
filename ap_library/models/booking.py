from odoo import models, fields,api
from odoo.exceptions import ValidationError
import logging
import base64
from collections import defaultdict
from datetime import datetime, timedelta
_logger = logging.getLogger(__name__)


class Bookinghistory(models.Model):
    _name='booking.history'
    _description='Booking History'
    _inherit=['mail.thread','mail.activity.mixin']

    name=fields.Char(string="Booking No", readonly=True,copy=False, default='New')
    booking_date=fields.Datetime(string="Booking Date",default=fields.Datetime.now)
    expiry_date=fields.Datetime(string="Booking Till",default=fields.Datetime.now)
    status=fields.Selection([
        ('draft','Draft'),
        ('pending','Pending'),
        ('approved','Approved'),
        ('returned','Returned'),
        ('rejected','Rejected')
    ],default='draft', string="Status",tracking=True,compute="_onchange_status",store=True)



    issued_by=fields.Many2one("res.users",string="Issued By",default=lambda self: self._get_default_issued_by() )
    received_by=fields.Many2one("res.users",string="Received By")
   
    book_id=fields.Many2one("book.books",string="Book",required=True)
    active = fields.Boolean(default=True)
    total_days=fields.Integer(string="Days",compute="compute_total_days",store=True)

    assign_to = fields.Many2one(
    "res.users",
    string="Assigned To",
    required=True,
    default=lambda self: self.env.user
    )


    partner_id = fields.Many2one(
        "res.partner",
        string="Customer",
        required=True,
        default=lambda self: self.env.user.partner_id.id,
       
    )

  
    
    def action_approved_booking(self):
        for rec in self:
            if not rec.issued_by:
                raise ValidationError("Issued By is necessary!.")
            rec.status='approved'
    def action_rejected_booking(self):
        self.status='rejected'
    def action_returned_booking(self):
        self.status='returned'

    def action_pending_booking(self):
        for record in self:
            if record.status == 'draft': 
                record.sudo().write({
                    'status': 'pending'  
                })
   
    
    def _get_default_issued_by(self):
        
        is_admin = self.env.user.has_group('wk_library_management.group_library_admin')
        is_librarian = self.env.user.has_group('wk_library_management.group_library_librarian')

        if is_admin or is_librarian:
            return self.env.user
        return False


    @api.depends("status")
    def _onchange_status(self):
        if self.status=="returned" and self.book_id:
            self.book_id.availability=True


    @api.depends("booking_date","expiry_date")
    def compute_total_days(self):
        for rec in self:
            if rec.booking_date and rec.expiry_date:
                delta=rec.expiry_date-rec.booking_date
                rec.total_days=delta.days+1
            else:
                rec.total_days=0


    def _update_book_copies(self, status, book):
        if not book:
            return

        if status == "approved":
            if book.no_of_copies <= 0:
                book.availability=False
                raise ValidationError("No copies available")
            book.no_of_copies -= 1

            if book.no_of_copies == 0:
                book.availability=False
                
        elif status == "returned":
            book.no_of_copies += 1
            book.availability=True





    def _send_mail_with_pdf(self, template):
        self.ensure_one()
        report_xml_id = "wk_library_management.action_report_booking_history"

        pdf_content, _ = self.env['ir.actions.report']._render_qweb_pdf(report_xml_id, [self.id])

        attachment = self.env['ir.attachment'].create({
            'name': f'Booking_{self.name.replace("/", "_")}.pdf',
            'type': 'binary',
            'datas': base64.b64encode(pdf_content),
            'res_model': 'booking.history',
            'res_id': self.id,
            'mimetype': 'application/pdf',
            'public': True,
        })
        email_values = {'attachment_ids': [(6, 0, [attachment.id])]}
        template.sudo().send_mail(self.id, force_send=True, email_values=email_values)

    
    def action_print_booking_report(self):
        self.ensure_one()
        return self.env.ref("wk_library_management.action_report_booking_history").report_action(self)
    

    def write(self, vals):
        res = super().write(vals)

        if 'status' in vals:
            for rec in self:
                rec._update_book_copies(vals['status'], rec.book_id)

               

        # logic for the during modification => booking number must be there inside the booking
        for rec in self:
            if not rec.name or rec.name=='New':
                vals['name']=self.env['ir.sequence'].next_by_code('booking.sequence') or 'New'
           
        #  Logic for email send when libraraian updates history
            template=self.env.ref("wk_library_management.email_template_library_librarian_status_update", raise_if_not_found=False)
            if template:
                # template.send_mail(rec.id, force_send=True)
                rec._send_mail_with_pdf(template)

        return res


#  Extra work -> to check that no duplicate of Booking number exist
    @api.constrains("name")
    def check_unique_Booing_sequence_number(self):
        for r in self:            
            if r.name:
                existing=self.search([
                    ('name','=',r.name),
                    ('id','!=',r.id)
                ])

                if existing:
                    raise ValidationError("Booking No  must be unique.")

# only method to check db unique by any way like sql query insert by shell
    _sql_constraints = [
    ('booking_name_unique', 'unique(name)', 'Booking No must be unique.')]
        

    @api.model
    def create(self, vals):
        if vals.get('name','New')=='New':
            vals['name']=self.env['ir.sequence'].next_by_code('booking.sequence') or 'New'
        
        if self.env.context.get('auto_pending'):
               vals['status'] = 'pending'

 
      
        record=super().create(vals)

        status = vals.get('status')
        if status:
           record._update_book_copies(status, record.book_id)
        
        
        # logic for the booking reminder
        template = self.env.ref('wk_library_management.email_template_library', raise_if_not_found=False)
        if template and record.assign_to.partner_id.email:
            record.sudo()._send_mail_with_pdf(template)
        

        return record


    # CHECK OVERLAPPING LOGIC
    def _get_overlapping_bookings(self):
        self.ensure_one()

        return self.search([
            ('id', '!=', self.id),
            ('book_id', '=', self.book_id.id),
            ('status', '=', 'approved'),
            ('booking_date', '<=', self.expiry_date),
            ('expiry_date', '>=', self.booking_date),
        ])

    
    # VALIDATE & APPROVE BUTTON
    def action_validate_approve(self):
        for record in self:
            overlapping = record._get_overlapping_bookings() 
            total_copies = record.book_id.no_of_copies or 0

            # If available copies exist
            if len(overlapping) < total_copies:

                vals = {'status': 'approved',}

                if not record.issued_by:
                    vals['issued_by'] = self.env.user.id

                record.write(vals)

            else:
                # Copies fully occupied → Open conflict wizard
                return {
                    'name': 'Booking Conflict Detected',
                    'type': 'ir.actions.act_window',
                    'res_model': 'booking.conflict.wizard',
                    'view_mode': 'form',
                    'target': 'new',
                    'context': {
                        'default_booking_id': record.id,
                
                    }
                }


    available_slot_html = fields.Html(string="Available Slots (Email)")

 
    @api.model
    def load_demo_bookings(self):

        books = self.env['book.books'].search([], limit=20)
        admin = self.env.ref('base.user_admin')

        if not books:
            _logger.warning("No books found — skipping demo bookings.")
            return

        today = datetime.now()

        DEMO_BOOKINGS = [
            {'book_idx': 0, 'days_ago': 40, 'duration': 10, 'status': 'returned'},
            {'book_idx': 1, 'days_ago': 35, 'duration': 7,  'status': 'returned'},
            {'book_idx': 2, 'days_ago': 30, 'duration': 12, 'status': 'returned'},
            {'book_idx': 3, 'days_ago': 25, 'duration': 10, 'status': 'approved'},
            {'book_idx': 4, 'days_ago': 20, 'duration': 8,  'status': 'approved'},
            {'book_idx': 5, 'days_ago': 15, 'duration': 7,  'status': 'approved'},
            {'book_idx': 6, 'days_ago': 10, 'duration': 6,  'status': 'pending'},
            {'book_idx': 7, 'days_ago': 8,  'duration': 5,  'status': 'pending'},
            {'book_idx': 8, 'days_ago': 5,  'duration': 4,  'status': 'pending'},
            {'book_idx': 9, 'days_ago': 2,  'duration': 7,  'status': 'draft'},
        ]


        for entry in DEMO_BOOKINGS:

            idx = entry['book_idx']

            if idx >= len(books):
                continue

            book = books[idx]

            booking_date = today - timedelta(days=entry['days_ago'])
            expiry_date = booking_date + timedelta(days=entry['duration'])


            existing = self.search([
                ('book_id', '=', book.id),
                ('status', '=', entry['status'])
            ], limit=1)

            if existing:
                _logger.info(f"Skipping booking for '{book.name}' — already exists.")
                continue


            vals = {
                'book_id': book.id,
                'booking_date': booking_date,
                'expiry_date': expiry_date,
                'status': entry['status'],
                'assign_to': admin.id,
                'issued_by': admin.id,
            }


            if entry['status'] == 'returned':
                vals['received_by'] = admin.id


            self.create(vals)


    def action_send_return_reminder(self):
        today = fields.Datetime.now()

        # Get all expired bookings
        expired_bookings = self.search([
            ('status', '=', 'approved'),
            ('expiry_date', '<=', today)
        ])

        # Group bookings by partner
        bookings_by_partner = defaultdict(list)
        for booking in expired_bookings:
            if booking.partner_id.email:
                bookings_by_partner[booking.partner_id.id].append(booking)

        template = self.env.ref(
            'wk_library_management.mail_template_booking_reminder',
            raise_if_not_found=True
        )

        for partner_id, bookings in bookings_by_partner.items():

            ctx = {
                'default_bookings': bookings
            }

            template.with_context(ctx).send_mail(
                bookings[0].id,
                force_send=True
            )