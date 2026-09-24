import inspect
from collections.abc import Callable, Iterable
from typing import Any, Optional, Tuple

from quyca.domain.constants.articles_types import articles_types_list
from quyca.domain.models.affiliation_model import Affiliation
from quyca.domain.models.base_model import QueryParams
from quyca.domain.models.calculations_model import Calculations
from quyca.infrastructure.repositories import (
    affiliation_repository,
    calculations_repository,
    plot_repository,
    work_repository,
)
from quyca.domain.parsers import map_parser
from quyca.domain.parsers.export import export_plot_parser


PlotExporter = Callable[..., Any]


def call_exporter(exporter: PlotExporter, **available: Any) -> Any:
    accepted_params = inspect.signature(exporter).parameters
    kwargs = {name: value for name, value in available.items() if name in accepted_params}
    return exporter(**kwargs)


def export_affiliations_by_product_type(
    affiliation_id: str,
    affiliation_type: str,
    query_params: QueryParams,
) -> Iterable[dict[str, Any]]:
    plot = query_params.plot
    if plot is None:
        raise ValueError("El parámetro 'plot' es obligatorio.")

    relation_type = {
        "faculties_by_product_type": "faculty",
        "departments_by_product_type": "department",
        "research_groups_by_product_type": "group",
    }[plot]

    if affiliation_type == "institution":
        return plot_repository.get_affiliations_scienti_works_count_by_institution(
            affiliation_id,
            relation_type,
            query_params,
        )

    if affiliation_type == "faculty" and relation_type == "department":
        return plot_repository.get_departments_scienti_works_count_by_faculty(
            affiliation_id,
            query_params,
        )

    if affiliation_type in {"faculty", "department"} and relation_type == "group":
        return plot_repository.get_groups_scienti_works_count_by_faculty_or_department(
            affiliation_id,
            query_params,
        )

    raise ValueError(f"El plot '{query_params.plot}' no está disponible " f"para la afiliación '{affiliation_type}'.")


def export_citations_by_affiliation(
    affiliation_id: str,
    affiliation_type: str,
    query_params: QueryParams,
) -> Iterable[dict[str, Any]]:
    plot = query_params.plot
    if plot is None:
        raise ValueError("El parámetro 'plot' es obligatorio.")

    relation_type = {
        "citations_by_faculty": "faculty",
        "citations_by_department": "department",
        "citations_by_research_group": "group",
    }[plot]

    if affiliation_type == "institution":
        return plot_repository.get_affiliations_citations_count_by_institution(
            affiliation_id,
            relation_type,
            query_params,
        )

    if affiliation_type == "faculty" and relation_type == "department":
        return plot_repository.get_departments_citations_count_by_faculty(
            affiliation_id,
            query_params,
        )

    if affiliation_type in {"faculty", "department"} and relation_type == "group":
        return plot_repository.get_groups_citations_count_by_faculty_or_department(
            affiliation_id,
            query_params,
        )

    raise ValueError(f"El plot '{query_params.plot}' no está disponible " f"para la afiliación '{affiliation_type}'.")


def export_apc_expenses_by_affiliation(
    affiliation_id: str,
    affiliation_type: str,
    query_params: QueryParams,
) -> Iterable[dict[str, Any]]:
    plot = query_params.plot
    if plot is None:
        raise ValueError("El parámetro 'plot' es obligatorio.")

    relation_type = {
        "apc_expenses_by_faculty": "faculty",
        "apc_expenses_by_department": "department",
        "apc_expenses_by_group": "group",
    }[plot]

    if affiliation_type == "institution":
        return plot_repository.get_affiliations_apc_expenses_by_institution(
            affiliation_id,
            relation_type,
            query_params,
        )

    if affiliation_type == "faculty" and relation_type == "department":
        return plot_repository.get_departments_apc_expenses_by_faculty(
            affiliation_id,
            query_params,
        )

    if affiliation_type in {"faculty", "department"} and relation_type == "group":
        return plot_repository.get_groups_apc_expenses_by_faculty_or_department(
            affiliation_id,
            query_params,
        )

    raise ValueError(f"El plot '{query_params.plot}' no está disponible " f"para la afiliación '{affiliation_type}'.")


