from typing import Any, Callable
from pymongo.command_cursor import CommandCursor

from quyca.constants.articles_types import articles_types_list
from quyca.exceptions import InvalidParamException
from quyca.models.base_model import QueryParams
from quyca.parsers import bar_parser, map_parser, network_parser, pie_parser
from quyca.repositories import calculations_repository
from quyca.parsers import venn_parser
from quyca.repositories import affiliation_repository
from quyca.repositories import plot_repository
from quyca.repositories import work_repository

RELATION_PLOTS = {
    "faculties_by_product_type": ("product_type", "faculty"),
    "departments_by_product_type": ("product_type", "department"),
    "research_groups_by_product_type": ("product_type", "group"),
    "citations_by_faculty": ("citations", "faculty"),
    "citations_by_department": ("citations", "department"),
    "citations_by_research_group": ("citations", "group"),
    "apc_expenses_by_faculty": ("apc_expenses", "faculty"),
    "apc_expenses_by_department": ("apc_expenses", "department"),
    "apc_expenses_by_group": ("apc_expenses", "group"),
    "h_index_by_faculty": ("h_index", "faculty"),
    "h_index_by_department": ("h_index", "department"),
    "h_index_by_research_group": ("h_index", "group"),
}

RELATION_PLOT_PARSERS: dict[str, Callable[[CommandCursor], Any]] = {
    "product_type": bar_parser.parse_affiliations_by_product_type,
    "citations": pie_parser.parse_citations_by_affiliations,
    "apc_expenses": pie_parser.parse_apc_expenses_by_affiliations,
    "h_index": pie_parser.parse_h_index_by_affiliation,
}


def get_affiliation_plot(affiliation_id: str, affiliation_type: str, query_params: QueryParams) -> Any:
    plot_type = query_params.plot
    if plot_type in RELATION_PLOTS:
        metric, _ = RELATION_PLOTS[plot_type]
        return RELATION_PLOT_PARSERS[metric](get_relation_plot_data(affiliation_id, affiliation_type, query_params))

    func: Callable[[str, QueryParams], dict[str, Any] | None] | None = globals().get(f"plot_{plot_type}")
    if func is None:
        raise InvalidParamException(f"The plot '{plot_type}' is not available for affiliation '{affiliation_type}'.")

    result = func(affiliation_id, query_params)
    if not (result is None or isinstance(result, dict)):
        raise TypeError(f"La función plot_{plot_type} debe retornar un dict o None, no {type(result)}.")
    return result


def get_relation_plot_data(affiliation_id: str, affiliation_type: str, query_params: QueryParams) -> CommandCursor:
    """Data of a RELATION_PLOTS plot, shared by the chart and its CSV export."""
    plot_type = str(query_params.plot)
    metric, relation_type = RELATION_PLOTS[plot_type]
    data = plot_repository.get_affiliations_metric(
        metric, affiliation_id, affiliation_type, relation_type, query_params
    )
    if data is None:
        raise InvalidParamException(
            f"El plot '{plot_type}' no está disponible para la afiliación '{affiliation_type}'."
        )
    return data


def plot_annual_evolution_by_impactu_classification(affiliation_id: str, query_params: QueryParams) -> dict:
    pipeline_params = {"project": ["year_published", "types"]}
    works = work_repository.get_works_by_affiliation(affiliation_id, query_params, pipeline_params)
    return bar_parser.parse_annual_evolution_by_impactu_classification(works)


def plot_annual_citation_count(affiliation_id: str, query_params: QueryParams) -> dict:
    pipeline_params = {"project": ["citations_by_year"]}
    works = work_repository.get_works_by_affiliation(affiliation_id, query_params, pipeline_params)
    return bar_parser.parse_annual_citation_count(works)


def plot_annual_articles_open_access(affiliation_id: str, query_params: QueryParams) -> dict:
    pipeline_params = {
        "project": ["year_published", "open_access"],
        "match": {"types.type": {"$in": articles_types_list}},
    }
    works = work_repository.get_works_by_affiliation(affiliation_id, query_params, pipeline_params)
    return bar_parser.parse_annual_articles_open_access(works)


def plot_annual_articles_by_top_publishers(affiliation_id: str, query_params: QueryParams) -> dict:
    pipeline_params = {
        "project": ["source.name", "source.publisher.name", "source.id", "year_published", "types"],
        "match": {
            "types.type": {"$in": articles_types_list},
            "source.publisher.name": {"$ne": None},
        },
    }
    works = work_repository.get_works_by_affiliation(affiliation_id, query_params, pipeline_params)
    return bar_parser.parse_annual_articles_by_top_publishers(works)


def plot_most_used_title_words(affiliation_id: str, query_params: QueryParams) -> dict:
    data = calculations_repository.get_affiliation_calculations(affiliation_id)
    return pie_parser.parse_most_used_title_words(data)


