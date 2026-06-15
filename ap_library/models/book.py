from odoo import models, fields,api
from odoo.exceptions import ValidationError
import base64
import requests
import logging

_logger = logging.getLogger(__name__)

class Book(models.Model):
    _name='book.books'
    _description="Books"


    name=fields.Char(string="Name",required=True)
    image=fields.Image(string="Image")
    isbn=fields.Char(string="ISBN", required=True)
    description=fields.Text(string="Description")
    no_of_copies=fields.Integer(string="Copies")
    availability=fields.Boolean(string="Availability",default=False,)

    is_favorite=fields.Boolean(string='Favorite',default=False)

    author_ids=fields.Many2many("res.partner",string="Authors")
    responsible=fields.Many2one("res.users",string="Responsible")
    category_ids = fields.Many2many(
        'book.category',
        'books_category_rel',  
        'book_id',              
        'category_id',          
        string="Categories"
    )
    history_ids=fields.One2many("booking.history","book_id",string="Booking History")
   

    #  Decorator => No two isbn same
    @api.constrains("isbn")
    def check_unique_isbn(self):
        for r in self:            
            if r.isbn:
                existing=self.search([
                    ('isbn','=',r.isbn),
                    ('id','!=',r.id)
                ])

                if existing:
                    raise ValidationError("ISBN must be unique.")
            

   

    def action_request_books(self):
        self.ensure_one()

        if self.no_of_copies <= 0:
            raise ValidationError("Book is not available.")
        
        active_booking=self.env['booking.history'].search([('book_id','=',self.id),('assign_to','=',self.env.user.id),('status','in',['pending','approved','draft'])])
        if active_booking:
            raise ValidationError("Already active booking for this book")
        
        return {
            'name': f"Request Book: {self.name}",
            'type': 'ir.actions.act_window',
            'res_model': 'booking.history',
            'view_mode': 'form',
            'target': 'new',  
            'context': {
                'default_book_id': self.id,
                # 'default_user_id': self.env.user.id,
                'default_assign_to': self.env.user.id,
                'default_booking_date': fields.Datetime.now(),
                'default_partner_id': self.env.user.partner_id.id,
                'hide_header':True,
                'redonly_book':True,
                'auto_pending':True,
                
            }
        }


    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            copies = vals.get("no_of_copies", 0)
            vals["availability"] = copies > 0
        return super().create(vals_list)

    
    #  for user open wizard

    def action_request_books_user(self):
        self.ensure_one()

        
        active_booking=self.env['booking.history'].search([('book_id','=',self.id),('assign_to','=',self.env.user.id),('status','in',['pending','approved','draft'])])
        if active_booking:
            raise ValidationError("Already active booking for this book")
        
        return{
            'name':f"Requested Book :{self.name}",
            'type':'ir.actions.act_window',
            'res_model':'book.issue.wizard',
            'view_mode':'form',
            'view_id':self.env.ref('wk_library_management.book_issued_request_wizard_form').id,
            'target':'new',
            'context':{
                'default_book_id':self.id,
                'default_assign_to':self.env.user.id
            }
        }
    

    def _fetch_book_cover(self, isbn):
        try:
            url = f"https://covers.openlibrary.org/b/isbn/{isbn}-L.jpg"
            response = requests.get(url, timeout=10)

            if response.status_code == 200:
                return base64.b64encode(response.content)

        except Exception as e:
            _logger.warning(f"Failed to fetch image for ISBN {isbn}: {e}")

        return False


    @api.model
    def load_demo_books(self):
        admin_user = self.env.ref('base.user_admin')

        def get_or_create_author(name):

            partner = self.env['res.partner'].search([('name', '=', name)], limit=1)

            if not partner:
                partner = self.env['res.partner'].create({
                    'name': name,
                    'is_company': False,
                })

            return partner


        DEMO_BOOKS = [
            {"name":"Python Programming Basics","isbn":"9780134853987","description":"Introduction to Python covering syntax, logic and programming concepts.","no_of_copies":6,"availability":True,"is_favorite":True,"authors":["John Smith"],"categories":["Education"]},

            {"name":"Deep Space Journey","isbn":"9780553382563","description":"Sci-fi adventure exploring distant galaxies and alien civilizations.","no_of_copies":5,"availability":True,"authors":["Arthur Clarke"],"categories":["Science Fiction"]},

            {"name":"Secrets of the Lost Kingdom","isbn":"9780671023379","description":"Fantasy quest with dragons, magic and ancient kingdoms.","no_of_copies":7,"availability":True,"authors":["Emily Carter"],"categories":["Fantasy","Adventure"]},

            {"name":"The Political Mind","isbn":"9780143127741","description":"Explains how politics shapes societies and human thinking.","no_of_copies":4,"availability":True,"authors":["David Brown"],"categories":["Politics & Society"]},

            {"name":"Love Beyond Time","isbn":"9780312600000","description":"Romantic story about love surviving across generations.","no_of_copies":3,"availability":True,"authors":["Sophia Wilson"],"categories":["Romance"]},

            {"name":"Mystery of Silent Lake","isbn":"9780307743657","description":"A detective investigates strange events in a quiet town.","no_of_copies":5,"availability":True,"authors":["Robert King"],"categories":["Mystery & Thriller"]},

            {"name":"History of Ancient Empires","isbn":"9780192802071","description":"A journey through the rise and fall of great civilizations.","no_of_copies":4,"availability":True,"authors":["Michael Grant"],"categories":["Historical Fiction"]},

            {"name":"Machine Learning Guide","isbn":"9781491957660","description":"Practical introduction to machine learning concepts.","no_of_copies":6,"availability":True,"authors":["Andrew Miller"],"categories":["Education"]},

            {"name":"Island Adventure","isbn":"9780061120084","description":"Group of explorers uncover hidden treasures on an island.","no_of_copies":5,"availability":True,"authors":["Laura Scott"],"categories":["Adventure"]},

            {"name":"Future Cities","isbn":"9780525533033","description":"Imagining cities powered by futuristic technology.","no_of_copies":3,"availability":True,"authors":["Daniel Brooks"],"categories":["Science Fiction"]},

            {"name":"Philosophy of Life","isbn":"9780140449334","description":"Thought provoking ideas about life and human existence.","no_of_copies":4,"availability":True,"authors":["Marcus Aurelius"],"categories":["Philosophy"]},

            {"name":"The Final Clue","isbn":"9780062073488","description":"Detective story filled with suspense and unexpected twists.","no_of_copies":6,"availability":True,"authors":["Agatha Hill"],"categories":["Mystery & Thriller"]},

            {"name":"Romantic Escapes","isbn":"9781250189967","description":"Stories about love, emotions and relationships.","no_of_copies":5,"availability":True,"authors":["Anna Taylor"],"categories":["Romance"]},

            {"name":"Journey Through Time","isbn":"9780345339683","description":"Adventure of a scientist traveling across centuries.","no_of_copies":4,"availability":True,"authors":["Samuel Reed"],"categories":["Science Fiction"]},

            {"name":"Legends of the Dragon","isbn":"9780545582957","description":"Epic fantasy story about dragons and brave warriors.","no_of_copies":7,"availability":True,"authors":["Liam Knight"],"categories":["Fantasy"]},

            {"name":"World War Chronicles","isbn":"9780307387899","description":"Historical accounts of global conflicts and heroes.","no_of_copies":4,"availability":True,"authors":["Peter Johnson"],"categories":["Historical Fiction"]},

            {"name":"Modern Political Systems","isbn":"9780198700616","description":"Explains how modern governments function worldwide.","no_of_copies":3,"availability":True,"authors":["Kevin Parker"],"categories":["Politics & Society"]},

            {"name":"Data Science Essentials","isbn":"9781491912058","description":"Covers statistics, data analysis and visualization.","no_of_copies":6,"availability":True,"authors":["Rachel Adams"],"categories":["Education"]},

            {"name":"Hidden Jungle Temple","isbn":"9780439064873","description":"Adventurers uncover secrets in an ancient jungle temple.","no_of_copies":5,"availability":True,"authors":["Victor Lane"],"categories":["Adventure"]},

            {"name":"Stars Beyond Galaxy","isbn":"9780765377067","description":"Space exploration mission discovering new planets.","no_of_copies":5,"availability":True,"authors":["Neil Harper"],"categories":["Science Fiction"]},
        ]


        for book_data in DEMO_BOOKS:

            existing = self.search([('isbn', '=', book_data['isbn'])], limit=1)

            if existing:
                continue


            author_ids = []
            for author_name in book_data.pop('authors'):
                author = get_or_create_author(author_name)
                author_ids.append(author.id)


            category_ids = []
            for cat_name in book_data.pop('categories'):

                category = self.env['book.category'].search(
                    [('name', '=', cat_name)], limit=1
                )

                if category:
                    category_ids.append(category.id)


            image_b64 = self._fetch_book_cover(book_data['isbn'])


            vals = {
                **book_data,
                'author_ids': [(6, 0, author_ids)],
                'category_ids': [(6, 0, category_ids)],
                'responsible': admin_user.id,
            }


            if image_b64:
                vals['image'] = image_b64


            self.create(vals)


    def _get_report_values(self, docids, data=None):
        books = self.env['book.books'].browse(docids)
        return {
            'docs': books,
        }

