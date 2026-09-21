from quyca.domain.models.patent_model import Patent


def parse_patents_by_entity(patents: list) -> list:
    include = [
        "id",
        "authors",
        "authors_count",
        "product_types",
        "title",
        "external_ids",
    ]
    return [patent.model_dump(include=include) for patent in patents]


def parse_patent(patent: Patent) -> dict:
    return patent.model_dump()
