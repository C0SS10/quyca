import math
from typing import Any, Union


def clean_nan(value: Union[str, float, None]) -> Any | None:
    """
    This function converts the NaN values to None. Because JSON does not support NaN values. In sources many fields like 'ranking.rank' and 'publisher.name' are affected

    Parameter
    ---------
    value: The value to be checked for NaN.

    Response
    --------
    If the value is NaN, it returns None. Otherwise, it returns the original value.
    """
    if isinstance(value, float) and math.isnan(value):
        return None
    return value
