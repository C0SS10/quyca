# First-level work fields a client may pick with ?fields=. Nested fields (authors.full_name) are not offered: the
# projection would have to rebuild every subdocument and lose the speed it is meant to give.
WORK_SELECTABLE_FIELDS: frozenset[str] = frozenset(
    {
        "id",
        "authors",
        "titles",
        "keywords",
        "topics",
        "subjects",
        "source",
        "types",
        "year_published",
        "citations_by_year",
        "citations_count",
        "updated",
    }
)

WORK_SUMMARY_FIELDS: list[str] = [
    "_id",
    "author_count",
    "open_access",
    "authors.full_name",
    "authors.id",
    "authors.type",
    "authors.affiliations.id",
    "authors.affiliations.name",
    "authors.affiliations.types",
    "citations_count",
    "bibliographic_info",
    "types",
    "source",
    "titles",
    "subjects",
    "year_published",
    "external_ids",
    "external_urls",
    "ranking",
    "topics",
]

PERSON_SUMMARY_FIELDS: list[str] = [
    "_id",
    "full_name",
    "affiliations",
    "external_ids",
    "citations_count",
    "products_count",
    "h_index",
    "h5_index",
]

AFFILIATION_SUMMARY_FIELDS: list[str] = [
    "_id",
    "names",
    "addresses.country_code",
    "addresses.country",
    "external_ids",
    "external_urls",
    "relations",
    "ranking",
    "types",
    "citations_count",
    "products_count",
    "h_index",
    "h5_index",
]

PATENT_SUMMARY_FIELDS: list[str] = [
    "_id",
    "author_count",
    "authors",
    "types",
    "titles",
    "subjects",
    "external_ids",
    "external_urls",
]

PROJECT_SUMMARY_FIELDS: list[str] = [
    "_id",
    "author_count",
    "authors",
    "types",
    "titles",
    "subjects",
    "year_init",
    "year_end",
    "external_ids",
    "external_urls",
]

SOURCE_SUMMARY_FIELDS: list[str] = [
    "external_ids",
    "external_urls",
    "global_citations_count",
    "global_products_count",
    "keywords",
    "names",
    "publisher",
    "ranking",
    "subjects",
    "types",
]
