from typing import Iterable, Iterator, Union
from urllib.parse import urlparse
from quyca.constants.external_urls import external_urls_dict
from quyca.constants.summary_rules import WORK_SUMMARY_FIELDS
from quyca.models.base_model import QueryParams, Title, ProductType, ExternalUrl, Type
from quyca.models.patent_model import Patent
from quyca.models.project_model import Project
from quyca.models.work_model import Work
from quyca.repositories import person_repository

SUMMARY_AUTHORS_LIMIT = 10
# As in OpenAlex: product listings show the first 100 authors; the work detail and /authors show all of them.
LISTING_AUTHORS_LIMIT = 100


def get_entity_data(workables: Iterable, view: str = "full") -> list:
    authors_limit = SUMMARY_AUTHORS_LIMIT if view == "summary" else None
    data = []
    for workable in workables:
        limit_authors(workable, authors_limit)
        set_title_and_language(workable)
        set_product_types(workable)
        set_authors_affiliation_years(workable)
        data.append(workable)
    return data


def set_title_and_language(workable: Union[Work, Patent, Project]) -> None:
    if not workable.titles:
        workable.title = None
        workable.language = None
        return

    hierarchy = ["openalex", "scienti", "minciencias", "ranking", "scholar"]

    def order(title: Title) -> float:
        return hierarchy.index(title.source) if title.source in hierarchy else float("inf")

    first_title = min(workable.titles, key=order)
    workable.title = first_title.title
    workable.language = first_title.lang


def set_product_types(workable: Union[Work, Patent, Project]) -> None:
    def order(product_type: ProductType) -> float:
        hierarchy = ["openalex", "scienti", "minciencias", "scholar"]
        return hierarchy.index(product_type.source) if product_type.source in hierarchy else float("inf")

    scienti_levels = {ptype.level for ptype in workable.types or [] if ptype.source == "scienti"}

    def filter_func(product_type: Type) -> bool:
        if product_type.source == "minciencias" and product_type.level == 0:
            return False
        if product_type.source == "scienti":
            if 2 in scienti_levels:
                return (product_type.level or 0) >= 2
            else:
                return (product_type.level or 0) >= 1
        return True

    types: Iterator[Type] = filter(filter_func, workable.types or [])
    product_types: list[ProductType] = [ProductType(name=x.type, source=x.source) for x in types]
    workable.product_types = sorted(product_types, key=order)


def set_authors_external_ids(workable: Union[Work, Patent, Project]) -> None:
    if not workable.authors:
        return

    if isinstance(workable.authors, str):
        return

    for author in workable.authors:
        if author.id:
            author.external_ids = person_repository.get_person_external_ids(str(author.id))


def limit_authors(workable: Union[Work, Patent, Project], limit: int | None = None) -> None:
    if not workable.authors or limit is None:
        return
    if isinstance(workable.authors, str):
        return
    if len(workable.authors) > limit:
        workable.authors = workable.authors[:limit]


def set_external_ids(workable: Union[Work, Patent, Project]) -> None:
    if not workable.external_ids:
        return

    if workable.external_urls is None:
        workable.external_urls = []

    new_external_ids = []
    for external_id in workable.external_ids:
        if external_id.source in ["minciencias", "scienti"]:
            new_external_ids.append(external_id)
        else:
            url_value = str(external_id.id)
            workable.external_urls.append(ExternalUrl(url=url_value, source=external_id.source))
    workable.external_ids = list(set(new_external_ids))


def set_external_urls(workable: Union[Work, Patent, Project]) -> None:
    if not workable.external_urls:
        return
    new_external_urls = []
    for external_url in workable.external_urls:
        url = str(external_url.url)
        if urlparse(url).scheme and urlparse(url).netloc:
            new_external_urls.append(external_url)
        else:
            source = external_url.source
            if source is not None and source in external_urls_dict and url != "":
                new_external_urls.append(
                    ExternalUrl(
                        url=external_urls_dict[source].format(id=url),
                        source=source,
                    )
                )
    workable.external_urls = list(set(new_external_urls))


def set_authors_affiliation_years(workables: list | Work | Patent | Project) -> None:
    if not isinstance(workables, list):
        workables = [workables]
    person_ids = {a.id for d in workables for a in (d.authors or []) if a.id}
    years_by_person = person_repository.get_affiliation_years(person_ids)
    for workable in workables:
        for author in workable.authors or []:
            author_years = years_by_person.get(author.id, {})
            for aff in author.affiliations or []:
                aff.years = author_years.get(aff.id, [])


def build_pipeline_params(view: str, summary_fields: list[str], **extra: str) -> dict:
    """The summary view only projects the fields its cards show."""
    return {"project": summary_fields, **extra} if view == "summary" else {}


def build_works_pipeline_params(query_params: QueryParams) -> dict:
    """?fields= projects exactly the requested fields at the end of the pipeline; without it the view decides.
    `authors_limit` only applies to listings (set_search_end_stages); a work looked up by DOI keeps all its authors."""
    authors_limit = SUMMARY_AUTHORS_LIMIT if query_params.view == "summary" else LISTING_AUTHORS_LIMIT
    if fields := query_params.selected_fields:
        return {"project": ["_id", *(field for field in fields if field != "id")], "authors_limit": authors_limit}
    return {**build_pipeline_params(query_params.view, WORK_SUMMARY_FIELDS), "authors_limit": authors_limit}
