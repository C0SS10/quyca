from typing import Any, Callable, Dict, List

from pymongo.command_cursor import CommandCursor

from quyca.models.base_model import QueryParams
from quyca.clients.mongo import database
from quyca.repositories import base_repository
from quyca.repositories import work_repository
from quyca.repositories import affiliation_repository

# Fields every plot pipeline keeps so the product filters still apply after the projection.
FILTERS_PROJECT_FIELDS = [
    "types.source",
    "types.type",
    "types.code",
    "year_published",
    "open_access.open_access_status",
    "subjects.subjects.level",
    "subjects.subjects.name",
    "primary_topic.id",
    "authors.affiliations.addresses.country_code",
    "groups.ranking.rank",
    "authors.ranking.rank",
]


def get_affiliations_impactu_works_count_by_institution(
    institution_id: str, relation_type: str, query_params: QueryParams
) -> CommandCursor:
    affiliation_ids = get_affiliation_ids_by_institution(institution_id, relation_type)
    match_initial: dict[str, Any] = {
        "$match": {
            "authors.affiliations.id": {"$in": affiliation_ids},
            "types.source": "impactu",
        }
    }
    pipeline: list[dict[str, Any]] = [match_initial]
    work_repository.set_product_filters(pipeline, query_params)

    static_fields = [
        "authors.affiliations.name",
        "authors.affiliations.id",
        "citations_count",
        "types.source",
    ]
    pipeline.append(build_project_stage(static_fields))

    pipeline += [
        {"$unwind": "$authors"},
        {"$unwind": "$authors.affiliations"},
        {"$match": {"authors.affiliations.id": {"$in": affiliation_ids}}},
        {"$unwind": "$types"},
        {"$match": {"types.source": "impactu"}},
        {
            "$group": {
                "_id": {
                    "id": "$_id",
                    "type": "$types.type",
                    "name": "$authors.affiliations.name",
                },
            }
        },
        {
            "$group": {
                "_id": {
                    "type": "$_id.type",
                    "name": "$_id.name",
                },
                "works_count": {"$sum": 1},
            }
        },
        {
            "$project": {
                "_id": 0,
                "type": "$_id.type",
                "name": "$_id.name",
                "works_count": 1,
            }
        },
    ]
    return database["works"].aggregate(pipeline)


def get_departments_scienti_works_count_by_faculty(affiliation_id: str, query_params: QueryParams) -> CommandCursor:
    return get_affiliations_impactu_works_count_by_institution(affiliation_id, "department", query_params)


def get_groups_impactu_works_count_by_faculty_or_department(
    affiliation_id: str, query_params: QueryParams
) -> CommandCursor:
    group_ids = get_group_ids_by_faculty_or_department(affiliation_id)
    static_fields = [
        "citations_count",
        "types.source",
        "groups.id",
        "groups.name",
    ]
    pipeline: List[Dict[str, Any]] = [build_project_stage(static_fields)]
    work_repository.set_product_filters(pipeline, query_params)
    pipeline += [
        {"$match": {"groups.id": {"$in": group_ids}}},
        {"$unwind": "$groups"},
        {"$match": {"groups.id": {"$in": group_ids}}},
        {"$unwind": "$types"},
        {"$match": {"types.source": "impactu"}},
        {
            "$group": {
                "_id": {
                    "id": "$_id",
                    "type": "$types.type",
                    "name": "$groups.name",
                },
            }
        },
        {
            "$group": {
                "_id": {
                    "type": "$_id.type",
                    "name": "$_id.name",
                },
                "works_count": {"$sum": 1},
            }
        },
        {"$project": {"_id": 0, "type": "$_id.type", "works_count": 1, "name": "$_id.name"}},
    ]
    return database["works"].aggregate(pipeline)


