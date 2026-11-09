from datetime import datetime, date
import pandas as pd
from typing import Dict, Any, List, Tuple
from quyca.constants.staff_field_values import EXCEL_ZERO_DATES
from quyca.normalizers.staff_normalizer import split_date_text
from quyca.validators import base_validator

DATE_FIELDS = ["fecha_nacimiento", "fecha_inicial_vinculación", "fecha_final_vinculación"]
MIN_YEAR = 1900


def _finding(index: int, field: str, detail: str, value: Any) -> Dict[str, Any]:
    return {"fila": index, "columna": field, "detalle": detail, "valor": value}


def validate(row: dict, index: int) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Checks the three Staff dates; returns (errors, warnings)."""
    errors: List[Dict[str, Any]] = []
    warnings: List[Dict[str, Any]] = []
    dates: Dict[str, date] = {}

    for field in DATE_FIELDS:
        value = row.get(field)
        if base_validator.is_empty(value):
            continue
        if isinstance(value, (pd.Timestamp, datetime, date)):
            dates[field] = pd.Timestamp(value).date()
            continue
        if str(value).strip().lower() == "desconocido":
            warnings.append(_finding(index, field, f"{field} fuera de catálogo, se normalizó a desconocido", value))
            continue

        parts = split_date_text(str(value))
        if parts is None:
            errors.append(_finding(index, field, f"Formato inválido, debe ser DD/MM/YYYY y enviaste: {value}", value))
            continue
        day, month, year = parts

        if f"{day:02d}/{month:02d}/{year}" in EXCEL_ZERO_DATES:
            warnings.append(_finding(index, field, "Fecha equivalente a vacío en Excel, se cargará vacía", value))
            continue

        try:
            parsed = date(year, month, day)
        except ValueError:
            if month > 12 and day <= 12:
                errors.append(_finding(index, field, "La fecha parece MM/DD/YYYY, use DD/MM/YYYY", value))
            else:
                errors.append(_finding(index, field, "La fecha no existe", value))
            continue

        if year < MIN_YEAR:
            errors.append(_finding(index, field, f"La fecha es anterior a {MIN_YEAR}", value))
        elif field == "fecha_nacimiento" and parsed > date.today():
            errors.append(_finding(index, field, "La fecha de nacimiento es posterior a hoy", value))
        else:
            dates[field] = parsed

    start, end = dates.get("fecha_inicial_vinculación"), dates.get("fecha_final_vinculación")
    if start and end and end < start:
        errors.append(
            _finding(
                index,
                "fecha_final_vinculación",
                "La fecha final de vinculación es anterior a la fecha inicial",
                row.get("fecha_final_vinculación"),
            )
        )

    return errors, warnings