def export_h_index_by_affiliation(
    affiliation_id: str,
    affiliation_type: str,
    query_params: QueryParams,
) -> Iterable[dict[str, Any]]:
    plot = query_params.plot
    if plot is None:
        raise ValueError("El parámetro 'plot' es obligatorio.")

    relation_type = {
        "h_index_by_faculty": "faculty",
        "h_index_by_department": "department",
        "h_index_by_research_group": "group",
    }[plot]

    if affiliation_type == "institution":
        return plot_repository.get_affiliations_works_citations_count_by_institution(
            affiliation_id,
            relation_type,
            query_params,
        )

    if affiliation_type == "faculty" and relation_type == "department":
        return plot_repository.get_departments_works_citations_count_by_faculty(
            affiliation_id,
            query_params,
        )

    if affiliation_type in {"faculty", "department"} and relation_type == "group":
        return plot_repository.get_groups_works_citations_count_by_faculty_or_department(
            affiliation_id,
            query_params,
        )

    raise ValueError(f"El plot '{query_params.plot}' no está disponible " f"para la afiliación '{affiliation_type}'.")


def export_products_by_database(
    affiliation_id: str,
    affiliation_type: str,
    query_params: QueryParams,
) -> Iterable[dict[str, Any]]:
    if affiliation_type not in {
        "institution",
        "faculty",
        "department",
        "group",
    }:
        raise ValueError(f"Tipo de afiliación no válido: '{affiliation_type}'.")

    return plot_repository.get_products_by_database_by_affiliation(
        affiliation_id,
        query_params,
    )


def export_coauthorship_by_country_map(
    affiliation_id: str,
    query_params: QueryParams,
) -> dict[str, dict[str, Any]]:
    data = plot_repository.get_coauthorship_by_country_map_by_affiliation(affiliation_id, query_params)
    return map_parser.aggregate_coauthorship_by_country(data)


def export_coauthorship_by_colombian_department_map(
    affiliation_id: str,
    query_params: QueryParams,
) -> dict[str, dict[str, Any]]:
    data = plot_repository.get_coauthorship_by_colombian_department_map_by_affiliation(affiliation_id, query_params)
    return map_parser.aggregate_coauthorship_by_colombian_department(data)


def export_institutional_coauthorship_network(affiliation_id: str) -> Calculations:
    return calculations_repository.get_affiliation_calculations(affiliation_id)


def export_annual_evolution_by_scienti_classification(
    affiliation_id: str,
    query_params: QueryParams,
) -> Iterable[Any]:
    pipeline_params = {"project": ["year_published", "types"]}
    return work_repository.get_works_by_affiliation(affiliation_id, query_params, pipeline_params)


def export_annual_citation_count(
    affiliation_id: str,
    query_params: QueryParams,
) -> Iterable[Any]:
    pipeline_params = {"project": ["citations_by_year"]}
    return work_repository.get_works_by_affiliation(affiliation_id, query_params, pipeline_params)


def export_annual_articles_open_access(
    affiliation_id: str,
    query_params: QueryParams,
) -> Iterable[Any]:
    pipeline_params = {
        "project": ["year_published", "open_access"],
        "match": {"types.type": {"$in": articles_types_list}},
    }
    return work_repository.get_works_by_affiliation(affiliation_id, query_params, pipeline_params)


def export_annual_articles_by_top_publishers(
    affiliation_id: str,
    query_params: QueryParams,
) -> Iterable[Any]:
    pipeline_params = {
        "work_project": ["source.name", "source.publisher.name", "source.id", "year_published", "types"],
        "match": {
            "types.type": {"$in": articles_types_list},
            "source.publisher.name": {"$ne": None},
        },
    }
    return work_repository.get_works_with_source_by_affiliation(affiliation_id, query_params, pipeline_params)


def export_most_used_title_words(affiliation_id: str) -> Calculations:
    return calculations_repository.get_affiliation_calculations(affiliation_id)


def export_articles_by_publisher(
    affiliation_id: str,
    query_params: QueryParams,
) -> Iterable[Any]:
    pipeline_params = {
        "work_project": ["source.id", "source.publisher.name", "source.name"],
        "match": {"types.type": {"$in": articles_types_list}},
    }
    return work_repository.get_works_with_source_by_affiliation(affiliation_id, query_params, pipeline_params)


def export_products_by_subject(
    affiliation_id: str,
    query_params: QueryParams,
) -> Iterable[Any]:
    pipeline_params = {
        "project": ["primary_topic.display_name"],
        "match": {"primary_topic.display_name": {"$exists": True, "$ne": None}},
    }
    return work_repository.get_works_by_affiliation(affiliation_id, query_params, pipeline_params)


def export_articles_by_access_route(
    affiliation_id: str,
    query_params: QueryParams,
) -> Iterable[Any]:
    pipeline_params = {
        "match": {"types.type": {"$in": articles_types_list}},
        "project": ["open_access"],
    }
    return work_repository.get_works_by_affiliation(affiliation_id, query_params, pipeline_params)


