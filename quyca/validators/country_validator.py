import re
from typing import List, Dict, Any
from quyca.validators import base_validator

COUNTRY_RE = re.compile(r"^[A-z]{2}$")


def validate(row: dict, index: int) -> List[Dict[str, Any]]:
    warning = []
    country = row.get("pais_producto")
    if not base_validator.is_empty(country) and not COUNTRY_RE.match(str(country).upper().strip()):
        warning.append(
            {
                "fila": index,
                "columna": "pais_producto",
                "detalle": "Formato de pais_producto inválido (debe ser ISO 3166-1 alfa-2, ej: 'CO', 'US')",
                "valor": country,
            }
        )

    return warning
