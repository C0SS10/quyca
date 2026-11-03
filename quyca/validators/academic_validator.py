from typing import List, Dict, Any, Tuple

from quyca.normalizers.text_normalizer import normalize_key
from quyca.validators import base_validator
from quyca.constants.staff_field_values import (
    ACADEMIC_LEVELS,
    ACADEMIC_LEVEL_MAP,
    CONTRACT_TYPES,
    CONTRACT_TYPE_MAP,
    WORK_SCHEDULES,
    WORK_SCHEDULE_MAP,
    JOB_CATEGORIES,
    JOB_CATEGORY_MAP,
    SEX,
    SEX_MAP,
)

_UNKNOWN_VALUE = "desconocido"


def _is_known_value(value: Any, canonicals: set[str], aliases: dict[str, str]) -> bool:
    normalized = normalize_key(value)
    normalized_canonicals = {normalize_key(item) for item in canonicals}
    normalized_aliases = {normalize_key(item) for item in aliases.keys()}
    return normalized in normalized_canonicals or normalized in normalized_aliases or normalized == _UNKNOWN_VALUE


def validate(row: dict, index: int) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    errors: List[Dict[str, Any]] = []
    warnings: List[Dict[str, Any]] = []

    nivel = row.get("nivel_académico")
    if not base_validator.is_empty(nivel) and not _is_known_value(nivel, ACADEMIC_LEVELS, ACADEMIC_LEVEL_MAP):
        warnings.append(
            {
                "fila": index,
                "columna": "nivel_académico",
                "detalle": f"El nivel académico {nivel} no existe en el listado y se normalizó a desconocido",
                "valor": nivel,
            }
        )

    tc = row.get("tipo_contrato")
    if not base_validator.is_empty(tc) and not _is_known_value(tc, CONTRACT_TYPES, CONTRACT_TYPE_MAP):
        warnings.append(
            {
                "fila": index,
                "columna": "tipo_contrato",
                "detalle": f"El tipo de contrato {tc} no está en el listado",
                "valor": tc,
            }
        )

    jr = row.get("jornada_laboral")
    if not base_validator.is_empty(jr) and not _is_known_value(jr, WORK_SCHEDULES, WORK_SCHEDULE_MAP):
        warnings.append(
            {
                "fila": index,
                "columna": "jornada_laboral",
                "detalle": f"La jornada laboral {jr} no se encontró en el listado y se normalizó a desconocido",
                "valor": jr,
            }
        )

    cat = row.get("categoría_laboral")
    if not base_validator.is_empty(cat) and not _is_known_value(cat, JOB_CATEGORIES, JOB_CATEGORY_MAP):
        warnings.append(
            {
                "fila": index,
                "columna": "categoría_laboral",
                "detalle": f"{cat} no está en el listado de categoría laboral y se normalizó a desconocido",
                "valor": cat,
            }
        )

    sexo = row.get("sexo")
    if not base_validator.is_empty(sexo) and not _is_known_value(sexo, SEX, SEX_MAP):
        warnings.append(
            {
                "fila": index,
                "columna": "sexo",
                "detalle": f"{sexo} no válido y se normalizó a desconocido",
                "valor": sexo,
            }
        )

    return errors, warnings
