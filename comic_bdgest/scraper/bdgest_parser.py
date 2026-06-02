"""
Parser HTML pour bedetheque.com — sans dépendance HTTP ni Odoo.

Toutes les méthodes sont statiques et prennent du HTML brut (str) en entrée.
Cela permet de les tester en isolation avec des fixtures.

Structure HTML bedetheque.com (documentée après inspection) :

SEARCH RESULTS
  <ul class="search-list">
    <li>
      <a class="lnk_couv" href="/album-12345-BD-Titre.html"><img src="..."/></a>
      <div class="infos-serie">
        <a href="/serie-678-Serie.html">Série</a>
        <span class="ntome">Tome 1</span>
      </div>
      <div class="infos-album">
        <a class="lnk_titre" href="/album-12345-...">Titre album</a>
      </div>
      <ul class="auteurs">
        <li><label>Scénario</label> <a href="/auteur-...">Goscinny</a></li>
        <li><label>Dessin</label>   <a href="/auteur-...">Uderzo</a></li>
      </ul>
      <div class="infos-editeur"><a>Albert René</a></div>
    </li>
  </ul>

ALBUM DETAIL
  <div class="album-main">
    <ul class="informations">
      <li><label>Titre</label>        <span>Astérix le Gaulois</span></li>
      <li><label>Série</label>        <a href="/serie-678-...">Astérix</a></li>
      <li><label>Tome</label>         <span>1</span></li>
      <li><label>EAN/ISBN</label>     <span>9782012101302</span></li>
      <li><label>Dépôt légal</label>  <span>01/1961</span></li>
      <li><label>Parution</label>     <span>01/01/1961</span></li>
      <li><label>Planches</label>     <span>48</span></li>
      <li><label>Éditeur</label>      <a href="...">Albert René</a></li>
    </ul>
    <ul class="auteurs">
      <li><label>Scénario</label> <a href="/auteur-...">Goscinny</a></li>
      <li><label>Dessin</label>   <a href="/auteur-...">Uderzo</a></li>
    </ul>
    <div class="couverture"><img src="https://..."/></div>
    <div class="resume"><p>Synopsis...</p></div>
  </div>

SERIE PAGE
  <h1 itemprop="name">Astérix</h1>
  <ul class="serie-albums">
    <li>
      <a href="/album-12345-BD-Titre.html">Astérix le Gaulois</a>
      <span class="ntome">1</span>
    </li>
    ...
  </ul>
"""

import re
from bs4 import BeautifulSoup

BASE_URL = "https://www.bedetheque.com"
try:
    BeautifulSoup("", "lxml")
    _BS_PARSER = "lxml"
except Exception:
    _BS_PARSER = "html.parser"


