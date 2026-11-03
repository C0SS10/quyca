from datetime import datetime, date
import pandas as pd
from typing import Dict, Any, Optional
from quyca.validators import base_validator


def validate(value: Any, field: str, index: int) -> Optional[Dict[str, Any]]:
    if base_validator.is_empty(value):
        return None
    if isinstance(value, str) and value.strip().lower() == "desconocido":
        return None
    if isinstance(value, (pd.Timestamp, datetime, date)):
        return None

    try:
        datetime.strptime(str(value).strip(), "%d/%m/%Y")
        return None
    except Exception:
        return {
            "fila": index,
            "columna": field,
            "detalle": f"Formato inválido, debe ser DD/MM/YYYY y enviaste: {value}",
            "valor": value,
        }