def get_affiliations_citations_count_by_institution(
    institution_id: str, relation_type: str, query_params: QueryParams
) -> CommandCursor:
    affiliation_ids = get_affiliation_ids_by_institution(institution_id, relation_type)
    static_fields = [
        "authors.affiliations.id",
        "authors.affiliations.name",
        "authors.affiliations.types.type",
        "citations_count",
    ]
    pipeline = [build_project_stage(static_fields)]
    work_repository.set_product_filters(pipeline, query_params)
    pipeline += [
        {"$match": {"authors.affiliations.id": {"$in": affiliation_ids}}},
        {"$unwind": "$authors"},
        {"$unwind": "$authors.affiliations"},
        {
            "$match": {
                "authors.affiliations.id": {"$in": affiliation_ids},
                "authors.affiliations.types.type": relation_type,
            }
        },
        {"$unwind": "$citations_count"},
        {
            "$group": {
                "_id": "$authors.affiliations.id",
                "name": {"$first": "$authors.affiliations.name"},
                "citations_count": {"$push": "$citations_count"},
            }
        },
        {"$project": {"_id": 0, "id": "$_id", "name": 1, "citations_count": 1}},
    ]
    return database["works"].aggregate(pipeline)


def get_departments_citations_count_by_faculty(affiliation_id: str, query_params: QueryParams) -> CommandCursor:
    return get_affiliations_citations_count_by_institution(affiliation_id, "department", query_params)


def get_groups_citations_count_by_faculty_or_department(
    affiliation_id: str, query_params: QueryParams
) -> CommandCursor:
    group_ids = get_group_ids_by_faculty_or_department(affiliation_id)
    static_fields = [
        "groups.name",
        "groups.id",
        "groups.citations_count",
    ]
    pipeline: List[Dict[str, Any]] = [build_project_stage(static_fields)]
    work_repository.set_product_filters(pipeline, query_params)
    pipeline += [
        {"$match": {"groups.id": {"$in": group_ids}}},
        {"$unwind": "$groups"},
        {"$match": {"groups.id": {"$in": group_ids}}},
        {"$unwind": "$groups.citations_count"},
        {
            "$group": {
                "_id": "$groups.id",
                "name": {"$first": "$groups.name"},
                "citations_count": {"$push": "$groups.citations_count"},
            }
        },
        {"$project": {"_id": 0, "id": "$_id", "name": 1, "citations_count": 1}},
    ]
    return database["works"].aggregate(pipeline)


def get_affiliations_apc_expenses_by_institution(
    institution_id: str, relation_type: str, query_params: QueryParams
) -> CommandCursor:
    affiliation_ids = get_affiliation_ids_by_institution(institution_id, relation_type)
    static_fields = [
        "authors.affiliations.id",
        "authors.affiliations.name",
        "source.apc",
    ]
    pipeline: List[Dict[str, Any]] = [build_project_stage(static_fields)]
    work_repository.set_product_filters(pipeline, query_params)
    pipeline += [
        {"$match": {"authors.affiliations.id": {"$in": affiliation_ids}}},
        {"$match": {"source.apc": {"$exists": True, "$ne": {}}}},
        {"$unwind": "$authors"},
        {"$unwind": "$authors.affiliations"},
        {"$match": {"authors.affiliations.id": {"$in": affiliation_ids}}},
        {"$project": {"name": "$authors.affiliations.name", "apc": "$source.apc"}},
    ]
    return database["works"].aggregate(pipeline)


def get_departments_apc_expenses_by_faculty(affiliation_id: str, query_params: QueryParams) -> CommandCursor:
    return get_affiliations_apc_expenses_by_institution(affiliation_id, "department", query_params)


def get_groups_apc_expenses_by_faculty_or_department(affiliation_id: str, query_params: QueryParams) -> CommandCursor:
    group_ids = get_group_ids_by_faculty_or_department(affiliation_id)
    static_fields = [
        "groups.id",
        "groups.name",
        "source.apc",
    ]
    pipeline: List[Dict[str, Any]] = [build_project_stage(static_fields)]
    work_repository.set_product_filters(pipeline, query_params)
    pipeline += [
        {"$match": {"groups.id": {"$in": group_ids}}},
        {"$unwind": "$groups"},
        {"$match": {"groups.id": {"$in": group_ids}}},
        {"$project": {"name": "$groups.name", "apc": "$source.apc"}},
    ]
    return database["works"].aggregate(pipeline)


