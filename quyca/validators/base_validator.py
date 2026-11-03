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
