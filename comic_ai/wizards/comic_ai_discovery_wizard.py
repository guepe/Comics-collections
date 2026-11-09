"""Découverte IA par profil de goûts (US-029).

Le profil est formé des séries dont l'utilisateur a noté au moins un album 4★ ou plus
(modifiable avant l'appel). L'IA propose 10 à 15 séries inconnues ; celles déjà en
collection ou en wishlist sont exclues (titre normalisé), dans le prompt et après coup.
Chaque suggestion peut être vérifiée sur les sources (comic_datasource) puis ajoutée à
la wishlist : tome 1 de la série du catalogue, ou série + tome 1 créés.

Le même assistant sert le portail (module comic_ai_shop) : enregistrements créés en
sudo, toujours pour le partenaire de l'utilisateur courant (forcé à la création).
"""

import json
import logging
import re

from odoo import api, fields, models
from odoo.exceptions import UserError

from ..models.comic_ai_service import ComicAiError
from odoo.addons.comic_datasource.aggregator import ComicDataAggregator
from odoo.addons.comic_datasource.sources.base import normalize_isbn
from odoo.addons.comic_datasource.sources.google_books import GoogleBooksQuotaError
from odoo.addons.comics_collections.models.comic_isbn import ComicIsbn
from odoo.addons.comics_collections.utils.normalize import normalize_title

_logger = logging.getLogger(__name__)

MIN_SUGGESTIONS = 10
MAX_SUGGESTIONS = 15
PROFILE_MIN_NOTE = 4.0
# Bornes du prompt : coût maîtrisé même pour une très grande bibliothèque
PROMPT_MAX_PROFILE = 40
PROMPT_MAX_EXCLUDED = 150
PROMPT_MAX_AUTHORS = 4

SOURCE_LABELS = {"google": "Google Books", "openlibrary": "Open Library", "bnf": "BnF"}

# Clés acceptées dans le JSON renvoyé par l'IA (le prompt demande les clés françaises)
_TITLE_KEYS = ("titre", "serie", "série", "title", "series", "name")
_AUTHOR_KEYS = ("auteurs", "auteur", "authors", "author")
_GENRE_KEYS = ("genre", "genres")
_REASON_KEYS = ("raison", "reason", "pourquoi", "why")
_LIST_KEYS = ("suggestions", "series", "séries", "results")


def _first_value(item, keys):
    for key in keys:
        value = item.get(key)
        if isinstance(value, list):
            value = ", ".join(str(v).strip() for v in value if v and str(v).strip())
        if value and str(value).strip():
            return str(value).strip()
    return ""


def parse_suggestions(text):
    """Extract the suggestion list from an AI answer, tolerant to surrounding noise.

    Accepte un bloc ```json, du texte avant / après, une liste nue ou un objet
    ``{"suggestions": [...]}``. Retourne une liste de dicts ``titre`` / ``auteurs`` /
    ``genre`` / ``raison`` (titre non vide).

    :raise ValueError: aucun JSON exploitable (converti en ComicAiError par l'assistant)
    """
    raw = text or ""
    candidates = [match.group(1) for match in re.finditer(r"```(?:json)?\s*(.*?)```", raw, re.S | re.I)]
    candidates.append(raw)
    for chunk in list(candidates):
        for opening, closing in (("{", "}"), ("[", "]")):
            start, end = chunk.find(opening), chunk.rfind(closing)
            if start != -1 and end > start:
                candidates.append(chunk[start : end + 1])
    for chunk in candidates:
        try:
            data = json.loads(chunk.strip())
        except ValueError:
            continue
        items = data
        if isinstance(data, dict):
            items = next((data[key] for key in _LIST_KEYS if isinstance(data.get(key), list)), None)
        if not isinstance(items, list):
            continue
        suggestions = []
        for item in items:
            if not isinstance(item, dict):
                continue
            titre = _first_value(item, _TITLE_KEYS)
            if titre:
                suggestions.append(
                    {
                        "titre": titre[:200],
                        "auteurs": _first_value(item, _AUTHOR_KEYS)[:200],
                        "genre": _first_value(item, _GENRE_KEYS)[:100],
                        "raison": _first_value(item, _REASON_KEYS)[:1000],
                    }
                )
        if suggestions:
            return suggestions
    raise ValueError("no usable JSON suggestion list in the AI answer")


