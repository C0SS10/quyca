from typing import Any
from quyca.constants.articles_types import articles_types_list
from quyca.exceptions import InvalidParamException
from quyca.models.base_model import QueryParams
from quyca.parsers import bar_parser, map_parser, network_parser, pie_parser
from quyca.repositories import calculations_repository
from quyca.parsers import venn_parser
from quyca.repositories import affiliation_repository
from quyca.repositories import person_repository
from quyca.repositories import plot_repository
from quyca.repositories import work_repository


def get_person_plot(person_id: str, query_params: QueryParams) -> dict[str, Any]:
    func = globals().get(f"plot_{query_params.plot}")
    if not callable(func):
        raise InvalidParamException(f"The plot '{query_params.plot}' is not available for person.")

    result = func(person_id, query_params)
    if not isinstance(result, dict):
        raise TypeError(f"La función 'plot_{query_params.plot}' debe retornar un dict, no {type(result)}.")
    return result


def plot_annual_evolution_by_impactu_classification(person_id: str, query_params: QueryParams) -> dict:
    pipeline_params = {"project": ["year_published", "types"]}
    works = work_repository.get_works_by_person(person_id, query_params, pipeline_params)
    return bar_parser.parse_annual_evolution_by_impactu_classification(works)


def plot_annual_citation_count(person_id: str, query_params: QueryParams) -> dict:
    pipeline_params = {"project": ["citations_by_year"]}
    works = work_repository.get_works_by_person(person_id, query_params, pipeline_params)
    return bar_parser.parse_annual_citation_count(works)


def plot_annual_apc_expenses(person_id: str, query_params: QueryParams) -> dict:
    pipeline_params = {
        "project": [
            "source.id",
            "source.name",
            "year_published",
            "source.apc",
        ]
    }
    works = work_repository.get_works_by_person(person_id, query_params, pipeline_params)
    return bar_parser.parse_annual_apc_expenses(works)


def plot_annual_articles_open_access(person_id: str, query_params: QueryParams) -> dict:
    pipeline_params = {
        "project": ["year_published", "open_access"],
        "match": {"types.type": {"$in": articles_types_list}},
    }
    works = work_repository.get_works_by_person(person_id, query_params, pipeline_params)
    return bar_parser.parse_annual_articles_open_access(works)


def plot_annual_articles_by_top_publishers(person_id: str, query_params: QueryParams) -> dict:
    pipeline_params = {
        "project": [
            "source.id",
            "source.name",
            "source.publisher.name",
            "year_published",
            "types",
            "source.apc",
        ],
        "match": {
            "types.type": {"$in": articles_types_list},
            "source.publisher.name": {"$ne": None},
        },
    }
    works = work_repository.get_works_by_person(person_id, query_params, pipeline_params)
    return bar_parser.parse_annual_articles_by_top_publishers(works)


def plot_most_used_title_words(person_id: str, query_params: QueryParams) -> dict:
    data = calculations_repository.get_person_calculations(person_id)
    return pie_parser.parse_most_used_title_words(data)


def plot_articles_by_publisher(person_id: str, query_params: QueryParams) -> dict:
    pipeline_params = {
        "project": ["source.id", "source.name", "source.publisher.name"],
        "match": {"types.type": {"$in": articles_types_list}},
    }
    works = work_repository.get_works_by_person(person_id, query_params, pipeline_params)
    return pie_parser.parse_articles_by_publisher(works)


def plot_products_by_subject(person_id: str, query_params: QueryParams) -> dict:
    pipeline_params = {
        "match": {"primary_topic.display_name": {"$exists": True, "$ne": None}},
        "project": ["primary_topic.display_name"],
    }
    works = work_repository.get_works_by_person(person_id, query_params, pipeline_params)
    return pie_parser.parse_products_by_subject(works)


def plot_products_by_database(person_id: str, query_params: QueryParams) -> dict:
    data = plot_repository.get_products_by_database_by_person(person_id, query_params)
    return venn_parser.parse_products_by_database(data)


def plot_articles_by_access_route(person_id: str, query_params: QueryParams) -> dict:
    pipeline_params = {
        "match": {"types.type": {"$in": articles_types_list}},
        "project": ["open_access"],
    }
    works = work_repository.get_works_by_person(person_id, query_params, pipeline_params)
    return pie_parser.parse_products_by_access_route(works)


def plot_articles_by_scienti_category(person_id: str, query_params: QueryParams) -> dict:
    pipeline_params = {
        "match": {"types.type": {"$in": articles_types_list}},
        "project": ["ranking"],
    }
    works = work_repository.get_works_by_person(person_id, query_params, pipeline_params)
    return pie_parser.parse_articles_by_scienti_category(list(works))


def plot_articles_by_scimago_quartile(person_id: str, query_params: QueryParams) -> dict:
    pipeline_params = {
        "project": [
            "source.id",
            "source.name",
            "date_published",
            "source.ranking",
        ],
        "match": {"types.type": {"$in": articles_types_list}},
    }
    works = work_repository.get_works_by_person(person_id, query_params, pipeline_params)
    return pie_parser.parse_articles_by_scimago_quartile(works)


def plot_articles_by_publishing_institution(
    person_id: str,
    query_params: QueryParams,
) -> dict:
    person = person_repository.get_person_by_id(person_id, {"project": ["full_name", "affiliations"]})
    institution = None

    if person.affiliations:
        for affiliation in person.affiliations:
            if affiliation.types and any(
                affiliation_type.type not in ["faculty", "department", "group"]
                for affiliation_type in affiliation.types
            ):
                institution = affiliation_repository.get_affiliation_by_id(str(affiliation.id))
                break

    work_pipeline_params: dict[str, Any] = {
        "project": ["source.id", "source.name", "source.publisher.name"],
        "match": {"types.type": {"$in": articles_types_list}},
    }

    works = work_repository.get_works_by_person(
        person_id,
        query_params,
        work_pipeline_params,
    )

    return pie_parser.parse_articles_by_publishing_institution(
        works,
        institution,
    )


def plot_coauthorship_by_country_map(person_id: str, query_params: QueryParams) -> dict:
    data = plot_repository.get_coauthorship_by_country_map_by_person(person_id, query_params)
    return map_parser.parse_coauthorship_by_country_map(data)


def plot_coauthorship_by_colombian_department_map(person_id: str, query_params: QueryParams) -> dict:
    data = plot_repository.get_coauthorship_by_colombian_department_map_by_person(person_id, query_params)
    return map_parser.parse_coauthorship_by_colombian_department_map(data)


def plot_author_coauthorship_network(person_id: str, query_params: QueryParams) -> dict:
    data = calculations_repository.get_person_calculations(person_id)
    return network_parser.parse_institutional_coauthorship_network(data)
