"""
core/filters.py
Music content filters — identify UGC noise and genre-specific sounds.
"""

_FUNK_KW = [
    "montagem", "batidao", "funk", "phonk", "baile", "tamborzao", "pancadao",
    "proibidao", "berimbau", "pisadinha", "brega", "ostentacao", "favela",
    "mc ", "dj ", "mtg", "jumpstyle",
]

_UGC_STARTS = [
    "original sound", "origineel geluid", "sonido original", "son original",
    "som original", "originaler ton", "originalton", "suono originale",
    "orijinal ses", "oryginalny dzwiek", "dzwiek oryginalny",
    "orihinal na tunog", "originalljud", "original na tunog",
]
_UGC_ANY = [
    "orijinal", "oryginalny", "dzwiek", "originale", "orihinal", "originalny",
    "original sound", "originalljud",
]


def is_funk(title: str) -> bool:
    t = title.lower()
    return any(k in t for k in _FUNK_KW)


def is_mostly_nonlatin(title: str) -> bool:
    latin_chars = sum(1 for c in title if c.isascii() and c.isalpha())
    total_chars = sum(1 for c in title if c.isalpha())
    return total_chars > 0 and latin_chars / total_chars < 0.5


def check_garbage(title: str, author: str) -> str | None:
    """
    Returns a reason string if the sound should be filtered out, else None.
    """
    t = title.lower().strip()
    a = (author or "").lower().strip()

    if not t:
        return "empty title"
    for p in _UGC_STARTS:
        if t.startswith(p):
            return f"UGC: {p}"
    for s in _UGC_ANY:
        if s in t:
            return f"UGC keyword: {s}"
    if is_mostly_nonlatin(t):
        return "non-latin script"
    if a and t == a:
        return "title = author name"
    if " - " in t:
        after = t.split(" - ", 1)[1].strip()
        for s in _UGC_ANY + ["sound", "ses", "son", "zvuk", "tunog"]:
            if s in after:
                return f"UGC suffix: {s}"
    return None
