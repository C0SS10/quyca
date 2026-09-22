from io import BytesIO
from typing import Generator

from quyca.domain.models.base_model import QueryParams
from quyca.domain.models.export_model import ExportEntity
from quyca.infrastructure.repositories import export_repository
from quyca.domain.parsers.export import export_parser


def get_works_csv_by_affiliation(
    affiliation_id: str, affiliation_type: str, query_params: QueryParams
) -> Generator[str, None, None]:
    pipeline_params = build_export_pipeline_params()
    works = export_repository.get_works_by_affiliation(affiliation_id, affiliation_type, query_params, pipeline_params)
    return export_parser.parse_csv(works, entity=ExportEntity.AFFILIATION)


def get_works_excel_by_affiliation(affiliation_id: str, affiliation_type: str, query_params: QueryParams) -> BytesIO:
    pipeline_params = build_export_pipeline_params()
    works = export_repository.get_works_by_affiliation(
        affiliation_id,
        affiliation_type,
        query_params,
        pipeline_params,
    )
    return export_parser.parse_excel(works, entity=ExportEntity.AFFILIATION)


def get_works_csv_by_person(person_id: str, query_params: QueryParams) -> Generator[str, None, None]:
    pipeline_params = build_export_pipeline_params()
    works = export_repository.get_works_by_person(person_id, query_params, pipeline_params)
    return export_parser.parse_csv(works, entity=ExportEntity.PERSON, person_id=person_id)


def get_works_excel_by_person(person_id: str, query_params: QueryParams) -> BytesIO:
    pipeline_params = build_export_pipeline_params()
    works = export_repository.get_works_by_person(person_id, query_params, pipeline_params)
    return export_parser.parse_excel(works, entity=ExportEntity.PERSON, person_id=person_id)


def get_works_csv_by_source(source_id: str, query_params: QueryParams) -> Generator[str, None, None]:
    pipeline_params = build_export_pipeline_params()
    works = export_repository.get_works_by_source(source_id, query_params, pipeline_params)
    return export_parser.parse_csv(works, entity=ExportEntity.SOURCE)


def get_works_excel_by_source(source_id: str, query_params: QueryParams) -> BytesIO:
    pipeline_params = build_export_pipeline_params()
    works = export_repository.get_works_by_source(source_id, query_params, pipeline_params)
    return export_parser.parse_excel(works, entity=ExportEntity.SOURCE)


def build_export_pipeline_params() -> dict:
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
