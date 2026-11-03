import re
from typing import List, Dict, Any
from quyca.validators import base_validator

LANG_RE = re.compile(r"^[a-z]{2}$")


def validate(row: dict, index: int) -> List[Dict[str, Any]]:
    warnings = []

    language = row.get("idioma")
    if not base_validator.is_empty(language) and not LANG_RE.match(str(language).lower().strip()):
        warnings.append(
            {
                "fila": index,
                "columna": "idioma",
                "detalle": "Formato de idioma inválido (debe ser ISO 639-1, ej: 'es', 'en')",
                "valor": language,
            }
        )

    return warnings
