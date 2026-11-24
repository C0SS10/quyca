import re
from typing import List, Dict, Any
from quyca.validators import base_validator

CODE_RE = re.compile(r"^[A-Za-z0-9_-]+$")
# Any character a unit name may not have: "Dpto. de Química (Sede Norte)" or "Tecnologías de Información (TIC)" are fine.
UNIT_INVALID_CHAR_RE = re.compile(r"[^A-Za-zÁÉÍÓÚÜÑáéíóúüñ0-9, \-:().\/&']")


def _normalize_code_value(value: Any) -> str:
    """Normalize numeric-looking codes so Excel floats like 118.0 become 118."""
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value).strip()


def validate(row: dict, index: int) -> List[Dict[str, Any]]:
    errors: List[Dict[str, Any]] = []
    for field in ["código_unidad_académica", "código_subunidad_académica"]:
        value = row.get(field)
        normalized_value = _normalize_code_value(value)
        if not base_validator.is_empty(value) and not CODE_RE.match(normalized_value):
            errors.append(
                {
                    "fila": index,
                    "columna": field,
                    "detalle": f"No se permite {normalized_value}, solo letras, números, _ y -",
                    "valor": value,
                }
            )

    for field in ["unidad_académica", "subunidad_académica"]:
        value = row.get(field)
        if base_validator.is_empty(value):
            continue
        text = str(value).strip()
        if base_validator.has_broken_encoding(text):
            detail = "Posible problema de codificación (caracteres como ¿ o Ã± en lugar de letras como ñ o tildes)"
        else:
            invalid = sorted(
                {char if char.isprintable() else "carácter de control" for char in UNIT_INVALID_CHAR_RE.findall(text)}
            )
            if not invalid:
                continue
            detail = f"Contiene caracteres no permitidos: {', '.join(invalid)}"
        errors.append({"fila": index, "columna": field, "detalle": detail, "valor": value})
    return errors