def filter_suggestions(suggestions, excluded_norms, limit=MAX_SUGGESTIONS):
    """Drop the suggestions already known (normalized title) and the duplicates."""
    seen = set(excluded_norms)
    kept = []
    for suggestion in suggestions:
        norm = normalize_title(suggestion["titre"])
        if not norm or norm in seen:
            continue
        seen.add(norm)
        kept.append(suggestion)
    return kept[:limit]


class ComicAiDiscoveryWizard(models.TransientModel):
    _name = "comic.ai.discovery.wizard"
    _description = "Découvrir de nouvelles BD (IA)"

    partner_id = fields.Many2one(
        "res.partner",
        string="Collectionneur",
        readonly=True,
        default=lambda self: self.env.user.partner_id,
    )
    portal = fields.Boolean(help="Assistant ouvert depuis le portail client (création modérée).")
    state = fields.Selection([("profile", "Profil"), ("suggestions", "Suggestions")], default="profile")
    profile_serie_ids = fields.Many2many(
        "comic.serie",
        "comic_ai_discovery_wizard_serie_rel",
        "wizard_id",
        "serie_id",
        string="Mon profil de goûts",
        default=lambda self: self._get_profile_series(self.env.user.partner_id),
        help="Séries dont vous avez noté au moins un album 4★ ou plus. Retirez ou ajoutez des "
        "séries avant de lancer la recherche.",
    )
    line_ids = fields.One2many("comic.ai.discovery.line", "wizard_id", string="Suggestions")
    nb_excluded = fields.Integer(string="Séries exclues", readonly=True)
    nb_ignored = fields.Integer(
        string="Suggestions écartées",
        readonly=True,
        help="Suggestions de l'IA écartées car déjà en collection, en wishlist ou en double.",
    )

    @api.model_create_multi
    def create(self, vals_list):
        # Toujours le partenaire de l'utilisateur courant, même en sudo (portail)
        for vals in vals_list:
            vals["partner_id"] = self.env.user.partner_id.id
        return super().create(vals_list)

    # ── Profil et exclusions ────────────────────────────────────────────────

    @api.model
    def _get_profile_series(self, partner):
        """Series of the albums rated 4★ or more by ``partner``, best rated first."""
        entries = (
            self.env["comic.customer.album"]
            .sudo()
            .search([("partner_id", "=", partner.id), ("note", ">=", PROFILE_MIN_NOTE)])
        )
        best = {}
        for entry in entries:
            serie = entry.work_id.serie_id
            if serie:
                best[serie] = max(best.get(serie, 0.0), entry.note)
        ordered = sorted(best, key=lambda serie: (-best[serie], serie.name or ""))
        return self.env["comic.serie"].browse([serie.id for serie in ordered])

    @api.model
    def _get_excluded_series(self, partner):
        """Series already known by ``partner``: in its library (owned or wished) or followed.

        Les séries suivies forment la wishlist (tomes manquants) des utilisateurs internes.
        """
        Serie = self.env["comic.serie"].sudo()
        entries = (
            self.env["comic.customer.album"]
            .sudo()
            .search(
                [
                    ("partner_id", "=", partner.id),
                    "|",
                    ("dans_collection", "=", True),
                    ("dans_wishlist", "=", True),
                ]
            )
        )
        series = entries.work_id.serie_id
        users = partner.sudo().user_ids.filtered(lambda u: not u.share)
        if users:
            series |= Serie.search([("suivi_user_ids", "in", users.ids)])
        return series

    def _excluded_norms(self, excluded=None):
        self.ensure_one()
        excluded = self._get_excluded_series(self.partner_id) if excluded is None else excluded
        series = excluded | self.profile_serie_ids
        return {norm for norm in series.sudo().mapped("name_normalise") if norm}

    def _profile_prompt_lines(self):
        self.ensure_one()
        notes = {}
        entries = (
            self.env["comic.customer.album"].sudo().search([("partner_id", "=", self.partner_id.id), ("note", ">", 0)])
        )
        for entry in entries:
            if entry.work_id.serie_id:
                notes.setdefault(entry.work_id.serie_id.id, []).append(entry.note)
        lines = []
        for serie in self.profile_serie_ids.sudo()[:PROMPT_MAX_PROFILE]:
            authors = []
            for name in serie.work_ids.auteur_line_ids.partner_id.mapped("name"):
                if name not in authors:
                    authors.append(name)
            parts = [serie.name]
            if serie.genre_id:
                parts.append("genre : %s" % serie.genre_id.name)
            if authors:
                parts.append("auteurs : %s" % ", ".join(authors[:PROMPT_MAX_AUTHORS]))
            if notes.get(serie.id):
                parts.append("note : %.1f/5" % max(notes[serie.id]))
            lines.append("- " + " ; ".join(parts))
        return "\n".join(lines)

    # ── Appel IA ────────────────────────────────────────────────────────────

    def _check_profile(self):
        self.ensure_one()
        if not self.profile_serie_ids:
            raise UserError(
                self.env._(
                    "Votre profil de goûts est vide : notez au moins une BD 4★ dans votre bibliothèque "
                    "(ou ajoutez des séries au profil) pour obtenir des suggestions."
                )
            )

    def _build_prompt(self, excluded):
        service = self.env["comic.ai.service"]
        excluded_names = sorted(set((excluded - self.profile_serie_ids).sudo().mapped("name")))
        return service._render_prompt(
            "discovery",
            profile=self._profile_prompt_lines(),
            excluded="\n".join("- %s" % name for name in excluded_names[:PROMPT_MAX_EXCLUDED]) or "- (aucune)",
            min=MIN_SUGGESTIONS,
            max=MAX_SUGGESTIONS,
            lang=service._lang_name(service._get_default_lang()),
        )

    def _generate_suggestions(self):
        """Call the AI, parse and filter the answer, then replace the suggestion lines."""
        self.ensure_one()
        excluded = self._get_excluded_series(self.partner_id)
        result = self.env["comic.ai.service"]._generate(
            self._build_prompt(excluded),
            system="Tu es un libraire spécialisé en bande dessinée. Tu réponds uniquement en JSON.",
            max_tokens=3000,
            effort="low",
        )
        try:
            parsed = parse_suggestions(result["text"])
        except ValueError as exc:
            _logger.info("Discovery: unreadable AI answer: %.500s", result["text"])
            raise ComicAiError(
                self.env._(
                    "La réponse de l'IA est illisible (JSON invalide ou sans suggestion). Relancez la recherche."
                )
            ) from exc
        kept = filter_suggestions(parsed, self._excluded_norms(excluded))
        Line = self.env["comic.ai.discovery.line"]
        self.line_ids.unlink()
        Line.create(
            [
                {
                    "wizard_id": self.id,
                    "sequence": index,
                    "name": suggestion["titre"],
                    "auteurs": suggestion["auteurs"],
                    "genre": suggestion["genre"],
                    "raison": suggestion["raison"],
                    "serie_id": Line._match_serie(suggestion["titre"]).id,
                }
                for index, suggestion in enumerate(kept)
            ]
        )
        self.write({"state": "suggestions", "nb_excluded": len(excluded), "nb_ignored": len(parsed) - len(kept)})
        return kept

    def action_generate(self):
        self.ensure_one()
        self._check_profile()
        self._generate_suggestions()
        return self._reopen()

    def action_back(self):
        self.ensure_one()
        self.state = "profile"
        return self._reopen()

    # ── Ajout en wishlist ───────────────────────────────────────────────────

    def _add_selected_to_wishlist(self):
        """Add the selected (not yet added) suggestions; return the added lines."""
        self.ensure_one()
        added = self.env["comic.ai.discovery.line"]
        for line in self.line_ids.filtered(lambda line: line.selected and not line.added):
            if line._add_to_wishlist():
                added |= line
        added.write({"added": True, "selected": False})
        return added

    def action_add_to_wishlist(self):
        self.ensure_one()
        if not self.line_ids.filtered(lambda line: line.selected and not line.added):
            raise UserError(self.env._("Sélectionnez au moins une suggestion à ajouter à votre wishlist."))
        added = self._add_selected_to_wishlist()
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "type": "success",
                "message": self.env._(
                    "%(count)s série(s) ajoutée(s) à votre wishlist : %(names)s",
                    count=len(added),
                    names=", ".join(added.mapped("name")),
                ),
                "next": self._reopen(),
            },
        }

    def _reopen(self):
        return {
            "type": "ir.actions.act_window",
            "name": self.env._("Découvrir de nouvelles BD"),
            "res_model": self._name,
            "res_id": self.id,
            "view_mode": "form",
            "views": [(False, "form")],
            "target": "new",
        }


