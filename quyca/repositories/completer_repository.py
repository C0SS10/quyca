from quyca.clients.elasticsearch import es_database
from typing import Any, Dict, List, cast
from quyca.config import settings


def get_person_completions(text: str) -> List[Dict[str, Any]]:
    if es_database is None:
        raise RuntimeError("Elasticsearch client is not initialized")

    query = {
        "suggest": {
            "name_suggest": {
                "prefix": text,
                "completion": {"field": "full_name", "size": 5},
            }
        }
    }

    response = es_database.search(index=settings.ES_PERSON_COMPLETER_INDEX, body=query)

    options = cast(List[Dict[str, Any]], response["suggest"]["name_suggest"][0]["options"])
    for opt in options:
        full_name = ""
        for name in opt["_source"]["full_name"]["input"]:
            if len(full_name) < len(name):
                full_name = name
        opt["full_name"] = full_name

    return options


def get_affiliation_completions(affiliation_type: str, text: str) -> List[Dict[str, Any]]:
    query = {
        "suggest": {
            "affiliation_suggest": {
                "prefix": text,
                "completion": {"field": "name", "size": 5},
            }
        }
    }

    index = ""
    if affiliation_type == "institution":
        index = settings.ES_INSTITUTION_COMPLETER_INDEX
    elif affiliation_type == "group":
        index = settings.ES_GROUP_COMPLETER_INDEX
    elif affiliation_type == "department":
        index = settings.ES_DEPARTMENT_COMPLETER_INDEX
    elif affiliation_type == "faculty":
        index = settings.ES_FACULTY_COMPLETER_INDEX
    else:
        raise ValueError("Invalid affiliation type")

    if es_database is None:
        raise ValueError("Elasticsearch database is not initialized")

    response = es_database.search(index=index, body=query)

    options = cast(List[Dict[str, Any]], response["suggest"]["affiliation_suggest"][0]["options"])

    for opt in options:
        name = ""
        if opt["_source"].get("full_name"):
            name = opt["_source"]["full_name"]
        else:
            for _name in opt["_source"]["name"]["input"]:
                if len(name) < len(_name):
                    name = _name
        opt["name"] = name

    return options


def get_source_completions(text: str) -> List[Dict[str, Any]]:
    if es_database is None:
        raise RuntimeError("Elasticsearch client is not initialized")

    query = {
        "suggest": {
            "source_suggest": {
                "prefix": text,
                "completion": {"field": "name", "size": 5},
            }
        }
    }

    response = es_database.search(index=settings.ES_SOURCES_COMPLETER_INDEX, body=query)

    options = cast(List[Dict[str, Any]], response["suggest"]["source_suggest"][0]["options"])

    for opt in options:
        opt["name"] = opt["_source"].get("name", {}).get("input", [""])[0]
        opt["publisher"] = opt["_source"].get("publisher", "")
        opt["products_count"] = opt["_source"].get("products_count", 0)

    return options
