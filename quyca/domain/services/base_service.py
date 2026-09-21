from typing import Generator, Iterator, Union, Any, Dict, List, Union, cast
from urllib.parse import urlparse
from quyca.domain.constants.institutions import institutions_list
from quyca.domain.models.affiliation_model import Affiliation, Relation
from quyca.domain.constants.external_urls import external_urls_dict
from quyca.domain.models.base_model import Title, ProductType, ExternalUrl, Type
from quyca.domain.models.patent_model import Patent
from quyca.domain.models.project_model import Project
from quyca.domain.models.work_model import Work
from quyca.infrastructure.repositories import affiliation_repository, person_repository
from quyca.domain.constants.sensitive_data import SENSITIVE_ID_SOURCES


def get_entity_data(documents: Generator) -> list:
    data = []
    for doc in documents:
        limit_authors(doc)
        set_title_and_language(doc)
        set_product_types(doc)
        data.append(doc)
    return data


def get_affiliation_by_entity_data(affiliation_type: str, affiliations: Generator) -> list:
    affiliations_list = []
    for affiliation in affiliations:
        set_relation_external_urls(affiliation)
        set_upper_affiliations_and_logo(affiliation, affiliation_type)
        affiliations_list.append(affiliation)
    return affiliations_list


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


def set_authors_external_ids(workable: Union[Work, Patent, Project], filter_sensitive: bool = False) -> None:
    if not workable.authors:
        return

    if isinstance(workable.authors, str):
        return

    for author in workable.authors:
        if author.id:
            external_ids = person_repository.get_person_external_ids(str(author.id))
            if filter_sensitive:
                external_ids = [eid for eid in external_ids if eid.source not in SENSITIVE_ID_SOURCES]
            author.external_ids = external_ids


def limit_authors(workable: Union[Work, Patent, Project], limit: int = 10) -> None:
    if not workable.authors:
        return
    if len(workable.authors) > limit:
        workable.authors = workable.authors[:limit]


def set_external_ids(workable: Union[Work, Patent, Project], filter_sensitive: bool = False) -> None:
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
            if external_url.source in external_urls_dict.keys() and url != "":
                new_external_urls.append(
                    ExternalUrl(
                        url=external_urls_dict[external_url.source].format(id=url),
                        source=external_url.source,
                    )
                )
    workable.external_urls = list(set(new_external_urls))


def set_relation_external_urls(affiliation: Affiliation) -> None:
    if not affiliation.relations:
        return

    if isinstance(affiliation.relations, (list, tuple)):
        relations_iterable = affiliation.relations
    elif isinstance(affiliation.relations, dict):
        relations_iterable = [Relation(**affiliation.relations)]
    elif isinstance(affiliation.relations, Relation):
        relations_iterable = [affiliation.relations]
    else:
        return

    for relation in relations_iterable:
        if not isinstance(relation, Relation):
            continue

        if getattr(relation, "external_urls", None):
            continue

        relation_external_urls = None

        if getattr(relation, "id", None):
            try:
                related_aff = affiliation_repository.get_affiliation_by_id(str(relation.id))
                if getattr(related_aff, "external_urls", None):
                    relation_external_urls = related_aff.external_urls
            except Exception:
                relation_external_urls = None

        relation.external_urls = relation_external_urls or []


def set_upper_affiliations_and_logo(affiliation: Affiliation, affiliation_type: str) -> None:
    if affiliation_type == "institution" and affiliation.external_urls:
        logo_url = next(
            (x.url for x in affiliation.external_urls if x.source == "logo"),
            None,
        )
        if logo_url:
            affiliation.logo = str(logo_url)

    relations_iterable: List[Relation]
    if isinstance(affiliation.relations, (list, tuple)):
        relations_iterable = affiliation.relations
    elif isinstance(affiliation.relations, Dict):
        relations_iterable = [Relation(**affiliation.relations)]
    elif isinstance(affiliation.relations, Relation):
        relations_iterable = [affiliation.relations]
    else:
        affiliation.affiliations = []
        return

    upper_affiliations: list[Relation] = []
    if not affiliation.relations:
        affiliation.affiliations = []
        return

    for relation in relations_iterable:
        if not isinstance(relation, Relation):
            continue
        if not relation.types:
            continue

        first_type = relation.types[0].type

        if affiliation_type == "faculty" and first_type in institutions_list:
            set_logo(affiliation, relation)
            upper_affiliations.append(relation)

        elif affiliation_type == "department" and first_type in institutions_list + ["faculty"]:
            set_logo(affiliation, relation)
            upper_affiliations.append(relation)

        elif affiliation_type == "group" and first_type in institutions_list + ["department", "faculty"]:
            set_logo(affiliation, relation)
            upper_affiliations.append(relation)

    affiliation.affiliations = cast(List[Union[Dict[Any, Any], Relation]], upper_affiliations) or []


def set_logo(affiliation: Affiliation, relation: Relation) -> None:
    if not relation.types or not relation.external_urls:
        return
    if relation.types[0].type in institutions_list:
        logo_url = next(
            (x.url for x in relation.external_urls if x.source == "logo"),
            None,
        )
        if logo_url:
            affiliation.logo = str(logo_url)


def build_work_pipeline_params() -> dict:
    pipeline_params = {
        "project": [
            "_id",
            "author_count",
            "open_access",
            "authors.full_name",
            "authors.id",
            "authors.type",
            "authors.affiliations.id",
            "authors.affiliations.name",
            "authors.affiliations.types",
            "citations_count",
            "bibliographic_info",
            "types",
            "source",
            "titles",
            "subjects",
            "year_published",
            "external_ids",
            "external_urls",
            "ranking",
            "topics",
        ]
    }
    return pipeline_params


def build_person_pipeline_params() -> dict:
    pipeline_params = {
        "project": [
            "_id",
            "full_name",
            "affiliations",
            "external_ids",
            "citations_count",
            "products_count",
            "affiliations_data",
            "logo",
            "h_index",
            "h5_index",
        ]
    }
    return pipeline_params


def build_affiliation_pipeline_params() -> dict:
    pipeline_params = {
        "project": [
            "_id",
            "names",
            "addresses.country_code",
            "addresses.country",
            "external_ids",
            "external_urls",
            "relations",
            "ranking",
            "types",
            "citations_count",
            "products_count",
            "h_index",
            "h5_index",
        ]
    }

    return pipeline_params


def build_patents_pipeline_params() -> dict:
    pipeline_params = {
        "project": [
            "_id",
            "author_count",
            "authors",
            "types",
            "titles",
            "subjects",
            "external_ids",
            "external_urls",
            "authors_data",
        ]
    }
    return pipeline_params


def build_projects_pipeline_params() -> dict:
    pipeline_params = {
        "project": [
            "_id",
            "author_count",
            "authors",
            "types",
            "titles",
            "subjects",
            "year_init",
            "year_end",
            "external_ids",
            "external_urls",
            "authors_data",
        ]
    }
    return pipeline_params


def build_sources_pipeline_params() -> dict:
    pipeline_source_params = {
        "source": [
            "external_ids",
            "external_urls",
            "global_citations_count",
            "global_products_count",
            "keywords",
            "names",
            "publisher",
            "ranking",
            "subjects",
            "types",
        ],
        "collection": "sources",
    }

    return pipeline_source_params