def get_h_index_by_institution(institution_id: str, relation_type: str) -> CommandCursor:
    return affiliation_repository.get_h_index_by_institution(institution_id, relation_type)


def get_h_index_by_faculty_or_department(affiliation_id: str) -> CommandCursor:
    group_ids = get_group_ids_by_faculty_or_department(affiliation_id)
    return affiliation_repository.get_h_index_by_ids(group_ids)


def get_active_authors_by_sex(affiliation_id: str, query_params: QueryParams) -> CommandCursor:
    static_fields = [
        "authors.id",
        "authors.affiliations.id",
    ]
    pipeline: list[dict[str, Any]] = [build_project_stage(static_fields)]
    work_repository.set_product_filters(pipeline, query_params)
    pipeline += [
        {"$match": {"authors.affiliations.id": affiliation_id}},
        {"$unwind": "$authors"},
        {"$match": {"authors.affiliations.id": affiliation_id}},
        {"$project": {"authors.id": 1}},
    ]
    author_list = database["works"].aggregate(pipeline)

    author_ids = [author["authors"]["id"] for author in author_list]
    pipeline_person: list[dict[str, Any]] = [
        {
            "$project": {
                "_id": 1,
                "affiliations.id": 1,
                "affiliations.end_date": 1,
                "sex": 1,
                "end_date": 1,
                "updated.source": 1,
            }
        },
        {"$match": {"_id": {"$in": author_ids}, "updated.source": "staff"}},
        {"$match": {"affiliations": {"$elemMatch": {"id": affiliation_id, "end_date": -1}}}},
        {"$project": {"_id": 0, "sex": 1}},
    ]
    return database["person"].aggregate(pipeline_person)


def get_active_authors_by_age_range(affiliation_id: str, query_params: QueryParams) -> CommandCursor:
    match_initial: dict[str, Any] = {
        "$match": {
            "authors.affiliations.id": affiliation_id,
        }
    }
    pipeline: list[dict[str, Any]] = [match_initial]

    static_fields = [
        "authors.id",
        "authors.affiliations.id",
    ]
    pipeline.append(build_project_stage(static_fields))
    work_repository.set_product_filters(pipeline, query_params)
    pipeline += [
        {"$match": {"authors.affiliations.id": affiliation_id}},
        {"$unwind": "$authors"},
        {"$match": {"authors.affiliations.id": affiliation_id}},
        {"$project": {"authors.id": 1}},
    ]
    author_list = database["works"].aggregate(pipeline)

    author_ids = [author["authors"]["id"] for author in author_list]
    pipeline_person: list[dict[str, Any]] = [
        {
            "$match": {
                "_id": {"$in": author_ids},
                "updated.source": "staff",
                "affiliations": {
                    "$elemMatch": {
                        "id": affiliation_id,
                        "end_date": -1,
                    }
                },
            }
        },
        {"$project": {"_id": 0, "birthdate": 1}},
    ]
    return database["person"].aggregate(pipeline_person)


def get_coauthorship_by_country_map_by_affiliation(affiliation_id: str, query_params: QueryParams) -> list:
    data = []
    pipeline: List[Dict[str, Any]] = [
        {"$match": {"authors.affiliations.id": affiliation_id}},
    ]
    work_repository.set_product_filters(pipeline, query_params)
    pipeline += [
        {"$unwind": "$authors"},
        {"$unwind": "$authors.affiliations"},
        {"$group": {"_id": "$authors.affiliations.id", "count": {"$sum": 1}}},
        {
            "$lookup": {
                "from": "affiliations",
                "localField": "_id",
                "foreignField": "_id",
                "as": "affiliation",
                "pipeline": [
                    {
                        "$project": {
                            "addresses.country_code": 1,
                            "addresses.country": 1,
                        }
                    }
                ],
            }
        },
        {"$unwind": "$affiliation"},
        {"$unwind": "$affiliation.addresses"},
    ]
    for work in database["works"].aggregate(pipeline):
        data.append(work)
    return data


