from typing import List, Dict, Any


def _get(item: Dict[str, Any], *keys: str, default: Any = "") -> Any:
    """Retrieves the first available key value from a dictionary."""
    for key in keys:
        if key in item:
            return item[key]
    return default


def group_errors(errors: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Groups errors by column and detail."""
    grouped: dict[tuple[str, str], dict[str, Any]] = {}
    for e in errors:
        col = _get(e, "columna", "columna", default="")
        detail = _get(e, "detalle", "detalle", default="")
        row = _get(e, "fila", "fila", default=None)

        key = (str(col), str(detail))
        if key not in grouped:
            grouped[key] = {"detalle": detail, "fila": []}
        if row is not None:
            grouped[key]["fila"].append(row)

    return [
        {
            "columna": col,
            "detalle": info["detalle"],
            "ejemplos": info["fila"][:3],
            "total_filas": len(info["fila"]),
        }
        for (col, _), info in grouped.items()
    ]


def group_warnings(warnings: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Groups warnings by column, detail and value."""
    grouped: dict[tuple[str, str, str], dict[str, Any]] = {}
    for w in warnings:
        col = _get(w, "columna", "columna", default="")
        detail = _get(w, "detalle", "detalle", default="")
        value = _get(w, "valor", "valor", default="")
        row = _get(w, "fila", "fila", default=None)

        key = (str(col), str(detail), str(value))
        if key not in grouped:
            grouped[key] = {"detalle": detail, "valor": value, "fila": []}
        if row is not None:
            grouped[key]["fila"].append(row)

    return [
        {
            "columna": col,
            "detalle": info["detalle"],
            "valor": info["valor"],
            "ejemplos": info["fila"][:3],
            "total_filas": len(info["fila"]),
        }
        for (col, _, _), info in grouped.items()
    ]
