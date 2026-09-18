from io import BytesIO
from typing import Generator

from quyca.domain.models.base_model import QueryParams
from quyca.infrastructure.repositories import csv_repository
from quyca.domain.parsers import work_parser


def get_works_csv_by_affiliation(
    affiliation_id: str, affiliation_type: str, query_params: QueryParams
) -> Generator[str, None, None]:
    """
    Orchestrate the complete CSV generation process for works associated with a specific affiliation.

    Parameters
    ----------
    - affiliation_id: Unique identifier of the affiliation
    - affiliation_type: Type of the affiliation (e.g., "institution", "department", "faculty", "group")
    - query_params: Query parameters for filtering and pagination

    Returns
    -------
        Generator: Complete CSV file content as string, ready for HTTP response
    """
    pipeline_params = get_works_project_pipeline_params()
    works = csv_repository.get_works_by_affiliation(affiliation_id, affiliation_type, query_params, pipeline_params)
    return work_parser.parse_csv(works)


def get_works_excel_by_affiliation(affiliation_id: str, affiliation_type: str, query_params: QueryParams) -> BytesIO:
    """
    Orchestrate the complete Excel generation process for works associated with a specific affiliation.

    Parameters
    ----------
    - affiliation_id: Unique identifier of the affiliation
    - affiliation_type: Type of the affiliation (e.g., "institution", "department", "faculty", "group")
    - query_params: Query parameters for filtering and pagination

    Returns
    -------
        BytesIO: Complete Excel file as bytes, ready for HTTP response
    """
    pipeline_params = get_works_project_pipeline_params()
    works = csv_repository.get_works_by_affiliation(
        affiliation_id,
        affiliation_type,
        query_params,
        pipeline_params,
    )
    return work_parser.parse_excel(works)


def get_works_csv_by_person(person_id: str, query_params: QueryParams) -> Generator[str, None, None]:
    """
    Orchestrate the complete CSV generation process for works associated with a specific person.

    Parameters
    ----------
    - person_id: Unique identifier of the author
    - query_params: Query parameters for filtering and pagination

    Returns
    -------
        Generator: Complete CSV file content as string, ready for HTTP response
    """
    pipeline_params = get_works_project_pipeline_params()
    works = csv_repository.get_works_csv_by_person(person_id, query_params, pipeline_params)
    return work_parser.parse_csv(works, person_id)


def get_works_excel_by_person(person_id: str, query_params: QueryParams) -> BytesIO:
    """
    Orchestrate the complete Excel generation process for works associated with a specific person.

    Parameters
    ----------
    - person_id: Unique identifier of the author
    - query_params: Query parameters for filtering and pagination

    Returns
    -------
        BytesIO: Complete Excel file as bytes, ready for HTTP response
    """
    pipeline_params = get_works_project_pipeline_params()
    works = csv_repository.get_works_csv_by_person(person_id, query_params, pipeline_params)
    return work_parser.parse_excel(works, person_id)


def get_works_csv_by_source(source_id: str, query_params: QueryParams) -> Generator[str, None, None]:
    """
    Orchestrate the complete CSV generation process for works from a specific source.

    This is the main service function that coordinates the entire workflow:
    1. Define which fields to retrieve from database (projection)
    2. Query works from database with filters
    3. Process and transform raw data for CSV format
    4. Generate final CSV string

    Parameters
    ----------
    - source_id: Unique identifier of the source (institution, journal, etc.)
    - query_params: Query parameters for filtering and pagination

    Returns
    -------
        Generator: Complete CSV file content as string, ready for HTTP response
    """
    pipeline_params = get_works_project_pipeline_params()
    works = csv_repository.get_works_csv_by_source(source_id, query_params, pipeline_params)
    return work_parser.parse_csv(works)


def get_works_excel_by_source(source_id: str, query_params: QueryParams) -> BytesIO:
    """
    Orchestrate the complete Excel generation process for works from a specific source.

    This is the main service function that coordinates the entire workflow:
    1. Define which fields to retrieve from database (projection)
    2. Query works from database with filters
    3. Process and transform raw data for Excel format
    4. Generate final Excel file

    Parameters
    ----------
    - source_id: Unique identifier of the source (institution, journal, etc.)
    - query_params: Query parameters for filtering and pagination

    Returns
    -------
        BytesIO: Complete Excel file as bytes, ready for HTTP response
    """
    pipeline_params = get_works_project_pipeline_params()
    works = csv_repository.get_works_csv_by_source(source_id, query_params, pipeline_params)
    return work_parser.parse_excel(works)


def get_works_project_pipeline_params() -> dict:
    """
    Define database projection parameters for CSV export.

    Specifies which fields should be retrieved from the database to minimize
    data transfer and improve query performance. Only fields needed for CSV
    export are included.

    Returns:
        dict: Pipeline parameters with 'project' key containing list of field names

    Note:
        Adding new columns to CSV requires adding corresponding fields here
    """
    pipeline_params = {
        "$project": {
            "_id": 1,
            "authors.id": 1,
            "author_count": 1,
            "authors.full_name": 1,
            "authors.affiliations.id": 1,
            "authors.affiliations.types.type": 1,
            "authors.affiliations.types.source": 1,
            "authors.affiliations.name": 1,
            "authors.affiliations.addresses.country": 1,
            "authors.ranking": 1,
            "bibliographic_info.bibtex": 1,
            "bibliographic_info.pages": 1,
            "bibliographic_info.issue": 1,
            "bibliographic_info.start_page": 1,
            "bibliographic_info.end_page": 1,
            "bibliographic_info.volume": 1,
            "open_access.open_access_status": 1,
            "citations_count": 1,
            "subjects.source": 1,
            "subjects.subjects.name": 1,
            "titles": 1,
            "types": 1,
            "source.name": 1,
            "source.apc": 1,
            "source.external_urls": 1,
            "source.ranking": 1,
            "source.publisher": 1,
            "groups": 1,
            "year_published": 1,
            "ranking": 1,
            "primary_topic": 1,
            "doi": 1,
            "external_ids": 1,
        }
    }
    return pipeline_params
