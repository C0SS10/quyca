from typing import List, Dict, Any
from quyca.validators import base_validator

REQUIRED_FIELDS = [
    "tipo_documento",
    "identificación",
]

NAME_REQUIRED_FIELDS = [
    "primer_apellido",
    "nombres",
]


def validate(row: dict, index: int) -> List[Dict[str, Any]]:
    errors: List[Dict[str, Any]] = []

    # Campos siempre obligatorios
    for field in REQUIRED_FIELDS:
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

    # Regla especial de nombres
    nombre_completo = row.get("nombre_completo")

    if not base_validator.is_empty(nombre_completo):
        return errors

    # Si no existe nombre_completo, se mantienen
    # primer_apellido y nombres como obligatorios.
    for field in NAME_REQUIRED_FIELDS:
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
