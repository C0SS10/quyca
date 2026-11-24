from quyca.models.patent_model import Patent


def parse_patents_by_entity(patents: list) -> list:
    return [patent.model_dump(exclude_none=True) for patent in patents]


def parse_patent(patent: Patent) -> dict:
    return patent.model_dump()
