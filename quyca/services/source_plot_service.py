from typing import Any, Callable

from quyca.exceptions import InvalidParamException
from quyca.models.base_model import QueryParams
from quyca.parsers import bar_parser
from quyca.repositories import plot_repository


def get_source_products_plot(source_id: str, query_params: QueryParams) -> dict[str, Any] | None:
    plot_type = query_params.plot

    function: Callable[[str, QueryParams], dict[str, Any] | None] | None = globals().get(f"plot_{plot_type}")
    if function is None:
        raise InvalidParamException(f"The plot '{plot_type}' is not available for source.")

    result = function(source_id, query_params)
    if not (result is None or isinstance(result, dict)):
        raise TypeError(f"La función plot_{plot_type} debe retornar un dict o None, no {type(result)}.")
    return result


def plot_annual_scimago_quartile(source_id: str, query_params: QueryParams | None = None) -> dict:
    data = plot_repository.get_annual_scimago_quartile_by_source(source_id)
    return bar_parser.parse_annual_scimago_quartile(data)
