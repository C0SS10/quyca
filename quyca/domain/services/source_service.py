from quyca.infrastructure.repositories import source_repository
from quyca.domain.parsers import source_parser


def get_source_by_id(source_id: str) -> dict:
    """
    Retrieves a source by its ID.

    Parameters:
    -----------
    source_id : str
        The ID of the source to retrieve.

    Returns:
    --------
    dict
        A dictionary representation of the source.
    """
    source = source_repository.get_source_by_id(source_id)
    data = source_parser.parse_source(source)
    return {"data": data}
