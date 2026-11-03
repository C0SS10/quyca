from datetime import datetime
import re
from typing import Any, Dict, Optional

_INTEGER_TEXT_RE = re.compile(r"^[0-9]+(?:\.0+)?$")


def validate(value: Any, field: str, index: int) -> Optional[Dict[str, Any]]:
    if value is None or str(value).strip() == "":
        return None
    try:
        if isinstance(value, str):
            stripped = value.strip()
            if _INTEGER_TEXT_RE.match(stripped):
                year = int(float(stripped))
            else:
                year = int(stripped)
        else:
            year = int(value)
        current_year = datetime.now().year
        if year > current_year:
            return {
                "fila": index,
                "columna": field,
                "detalle": "Año no válido",
                "valor": value,
            }
    except Exception:
        return {"fila": index, "columna": field, "detalle": f"Formato inválido, debe ser numérico", "valor": value}
    return None
