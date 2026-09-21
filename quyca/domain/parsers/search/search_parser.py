from typing import List


def parse_works_search(works: List) -> List:
    nested_include = {
        "id": ...,
        "authors": {
            "__all__": {
                "id": ...,
                "full_name": ...,
                "type": ...,
                "affiliations": {
                    "__all__": {
                        "id": ...,
                        "name": ...,
                        "types": ...,
                    }
                },
            }
        },
        "authors_count": ...,
        "citations_count": ...,
        "open_access": ...,
        "product_types": ...,
        "year_published": ...,
        "title": ...,
        "source": {"id": ..., "name": ...},
        "external_ids": ...,
        "ranking": ...,
        "topics": ...,
        "citations_count_openalex": ...,
    }
    return [work.model_dump(include=nested_include, exclude_none=True) for work in works]


def parse_persons_search(persons: List) -> List:
    include = [
        "id",
        "full_name",
        "affiliations",
        "external_ids",
        "products_count",
        "citations_count",
        "h_index",
        "h5_index",
    ]
    return [person.model_dump(include=include) for person in persons]


def parse_affiliations_search(affiliations: List) -> List:
    include = [
        "id",
        "addresses",
        "affiliations",
        "external_ids",
        "external_urls",
        "products_count",
        "citations_count",
        "h_index",
        "h5_index",
        "logo",
        "name",
        "types",
        "products_count",
        "ranking",
    ]
    return [affiliation.model_dump(include=include, exclude_none=True) for affiliation in affiliations]


def parse_patents_search(patents: List) -> List:
    include = [
        "id",
        "authors",
        "authors_count",
        "product_types",
        "title",
        "external_ids",
        "external_urls",
    ]
    return [patent.model_dump(include=include) for patent in patents]


def parse_projects_search(projects: List) -> List:
    include = [
        "id",
        "authors",
        "authors_count",
        "product_types",
        "year_init",
        "year_end",
        "title",
        "external_ids",
        "external_urls",
    ]
    return [project.model_dump(include=include) for project in projects]


def parse_sources_search(sources: List) -> List:
    source_fields = [
        "id",
        "abbreviations",
        "addresses",
        "apc",
        "citations_count",
        "copyright",
        "external_ids",
        "external_urls",
        "global_citations_count",
        "global_products_count",
        "keywords",
        "languages",
        "licenses",
        "names",
        "open_access_start_year",
        "open_access_status",
        "plagiarism_detection",
        "publication_time_weeks",
        "products_count",
        "publisher",
        "ranking",
        "relations",
        "review_process",
        "subjects",
        "scimago_best_quartile",
        "topics",
        "type",
        "updated",
        "waiver",
    ]

    return [
        source.model_dump(include=source_fields, exclude={"citations_count": {"__all__": {"provenance"}}})
        for source in sources
    ]


def parse_geolocations_search(geolocations: List) -> List:
    data = []
    for geolocation in geolocations:
        data.append({"geoname": geolocation["_id"]})

    return data