class ComicAiDiscoveryLine(models.TransientModel):
    _name = "comic.ai.discovery.line"
    _description = "Suggestion de série (découverte IA)"
    _order = "sequence, id"

    wizard_id = fields.Many2one("comic.ai.discovery.wizard", required=True, ondelete="cascade", index=True)
    sequence = fields.Integer(default=10)
    selected = fields.Boolean(string="Sélection")
    name = fields.Char(string="Série", required=True)
    auteurs = fields.Char(string="Auteur(s)")
    genre = fields.Char()
    raison = fields.Text(string="Pourquoi")
    serie_id = fields.Many2one("comic.serie", string="Au catalogue", readonly=True)
    added = fields.Boolean(string="Ajoutée", readonly=True)
    verify_state = fields.Selection(
        [
            ("todo", "Non vérifiée"),
            ("found", "Trouvée"),
            ("not_found", "Introuvable"),
            ("error", "Erreur"),
        ],
        string="Vérification",
        default="todo",
        readonly=True,
    )
    verify_info = fields.Char(string="Résultat de la vérification", readonly=True)
    verified_title = fields.Char(readonly=True)
    verified_isbn = fields.Char(string="ISBN du tome 1", readonly=True)
    verified_editeur = fields.Char(string="Éditeur", readonly=True)

    # ── Catalogue ───────────────────────────────────────────────────────────

    @api.model
    def _match_serie(self, title):
        """Active catalogue series with the same normalized title, or an empty recordset."""
        norm = normalize_title(title)
        if not norm:
            return self.env["comic.serie"]
        return self.env["comic.serie"].sudo().search([("name_normalise", "=", norm)], limit=1)

    @staticmethod
    def _first_work(serie):
        works = serie.work_ids.filtered("active")
        numbered = works.filtered(lambda w: w.tome > 0).sorted(lambda w: (w.tome, w.id))
        return numbered[:1] or works.sorted("id")[:1]

    def _valid_isbn(self):
        isbn = normalize_isbn(self.verified_isbn or "")
        return isbn if ComicIsbn._validate_ean13(isbn) else ""

    def _create_catalog_entry(self, serie):
        """Create the missing series / volume 1 and return its edition (back-office).

        Surchargé par comic_ai_shop pour le portail (circuit modéré « à valider »).
        """
        self.ensure_one()
        env = self.env
        if not serie:
            serie = env["comic.serie"].create({"name": self.name})
        editeur = env["comic.editeur"]
        if self.verified_editeur:
            editeur = env["comic.editeur"].search([("name", "=ilike", self.verified_editeur)], limit=1)
            if not editeur:
                editeur = env["comic.editeur"].create({"name": self.verified_editeur})
            if not serie.editeur_id:
                serie.editeur_id = editeur
        work = env["comic.work"].create(
            {"serie_id": serie.id, "titre_canonique": self.verified_title or self.name, "tome": 1}
        )
        edition = work.primary_edition_id or env["comic.edition"].create({"work_id": work.id})
        if editeur and not edition.editeur_id:
            edition.editeur_id = editeur
        isbn = self._valid_isbn()
        if isbn:
            env["comic.isbn"].create({"edition_id": edition.id, "isbn_13": isbn})
        return edition

    def _get_first_edition(self):
        """Edition of the first volume of the suggested series, created if needed."""
        self.ensure_one()
        isbn = self._valid_isbn()
        if isbn:
            known = self.env["comic.isbn"].sudo().search([("isbn_13", "=", isbn)], limit=1)
            if known:
                return known.edition_id
        serie = (self.serie_id or self._match_serie(self.name)).with_env(self.env)
        if serie:
            work = self._first_work(serie)
            if work:
                return work.primary_edition_id or work.edition_ids[:1]
        return self._create_catalog_entry(serie)

    def _add_to_wishlist(self):
        """Put the first volume in the wishlist of the wizard's partner; return the edition."""
        self.ensure_one()
        edition = self._get_first_edition()
        if not edition:
            return False
        Album = self.env["comic.customer.album"]
        partner = self.wizard_id.partner_id
        existing = Album.sudo().search([("partner_id", "=", partner.id), ("edition_id", "=", edition.id)], limit=1)
        vals = {"dans_wishlist": True, "ignore_wishlist": False}
        if not existing:
            vals["dans_collection"] = False
        Album._upsert(partner, edition, vals)
        if not self.serie_id:
            self.serie_id = edition.work_id.serie_id
        return edition

    # ── Vérification sur les sources (contre les hallucinations) ────────────

    def _get_aggregator(self):
        return ComicDataAggregator(env=self.env)

    def _match_source_result(self, results):
        """Best source result for the suggested series (series name, then title)."""
        target = normalize_title(self.name)
        best, best_key = None, None
        for index, result in enumerate(results or []):
            serie_norm = normalize_title(getattr(result, "serie_name", "") or "")
            title_norm = normalize_title(getattr(result, "title", "") or "")
            if serie_norm == target:
                level = 3
            elif title_norm == target or title_norm.startswith(target + " "):
                level = 2
            elif f" {target} " in f" {title_norm} ":
                level = 1
            else:
                continue
            key = (level, getattr(result, "tome", None) == 1, bool(getattr(result, "isbn", None)), -index)
            if best_key is None or key > best_key:
                best, best_key = result, key
        return best

    def _verify_on_sources(self):
        """Search the series on the data sources and record what was found."""
        self.ensure_one()
        try:
            results = self._get_aggregator().search_list(title=self.name)
        except GoogleBooksQuotaError:
            self.write(
                {
                    "verify_state": "error",
                    "verify_info": self.env._("Quota Google Books atteint : réessayez plus tard."),
                }
            )
            return False
        except Exception as exc:  # sources externes : jamais d'erreur bloquante
            _logger.warning("Discovery verification failed for %s: %s", self.name, exc)
            self.write({"verify_state": "error", "verify_info": self.env._("Sources momentanément indisponibles.")})
            return False
        result = self._match_source_result(results)
        if not result:
            self.write(
                {
                    "verify_state": "not_found",
                    "verify_info": self.env._("Introuvable sur les sources : la suggestion est peut-être inexacte."),
                    "verified_title": False,
                    "verified_isbn": False,
                    "verified_editeur": False,
                }
            )
            return False
        isbn = normalize_isbn(result.isbn or "")
        isbn = isbn if ComicIsbn._validate_ean13(isbn) else ""
        is_first = result.tome == 1
        authors = ", ".join(a.get("name", "") for a in (result.auteurs or []) if a.get("name"))
        parts = [
            self.env._("Trouvée sur %s", SOURCE_LABELS.get(result.source, result.source)),
            "« %s »" % result.title,
        ]
        if result.editeur:
            parts.append(self.env._("éditeur : %s", result.editeur))
        if isbn:
            parts.append(self.env._("ISBN T1 : %s", isbn) if is_first else self.env._("ISBN : %s", isbn))
        if authors:
            parts.append(self.env._("auteurs : %s", authors))
        self.write(
            {
                "verify_state": "found",
                "verify_info": " — ".join(parts)[:500],
                # Seul un tome 1 identifié sert à créer la fiche (titre, ISBN)
                "verified_title": result.title if is_first else False,
                "verified_isbn": isbn if is_first else False,
                "verified_editeur": result.editeur or False,
            }
        )
        return True

    def action_verify(self):
        self.ensure_one()
        self._verify_on_sources()
        return self.wizard_id._reopen()
