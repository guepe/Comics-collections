from odoo import Command, models, fields, _
from odoo.exceptions import UserError
from odoo.tools import html2plaintext


class ComicEdition(models.Model):
    _inherit = "comic.edition"

    product_tmpl_id = fields.Many2one(
        "product.template",
        string="Produit",
        ondelete="set null",
        copy=False,
        help="Produit Odoo associé à cette édition pour la vente en ligne et en caisse.",
    )
    customer_album_ids = fields.One2many(
        "comic.customer.album",
        "edition_id",
        string="Bibliothèques",
        help="Entrées de bibliothèque (clients et utilisateurs) qui possèdent ou suivent cet album.",
    )
    sync_product = fields.Boolean(
        string="Synchro auto",
        default=True,
        help="Si activé, les modifications de l'édition (couverture, synopsis, ...) se répercutent "
        "automatiquement sur le produit lié.",
    )

    # --- Actions boutons ----------------------------------------------------

    def action_create_product(self):
        self.ensure_one()
        if self.product_tmpl_id:
            raise UserError(_("Cette édition est déjà liée à un produit."))
        if self.work_id.a_valider:
            raise UserError(_("Album à valider avant mise en vente."))

        category = self.env.ref("comic_shop.product_category_bd", raise_if_not_found=False)
        pos_category = self.env.ref("comic_shop.pos_category_bd", raise_if_not_found=False)
        vals = {
            "name": self._get_product_name(),
            "type": "consu",
            "comic_edition_id": self.id,
            "categ_id": category.id if category else False,
            "available_in_pos": True,
        }
        if pos_category:
            vals["pos_categ_ids"] = [Command.link(pos_category.id)]
        product = self.env["product.template"].create(vals)
        self.product_tmpl_id = product
        self._sync_to_product()

        return {
            "type": "ir.actions.act_window",
            "res_model": "product.template",
            "res_id": product.id,
            "view_mode": "form",
            "target": "current",
        }

    # --- Création depuis le portail client ----------------------------------

    def _create_from_portal_data(self, data, partner, cover_fetcher=None):
        """Find or create the editeur/serie/work/edition/isbn proposed by a portal customer.

        ``data`` is already cleaned by the controller: ``title``, ``serie_name``,
        ``editeur_name``, ``isbn`` (valid ISBN-13 or empty), ``tome`` (int) and
        ``cover_url``. ``cover_fetcher`` is called with ``cover_url`` only when a new
        edition is created and must return base64 image data or None.

        Records created here (not the reused ones) are flagged ``a_valider`` and linked
        to ``partner``; a To-Do activity is scheduled for the shop managers on each
        newly created album. Must be called in sudo (portal user).
        """
        title = (data.get("title") or "").strip()
        if not title:
            return None
        isbn = data.get("isbn") or ""
        serie_name = (data.get("serie_name") or "").strip()
        editeur_name = (data.get("editeur_name") or "").strip()
        cover_url = (data.get("cover_url") or "").strip()
        tome = data.get("tome") or 0

        env = self.env
        moderation_vals = {"a_valider": True, "portal_partner_id": partner.id if partner else False}

        # Editeur
        editeur = None
        if editeur_name:
            editeur = env["comic.editeur"].search([("name", "=", editeur_name)], limit=1)
            if not editeur:
                editeur = env["comic.editeur"].create(dict(moderation_vals, name=editeur_name))

        # Série
        serie = None
        if serie_name:
            serie = env["comic.serie"].search([("name", "=", serie_name)], limit=1)
            if not serie:
                serie = env["comic.serie"].create(dict(moderation_vals, name=serie_name))

        # Work
        work = None
        if serie and tome:
            work = env["comic.work"].search([("serie_id", "=", serie.id), ("tome", "=", tome)], limit=1)
        if not work and serie:
            work = env["comic.work"].search([("serie_id", "=", serie.id), ("titre_canonique", "=", title)], limit=1)
        if not work:
            work_vals = dict(moderation_vals, titre_canonique=title)
            if serie:
                work_vals["serie_id"] = serie.id
            if tome:
                work_vals["tome"] = tome
            work = env["comic.work"].create(work_vals)
            work._schedule_portal_validation_activity()

        # Edition
        edition = env["comic.edition"].search([("work_id", "=", work.id)], limit=1)
        if not edition:
            edition_vals = {"work_id": work.id}
            if editeur:
                edition_vals["editeur_id"] = editeur.id
            if cover_url and cover_fetcher:
                cover = cover_fetcher(cover_url)
                if cover:
                    edition_vals["image_couverture"] = cover
            edition = env["comic.edition"].create(edition_vals)

        # ISBN
        if isbn:
            if not env["comic.isbn"].search([("isbn_13", "=", isbn)], limit=1):
                env["comic.isbn"].create({"edition_id": edition.id, "isbn_13": isbn})

        return edition

    def action_view_product(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "res_model": "product.template",
            "res_id": self.product_tmpl_id.id,
            "view_mode": "form",
            "target": "current",
        }

    def action_unlink_product(self):
        self.ensure_one()
        if self.product_tmpl_id:
            self.product_tmpl_id.comic_edition_id = False
        self.product_tmpl_id = False

    def action_resync_product(self):
        self.ensure_one()
        if not self.product_tmpl_id:
            raise UserError(_("Aucun produit lié à cette édition."))
        self._sync_to_product()

    # --- Auto-sync on write -------------------------------------------------

    _SYNC_TRIGGER_FIELDS = {"image_couverture", "synopsis", "editeur_id", "isbn_ids", "work_id"}

    def write(self, vals):
        res = super().write(vals)
        if self._SYNC_TRIGGER_FIELDS & set(vals):
            self._auto_sync_products()
        return res

    def _auto_sync_products(self):
        """Sync linked products (editions with sync_product enabled only)."""
        for edition in self.filtered(lambda e: e.product_tmpl_id and e.sync_product):
            edition._sync_to_product()

    # --- Helpers ------------------------------------------------------------

    def _sync_to_product(self):
        self.ensure_one()
        if not self.product_tmpl_id:
            return
        pos_category = self.env.ref("comic_shop.pos_category_bd", raise_if_not_found=False)
        vals = {
            "name": self._get_product_name(),
            "image_1920": self.image_couverture or False,
            "description_sale": html2plaintext(self.synopsis) if self.synopsis else False,
            # available_in_pos n'est fixé qu'à la création du produit : le commerçant
            # doit pouvoir retirer un album de la caisse sans que la synchro le remette.
        }
        isbn = self._get_primary_isbn()
        if isbn:
            # Pas d'ISBN → on garde le code-barres éventuellement saisi à la main
            vals["barcode"] = isbn
        if pos_category and pos_category not in self.product_tmpl_id.pos_categ_ids:
            vals["pos_categ_ids"] = [Command.link(pos_category.id)]
        self.product_tmpl_id.write(vals)

    def _get_product_name(self):
        work = self.work_id
        parts = []
        if work.serie_id:
            parts.append(work.serie_id.name)
        if work.titre_canonique:
            parts.append(work.titre_canonique)
        name = " — ".join(parts) if parts else _("Édition BD")
        if work.tome:
            name = f"{name} (T{work.tome})"
        return name
