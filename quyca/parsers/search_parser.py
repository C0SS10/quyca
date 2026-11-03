from typing import List


def parse_works_search(works: List, fields: List[str] | None = None) -> List:
    include = {"id", *fields} if fields else None
    return [work.model_dump(include=include) for work in works]


def parse_persons_search(persons: List) -> List:
    exclude = [
        "birthdate",
    ]
    return [person.model_dump(exclude=exclude) for person in persons]


def parse_affiliations_search(affiliations: List) -> List:
    return [affiliation.model_dump() for affiliation in affiliations]


def parse_sources_search(sources: List) -> List:
    return [source.model_dump() for source in sources]


def parse_patents_search(patents: List) -> List:
    return [patent.model_dump() for patent in patents]


def parse_projects_search(projects: List) -> List:
    return [project.model_dump() for project in projects]


def parse_geolocations_search(geolocations: List) -> List:
    exclude = [
        "groups",
        "institutions",
        "cities",
    ]
    return [geo.model_dump(exclude_none=True, exclude=exclude) for geo in geolocations]
