from quyca.repositories import info_repository


def get_info() -> dict:
    return {
        "db_update": info_repository.get_last_db_update(),
        "total_products": info_repository.get_entity_count("works"),
        "total_institutions": info_repository.get_entity_count("affiliations", "institution"),
        "total_faculties": info_repository.get_entity_count("affiliations", "faculty"),
        "total_departments": info_repository.get_entity_count("affiliations", "department"),
        "total_groups": info_repository.get_entity_count("affiliations", "group"),
        "total_patents": info_repository.get_entity_count("patents"),
        "total_projects": info_repository.get_entity_count("projects"),
        "total_authors": info_repository.get_entity_count("person"),
        "total_news": info_repository.get_news_count(),
        "total_open_access": info_repository.get_open_access_count(),
        "total_sources": info_repository.get_entity_count("sources"),
    }


def get_quality_metrics() -> list:
    return info_repository.get_quality_metrics_history()
