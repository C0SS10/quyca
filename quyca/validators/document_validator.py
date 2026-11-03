import re
import unicodedata
from typing import List, Dict, Any
from quyca.validators import base_validator
from quyca.constants.staff_field_values import DOCUMENT_TYPES

PASSPORT_RE = re.compile(r"^[A-Za-z0-9]+$")

_NUMERIC_ID_TYPES = {"cédula de ciudadanía", "cédula de extranjería"}

_INTEGER_TEXT_RE = re.compile(r"^[0-9]+(?:\.0+)?$")


def _is_numeric_identification(value: Any) -> bool:
    """Accept integer-like values even when Excel stored them as text or float strings."""
    if base_validator.is_empty(value):
        return False

    normalized = unicodedata.normalize("NFKC", str(value)).strip()
    return bool(_INTEGER_TEXT_RE.match(normalized))


def validate(tipo_documento: str, identificacion: str, index: int) -> List[Dict[str, Any]]:
    errors: List[Dict[str, Any]] = []

    if not base_validator.is_empty(tipo_documento):
        tnorm = str(tipo_documento).strip().lower()

        if tnorm not in DOCUMENT_TYPES:
            errors.append(
                {
                    "fila": index,
                    "columna": "tipo_documento",
                    "detalle": f"El tipo de documento '{tipo_documento}' no es válido",
                    "value": tipo_documento,
                }
            )

        if not base_validator.is_empty(identificacion):
            id_str = str(identificacion).strip()

            if tnorm in _NUMERIC_ID_TYPES and not _is_numeric_identification(identificacion):
                errors.append(
                    {
                        "fila": index,
                        "columna": "identificación",
                        "detalle": f"La {tnorm} debe ser numérica",
                        "valor": identificacion,
                    }
                )
            elif tnorm == "pasaporte" and not PASSPORT_RE.match(id_str):
                errors.append(
                    {
                        "fila": index,
                        "columna": "identificación",
                        "detalle": "Formato inválido para pasaporte",
                        "valor": identificacion,
                    }
                )

    return errors
