import re
import unicodedata


def normalize_title(title):
    """Normalize a comic title for deduplication.

    Strips accents, leading articles (FR/NL/EN), trailing catalog suffixes,
    non-significant punctuation, and collapses whitespace.

    Examples:
        "Les Landes perdues"       → "landes perdues"
        "Landes perdues (Les)"     → "landes perdues"
        "l'Enfant des étoiles"     → "enfant des etoiles"
        "Thorgal"                  → "thorgal"
    """
    if not title:
        return ""
    nfd = unicodedata.normalize("NFD", title)
    no_accents = "".join(c for c in nfd if unicodedata.category(c) != "Mn")
    s = no_accents.lower().strip()
    for article in ("l'", "les ", "le ", "la ", "de ", "het ", "een ", "the ", "an ", "a "):
        if s.startswith(article):
            s = s[len(article) :]
            break
    s = re.sub(r"\s*\((les|de|the|het|een|an|a)\)\s*$", "", s)
    s = re.sub(r"[,.\-'\"!?;:]", " ", s)
    return " ".join(s.split())