def get_coauthorship_by_country_map_by_person(person_id: str, query_params: QueryParams) -> list:
    data = []
    pipeline: List[Dict[str, Any]] = [
        {"$match": {"authors.id": person_id}},
    ]
    work_repository.set_product_filters(pipeline, query_params)
    pipeline += [
        {"$unwind": "$authors"},
        {"$unwind": "$authors.affiliations"},
        {"$group": {"_id": "$authors.affiliations.id", "count": {"$sum": 1}}},
        {"$unwind": "$_id"},
        {
            "$lookup": {
                "from": "affiliations",
                "localField": "_id",
                "foreignField": "_id",
                "as": "affiliation",
                "pipeline": [
                    {
                        "$project": {
                            "addresses.country_code": 1,
                            "addresses.country": 1,
                        }
                    }
                ],
            }
        },
        {
            "$project": {
                "count": 1,
                "affiliation.addresses.country_code": 1,
                "affiliation.addresses.country": 1,
            }
        },
        {"$unwind": "$affiliation"},
        {"$unwind": "$affiliation.addresses"},
    ]
    for work in database["works"].aggregate(pipeline):
        data.append(work)
    return data


def get_coauthorship_by_colombian_department_map_by_affiliation(affiliation_id: str, query_params: QueryParams) -> list:
    pipeline: List[Dict[str, Any]] = [
        {"$match": {"authors.affiliations.id": affiliation_id}},
    ]
    work_repository.set_product_filters(pipeline, query_params)
    pipeline.extend(
        [
            {
                "$project": {
                    "authors.affiliations.id": 1,
                    "authors.affiliations.addresses.country_code": 1,
                    "authors.affiliations.addresses.city": 1,
                }
            },
            {
                "$match": {
                    "authors.affiliations.addresses.country_code": "CO",
                }
            },
            {"$unwind": "$authors"},
            {"$unwind": "$authors.affiliations"},
            {
                "$match": {
                    "authors.affiliations.addresses.country_code": "CO",
                }
            },
            {
                "$group": {
                    "_id": "$authors.affiliations.id",
                    "count": {"$sum": 1},
                    "addresses": {
                        "$addToSet": "$authors.affiliations.addresses",
                    },
                }
            },
        ]
    )

    return list(database["works"].aggregate(pipeline))


def get_coauthorship_by_colombian_department_map_by_person(person_id: str, query_params: QueryParams) -> list:
    data = []
    pipeline: List[Dict[str, Any]] = [
        {"$match": {"authors.id": person_id}},
    ]
    work_repository.set_product_filters(pipeline, query_params)
    pipeline += [
        {"$unwind": "$authors"},
        {"$group": {"_id": "$authors.affiliations.id", "count": {"$sum": 1}}},
        {"$unwind": "$_id"},
        {
            "$lookup": {
                "from": "affiliations",
                "localField": "_id",
                "foreignField": "_id",
                "as": "affiliation",
            }
        },
        {
            "$project": {
                "count": 1,
                "affiliation.addresses.country_code": 1,
                "affiliation.addresses.city": 1,
            }
        },
        {"$unwind": "$affiliation"},
        {"$unwind": "$affiliation.addresses"},
    ]
    for work in database["works"].aggregate(pipeline):
        data.append(work)
    return data


def get_annual_scimago_quartile_by_source(source_id: str) -> CommandCursor:
    pipeline: List[Dict[str, Any]] = [
        {"$match": {"_id": base_repository.to_object_id(source_id)}},
        {"$project": {"ranking.from_date": 1, "ranking.rank": 1, "ranking.source": 1}},
        {"$unwind": "$ranking"},
        {"$match": {"ranking.source": {"$in": ["scimago Best Quartile", "Scimago Best Quartile"]}}},
        {
            "$project": {
                "year": {"$year": {"$toDate": {"$multiply": ["$ranking.from_date", 1000]}}},
                "quartile": "$ranking.rank",
            }
        },
        {"$sort": {"year": 1}},
    ]
    return database["sources"].aggregate(pipeline)


