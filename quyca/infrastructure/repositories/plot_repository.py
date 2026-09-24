from typing import Any, Dict, Generator, List, Tuple

from bson import ObjectId
from pymongo.command_cursor import CommandCursor

from quyca.domain.models.base_model import QueryParams
from quyca.infrastructure.generators import work_generator
from quyca.infrastructure.mongo import database, calculations_database
from quyca.infrastructure.repositories import work_repository
from quyca.infrastructure.repositories import affiliation_repository


def get_affiliations_scienti_works_count_by_institution(
    institution_id: str, relation_type: str, query_params: QueryParams
) -> CommandCursor:
    affiliation_ids = affiliation_ids_for_institution(institution_id, relation_type)
    match_initial: dict[str, Any] = {
        "$match": {
            "authors.affiliations.id": {"$in": affiliation_ids},
            "types.source": "scienti",
            "types.level": 2,
        }
    }
    pipeline: list[dict[str, Any]] = [match_initial]
    work_repository.set_product_filters(pipeline, query_params)

    static_fields = [
        "authors.affiliations.name",
        "authors.affiliations.id",
        "citations_count",
        "types.source",
        "types.level",
    ]
    pipeline.append(build_project_stage(static_fields))

    pipeline += [
        {"$unwind": "$authors"},
        {"$unwind": "$authors.affiliations"},
        {"$match": {"authors.affiliations.id": {"$in": affiliation_ids}}},
        {"$unwind": "$types"},
        {"$match": {"types.source": "scienti", "types.level": 2}},
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
    return get_affiliations_scienti_works_count_by_institution(affiliation_id, "department", query_params)


def get_groups_scienti_works_count_by_faculty_or_department(
    affiliation_id: str, query_params: QueryParams
) -> CommandCursor:
    group_ids = group_ids_for_faculty_or_department(affiliation_id)
    static_fields = [
        "citations_count",
        "types.source",
        "types.level",
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
        {"$match": {"types.source": "scienti", "types.level": 2}},
        {
            "$group": {
                "_id": {
                    "id": "$_id",
                    "type": "$types.type",
                    "name": "$groups.name",
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
    affiliation_ids = affiliation_ids_for_institution(institution_id, relation_type)
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
    group_ids = group_ids_for_faculty_or_department(affiliation_id)
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
    affiliation_ids = affiliation_ids_for_institution(institution_id, relation_type)
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
    group_ids = group_ids_for_faculty_or_department(affiliation_id)
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


def get_affiliations_works_citations_count_by_institution(
    institution_id: str, relation_type: str, query_params: QueryParams
) -> CommandCursor:
    affiliation_ids = affiliation_ids_for_institution(institution_id, relation_type)
    static_fields = [
        "authors.affiliations.id",
        "authors.affiliations.name",
        "citations_count",
    ]
    pipeline: List[Dict[str, Any]] = [build_project_stage(static_fields)]
    work_repository.set_product_filters(pipeline, query_params)
    pipeline += [
        {"$match": {"authors.affiliations.id": {"$in": affiliation_ids}}},
        {"$unwind": "$authors"},
        {"$unwind": "$authors.affiliations"},
        {"$match": {"authors.affiliations.id": {"$in": affiliation_ids}}},
        {"$match": {"citations_count": {"$exists": True, "$ne": []}}},
        {"$unwind": "$citations_count"},
        {"$match": {"citations_count.source": "scholar"}},
        {
            "$group": {
                "_id": "$authors.affiliations.id",
                "name": {"$first": "$authors.affiliations.name"},
                "scholar_distribution": {"$push": "$citations_count.count"},
            }
        },
        {"$project": {"_id": 0, "name": 1, "scholar_distribution": 1}},
    ]
    return database["works"].aggregate(pipeline)


def get_departments_works_citations_count_by_faculty(affiliation_id: str, query_params: QueryParams) -> CommandCursor:
    return get_affiliations_works_citations_count_by_institution(affiliation_id, "department", query_params)


def get_groups_works_citations_count_by_faculty_or_department(
    affiliation_id: str, query_params: QueryParams
) -> CommandCursor:
    group_ids = group_ids_for_faculty_or_department(affiliation_id)
    static_fields = [
        "citations_count",
        "groups.id",
        "groups.name",
    ]
    pipeline: List[Dict[str, Any]] = [build_project_stage(static_fields)]
    work_repository.set_product_filters(pipeline, query_params)
    pipeline += [
        {"$match": {"groups.id": {"$in": group_ids}}},
        {"$match": {"citations_count": {"$exists": True, "$ne": []}}},
        {"$unwind": "$groups"},
        {"$match": {"groups.id": {"$in": group_ids}}},
        {"$unwind": "$citations_count"},
        {"$match": {"citations_count.source": "scholar"}},
        {
            "$group": {
                "_id": "$groups.id",
                "name": {"$first": "$groups.name"},
                "scholar_distribution": {"$push": "$citations_count.count"},
            }
        },
        {"$project": {"_id": 0, "name": 1, "scholar_distribution": 1}},
    ]
    return database["works"].aggregate(pipeline)


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
            "$project": {
                "_id": 1,
                "affiliations.id": 1,
                "affiliations.end_date": 1,
                "birthday": 1,
                "end_date": 1,
                "updated.source": 1,
            }
        },
        {"$match": {"_id": {"$in": author_ids}, "updated.source": "staff"}},
        {"$match": {"affiliations": {"$elemMatch": {"id": affiliation_id, "end_date": -1}}}},
        {"$project": {"_id": 0, "birthday": 1}},
    ]
    return database["person"].aggregate(pipeline_person)


def get_products_by_author_age_and_person(person_id: str, query_params: QueryParams) -> CommandCursor:
    pipeline: List[Dict[str, Any]] = [
        {"$match": {"authors.id": person_id}},
    ]
    work_repository.set_product_filters(pipeline, query_params)
    pipeline += [
        {"$project": {"authors": 1, "date_published": 1, "year_published": 1}},
        {
            "$lookup": {
                "from": "person",
                "localField": "authors.id",
                "foreignField": "_id",
                "pipeline": [{"$project": {"birthdate": 1}}],
                "as": "author",
            }
        },
        {"$unwind": "$author"},
        {
            "$project": {
                "work.date_published": "$date_published",
                "work.year_published": "$year_published",
                "birthdate": "$author.birthdate",
            }
        },
    ]
    return database["works"].aggregate(pipeline)


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


def get_collaboration_network(affiliation_id: str) -> CommandCursor:
    pipeline: List[Dict[str, Any]] = [
        {"$match": {"_id": affiliation_id}},
        {"$project": {"coauthorship_network": 1}},
        {
            "$lookup": {
                "from": "affiliations_edges",
                "localField": "_id",
                "foreignField": "_id",
                "as": "complement",
            }
        },
        {"$unwind": "$complement"},
        {
            "$project": {
                "coauthorship_network": {
                    "nodes": "$coauthorship_network.nodes",
                    "edges": {
                        "$concatArrays": [
                            "$coauthorship_network.edges",
                            "$complement.coauthorship_network.edges",
                        ]
                    },
                }
            }
        },
    ]
    return calculations_database["affiliations"].aggregate(pipeline)


def get_works_rankings_by_person(person_id: str, query_params: QueryParams) -> Tuple[Generator, int]:
    pipeline: List[Dict[str, Any]] = [
        {"$match": {"authors.id": person_id}},
    ]
    work_repository.set_product_filters(pipeline, query_params)
    pipeline += [
        {
            "$project": {
                "_id": 1,
                "source.id": 1,
                "date_published": 1,
                "source.ranking": 1,
            }
        },
    ]
    count_pipeline: List[Dict[str, Any]] = [
        {"$match": {"authors.id": person_id}},
    ]
    work_repository.set_product_filters(count_pipeline, query_params)

    count_pipeline += [
        {"$count": "total_results"},
    ]

    total_results = next(database["works"].aggregate(count_pipeline), {"total_results": 0})["total_results"]

    works = database["works"].aggregate(pipeline)
    return work_generator.get(works), total_results


def get_annual_scimago_quartile_by_source(source_id: str) -> CommandCursor:
    pipeline: List[Dict[str, Any]] = [
        {"$match": {"_id": ObjectId(source_id)}},
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


def pipeline_to_filter_for_affiliation(pipeline: list[dict[str, Any]], sources: list[str]) -> dict[str, Any]:
    filters: list[dict[str, Any]] = []
    valid_sources = ["minciencias", "openalex", "scholar", "scienti"]

    for stage in pipeline:
        if "$match" in stage:
            filters.append(stage["$match"])

    expr_filter = {
        "$expr": {
            "$setEquals": [
                {"$setIntersection": ["$updated.source", valid_sources]},
                sources,
            ]
        }
    }

    filters.append(expr_filter)
    return {"$and": filters} if filters else expr_filter


def pipeline_to_filter_for_person(pipeline: list[dict[str, Any]], person_id: str, sources: list[str]) -> dict[str, Any]:
    filters: list[dict[str, Any]] = [{"authors.id": person_id}]
    valid_sources = ["minciencias", "openalex", "scholar", "scienti"]

    if len(sources) == 1:
        filters.append({"updated.source": sources[0]})
    else:
        filters.append({"$expr": {"$setEquals": [{"$setIntersection": ["$updated.source", valid_sources]}, sources]}})
    for stage in pipeline:
        if "$match" in stage:
            filters.append(stage["$match"])

    return {"$and": filters}


def project_pipeline_params_for_filter() -> Dict[str, List[str]]:
    pipeline_params = {
        "filters_project": [
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
    }
    return pipeline_params


def affiliation_ids_for_institution(institution_id: str, relation_type: str) -> List[str]:
    affiliations = affiliation_repository.get_affiliations_by_institution(institution_id, relation_type)
    return [affiliation.id for affiliation in affiliations] if affiliations else []


def group_ids_for_faculty_or_department(affiliation_id: str) -> List[str]:
    groups = affiliation_repository.get_groups_by_faculty_or_department(affiliation_id)
    return [group.id for group in groups] if groups else []


def build_project_stage(dynamic_fields: list[str]) -> dict:
    pipeline_params = project_pipeline_params_for_filter()
    static_fields = pipeline_params.get("filters_project") or []
    project = {field: 1 for field in static_fields}

    if dynamic_fields:
        project.update({field: 1 for field in dynamic_fields})

    return {"$project": project}