class BdgestParser:

    # ──────────────────────────────────────────────────────────
    # Résultats de recherche
    # ──────────────────────────────────────────────────────────

    @staticmethod
    def parse_search_results(html):
        """
        Parse la page de résultats de recherche d'albums.
        Retourne : list[dict] avec les clés :
          bdgest_album_id, bdgest_serie_id, serie_name, tome,
          titre, editeur, auteurs, couverture_url, isbn
        """
        soup = BeautifulSoup(html, _BS_PARSER)
        results = []

        items = soup.select("ul.search-list > li") or soup.select("ul.liste-albums > li")

        for item in items:
            r = BdgestParser._parse_search_item(item)
            if r:
                results.append(r)

        return results

    @staticmethod
    def _parse_search_item(item):
        # Lien + ID album
        album_link = (
            item.select_one('a.lnk_couv[href*="/album-"]')
            or item.select_one('a.lnk_titre[href*="/album-"]')
            or item.select_one('a[href*="/album-"]')
        )
        if not album_link:
            return None
        bdgest_album_id = BdgestParser._id_from_url(album_link["href"], "album")
        if not bdgest_album_id:
            return None

        # Couverture
        img = item.select_one("a.lnk_couv img") or item.select_one("img")
        couverture_url = BdgestParser._abs(img.get("src", "")) if img else ""

        # Série
        serie_link = item.select_one('a[href*="/serie-"]')
        serie_name = serie_link.get_text(strip=True) if serie_link else ""
        bdgest_serie_id = BdgestParser._id_from_url(serie_link["href"], "serie") if serie_link else None

        # Tome
        tome_tag = item.select_one('.ntome, span.ntome, [class*="ntome"]')
        tome = BdgestParser._int(tome_tag.get_text(strip=True)) if tome_tag else None

        # Titre
        titre_tag = item.select_one("a.lnk_titre") or item.select_one(".infos-album a") or item.select_one(".titre")
        titre = titre_tag.get_text(strip=True) if titre_tag else album_link.get_text(strip=True)

        # Éditeur
        editeur_tag = item.select_one(".infos-editeur a") or item.select_one(".editeur")
        editeur = editeur_tag.get_text(strip=True) if editeur_tag else ""

        # Auteurs
        auteurs = BdgestParser._parse_auteurs_tag(item)

        return {
            "bdgest_album_id": bdgest_album_id,
            "bdgest_serie_id": bdgest_serie_id,
            "serie_name": serie_name,
            "tome": tome,
            "titre": titre,
            "editeur": editeur,
            "auteurs": auteurs,
            "couverture_url": couverture_url,
            "isbn": "",
        }

    # ──────────────────────────────────────────────────────────
    # Fiche album complète
    # ──────────────────────────────────────────────────────────

    @staticmethod
    def parse_album_detail(html, bdgest_album_id):
        """
        Parse une fiche album complète.
        Retourne : dict avec tous les champs disponibles.
        """
        soup = BeautifulSoup(html, _BS_PARSER)
        result = {"bdgest_album_id": bdgest_album_id}

        section = soup.select_one("div.album-main") or soup.select_one("div.main-infos") or soup.body

        # ── ul.informations — label/valeur ──
        for li in section.select("ul.informations > li, ul.infos > li"):
            label_tag = li.select_one("label")
            if not label_tag:
                continue
            key = label_tag.get_text(strip=True).lower().rstrip(":").strip()

            # Valeur : tout sauf le label
            label_tag.extract()
            value = li.get_text(separator=" ", strip=True)

            BdgestParser._map_info_field(result, key, value, li)

        # ── Série depuis lien si pas encore trouvée ──
        if not result.get("serie_name") or not result.get("bdgest_serie_id"):
            serie_link = soup.select_one('a[href*="/serie-"]')
            if serie_link:
                result.setdefault("serie_name", serie_link.get_text(strip=True))
                result.setdefault("bdgest_serie_id", BdgestParser._id_from_url(serie_link["href"], "serie"))

        # ── Couverture ──
        cover_img = (
            soup.select_one("div.couverture img")
            or soup.select_one("img.couv_serie")
            or soup.select_one('[class*="couv"] img')
        )
        couverture_url = ""
        if cover_img:
            src = cover_img.get("src") or cover_img.get("data-src", "")
            couverture_url = BdgestParser._abs(src)
        result["couverture_url"] = couverture_url

        # ── Synopsis ──
        if not result.get("synopsis"):
            resume_tag = (
                soup.select_one("div.resume") or soup.select_one("div.synopsis") or soup.select_one('[class*="resume"]')
            )
            if resume_tag:
                result["synopsis"] = resume_tag.get_text(separator="\n", strip=True)

        # ── Auteurs ──
        result["auteurs"] = BdgestParser._parse_auteurs_detail(section)

        # ── Normalisation ──
        if result.get("tome"):
            result["tome"] = BdgestParser._int(result["tome"])
        if result.get("nb_pages"):
            result["nb_pages"] = BdgestParser._int(result["nb_pages"])
        if result.get("isbn"):
            result["isbn"] = re.sub(r"[\s\-]", "", str(result["isbn"]))

        return result

    @staticmethod
    def _map_info_field(result, key, value, li):
        """Mappe un label bedetheque → champ interne."""
        if any(k in key for k in ("titre", "title")):
            result.setdefault("titre", value)
        elif any(k in key for k in ("série", "serie", "collection")):
            result.setdefault("serie_name", value)
            serie_link = li.select_one('a[href*="/serie-"]')
            if serie_link:
                result.setdefault("bdgest_serie_id", BdgestParser._id_from_url(serie_link["href"], "serie"))
        elif key in ("tome", "volume", "numéro"):
            result.setdefault("tome", value)
        elif any(k in key for k in ("ean", "isbn")):
            result.setdefault("isbn", value)
        elif any(k in key for k in ("parution", "date de parution")):
            result.setdefault("date_parution", BdgestParser._parse_date(value))
        elif any(k in key for k in ("dépôt légal", "depot legal")):
            result.setdefault("date_depot_legal", BdgestParser._parse_date(value))
        elif any(k in key for k in ("planches", "pages", "nb pages")):
            result.setdefault("nb_pages", value)
        elif any(k in key for k in ("éditeur", "editeur", "publisher")):
            result.setdefault("editeur", value)
        elif any(k in key for k in ("résumé", "resume", "synopsis")):
            result.setdefault("synopsis", value)

    # ──────────────────────────────────────────────────────────
    # Albums d'une série
    # ──────────────────────────────────────────────────────────

    @staticmethod
    def parse_serie_albums(html):
        """
        Parse la page d'une série pour lister ses albums.
        Retourne : list[dict] avec bdgest_album_id, tome, titre, bdgest_serie_id.
        """
        soup = BeautifulSoup(html, _BS_PARSER)

        # ID et nom série
        canonical = soup.select_one('link[rel="canonical"]')
        bdgest_serie_id = BdgestParser._id_from_url(canonical["href"], "serie") if canonical else None
        h1 = soup.select_one('h1[itemprop="name"]') or soup.select_one("h1.serie") or soup.select_one("h1")
        serie_name = h1.get_text(strip=True) if h1 else ""

        results = []
        seen = set()

        # Liens album dans la liste de la série
        for link in soup.select('ul.serie-albums a[href*="/album-"], li.album a[href*="/album-"], a[href*="/album-"]'):
            bdgest_album_id = BdgestParser._id_from_url(link["href"], "album")
            if not bdgest_album_id or bdgest_album_id in seen:
                continue
            seen.add(bdgest_album_id)

            parent = link.find_parent("li") or link.parent
            tome_tag = parent.select_one(".ntome, span.ntome") if parent else None
            tome = BdgestParser._int(tome_tag.get_text(strip=True)) if tome_tag else None

            results.append(
                {
                    "bdgest_album_id": bdgest_album_id,
                    "bdgest_serie_id": bdgest_serie_id,
                    "serie_name": serie_name,
                    "tome": tome,
                    "titre": link.get_text(strip=True),
                }
            )

        return results

    # ──────────────────────────────────────────────────────────
    # Auteurs
    # ──────────────────────────────────────────────────────────

    @staticmethod
    def _parse_auteurs_tag(tag):
        """Extrait auteurs + rôles depuis un tag quelconque (list item)."""
        auteurs = []
        for li in tag.select("ul.auteurs > li, .auteurs > li"):
            label = li.select_one("label")
            role_text = label.get_text(strip=True).lower() if label else ""
            role = BdgestParser._role(role_text)
            for a in li.select("a"):
                nom = a.get_text(strip=True)
                if nom:
                    auteurs.append({"nom": nom, "role": role})
        # Fallback : liens auteur directs
        if not auteurs:
            for a in tag.select('a[href*="/auteur-"]'):
                nom = a.get_text(strip=True)
                parent_text = a.parent.get_text(" ", strip=True).lower() if a.parent else ""
                if nom:
                    auteurs.append({"nom": nom, "role": BdgestParser._role(parent_text)})
        return auteurs

    @staticmethod
    def _parse_auteurs_detail(section):
        """Extrait auteurs avec rôles depuis la section d'une fiche album."""
        auteurs = []
        for li in section.select("ul.auteurs > li"):
            label = li.select_one("label")
            role_text = label.get_text(strip=True).lower() if label else ""
            role = BdgestParser._role(role_text)
            for a in li.select('a[href*="/auteur-"]'):
                nom = a.get_text(strip=True)
                if nom:
                    auteurs.append({"nom": nom, "role": role})
        if not auteurs:
            auteurs = BdgestParser._parse_auteurs_tag(section)
        return auteurs

    # ──────────────────────────────────────────────────────────
    # Helpers
    # ──────────────────────────────────────────────────────────

    @staticmethod
    def _id_from_url(url, prefix):
        """
        Extrait l'ID numérique d'une URL bedetheque.com.
        /album-12345-BD-Titre.html → 12345
        /serie-678-Titre.html      → 678
        """
        m = re.search(rf"/{prefix}-(\d+)-", url or "")
        return int(m.group(1)) if m else None

    @staticmethod
    def _int(value):
        """Convertit une chaîne en entier en ignorant les caractères non numériques."""
        digits = re.sub(r"\D", "", str(value or ""))
        return int(digits) if digits else None

    @staticmethod
    def _abs(url):
        """Retourne une URL absolue."""
        if not url:
            return ""
        return url if url.startswith("http") else BASE_URL + url

    @staticmethod
    def _parse_date(value):
        """
        Normalise une date bedetheque en ISO (YYYY-MM-DD).
        Formats rencontrés : '01/1961', '01/01/1961', '1961', 'janvier 1961'.
        """
        if not value:
            return ""
        value = value.strip()
        # JJ/MM/AAAA
        m = re.match(r"(\d{2})/(\d{2})/(\d{4})", value)
        if m:
            return f"{m.group(3)}-{m.group(2)}-{m.group(1)}"
        # MM/AAAA
        m = re.match(r"(\d{2})/(\d{4})", value)
        if m:
            return f"{m.group(2)}-{m.group(1)}-01"
        # AAAA seul
        m = re.match(r"(\d{4})", value)
        if m:
            return f"{m.group(1)}-01-01"
        return value

    @staticmethod
    def _role(text):
        """Déduit le rôle d'un auteur depuis le texte du label (FR)."""
        t = text.lower()
        if any(k in t for k in ("scénario", "scenar", "script", "texte")):
            return "scenariste"
        if any(k in t for k in ("dessin", "illustration", "crayon", "pencil")):
            return "dessinateur"
        if any(k in t for k in ("colori", "couleur", "color")):
            return "coloriste"
        if any(k in t for k in ("encr", "ink")):
            return "encreur"
        if any(k in t for k in ("traduct", "translat")):
            return "traducteur"
        return "autre"
