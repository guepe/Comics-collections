import base64
import logging
import re

import requests

from odoo import api, fields, models

_logger = logging.getLogger(__name__)

# Patterns de fallback pour extraire un numéro de tome depuis un titre brut
_TOME_PATTERNS = re.compile(
    r"(?:tome|t\.?|vol(?:ume)?\.?|n°|#)\s*\.?\s*(\d{1,3})",
    re.IGNORECASE,
)


def _extract_tome_fallback(title: str):
    m = _TOME_PATTERNS.search(title or "")
    return int(m.group(1)) if m else None


def _normalize_isbn(isbn: str) -> str:
    """Normalise un ISBN : supprime tirets/espaces, convertit ISBN-10 → ISBN-13."""
    raw = re.sub(r"[\-\s]", "", isbn or "")
    if len(raw) == 10 and raw[:9].isdigit():
        base = "978" + raw[:9]
        total = sum(int(d) * (1 if i % 2 == 0 else 3) for i, d in enumerate(base))
        check = (10 - total % 10) % 10
        return base + str(check)
    return raw


def _normalize_title(title: str) -> str:
    """Titre en minuscules, sans ponctuation, pour comparaison floue."""
    return re.sub(r"\W+", " ", (title or "").lower()).strip()


class ComicSerieMissingWizard(models.TransientModel):
    _name = "comic.serie.missing.wizard"
    _description = "Détection des tomes manquants dans une série"

    serie_id = fields.Many2one("comic.serie", required=True, readonly=True)
    state = fields.Selection(
        [("confirm", "Confirmation"), ("results", "Résultats"), ("done", "Terminé")],
        default="confirm",
    )
    nb_existing = fields.Integer(compute="_compute_nb_existing")
    line_ids = fields.One2many("comic.serie.missing.line", "wizard_id", string="Tomes manquants")
    nb_missing = fields.Integer(compute="_compute_nb_missing")
    import_report = fields.Html(readonly=True)

    @api.depends("serie_id.work_ids")
    def _compute_nb_existing(self):
        for rec in self:
            rec.nb_existing = len(rec.serie_id.work_ids)

    @api.depends("line_ids")
    def _compute_nb_missing(self):
        for rec in self:
            rec.nb_missing = len(rec.line_ids)

    # ── Recherche ──────────────────────────────────────────────────────────────

    def action_search(self):
        self.ensure_one()
        from ..sources.google_books import GoogleBooksSource
        from ..sources.bnf import BnfSource

        serie_name = self.serie_id.name

        # --- Données existantes (3 axes de déduplication) ---
        existing_works = self.serie_id.work_ids
        existing_tomes = {t for t in existing_works.mapped("tome") if t}
        existing_isbns = {
            _normalize_isbn(isbn.isbn_13)
            for work in existing_works
            for edition in work.edition_ids
            for isbn in edition.isbn_ids
            if isbn.isbn_13
        }
        existing_titles = {_normalize_title(w.titre_canonique) for w in existing_works if w.titre_canonique}

        # candidates: tome -> {'name', 'isbn', 'cover_url', 'date_parution', 'source'}
        candidates = {}

        # --- Google Books (paginé jusqu'au total réel, max 200) ---
        google_source = GoogleBooksSource(env=self.env)
        for item in self._fetch_google_all(google_source, serie_name, max_total=200):
            self._process_google_item(
                item,
                google_source,
                serie_name,
                existing_tomes,
                existing_isbns,
                existing_titles,
                candidates,
            )

        # --- BnF (par champ série) ---
        bnf_source = BnfSource(env=self.env)
        for result in self._fetch_bnf(bnf_source, serie_name):
            tome = result.tome
            norm_isbn = _normalize_isbn(result.isbn) if result.isbn else None
            if not tome or tome in existing_tomes:
                continue
            if norm_isbn and norm_isbn in existing_isbns:
                continue
            if result.title and _normalize_title(result.title) in existing_titles:
                continue
            if tome not in candidates:
                candidates[tome] = {
                    "name": result.title or f"{serie_name} - Tome {tome}",
                    "isbn": norm_isbn or "",
                    "cover_url": None,
                    "date_parution": result.date_parution,
                    "source": "bnf",
                }

        # --- Vérification globale ISBN (une requête pour tous les candidats) ---
        candidate_isbns = [c["isbn"] for c in candidates.values() if c.get("isbn")]
        if candidate_isbns:
            already_in_db = self.env["comic.isbn"].search_read(
                [("isbn_13", "in", candidate_isbns)],
                ["isbn_13"],
            )
            db_isbns = {_normalize_isbn(r["isbn_13"]) for r in already_in_db if r.get("isbn_13")}
            candidates = {
                t: c for t, c in candidates.items() if not (c.get("isbn") and _normalize_isbn(c["isbn"]) in db_isbns)
            }

        # --- Vérification complémentaire pour les candidats SANS ISBN ---
        # Google Books/BnF ne retournent pas toujours un ISBN.
        # On filtre par titre (souple) contre les albums existants dans la série.
        no_isbn = [t for t, c in candidates.items() if not c.get("isbn")]
        if no_isbn:
            # Titres existants : mots de ≥3 chars pour éviter les faux positifs
            existing_words = {
                word
                for w in existing_works
                if w.titre_canonique
                for word in re.findall(r"\w{3,}", w.titre_canonique.lower())
            }
            for t in no_isbn:
                cand_words = set(re.findall(r"\w{3,}", candidates[t]["name"].lower()))
                if cand_words and existing_words:
                    overlap = len(cand_words & existing_words) / len(cand_words)
                    if overlap >= 0.6:
                        del candidates[t]
                        continue
                # Marque comme non-vérifié (ISBN absent) pour alerter l'utilisateur
                candidates[t]["isbn_unverified"] = True

        # --- Stubs pour les tomes attendus mais introuvables ---
        if self.serie_id.nb_works_total:
            for t in range(1, self.serie_id.nb_works_total + 1):
                if t not in existing_tomes and t not in candidates:
                    candidates[t] = {
                        "name": f"{serie_name} - Tome {t}",
                        "isbn": "",
                        "cover_url": None,
                        "date_parution": None,
                        "source": "expected",
                    }

        # --- Création des lignes ---
        self.line_ids.unlink()
        lines = []
        for tome in sorted(candidates.keys()):
            c = candidates[tome]
            cover_data = self._fetch_cover(c["cover_url"]) if c["cover_url"] else False
            lines.append(
                {
                    "wizard_id": self.id,
                    "tome": tome,
                    "name": c["name"],
                    "isbn": c["isbn"],
                    "isbn_unverified": bool(c.get("isbn_unverified")),
                    "cover_data": cover_data,
                    "date_parution": self._parse_date(c["date_parution"]),
                    "selected": True,
                    "source": c["source"],
                }
            )
        if lines:
            self.env["comic.serie.missing.line"].create(lines)

        self.state = "results"
        return self._reopen()

    def _fetch_google_all(self, source, serie_name, max_total=200):
        """Génère tous les items Google Books pour une série, en paginant."""
        # Détermine la meilleure requête (avec guillemets si possible)
        query = None
        for q in [f'intitle:"{serie_name}"', f"intitle:{serie_name}"]:
            data = source._fetch({"q": q, "maxResults": 1, "startIndex": 0})
            if (data or {}).get("totalItems", 0) > 0:
                query = q
                total = min(data["totalItems"], max_total)
                break
        if not query:
            return

        _logger.info('Google Books série "%s" : %d résultats au total', serie_name, total)
        start = 0
        while start < total:
            data = source._fetch({"q": query, "maxResults": 40, "startIndex": start})
            items = (data or {}).get("items", [])
            if not items:
                break
            yield from items
            start += len(items)
            if len(items) < 40:
                break

    def _process_google_item(
        self, item, source, serie_name, existing_tomes, existing_isbns, existing_titles, candidates
    ):
        try:
            parsed = source._parse_volume(item)
        except Exception:
            return
        if not parsed:
            return

        raw_title = item.get("volumeInfo", {}).get("title", "")

        if not self._title_relates_to_serie(raw_title, parsed.serie_name, serie_name):
            return

        norm_isbn = _normalize_isbn(parsed.isbn) if parsed.isbn else None

        tome = parsed.tome or _extract_tome_fallback(raw_title)
        if not tome or tome in existing_tomes or tome > 999:
            return
        if norm_isbn and norm_isbn in existing_isbns:
            return
        candidate_title = parsed.title or raw_title
        if _normalize_title(candidate_title) in existing_titles:
            return
        if tome not in candidates:
            candidates[tome] = {
                "name": candidate_title,
                "isbn": norm_isbn or "",
                "cover_url": parsed.cover_url_small or parsed.cover_url,
                "date_parution": parsed.date_parution,
                "source": "google",
            }

    def _fetch_bnf(self, source, serie_name):
        try:
            return source.search_by_serie(serie_name)
        except Exception as e:
            _logger.warning("BnF serie search failed: %s", e)
            return []

    def _title_relates_to_serie(self, raw_title, parsed_serie_name, expected_serie):
        expected = expected_serie.lower()
        if expected in raw_title.lower():
            return True
        if parsed_serie_name:
            pn = parsed_serie_name.lower()
            if expected in pn or pn in expected:
                return True
        # Chevauchement de mots (min 3 chars pour éviter les faux positifs)
        words_e = set(re.findall(r"\w{3,}", expected))
        words_t = set(re.findall(r"\w{3,}", raw_title.lower()))
        if words_e and len(words_e & words_t) / len(words_e) >= 0.5:
            return True
        return False

    def _fetch_cover(self, url):
        if not url:
            return False
        try:
            resp = requests.get(url, timeout=8)
            if resp.status_code == 200 and len(resp.content) > 100:
                return base64.b64encode(resp.content).decode()
        except Exception as e:
            _logger.debug("Cover fetch failed: %s", e)
        return False

    def _parse_date(self, date_str):
        if not date_str:
            return False
        try:
            from datetime import date

            parts = str(date_str)[:10].split("-")
            return date(int(parts[0]), int(parts[1]), int(parts[2]))
        except Exception:
            return False

    # ── Actions ────────────────────────────────────────────────────────────────

    def action_add_to_wishlist(self):
        self.ensure_one()
        selected = self.line_ids.filtered("selected")
        added = []
        for line in selected:
            isbn = _normalize_isbn(line.isbn) if line.isbn else False
            isbn_rec = self.env["comic.isbn"].search([("isbn_13", "=", isbn)], limit=1) if isbn else False

            if isbn_rec:
                edition = isbn_rec.edition_id
                work = edition.work_id
                missing_vals = {}
                if not work.serie_id:
                    missing_vals["serie_id"] = self.serie_id.id
                if line.tome and not work.tome:
                    missing_vals["tome"] = line.tome
                if line.name and not work.titre_canonique:
                    missing_vals["titre_canonique"] = line.name
                if missing_vals:
                    work.write(missing_vals)
                added.append(line)
                continue

            work = self.env["comic.work"].search(
                [("serie_id", "=", self.serie_id.id), ("tome", "=", line.tome)],
                limit=1,
            )
            if not work:
                work = self.env["comic.work"].create(
                    {
                        "titre_canonique": line.name,
                        "serie_id": self.serie_id.id,
                        "tome": line.tome,
                    }
                )

            edition = work.edition_ids[:1]
            if not edition or isbn:
                ed_vals = {"work_id": work.id}
                if line.date_parution:
                    ed_vals["date_parution"] = line.date_parution
                if line.cover_data:
                    ed_vals["image_couverture"] = line.cover_data
                edition = self.env["comic.edition"].create(ed_vals)
            if isbn:
                self.env["comic.isbn"].create({"edition_id": edition.id, "isbn_13": isbn})
            added.append(line)

        if added:
            items = "".join(f"<li>Tome {line.tome} — {line.name}</li>" for line in added)
            self.import_report = f"<b>✅ {len(added)} tome(s) ajouté(s) à la wishlist :</b><ul>{items}</ul>"
        else:
            self.import_report = "<p>Aucun tome sélectionné.</p>"

        self.state = "done"
        return self._reopen()

    def action_back(self):
        self.state = "confirm"
        return self._reopen()

    def action_close_and_return(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "res_model": "comic.serie",
            "res_id": self.serie_id.id,
            "view_mode": "form",
            "target": "current",
        }

    def _reopen(self):
        return {
            "type": "ir.actions.act_window",
            "res_model": self._name,
            "res_id": self.id,
            "view_mode": "form",
            "target": "new",
        }


class ComicSerieMissingLine(models.TransientModel):
    _name = "comic.serie.missing.line"
    _description = "Tome manquant détecté dans une série"
    _order = "tome"

    wizard_id = fields.Many2one("comic.serie.missing.wizard", required=True, ondelete="cascade")
    tome = fields.Integer()
    name = fields.Char(string="Titre")
    isbn = fields.Char(string="ISBN")
    isbn_unverified = fields.Boolean(
        string="ISBN absent",
        help="Aucun ISBN retourné par la source — déduplication moins fiable, vérifiez manuellement.",
    )
    cover_data = fields.Image(string="Couverture", max_width=80, max_height=110)
    date_parution = fields.Date(string="Parution")
    selected = fields.Boolean(string="Sélectionner", default=True)
    source = fields.Selection(
        [
            ("google", "Google Books"),
            ("bnf", "BnF"),
            ("expected", "Attendu"),
        ],
        default="google",
    )
