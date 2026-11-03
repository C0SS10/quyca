from typing import List, Dict, Any
from quyca.validators import base_validator

REQUIRED_FIELDS_CIARP = [
    "código_unidad_académica",
    "tipo_documento",
    "identificación",
    "año",
    "título",
]


def validate(row: dict, index: int) -> List[Dict[str, Any]]:
    errors = []
    for field in REQUIRED_FIELDS_CIARP:
        value = row.get(field)
        if base_validator.is_empty(value):
            errors.append(
                {
                    "fila": index,
                    "columna": field,
                    "detalle": "Campo obligatorio vacío",
                    "valor": "Vacío",
                }
            )
    return errors
