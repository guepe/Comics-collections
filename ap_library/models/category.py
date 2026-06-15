from odoo import models, fields,api

import base64
import requests
import logging
_logger = logging.getLogger(__name__)


class BookCategory(models.Model):
    _name="book.category"
    _description="Books Category"

    name=fields.Char(string="Name" , required=True)
    image=fields.Image(string="Image")
    description=fields.Text(string="Description")

    parent_id=fields.Many2one("book.category",string="Parent")
    book_ids = fields.Many2many(
        'book.books',
        'books_category_rel',
        'category_id',
        'book_id',
        string="Books"
    )

    count_book = fields.Integer(
        string="No of Books",
        compute="_compute_count_book",
        store=True
    )

    @api.depends('book_ids')
    def _compute_count_book(self):
        for rec in self:
            rec.count_book = len(rec.book_ids)

    def action_view_books(self):
        self.ensure_one()
        return {
            'name': f"Total no of Books belongs to {self.name} is :{self.count_book}",
            'type': 'ir.actions.act_window',
            'res_model': 'book.books',
            'view_mode': 'list,form',
            'domain': [('id', 'in', self.book_ids.ids)],
            'target': 'new',
            'context': {
            'create': False,
            'edit': False,
        },
        }
    


    @api.model
    def load_demo_categories(self):

        CATEGORIES = [
            {
                'name': 'Classic Literature',
                'description': 'Timeless literary works studied across generations. These books explore deep human emotions and social themes.',
                'isbn': '9780140449136'
            },
            {
                'name': 'Fantasy',
                'description': 'Magical worlds filled with mythical creatures, powerful wizards and epic adventures.',
                'isbn': '9780547928227'
            },
            {
                'name': 'Science Fiction',
                'description': 'Stories based on futuristic science, advanced technology and space exploration.',
                'isbn': '9780441013593'
            },
            {
                'name': 'Mystery & Thriller',
                'description': 'Suspenseful stories involving crimes, investigations and unexpected twists.',
                'isbn': '9780307474278'
            },
            {
                'name': 'Historical Fiction',
                'description': 'Fictional stories set in historical settings with real world cultural context.',
                'isbn': '9781501125927'
            },
        ]

        for cat in CATEGORIES:

            existing = self.search([('name', '=', cat['name'])], limit=1)

            if existing:
                _logger.info(f"Skipping category '{cat['name']}' — already exists.")
                continue

            image_base64 = False

            try:
                url = f"https://covers.openlibrary.org/b/isbn/{cat['isbn']}-L.jpg"
                response = requests.get(url)

                if response.status_code == 200:
                    image_base64 = base64.b64encode(response.content)

            except Exception as e:
                _logger.warning(f"Image download failed for {cat['name']} : {e}")

            vals = {
                'name': cat['name'],
                'description': cat['description'],
                'image': image_base64,
            }

            self.create(vals)

    
