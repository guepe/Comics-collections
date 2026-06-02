from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class ComicIsbn(models.Model):
    _name = "comic.isbn"
    _description = "ISBN d'une édition BD"
    _rec_name = "isbn_13"

    edition_id = fields.Many2one("comic.edition", string="Édition", required=True, ondelete="cascade", index=True)
    isbn_13 = fields.Char(string="ISBN-13 (EAN-13)")
    isbn_10 = fields.Char(string="ISBN-10")

    _unique_isbn13 = models.Constraint(
        "UNIQUE(isbn_13)",
        "Cet ISBN-13 est déjà enregistré pour une autre édition.",
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            self._normalize_isbn_vals(vals)
        return super().create(vals_list)

    def write(self, vals):
        self._normalize_isbn_vals(vals)
        return super().write(vals)

    @staticmethod
    def _normalize_isbn_vals(vals):
        for field in ("isbn_13", "isbn_10"):
            if vals.get(field):
                vals[field] = vals[field].replace("-", "").replace(" ", "")

    @api.constrains("isbn_13")
    def _check_isbn_13(self):
        for rec in self:
            if rec.isbn_13 and not self._validate_ean13(rec.isbn_13):
                raise ValidationError(_('"%s" n\'est pas un EAN-13 valide.') % rec.isbn_13)

    @api.constrains("isbn_10")
    def _check_isbn_10(self):
        for rec in self:
            if rec.isbn_10 and not self._validate_isbn10(rec.isbn_10):
                raise ValidationError(_('"%s" n\'est pas un ISBN-10 valide.') % rec.isbn_10)

    @staticmethod
    def _validate_ean13(isbn):
        isbn = isbn.replace("-", "").replace(" ", "")
        if len(isbn) != 13 or not isbn.isdigit():
            return False
        total = sum(int(d) * (1 if i % 2 == 0 else 3) for i, d in enumerate(isbn[:12]))
        return (10 - total % 10) % 10 == int(isbn[12])

    @staticmethod
    def _validate_isbn10(isbn):
        isbn = isbn.replace("-", "").replace(" ", "")
        if len(isbn) != 10 or not isbn[:9].isdigit():
            return False
        check = isbn[9]
        if not (check.isdigit() or check.upper() == "X"):
            return False
        total = sum(int(d) * (10 - i) for i, d in enumerate(isbn[:9]))
        check_val = 10 if check.upper() == "X" else int(check)
        return (total + check_val) % 11 == 0
