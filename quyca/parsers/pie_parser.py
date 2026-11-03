from functools import wraps
from datetime import datetime
from itertools import chain
from typing import Callable, Iterable, Generator
from collections import Counter, defaultdict

from currency_converter import CurrencyConverter
from pymongo.command_cursor import CommandCursor

from quyca.constants.apc_currencies import available_currencies
from quyca.constants.open_access_status import open_access_status_dict
from quyca.models.affiliation_model import Affiliation
from quyca.models.calculations_model import Calculations
from quyca.normalizers.affiliation_names import get_affiliation_name


def get_percentage(func: Callable[..., list]) -> Callable[..., dict]:
    @wraps(func)
    def wrapper(*args: Iterable, **kwargs: dict) -> dict:
        data = func(*args, **kwargs)
        total = sum(item["value"] for item in data)
        for item in data:
            item["percentage"] = round(item["value"] / total * 100, 2) if total else 0
        return {"plot": data, "sum": total}

    return wrapper


@get_percentage
def parse_citations_by_affiliations(data: CommandCursor) -> list:
    plot: list = []
    for item in data:
        citations_count = item.get("citations_count", {})
        scholar_citations_count: dict = next(filter(lambda x: x["source"] == "scholar", citations_count), {})
        plot.append({"name": item.get("name", "No name"), "value": scholar_citations_count.get("count", 0)})
    return sorted(plot, key=lambda x: x.get("value"), reverse=True)


@get_percentage
def parse_apc_expenses_by_affiliations(data: CommandCursor) -> list:
    result: defaultdict[str, int] = defaultdict(int)
    currency_converter = CurrencyConverter()

    for item in data:
        apc = item.get("apc", {})
        apc_charges = apc.get("charges", 0)
        apc_currency = apc.get("currency", "USD")
        if apc_currency not in available_currencies:
            continue
        usd_charges = currency_converter.convert(apc_charges, apc_currency, "USD")
        name = item.get("name", "No name")
        result[name] += int(usd_charges)

    return sorted([{"name": n, "value": v} for n, v in result.items()], key=lambda x: x["value"], reverse=True)


@get_percentage
def parse_h_index_by_affiliation(data: CommandCursor) -> list:
    plot = [
        {
            "name": get_affiliation_name(item.get("names")),
            "value": item.get("h_index") or 0,
        }
        for item in data
    ]
    return sorted(plot, key=lambda x: x["value"], reverse=True)


@get_percentage
def parse_articles_by_publisher(works: Generator) -> list:
    data = map(
        lambda x: (
            x.source.publisher.name
            if x.source.publisher and isinstance(x.source.publisher.name, str)
            else "Sin información"
        ),
        works,
    )
    counter = Counter(data)
    plot = []
    for name, value in counter.items():
        plot += [{"name": name, "value": value}]
    return sorted(plot, key=lambda x: x.get("value"), reverse=True)


@get_percentage
def parse_products_by_subject(works: Generator) -> list:
    names = [
        work.primary_topic.display_name for work in works if work.primary_topic and work.primary_topic.display_name
    ]

    results = Counter(names)
    plot = [{"name": name, "value": value} for name, value in results.items()]
    return sorted(plot, key=lambda x: x["value"], reverse=True)


@get_percentage
def parse_products_by_access_route(works: Generator) -> list:
    data = map(
        lambda x: (x.open_access.open_access_status if x.open_access.open_access_status else "no_info"),
        works,
    )
    counter = Counter(data)
    plot = []
    for name, value in counter.items():
        plot.append({"name": open_access_status_dict.get(name), "value": value})
    return sorted(plot, key=lambda x: x.get("value"), reverse=True)


@get_percentage
def parse_active_authors_by_sex(persons: CommandCursor) -> list:
    result: defaultdict = defaultdict(int)
    for person in persons:
        if not person.get("sex") or person.get("sex") == "":
            result["Sin información"] += 1
            continue
        result[person.get("sex")] += 1
    plot = []
    for name, value in result.items():
        plot.append({"name": name, "value": value})
    return plot


@get_percentage
def parse_active_authors_by_age_range(persons: CommandCursor) -> list:
    ranges = {"14-26": (14, 26), "27-59": (27, 59), "60+": (60, float("inf"))}
    result = {"14-26": 0, "27-59": 0, "60+": 0, "Sin información": 0}
    for person in persons:
        if not person.get("birthdate") or person.get("birthdate") == -1:
            result["Sin información"] += 1
            continue
        birthdate = datetime.fromtimestamp(person.get("birthdate")).year
        age = datetime.now().year - birthdate
        for name, (low_age, high_age) in ranges.items():
            if low_age <= age <= high_age:
                result[name] += 1
                break
    plot = []
    for name, value in result.items():
        plot.append({"name": name, "value": value})
    return plot


@get_percentage
def parse_articles_by_scienti_category(works: list) -> list:
    total_works = len(works)
    data = filter(
        lambda x: x.source == "scienti" and x.rank and x.rank.split("_")[-1] in ["A", "A1", "B", "C", "D"],
        chain.from_iterable(map(lambda x: x.ranking, works)),
    )
    counter = Counter(map(lambda x: x.rank.split("_")[-1], data))
    plot = []
    for name, value in counter.items():
        plot.append({"name": name, "value": value})
    plot.append({"name": "Sin información", "value": total_works - sum(counter.values())})
    return plot


@get_percentage
def parse_articles_by_scimago_quartile(works: Generator) -> list:
    valid_sources = {"Scimago Best Quartile", "scimago Best Quartile"}
    data = []
    total_articles = 0
    for work in works:
        total_articles += 1
        work_date = getattr(work, "date_published", None)
        if not work_date:
            continue
        source_rankings = getattr(work.source, "ranking", None) or []
        for ranking in source_rankings:
            if (
                ranking.source in valid_sources
                and ranking.rank != "-"
                and ranking.from_date <= work_date <= ranking.to_date
            ):
                data.append(ranking.rank)
                break
    counter = Counter(data)
    plot = [{"name": "Sin información", "value": total_articles - len(data)}]
    plot.extend({"name": name, "value": value} for name, value in counter.items())
    return plot


@get_percentage
def parse_articles_by_publishing_institution(works: Generator, institution: Affiliation) -> list:
    result = {"Misma": 0, "Diferente": 0, "Sin información": 0}
    names = []
    if institution and institution.names:
        names = list(set([name.name.lower() for name in institution.names if name.name is not None]))
    for work in works:
        if (
            not work.source.publisher
            or not work.source.publisher.name
            or not isinstance(work.source.publisher.name, str)
        ):
            result["Sin información"] += 1
            continue
        if work.source.publisher.name.lower() in names:
            result["Misma"] += 1
        else:
            result["Diferente"] += 1
    plot = []
    for name, value in result.items():
        plot.append({"name": name, "value": value})
    return plot


def parse_most_used_title_words(data: Calculations) -> dict:
    top_words = data.model_dump().get("top_words")
    if not top_words:
        return {
            "plot": [{"name": "Sin información", "value": 1, "percentage": 100}],
            "sum": 1,
        }
    return {"plot": sorted(top_words, key=lambda x: x.get("value"), reverse=True)}
