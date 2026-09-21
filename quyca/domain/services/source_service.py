from quyca.infrastructure.repositories import source_repository
from quyca.domain.models.work_model import Work, Source
from quyca.domain.parsers import source_parser


def update_csv_work_source(work: Work) -> None:
    if not work.source:
        return

    source = work.source
    work.source_name = str(source.name) if source.name else None
    if source.apc and source.apc.charges and source.apc.currency:
        work.source_apc = f"{source.apc.charges} / {source.apc.currency}"
    else:
        work.source_apc = None

    set_source_urls(work, source)
    set_scimago_quartile(work, source)


def set_source_urls(work: Work, source: Source) -> None:
    if source.external_urls:
        urls = {str(url.url) for url in source.external_urls if url.url}
        work.source_urls = " | ".join(urls) if urls else None
    else:
        work.source_urls = None


def set_scimago_quartile(work: Work, source: Source) -> None:
    work.scimago_quartile = None
    if source.ranking and work.date_published:
        for ranking in source.ranking:
            condition = (
                ranking.source == "scimago Best Quartile"
                and ranking.rank
                and ranking.rank != "-"
                and isinstance(ranking.from_date, int)
                and isinstance(ranking.to_date, int)
                and ranking.from_date <= work.date_published <= ranking.to_date
            )
            if condition:
                work.scimago_quartile = str(ranking.rank)
                break


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
