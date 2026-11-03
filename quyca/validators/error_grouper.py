from typing import List, Dict, Any


def group_errors(errors: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Groups errors by column and detail."""
    grouped: dict[tuple[str, str], dict[str, Any]] = {}
    for e in errors:
        col, detail, row = e.get("columna", ""), e.get("detalle", ""), e.get("fila")

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
        col, detail, value, row = w.get("columna", ""), w.get("detalle", ""), w.get("valor", ""), w.get("fila")

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
