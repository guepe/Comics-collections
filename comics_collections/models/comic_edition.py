from odoo import api, fields, models

_PURCHASE_LINK_TEMPLATES = {
    "url_club_be": "https://www.librairieclub.be/c/search?filter=search({isbn})&page=1&page_size=24&sort=RelevanceClub&sort_type=desc",  # noqa: E501
    "url_amazon_be": "https://www.amazon.com.be/s?k={isbn}",
    "url_fnac_be": "https://www.fnac.be/SearchResult/ResultList.aspx?Search={isbn}&sft=2",
}


class ComicEdition(models.Model):
    _name = "comic.edition"
    _description = "Comic work edition"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "work_id, date_parution"
    # Sans champ « name » : rechercher par titre / série de l'album ou par ISBN
    _rec_names_search = ["work_id.titre_canonique", "work_id.serie_id.name", "isbn_ids.isbn_13"]

    work_id = fields.Many2one(
        "comic.work", string="Work", required=True, ondelete="restrict", index=True, tracking=True
    )
    editeur_id = fields.Many2one("comic.editeur", string="Publisher", tracking=True)
    date_parution = fields.Date(string="Release date", tracking=True)
    date_depot_legal = fields.Date(string="Legal deposit")
    langue = fields.Selection(
        [
            ("fr", "French"),
            ("nl", "Dutch"),
            ("en", "English"),
            ("de", "German"),
            ("autre", "Other"),
        ],
        string="Language",
        default="fr",
        tracking=True,
    )
    format = fields.Selection(
        [
            ("broche", "Paperback"),
            ("cartonne", "Hardcover"),
            ("integrale", "Omnibus"),
            ("collector", "Collector's edition"),
            ("numerique", "Digital"),
            ("autre", "Other"),
        ],
        default="cartonne",
        tracking=True,
    )
    image_couverture = fields.Image(string="Cover")
    synopsis = fields.Html()
    nb_pages = fields.Integer(string="Number of pages")
    url_club_be = fields.Char(string="Club.be link")
    url_amazon_be = fields.Char(string="Amazon.be link")
    url_fnac_be = fields.Char(string="FNAC.be link")
    isbn_ids = fields.One2many("comic.isbn", "edition_id", string="ISBNs")
    customer_album_ids = fields.One2many(
        "comic.customer.album",
        "edition_id",
        string="Libraries",
        help="Library entries (customers and users) that own or follow this album.",
    )
    pret_ids = fields.One2many(
        "comic.pret",
        "edition_id",
        string="Loans",
        help="Loans of this album (private: access rules only show your own).",
    )
    active = fields.Boolean(default=True)

    nb_isbn = fields.Integer(string="Number of ISBNs", compute="_compute_nb_isbn", store=True)

    @api.depends("isbn_ids")
    def _compute_nb_isbn(self):
        for rec in self:
            rec.nb_isbn = len(rec.isbn_ids)

    def _compute_display_name(self):
        langue_labels = dict(self._fields["langue"]._description_selection(self.env))
        for rec in self:
            work_name = rec.work_id.display_name if rec.work_id else "?"
            parts = []
            if rec.langue:
                parts.append(langue_labels.get(rec.langue, rec.langue))
            if rec.editeur_id:
                parts.append(rec.editeur_id.name)
            if rec.date_parution:
                parts.append(str(rec.date_parution.year))
            suffix = f" ({' — '.join(parts)})" if parts else ""
            rec.display_name = f"{work_name}{suffix}"

    @staticmethod
    def _build_purchase_links(isbn):
        if not isbn:
            return {}
        return {field: tpl.format(isbn=isbn) for field, tpl in _PURCHASE_LINK_TEMPLATES.items()}

    def _get_primary_isbn(self):
        self.ensure_one()
        # Ordre déterministe : le plus ancien ISBN-13 enregistré (par id).
        isbns = self.isbn_ids.filtered("isbn_13").sorted("id")
        return isbns[:1].isbn_13 or False

    def action_generate_purchase_links(self):
        for edition in self:
            isbn = edition._get_primary_isbn()
            links = self._build_purchase_links(isbn)
            if links:
                edition.write(links)

    @api.model
    def _cron_fill_missing_purchase_links(self):
        missing_domain = [
            "|",
            "|",
            ("url_club_be", "in", [False, ""]),
            ("url_amazon_be", "in", [False, ""]),
            ("url_fnac_be", "in", [False, ""]),
        ]
        for edition in self.search(missing_domain):
            isbn = edition._get_primary_isbn()
            if not isbn:
                continue
            links = self._build_purchase_links(isbn)
            to_write = {f: u for f, u in links.items() if not getattr(edition, f)}
            if to_write:
                edition.write(to_write)
