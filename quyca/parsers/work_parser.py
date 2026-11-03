from quyca.constants.institutions import INSTITUTION_TYPE_LABELS
from quyca.models.work_model import Work

from quyca.constants import countries_iso
from quyca.constants.open_access_status import open_access_status_dict
from quyca.constants.product_types import source_titles


def parse_works(works: list, fields: list[str] | None = None) -> list:
    include = {"id", *fields} if fields else None
    return [work.model_dump(include=include, exclude_none=True) for work in works]


def parse_work(work: Work) -> dict:
    return dict(work.model_dump(exclude={"abstracts", "affiliations_data"}))


def parse_available_filters(filters: dict) -> dict:
    available_filters: dict = {}
    if product_types := filters.get("product_types"):
        available_filters["product_types"] = parse_product_type_filter(product_types)
    if institutions_type := filters.get("institutions_type"):
        available_filters["institutions_type"] = parse_institutions_type_filter(institutions_type)
    if years := filters.get("years"):
        available_filters["years"] = years
    if status := filters.get("status"):
        available_filters["status"] = parse_status_filter(status)
    if topics := filters.get("topics"):
        available_filters["topics"] = parse_topic_filter(topics)
    if countries := filters.get("countries"):
        available_filters["countries"] = parse_country_filter(countries)
    if groups_ranking := filters.get("groups_ranking"):
        available_filters["groups_ranking"] = parse_groups_ranking_filter(groups_ranking)
    if authors_ranking := filters.get("authors_ranking"):
        available_filters["authors_ranking"] = parse_authors_ranking_filter(authors_ranking)
    if authors_count := filters.get("authors_count"):
        available_filters["authors_count"] = authors_count
    return available_filters


def parse_authors_ranking_filter(authors_ranking: list) -> list:
    parsed_authors_ranking = []

    for ranking in authors_ranking:
        _id = ranking.get("_id")
        count = ranking.get("count", 0)

        if isinstance(_id, dict):
            label = (_id.get("rank") or "").strip()
            if label:
                parsed_authors_ranking.append(
                    {
                        "value": label,
                        "label": label,
                        "count": count,
                    }
                )
        elif _id:
            label = str(_id).strip()
            if label:
                parsed_authors_ranking.append(
                    {
                        "value": label,
                        "label": label,
                        "count": count,
                    }
                )

    parsed_authors_ranking.sort(key=lambda x: x.get("label") or "")
    return parsed_authors_ranking


def parse_groups_ranking_filter(groups_ranking: list) -> list:
    parsed_groups_ranking = []

    for ranking in groups_ranking:
        if ranking.get("_id"):
            parsed_groups_ranking.append(
                {
                    "value": ranking.get("_id") or "",
                    "label": ranking.get("_id") or "",
                    "count": ranking.get("count", 0),
                }
            )

    parsed_groups_ranking.sort(key=lambda x: x.get("label") or "")
    return parsed_groups_ranking


def parse_topic_filter(topics: list) -> list:
    tree: dict = {}
    for topic in topics:
        levels = [topic.get("domain"), topic.get("field"), topic.get("subfield"), topic]
        if any(not (level or {}).get("id") for level in levels):
            continue
        count = topic.get("count") or 0
        nodes = tree
        for level in levels:
            node = nodes.setdefault(
                level["id"],
                {"value": level["id"], "title": level.get("display_name"), "count": 0, "children": {}},
            )
            node["count"] += count
            nodes = node["children"]
    return topic_tree_to_list(tree)


def topic_tree_to_list(nodes: dict) -> list:
    result = []
    for node in sorted(nodes.values(), key=lambda n: n["count"], reverse=True):
        item = {"value": node["value"], "title": node["title"], "count": node["count"]}
        if children := topic_tree_to_list(node["children"]):
            item["children"] = children
        result.append(item)
    return result


def parse_country_filter(countries: list) -> list:
    parsed_countries = []
    for country in countries:
        if country.get("_id"):
            parsed_countries.append(
                {
                    "value": country.get("_id"),
                    "label": countries_iso.countries_dict.get(country.get("_id"), "Sin País"),
                    "count": country.get("count", 0),
                }
            )

    parsed_countries.sort(key=lambda x: x.get("count", 0), reverse=True)
    return parsed_countries


