import re
from dataclasses import dataclass

AUTHORS_COUNT_PATTERN = re.compile(r"^(?P<min>\d+)?(?P<dash>-)?(?P<max>\d+)?$")
ERROR_MESSAGE = "authors_count inválido. Formatos válidos: '5', '5-', '-5' o '5-8'"


@dataclass(frozen=True)
class AuthorsCountRange:
    min: int | None = None
    max: int | None = None


def parse_authors_count(value: str) -> AuthorsCountRange:
    match = AUTHORS_COUNT_PATTERN.fullmatch(value.strip())
    if not match or (match["min"] is None and match["max"] is None):
        raise ValueError(ERROR_MESSAGE)

    min_count = int(match["min"]) if match["min"] else None
    max_count = int(match["max"]) if match["max"] else None

    if not match["dash"]:
        max_count = min_count

    if (min_count is not None and min_count < 1) or (max_count is not None and max_count < 1):
        raise ValueError("authors_count inválido: los valores deben ser mayores que 0")
    if min_count is not None and max_count is not None and min_count > max_count:
        raise ValueError("authors_count inválido: el mínimo no puede ser mayor que el máximo")

    return AuthorsCountRange(min=min_count, max=max_count)