def export_active_authors_by_sex(
    affiliation_id: str,
    query_params: QueryParams,
) -> Iterable[Any]:
    return plot_repository.get_active_authors_by_sex(affiliation_id, query_params)


def export_active_authors_by_age_range(
    affiliation_id: str,
    query_params: QueryParams,
) -> Iterable[Any]:
    return plot_repository.get_active_authors_by_age_range(affiliation_id, query_params)


def export_articles_by_scienti_category(
    affiliation_id: str,
    query_params: QueryParams,
) -> list:
    pipeline_params = {
        "match": {"types.type": {"$in": articles_types_list}},
        "project": ["ranking"],
    }
    works = work_repository.get_works_by_affiliation(affiliation_id, query_params, pipeline_params)
    return list(works)


def export_articles_by_scimago_quartile(
    affiliation_id: str,
    query_params: QueryParams,
) -> Iterable[Any]:
    pipeline_params = {
        "work_project": ["source.id", "source.name", "date_published", "source.ranking"],
        "match": {"types.type": {"$in": articles_types_list}},
    }
    return work_repository.get_works_with_source_by_affiliation(affiliation_id, query_params, pipeline_params)


def export_articles_by_publishing_institution(
    affiliation_id: str,
    query_params: QueryParams,
) -> Tuple[Iterable[Any], Optional[Affiliation]]:
    institution = affiliation_repository.get_affiliation_by_id(affiliation_id)
    pipeline_params = {
        "work_project": ["source.id", "source.name", "source.publisher.name"],
        "match": {"types.type": {"$in": articles_types_list}},
    }
    works = work_repository.get_works_with_source_by_affiliation(affiliation_id, query_params, pipeline_params)
    return works, institution


def export_annual_apc_expenses(
    affiliation_id: str,
    query_params: QueryParams,
) -> Iterable[Any]:
    pipeline_params = {
        "work_project": [
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
    return work_repository.get_works_with_source_by_affiliation(affiliation_id, query_params, pipeline_params)


AFFILIATION_PLOT_EXPORTERS: dict[str, PlotExporter] = {
    "faculties_by_product_type": export_affiliations_by_product_type,
    "departments_by_product_type": export_affiliations_by_product_type,
    "research_groups_by_product_type": export_affiliations_by_product_type,
    "citations_by_faculty": export_citations_by_affiliation,
    "citations_by_department": export_citations_by_affiliation,
    "citations_by_research_group": export_citations_by_affiliation,
    "apc_expenses_by_faculty": export_apc_expenses_by_affiliation,
    "apc_expenses_by_department": export_apc_expenses_by_affiliation,
    "apc_expenses_by_group": export_apc_expenses_by_affiliation,
    "h_index_by_faculty": export_h_index_by_affiliation,
    "h_index_by_department": export_h_index_by_affiliation,
    "h_index_by_research_group": export_h_index_by_affiliation,
    "products_by_database": export_products_by_database,
    "coauthorship_by_country_map": export_coauthorship_by_country_map,
    "coauthorship_by_colombian_department_map": export_coauthorship_by_colombian_department_map,
    "institutional_coauthorship_network": export_institutional_coauthorship_network,
    "annual_evolution_by_scienti_classification": export_annual_evolution_by_scienti_classification,
    "annual_citation_count": export_annual_citation_count,
    "annual_articles_open_access": export_annual_articles_open_access,
    "annual_articles_by_top_publishers": export_annual_articles_by_top_publishers,
    "most_used_title_words": export_most_used_title_words,
    "articles_by_publisher": export_articles_by_publisher,
    "products_by_subject": export_products_by_subject,
    "articles_by_access_route": export_articles_by_access_route,
    "active_authors_by_sex": export_active_authors_by_sex,
    "active_authors_by_age_range": export_active_authors_by_age_range,
    "articles_by_scienti_category": export_articles_by_scienti_category,
    "articles_by_scimago_quartile": export_articles_by_scimago_quartile,
    "articles_by_publishing_institution": export_articles_by_publishing_institution,
    "annual_apc_expenses": export_annual_apc_expenses,
}


def get_plot_csv(
    affiliation_id: str,
    affiliation_type: str,
    query_params: QueryParams,
):
    plot = query_params.plot

    if not plot:
        raise ValueError("The 'plot' parameter is required.")

    exporter = AFFILIATION_PLOT_EXPORTERS.get(plot)

    if exporter is None:
        raise ValueError(f"The plot '{plot}' is not available for affiliation '{affiliation_type}'.")

    data = call_exporter(
        exporter,
        affiliation_id=affiliation_id,
        affiliation_type=affiliation_type,
        query_params=query_params,
    )

    return export_plot_parser.parse_plot_to_csv(
        plot,
        data,
    )