def parse_status_filter(status: list) -> list:
    statuses = []
    open_children = []

    for oa_status in status:
        count = oa_status.get("count", 0)

        if not oa_status.get("_id"):
            statuses.append({"value": "unknown", "title": "Sin información", "count": count})
        elif oa_status.get("_id") != "closed":
            open_children.append(
                {
                    "value": oa_status.get("_id"),
                    "title": open_access_status_dict.get(oa_status.get("_id")),
                    "count": count,
                }
            )
        else:
            statuses.append({"value": "closed", "title": "Cerrado", "count": count})

    if len(open_children) > 0:
        open_children.sort(key=lambda x: x.get("count", 0), reverse=True)

        total_open_count = sum(child.get("count", 0) for child in open_children)

        statuses.append({"value": "open", "title": "Abierto", "children": open_children, "count": total_open_count})

    statuses.sort(key=lambda x: x.get("count", 0), reverse=True)

    return statuses


def parse_product_type_filter(product_types: list) -> list:
    types = []
    for product_type in product_types:
        children = []
        ignore = ["crossref", "ciarp", "eu-repo", "redcol", "dspace", "coar"]
        if product_type.get("_id") in ignore:
            continue

        elif product_type.get("_id") == "minciencias":
            inner_types = list({element["type"]: element for element in product_type.get("types")}.values())
            for inner_type in inner_types:
                if inner_type.get("level") == 0:
                    continue
                children.append(
                    {
                        "value": product_type.get("_id") + "_" + inner_type.get("type"),
                        "title": inner_type.get("type"),
                        "count": inner_type.get("count", 0),
                    }
                )
            children.sort(key=lambda x: x.get("count", 0), reverse=True)

        elif product_type.get("_id") == "scienti":
            second_level_children = []
            third_level_children = []
            for inner_type in product_type.get("types"):
                if inner_type.get("level") == 0:
                    children.append(
                        {
                            "value": "scienti_" + inner_type.get("type") + "_" + inner_type.get("code"),
                            "title": inner_type.get("code") + " " + inner_type.get("type"),
                            "code": inner_type.get("code"),
                            "count": inner_type.get("count", 0),
                        }
                    )
                elif inner_type.get("level") == 1:
                    second_level_children.append(
                        {
                            "value": "scienti_" + inner_type.get("type") + "_" + inner_type.get("code"),
                            "title": inner_type.get("code") + " " + inner_type.get("type"),
                            "code": inner_type.get("code"),
                            "count": inner_type.get("count", 0),
                        }
                    )
                elif inner_type.get("level") == 2:
                    third_level_children.append(
                        {
                            "value": "scienti_" + inner_type.get("type") + "_" + inner_type.get("code"),
                            "title": inner_type.get("code") + " " + inner_type.get("type"),
                            "code": inner_type.get("code"),
                            "count": inner_type.get("count", 0),
                        }
                    )

            second_level_children.sort(key=lambda x: x.get("count", 0), reverse=True)
            third_level_children.sort(key=lambda x: x.get("count", 0), reverse=True)

            for child in second_level_children:
                child["children"] = list(
                    filter(lambda x: str(x.get("code")).startswith(str(child.get("code"))), third_level_children)
                )
            for child in children:
                child["children"] = list(
                    filter(lambda x: str(x.get("code")).startswith(str(child.get("code"))), second_level_children)
                )
        else:
            for inner_type in product_type.get("types"):
                children.append(
                    {
                        "value": product_type.get("_id") + "_" + inner_type.get("type"),
                        "title": inner_type.get("type"),
                        "count": inner_type.get("count", 0),
                    }
                )
            children.sort(key=lambda x: x.get("count", 0), reverse=True)

        types.append(
            {
                "value": product_type.get("_id"),
                "title": source_titles.get(product_type.get("_id")),
                "children": children,
            }
        )
    types.sort(key=lambda x: x["title"] != "Colav")
    return types


def parse_institutions_type_filter(institutions_type: list) -> list:
    counts = {item.get("_id"): item.get("count", 0) for item in institutions_type if item.get("_id")}
    return [
        {"value": value, "label": label, "count": counts[value]}
        for value, label in INSTITUTION_TYPE_LABELS.items()
        if value in counts
    ]
