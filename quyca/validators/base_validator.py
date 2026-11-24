from typing import Union
import pandas as pd


def is_empty(value: Union[str, float, None]) -> bool:
    """Checks whether a value is None, NaN or an empty string."""
    if value is None:
        return True
    if isinstance(value, float) and pd.isna(value):
        return True
    if isinstance(value, str) and value.strip() == "":
        return True
    return False


def excel_row_index(dataframe_index: int) -> int:
    """Row number the user sees in Excel: 1-based and below the header row."""
    return dataframe_index + 2


def has_broken_encoding(value: str) -> bool:
    """True for text damaged by a wrong encoding: ¿ or � in place of a letter, or UTF-8 read as Latin-1 (Ã± for ñ)."""
    if "¿" in value or "�" in value:
        return True
    # Mojibake is the only text that turns into different, valid UTF-8 when encoded back with the wrong codec.
    for codec in ("cp1252", "latin-1"):
        try:
            if value.encode(codec).decode("utf-8") != value:
                return True
        except UnicodeError:
            continue
    return False
