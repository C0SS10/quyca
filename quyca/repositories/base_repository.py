from bson import ObjectId
from pymongo.collection import Collection

from quyca.constants.institutions import institutions_list
from quyca.exceptions import InvalidParamException
from quyca.models.base_model import QueryParams


def text_search_match(keywords: str | None) -> list[dict]:
    """
    `$text` must be the first stage of a pipeline, so every search pipeline starts from this list.
    """
    return [{"$match": {"$text": {"$search": keywords}}}] if keywords else []


def to_object_id(value: str) -> ObjectId:
    """Ids that come in the URL; a malformed one answers 400 instead of failing inside Mongo's driver."""
    if not ObjectId.is_valid(value):
        raise InvalidParamException(f"Invalid id '{value}'.")
    return ObjectId(value)


def affiliation_match(affiliation_id: str, affiliation_type: str) -> dict:
    """Documents with an author in the affiliation, provided some author affiliation has that type."""
    types = institutions_list if affiliation_type == "institution" else [affiliation_type]
    return {"authors.affiliations.id": affiliation_id, "authors.affiliations.types.type": {"$in": types}}


def count(collection: Collection, match_stages: list[dict]) -> int:
    if not match_stages:
        return int(collection.estimated_document_count())
    result = next(collection.aggregate([*match_stages, {"$count": "total"}]), {"total": 0})
    return int(result["total"])


def set_search_end_stages(pipeline: list, query_params: QueryParams, pipeline_params: dict | None = None) -> list:
    if pipeline_params is None:
        pipeline_params = {}
    if match := pipeline_params.get("match"):
        pipeline.append({"$match": match})
    set_sort(pipeline, query_params.sort, pipeline_params.get("collection"))
    set_project(pipeline, pipeline_params.get("project"))
    set_pagination(pipeline, query_params)
    if authors_limit := pipeline_params.get("authors_limit"):
        set_authors_limit(pipeline, authors_limit)
    return pipeline


def set_authors_limit(pipeline: list, limit: int) -> None:
    """Keeps the first `limit` authors. After the pagination, so filters, sort and count still see every author."""
    authors = {"$cond": [{"$isArray": "$authors"}, {"$slice": ["$authors", limit]}, "$$REMOVE"]}
    pipeline.append({"$set": {"authors": authors}})


def set_pagination(pipeline: list, query_params: QueryParams) -> None:
    if limit := query_params.limit:
        page = query_params.page or 1
        skip = (page - 1) * limit
        pipeline.extend([{"$skip": skip}, {"$limit": limit}])


def set_project(pipeline: list, project: list | dict | None) -> None:
    if not project:
        return

    pipeline.append({"$project": {"_id": 1, **{p: 1 for p in project}}})


def set_sort(pipeline: list, sort: str | None, collection: str | None = None) -> None:
    if not sort:
        return
    sort_field, direction_str = sort.split("_")
    direction = -1 if direction_str == "desc" else 1

    if sort_field == "citations":
        if collection == "sources":
            pipeline += [
                {
                    "$addFields": {
                        "citations_count_openalex": {
                            "$let": {
                                "vars": {
                                    "openalexCitation": {
                                        "$arrayElemAt": [
                                            {
                                                "$filter": {
                                                    "input": "$citations_count",
                                                    "as": "cite",
                                                    "cond": {"$eq": ["$$cite.source", "openalex"]},
                                                }
                                            },
                                            0,
                                        ]
                                    }
                                },
                                "in": {"$ifNull": ["$$openalexCitation.count", 0]},
                            }
                        }
                    }
                }
            ]
            sort_field = "citations_count_openalex"
        else:
            sort_field = "citations_count_openalex"
    elif sort_field == "alphabetical":
        if collection == "sources":
            pipeline += [
                {
                    "$addFields": {
                        "names_order": {
                            "$map": {
                                "input": "$names",
                                "as": "name",
                                "in": {
                                    "source": "$$name.source",
                                    "name": "$$name.name",
                                    "order": {
                                        "$switch": {
                                            "branches": [
                                                {
                                                    "case": {
                                                        "$eq": [
                                                            "$$name.source",
                                                            "openalex",
                                                        ]
                                                    },
                                                    "then": 0,
                                                },
                                                {
                                                    "case": {"$eq": ["$$name.source", "doaj"]},
                                                    "then": 1,
                                                },
                                                {
                                                    "case": {"$eq": ["$$name.source", "scimago"]},
                                                    "then": 2,
                                                },
                                                {
                                                    "case": {"$eq": ["$$name.source", "scholar"]},
                                                    "then": 3,
                                                },
                                            ],
                                            "default": 10,
                                        }
                                    },
                                },
                            }
                        }
                    }
                },
                {
                    "$addFields": {
                        "first_name": {
                            "$arrayElemAt": [
                                {
                                    "$sortArray": {
                                        "input": "$names_order",
                                        "sortBy": {"order": 1},
                                    }
                                },
                                0,
                            ]
                        }
                    }
                },
                {"$addFields": {"sort_name": "$first_name.name"}},
                {"$unset": ["names_order", "first_name"]},
            ]
            sort_field = "sort_name"
        elif collection == "geo":
            sort_field = "name_normalized"
        else:
            pipeline += [
                {
                    "$addFields": {
                        "titles_order": {
                            "$map": {
                                "input": "$titles",
                                "as": "title",
                                "in": {
                                    "source": "$$title.source",
                                    "title": "$$title.title",
                                    "order": {
                                        "$switch": {
                                            "branches": [
                                                {
                                                    "case": {
                                                        "$eq": [
                                                            "$$title.source",
                                                            "openalex",
                                                        ]
                                                    },
                                                    "then": 0,
                                                },
                                                {
                                                    "case": {"$eq": ["$$title.source", "scholar"]},
                                                    "then": 1,
                                                },
                                                {
                                                    "case": {"$eq": ["$$title.source", "scienti"]},
                                                    "then": 2,
                                                },
                                                {
                                                    "case": {
                                                        "$eq": [
                                                            "$$title.source",
                                                            "minciencias",
                                                        ]
                                                    },
                                                    "then": 3,
                                                },
                                                {
                                                    "case": {"$eq": ["$$title.source", "ranking"]},
                                                    "then": 4,
                                                },
                                                {
                                                    "case": {"$eq": ["$$title.source", "siiu"]},
                                                    "then": 5,
                                                },
                                            ],
                                            "default": 10,
                                        }
                                    },
                                },
                            }
                        }
                    }
                },
                {
                    "$addFields": {
                        "first_title": {
                            "$arrayElemAt": [
                                {
                                    "$sortArray": {
                                        "input": "$titles_order",
                                        "sortBy": {"order": 1},
                                    }
                                },
                                0,
                            ]
                        }
                    }
                },
                {"$addFields": {"title": "$first_title.title"}},
                {"$unset": ["titles_order", "first_title"]},
            ]
            sort_field = "title"
    elif sort_field == "products":
        sort_field = "products_count"
    elif sort_field == "h":
        sort_field = "h_index"
    elif sort_field == "h5":
        sort_field = "h5_index"
    elif sort_field == "year":
        sort_field = "year_published"
    pipeline += [{"$sort": {sort_field: direction, "_id": 1}}]
