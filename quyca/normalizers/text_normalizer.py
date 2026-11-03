import unicodedata
from typing import Any


def normalize_key(value: Any) -> str:
    """Strips accents, surrounding spaces and case, so "Categoría " and "categoria" compare equal."""
    return unicodedata.normalize("NFD", str(value)).encode("ascii", "ignore").decode("ascii").strip().lower()
