from collections import defaultdict
from decimal import Decimal
from typing import Generator

from currency_converter import CurrencyConverter
from pymongo.command_cursor import CommandCursor
from quyca.constants.apc_currencies import available_currencies


def parse_annual_evolution_by_impactu_classification(works: Generator) -> dict:
    data: defaultdict = defaultdict(lambda: defaultdict(int))

    for work in works:
        if not work.year_published:
            continue

        for work_type in work.types:
            if work_type.source == "impactu":
                data[work.year_published][work_type.type] += 1

    plot = [
        {"x": year, "y": count, "type": work_type}
        for year, work_types in data.items()
        for work_type, count in work_types.items()
    ]

    return {
        "plot": sorted(
            plot,
            key=lambda x: (x.get("x"), -x.get("y")),
        ),
    }


def parse_affiliations_by_product_type(data: CommandCursor) -> dict:
    plot = [{"x": item["name"], "y": item["works_count"], "type": item["type"]} for item in data]
    totals_by_x: dict[str, int] = {}
    for item in plot:
        totals_by_x[item["x"]] = totals_by_x.get(item["x"], 0) + item["y"]
    plot.sort(key=lambda item: (totals_by_x[item["x"]], item["x"], -item["y"]))

    return {"plot": plot}


def parse_annual_citation_count(works: Generator) -> dict:
    data: dict = {}
    no_info = 0
    for work in works:
        if not work.citations_by_year:
            no_info += 1
            continue
        for citation in work.citations_by_year:
            if citation.year in data.keys():
                data[citation.year] += citation.cited_by_count
            else:
                data[citation.year] = citation.cited_by_count
    plot = [{"x": year, "y": count} for year, count in sorted(data.items(), reverse=True)]
    plot += [{"x": "Sin información", "y": no_info}]
    return {"plot": plot}


def parse_annual_articles_open_access(works: Generator) -> dict:
    data: defaultdict = defaultdict(lambda: {"Abierto": 0, "Cerrado": 0, "Sin información": 0})
    for work in works:
        access_type = "Abierto" if work.open_access.is_open_access else "Cerrado"
        if work.open_access.is_open_access is None and not work.year_published:
            data["Sin año"]["Sin información"] += 1
            continue
        if work.open_access.is_open_access is None:
            data[work.year_published]["Sin información"] += 1
            continue
        if work.year_published is None:
            data["Sin año"][access_type] += 1
            continue
        data[work.year_published][access_type] += 1
    plot = [
        {"x": year, "y": count, "type": access_type}
        for year, counts in data.items()
        for access_type, count in counts.items()
    ]
    return {"plot": sorted(plot, key=lambda x: float("inf") if x.get("x") == "Sin año" else -x.get("x"))}


def parse_annual_articles_by_top_publishers(works: Generator) -> dict:
    data: defaultdict = defaultdict(lambda: defaultdict(int))
    for work in works:
        if not work.source.publisher:
            data[work.year_published]["Sin información"] += 1
            continue
        data[work.year_published][work.source.publisher.name] += 1
    plot = [
        {"x": year, "y": count, "type": publisher}
        for year, publishers in data.items()
        for publisher, count in publishers.items()
        if year is not None and count is not None
    ]
    return {"plot": sorted(plot, key=lambda x: (-x.get("x"), -x.get("y")))}


def parse_annual_apc_expenses(works: Generator) -> dict:
    data: defaultdict = defaultdict(int)

    total_apc = Decimal(0)
    total_results = 0

    currency_converter = CurrencyConverter()

    for work in works:
        total_results += 1

        source_apc = getattr(work.source, "apc", None)
        apc_charges = getattr(source_apc, "charges", None)
        apc_currency = getattr(source_apc, "currency", None)

        if not apc_charges or not apc_currency or apc_currency not in available_currencies:
            continue

        usd_charges = currency_converter.convert(
            apc_charges,
            apc_currency,
            "USD",
        )

        data[work.year_published] += int(usd_charges)
        total_apc += Decimal(usd_charges)

    plot = [{"x": year, "y": value} for year, value in data.items()]

    return {
        "plot": sorted(plot, key=lambda x: -x.get("x")),
        "total_apc": int(total_apc),
        "total_results": total_results,
    }


def parse_annual_scimago_quartile(source: CommandCursor) -> dict:
    plot = []
    for record in source:
        year = record.get("year")
        quartile = record.get("quartile")

        if year and quartile and quartile in ["-", "NaN", None]:
            plot.append({"x": year, "y": "Sin cuartil"})
        else:
            plot.append({"x": year, "y": quartile})

    return {"plot": sorted(plot, key=lambda x: x.get("x", 0))}