def get_products_by_database_by_affiliation(affiliation_id: str, query_params: QueryParams) -> list:
    pipeline: list[dict[str, Any]] = [{"$match": {"authors.affiliations.id": affiliation_id}}]

    work_repository.set_product_filters(pipeline, query_params)

    pipeline.extend(
        [
            {
                "$project": {
                    "sources": {
                        "$setIntersection": [
                            "$updated.source",
                            ["minciencias", "openalex", "scholar", "scienti"],
                        ]
                    }
                }
            },
            {
                "$group": {
                    "_id": "$sources",
                    "count": {"$sum": 1},
                }
            },
        ]
    )

    results = list(database["works"].aggregate(pipeline))

    return results


def get_products_by_database_by_person(person_id: str, query_params: QueryParams) -> list:
    pipeline: list[dict[str, Any]] = [{"$match": {"authors.id": person_id}}]

    work_repository.set_product_filters(pipeline, query_params)

    pipeline.extend(
        [
            {
                "$project": {
                    "sources": {
                        "$setIntersection": [
                            "$updated.source",
                            ["minciencias", "openalex", "scholar", "scienti"],
                        ]
                    }
                }
            },
            {
                "$group": {
                    "_id": "$sources",
                    "count": {"$sum": 1},
                }
            },
        ]
    )

    results = list(database["works"].aggregate(pipeline))

    return results


def get_affiliation_ids_by_institution(institution_id: str, relation_type: str) -> List[str]:
    affiliations = affiliation_repository.get_affiliations_by_parent(institution_id, relation_type)
    return [affiliation.id for affiliation in affiliations] if affiliations else []


def get_group_ids_by_faculty_or_department(affiliation_id: str) -> List[str]:
    groups = affiliation_repository.get_groups_by_faculty_or_department(affiliation_id)
    return [group.id for group in groups] if groups else []


def build_project_stage(dynamic_fields: list[str]) -> dict:
    return {"$project": {field: 1 for field in FILTERS_PROJECT_FIELDS + dynamic_fields}}


AFFILIATIONS_METRIC_QUERIES: dict[str, tuple[Callable[..., CommandCursor], ...]] = {
    "product_type": (
        get_affiliations_impactu_works_count_by_institution,
        get_departments_scienti_works_count_by_faculty,
        get_groups_impactu_works_count_by_faculty_or_department,
    ),
    "citations": (
        get_affiliations_citations_count_by_institution,
        get_departments_citations_count_by_faculty,
        get_groups_citations_count_by_faculty_or_department,
    ),
    "apc_expenses": (
        get_affiliations_apc_expenses_by_institution,
        get_departments_apc_expenses_by_faculty,
        get_groups_apc_expenses_by_faculty_or_department,
    ),
    "h_index": (
        lambda institution_id, relation_type, query_params: get_h_index_by_institution(institution_id, relation_type),
        lambda faculty_id, query_params: get_h_index_by_institution(faculty_id, "department"),
        lambda affiliation_id, query_params: get_h_index_by_faculty_or_department(affiliation_id),
    ),
}


def get_affiliations_metric(
    metric: str, affiliation_id: str, affiliation_type: str, relation_type: str, query_params: QueryParams
) -> CommandCursor | None:
    """Metric of the faculties, departments or groups under an affiliation; None when it has none of that type."""
    by_institution, departments_by_faculty, groups_by_faculty_or_department = AFFILIATIONS_METRIC_QUERIES[metric]
    if affiliation_type == "institution":
        return by_institution(affiliation_id, relation_type, query_params)
    if affiliation_type == "faculty" and relation_type == "department":
        return departments_by_faculty(affiliation_id, query_params)
    if affiliation_type in ("faculty", "department") and relation_type == "group":
        return groups_by_faculty_or_department(affiliation_id, query_params)
    return None