def plot_articles_by_publisher(affiliation_id: str, query_params: QueryParams) -> dict:
    pipeline_params = {
        "project": ["source.id", "source.publisher.name", "source.name"],
        "match": {"types.type": {"$in": articles_types_list}},
    }
    works = work_repository.get_works_by_affiliation(affiliation_id, query_params, pipeline_params)
    return pie_parser.parse_articles_by_publisher(works)


def plot_products_by_subject(affiliation_id: str, query_params: QueryParams) -> dict:
    pipeline_params = {
        "project": ["primary_topic.display_name"],
        "match": {"primary_topic.display_name": {"$exists": True, "$ne": None}},
    }
    works = work_repository.get_works_by_affiliation(affiliation_id, query_params, pipeline_params)
    return pie_parser.parse_products_by_subject(works)


def plot_products_by_database(affiliation_id: str, query_params: QueryParams) -> dict:
    data = plot_repository.get_products_by_database_by_affiliation(affiliation_id, query_params)
    return venn_parser.parse_products_by_database(data)


def plot_articles_by_access_route(affiliation_id: str, query_params: QueryParams) -> dict:
    pipeline_params = {
        "match": {"types.type": {"$in": articles_types_list}},
        "project": ["open_access"],
    }
    works = work_repository.get_works_by_affiliation(affiliation_id, query_params, pipeline_params)
    return pie_parser.parse_products_by_access_route(works)


def plot_active_authors_by_sex(affiliation_id: str, query_params: QueryParams) -> dict:
    data = plot_repository.get_active_authors_by_sex(affiliation_id, query_params)
    return pie_parser.parse_active_authors_by_sex(data)


def plot_active_authors_by_age_range(affiliation_id: str, query_params: QueryParams) -> dict:
    persons = plot_repository.get_active_authors_by_age_range(affiliation_id, query_params)
    return pie_parser.parse_active_authors_by_age_range(persons)


def plot_articles_by_scienti_category(affiliation_id: str, query_params: QueryParams) -> dict:
    pipeline_params = {
        "match": {"types.type": {"$in": articles_types_list}},
        "project": ["ranking"],
    }
    works = work_repository.get_works_by_affiliation(affiliation_id, query_params, pipeline_params)
    return pie_parser.parse_articles_by_scienti_category(list(works))


def plot_articles_by_scimago_quartile(affiliation_id: str, query_params: QueryParams) -> dict:
    pipeline_params = {
        "project": ["source.id", "source.name", "date_published", "source.ranking"],
        "match": {"types.type": {"$in": articles_types_list}},
    }
    works = work_repository.get_works_by_affiliation(affiliation_id, query_params, pipeline_params)
    return pie_parser.parse_articles_by_scimago_quartile(works)


def plot_articles_by_publishing_institution(affiliation_id: str, query_params: QueryParams) -> dict:
    institution = affiliation_repository.get_affiliation_by_id(affiliation_id)
    pipeline_params = {
        "project": ["source.id", "source.name", "source.publisher.name"],
        "match": {"types.type": {"$in": articles_types_list}},
    }
    works = work_repository.get_works_by_affiliation(affiliation_id, query_params, pipeline_params)
    return pie_parser.parse_articles_by_publishing_institution(works, institution)


def plot_coauthorship_by_country_map(affiliation_id: str, query_params: QueryParams) -> dict:
    data = plot_repository.get_coauthorship_by_country_map_by_affiliation(affiliation_id, query_params)
    return map_parser.parse_coauthorship_by_country_map(data)


def plot_coauthorship_by_colombian_department_map(affiliation_id: str, query_params: QueryParams) -> dict:
    data = plot_repository.get_coauthorship_by_colombian_department_map_by_affiliation(affiliation_id, query_params)
    return map_parser.parse_coauthorship_by_colombian_department_map(data)


def plot_institutional_coauthorship_network(affiliation_id: str, query_params: QueryParams) -> dict:
    data = calculations_repository.get_affiliation_calculations(affiliation_id)
    return network_parser.parse_institutional_coauthorship_network(data)


def plot_annual_apc_expenses(affiliation_id: str, query_params: QueryParams) -> dict:
    pipeline_params = {
        "project": [
            "source.id",
            "source.name",
            "source.apc",
            "year_published",
            "authors.affiliations.addresses.country_code",
            "types",
            "year_published",
            "open_access.open_access_status",
            "subjects",
            "primary_topic.id",
            "authors.ranking",
        ],
        "match": {
            "source.apc.charges": {"$exists": True, "$ne": None},
            "source.apc.currency": {"$exists": True, "$ne": None},
        },
    }
    works = work_repository.get_works_by_affiliation(affiliation_id, query_params, pipeline_params)
    return bar_parser.parse_annual_apc_expenses(works)
