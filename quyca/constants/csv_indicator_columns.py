from collections.abc import Mapping

CsvColumns = Mapping[str, str]


def product_type_by(entity: str) -> dict[str, str]:
    return {"name": f"{entity}_name", "type": "product_type", "works_count": "product_count"}


def citations_by(entity: str) -> dict[str, str]:
    return {"name": f"{entity}_name", "citations": "scholar_citation_count"}


def apc_by(entity: str) -> dict[str, str]:
    return {"name": f"{entity}_name", "charges": "apc_charge_amount", "currency": "apc_currency"}


def h_index_by(entity: str) -> dict[str, str]:
    return {"name": f"{entity}_name", "h_index": "scholar_h_index"}


CSV_COLUMNS_BY_PLOT: dict[str, CsvColumns] = {
    "faculties_by_product_type": product_type_by("faculty"),
    "departments_by_product_type": product_type_by("department"),
    "research_groups_by_product_type": product_type_by("research_group"),
    "citations_by_faculty": citations_by("faculty"),
    "citations_by_department": citations_by("department"),
    "citations_by_research_group": citations_by("research_group"),
    "apc_expenses_by_faculty": apc_by("faculty"),
    "apc_expenses_by_department": apc_by("department"),
    "apc_expenses_by_group": apc_by("research_group"),
    "h_index_by_faculty": h_index_by("faculty"),
    "h_index_by_department": h_index_by("department"),
    "h_index_by_research_group": h_index_by("research_group"),
    "products_by_database": {
        "scienti": "in_scienti",
        "minciencias": "in_minciencias",
        "openalex": "in_openalex",
        "scholar": "in_scholar",
        "count": "product_count",
    },
    "coauthorship_by_country_map": {
        "country_name": "country_name",
        "latitude": "latitude",
        "longitude": "longitude",
        "coautorships": "coauthorship_count",
    },
    "coauthorship_by_colombian_department_map": {
        "department_name": "department_name",
        "latitude": "latitude",
        "longitude": "longitude",
        "coautorships": "coauthorship_count",
    },
    "annual_evolution_by_impactu_classification": {
        "year": "publication_year",
        "type": "scienti_product_type",
        "count": "product_count",
    },
    "annual_citation_count": {"year": "publication_year", "citations": "citation_count"},
    "annual_articles_open_access": {
        "year": "publication_year",
        "access_type": "open_access_status",
        "count": "article_count",
    },
    "annual_articles_by_top_publishers": {
        "year": "publication_year",
        "publisher": "publisher_name",
        "count": "article_count",
    },
    "most_used_title_words": {"word": "title_word", "count": "occurrence_count"},
    "articles_by_publisher": {"publisher": "publisher_name", "count": "article_count"},
    "products_by_subject": {"subject": "subject_name", "count": "product_count"},
    "articles_by_access_route": {"access_route": "access_route", "count": "article_count"},
    "active_authors_by_sex": {"sex": "author_sex", "count": "author_count"},
    "active_authors_by_age_range": {"age_range": "author_age_range", "count": "author_count"},
    "articles_by_scienti_category": {"category": "scienti_category", "count": "article_count"},
    "articles_by_scimago_quartile": {"quartile": "scimago_quartile", "count": "article_count"},
    "articles_by_publishing_institution": {
        "category": "publisher_institution_relation",
        "count": "article_count",
    },
    "annual_apc_expenses": {"year": "publication_year", "apc_usd": "apc_expense_usd"},
}
