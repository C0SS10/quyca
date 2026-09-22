import csv
import io
from collections import Counter, defaultdict
from collections.abc import Generator, Iterable, Iterator
from datetime import datetime
from itertools import chain
from typing import Any, Dict, Optional, Tuple

from currency_converter import CurrencyConverter
from pymongo.command_cursor import CommandCursor

from quyca.domain.constants.apc_currencies import available_currencies
from quyca.domain.constants.open_access_status import open_access_status_dict
from quyca.domain.models.affiliation_model import Affiliation
from quyca.domain.models.calculations_model import Calculations
from quyca.domain.parsers import map_parser
from quyca.domain.parsers.export import export_network_parser


VENN_SOURCES = (
    "scienti",
    "minciencias",
    "openalex",
    "scholar",
)


def csv_rows(
    rows: Iterable[dict[str, Any]],
    fieldnames: list[str],
) -> Iterator[str]:
    buffer = io.StringIO()
    writer = csv.DictWriter(
        buffer,
        fieldnames=fieldnames,
        extrasaction="ignore",
    )

    writer.writeheader()
    yield buffer.getvalue()

    for row in rows:
        buffer.seek(0)
        buffer.truncate(0)

        writer.writerow(row)

        yield buffer.getvalue()


def single_column_csv_rows(header: str, values: Iterable[str]) -> Iterator[str]:
    buffer = io.StringIO()
    writer = csv.writer(buffer)

    writer.writerow([header])
    yield buffer.getvalue()

    for value in values:
        buffer.seek(0)
        buffer.truncate(0)
        writer.writerow([value])
        yield buffer.getvalue()


def network_csv_rows(
    nodes: Iterable[str],
    edges: Iterable[Tuple[str, str]],
) -> Iterator[str]:
    """Escribe un CSV de dos secciones: nombres únicos, una línea en blanco, y relaciones 'nombre1-nombre2'."""
    yield from single_column_csv_rows("nombre", nodes)

    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow([])
    yield buffer.getvalue()

    yield from single_column_csv_rows(
        "relacion",
        (f"{source}-{target}" for source, target in edges),
    )


def parse_affiliations_by_product_type(
    data: Iterable[dict[str, Any]],
) -> Iterator[dict[str, Any]]:
    for item in data:
        yield {
            "name": item.get("name"),
            "works_count": item.get("works_count", 0),
            "type": item.get("type"),
        }


def parse_citations_by_affiliation(
    data: Iterable[dict[str, Any]],
) -> Iterator[dict[str, Any]]:
    for item in data:
        citations = item.get("citations_count", [])

        scholar_citations = sum(
            citation.get("count", 0) for citation in citations if citation.get("source") == "scholar"
        )

        yield {
            "name": item.get("name"),
            "citations": scholar_citations,
        }


def parse_apc_expenses_by_affiliation(
    data: Iterable[dict[str, Any]],
) -> Iterator[dict[str, Any]]:
    for item in data:
        apc = item.get("apc") or {}

        yield {
            "name": item.get("name"),
            "charges": apc.get("charges"),
            "currency": apc.get("currency"),
        }


def calculate_h_index(citations: Iterable[int]) -> int:
    ordered = sorted(
        (citation for citation in citations if isinstance(citation, (int, float))),
        reverse=True,
    )

    return sum(1 for position, citation in enumerate(ordered, start=1) if citation >= position)


def parse_h_index_by_affiliation(data: Iterable[dict[str, Any]]) -> Iterator[dict[str, Any]]:
    for item in data:
        citations = item.get("scholar_distribution", [])

        yield {
            "name": item.get("name"),
            "h_index": calculate_h_index(citations),
        }


def parse_products_by_database(data: Iterable[dict[str, Any]]) -> Iterator[dict[str, Any]]:
    for item in data:
        sources = set(item.get("_id", []))

        yield {
            **{source: int(source in sources) for source in VENN_SOURCES},
            "count": item.get("count", 0),
        }


def parse_coauthorship_by_country_map(
    counts: Dict[str, Dict[str, Any]],
) -> Iterator[dict[str, Any]]:
    centroids = map_parser.get_country_centroids()
    for country_code, info in counts.items():
        centroid = centroids.get(country_code)
        longitude, latitude = centroid if centroid else (None, None)
        yield {
            "country_name": info["name"],
            "latitude": latitude,
            "longitude": longitude,
            "coautorships": info["count"],
        }


def parse_coauthorship_by_colombian_department_map(
    counts: Dict[str, Dict[str, Any]],
) -> Iterator[dict[str, Any]]:
    centroids = map_parser.get_colombian_department_centroids()
    for department_name, info in counts.items():
        centroid = centroids.get(department_name)
        longitude, latitude = centroid if centroid else (None, None)
        yield {
            "department_name": info["name"],
            "latitude": latitude,
            "longitude": longitude,
            "coautorships": info["count"],
        }


def parse_annual_evolution_by_scienti_classification(works: Generator) -> Iterator[dict[str, Any]]:
    data: defaultdict = defaultdict(lambda: defaultdict(int))
    for work in works:
        if not work.year_published:
            continue
        for work_type in work.types:
            if work_type.source == "scienti" and work_type.level == 2:
                data[work.year_published][work_type.type] += 1

    for year, work_types in data.items():
        for work_type, count in work_types.items():
            yield {"year": year, "type": work_type, "count": count}


def parse_annual_citation_count(works: Generator) -> Iterator[dict[str, Any]]:
    data: dict = {}
    no_info = 0
    for work in works:
        if not work.citations_by_year:
            no_info += 1
            continue
        for citation in work.citations_by_year:
            data[citation.year] = data.get(citation.year, 0) + citation.cited_by_count

    for year, count in data.items():
        yield {"year": year, "citations": count}
    yield {"year": "Sin información", "citations": no_info}


def parse_annual_articles_open_access(works: Generator) -> Iterator[dict[str, Any]]:
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

    for year, counts in data.items():
        for access_type, count in counts.items():
            yield {"year": year, "access_type": access_type, "count": count}


def parse_annual_articles_by_top_publishers(works: Generator) -> Iterator[dict[str, Any]]:
    data: defaultdict = defaultdict(lambda: defaultdict(int))
    for work in works:
        if not work.source.publisher:
            data[work.year_published]["Sin información"] += 1
            continue
        data[work.year_published][work.source.publisher.name] += 1

    for year, publishers in data.items():
        for publisher, count in publishers.items():
            if year is not None and count is not None:
                yield {"year": year, "publisher": publisher, "count": count}


def parse_most_used_title_words(data: Calculations) -> Iterator[dict[str, Any]]:
    top_words = data.model_dump().get("top_words") or []
    for item in sorted(top_words, key=lambda x: x.get("value", 0), reverse=True):
        yield {"word": item.get("name"), "count": item.get("value")}


def parse_articles_by_publisher(works: Generator) -> Iterator[dict[str, Any]]:
    names = (
        work.source.publisher.name
        if work.source.publisher and isinstance(work.source.publisher.name, str)
        else "Sin información"
        for work in works
    )
    for publisher, count in Counter(names).items():
        yield {"publisher": publisher, "count": count}


def parse_products_by_subject(works: Generator) -> Iterator[dict[str, Any]]:
    names = (
        work.primary_topic.display_name for work in works if work.primary_topic and work.primary_topic.display_name
    )
    for subject, count in Counter(names).items():
        yield {"subject": subject, "count": count}


def parse_articles_by_access_route(works: Generator) -> Iterator[dict[str, Any]]:
    statuses = (
        work.open_access.open_access_status if work.open_access.open_access_status else "no_info" for work in works
    )
    for status, count in Counter(statuses).items():
        yield {"access_route": open_access_status_dict.get(status, status), "count": count}


def parse_active_authors_by_sex(persons: CommandCursor) -> Iterator[dict[str, Any]]:
    result: defaultdict = defaultdict(int)
    for person in persons:
        sex = person.get("sex") or "Sin información"
        result[sex] += 1

    for sex, count in result.items():
        yield {"sex": sex, "count": count}


def parse_active_authors_by_age_range(persons: CommandCursor) -> Iterator[dict[str, Any]]:
    ranges = {"14-26": (14, 26), "27-59": (27, 59), "60+": (60, float("inf"))}
    result = {"14-26": 0, "27-59": 0, "60+": 0, "Sin información": 0}
    for person in persons:
        if not person.get("birthdate") or person.get("birthdate") == -1:
            result["Sin información"] += 1
            continue
        birthdate_year = datetime.fromtimestamp(person.get("birthdate")).year
        age = datetime.now().year - birthdate_year
        for age_range, (low_age, high_age) in ranges.items():
            if low_age <= age <= high_age:
                result[age_range] += 1
                break

    for age_range, count in result.items():
        yield {"age_range": age_range, "count": count}


def parse_articles_by_scienti_category(works: list) -> Iterator[dict[str, Any]]:
    total_works = len(works)
    rankings = chain.from_iterable(work.ranking for work in works)
    valid_rankings = filter(
        lambda ranking: (
            ranking.source == "scienti" and ranking.rank and ranking.rank.split("_")[-1] in ["A", "A1", "B", "C", "D"]
        ),
        rankings,
    )
    counter = Counter(ranking.rank.split("_")[-1] for ranking in valid_rankings)

    for category, count in counter.items():
        yield {"category": category, "count": count}
    yield {"category": "Sin información", "count": total_works - sum(counter.values())}


def parse_articles_by_scimago_quartile(works: Generator) -> Iterator[dict[str, Any]]:
    valid_sources = {"Scimago Best Quartile", "scimago Best Quartile"}
    quartiles = []
    total_articles = 0
    for work in works:
        total_articles += 1
        work_date = getattr(work, "date_published", None)
        if not work_date:
            continue
        source_rankings = getattr(work.source, "ranking", None) or []
        for ranking in source_rankings:
            if ranking.source in valid_sources and ranking.rank != "-" and ranking.from_date <= work_date <= ranking.to_date:
                quartiles.append(ranking.rank)
                break

    yield {"quartile": "Sin información", "count": total_articles - len(quartiles)}
    for quartile, count in Counter(quartiles).items():
        yield {"quartile": quartile, "count": count}


def parse_articles_by_publishing_institution(
    data: Tuple[Generator, Optional[Affiliation]],
) -> Iterator[dict[str, Any]]:
    works, institution = data
    result = {"Misma": 0, "Diferente": 0, "Sin información": 0}
    names: set = set()
    if institution and institution.names:
        names = {name.name.lower() for name in institution.names if name.name is not None}

    for work in works:
        publisher = work.source.publisher
        if not publisher or not publisher.name or not isinstance(publisher.name, str):
            result["Sin información"] += 1
            continue
        if publisher.name.lower() in names:
            result["Misma"] += 1
        else:
            result["Diferente"] += 1

    for category, count in result.items():
        yield {"category": category, "count": count}


def parse_annual_apc_expenses(works: Generator) -> Iterator[dict[str, Any]]:
    data: defaultdict = defaultdict(int)
    currency_converter = CurrencyConverter()

    for work in works:
        source_apc = getattr(work.source, "apc", None)
        apc_charges = getattr(source_apc, "charges", None)
        apc_currency = getattr(source_apc, "currency", None)
        if not apc_charges or not apc_currency or apc_currency not in available_currencies:
            continue
        usd_charges = currency_converter.convert(apc_charges, apc_currency, "USD")
        data[work.year_published] += int(usd_charges)

    for year, value in data.items():
        yield {"year": year, "apc_usd": value}


PLOT_PARSERS = {
    "faculties_by_product_type": (
        parse_affiliations_by_product_type,
        ["name", "works_count", "type"],
    ),
    "departments_by_product_type": (
        parse_affiliations_by_product_type,
        ["name", "works_count", "type"],
    ),
    "research_groups_by_product_type": (
        parse_affiliations_by_product_type,
        ["name", "works_count", "type"],
    ),
    "citations_by_faculty": (
        parse_citations_by_affiliation,
        ["name", "citations"],
    ),
    "citations_by_department": (
        parse_citations_by_affiliation,
        ["name", "citations"],
    ),
    "citations_by_research_group": (
        parse_citations_by_affiliation,
        ["name", "citations"],
    ),
    "apc_expenses_by_faculty": (
        parse_apc_expenses_by_affiliation,
        ["name", "charges", "currency"],
    ),
    "apc_expenses_by_department": (
        parse_apc_expenses_by_affiliation,
        ["name", "charges", "currency"],
    ),
    "apc_expenses_by_group": (
        parse_apc_expenses_by_affiliation,
        ["name", "charges", "currency"],
    ),
    "h_index_by_faculty": (
        parse_h_index_by_affiliation,
        ["name", "h_index"],
    ),
    "h_index_by_department": (
        parse_h_index_by_affiliation,
        ["name", "h_index"],
    ),
    "h_index_by_research_group": (
        parse_h_index_by_affiliation,
        ["name", "h_index"],
    ),
    "products_by_database": (
        parse_products_by_database,
        [
            "scienti",
            "minciencias",
            "openalex",
            "scholar",
            "count",
        ],
    ),
    "coauthorship_by_country_map": (
        parse_coauthorship_by_country_map,
        ["country_name", "latitude", "longitude", "coautorships"],
    ),
    "coauthorship_by_colombian_department_map": (
        parse_coauthorship_by_colombian_department_map,
        ["department_name", "latitude", "longitude", "coautorships"],
    ),
    "annual_evolution_by_scienti_classification": (
        parse_annual_evolution_by_scienti_classification,
        ["year", "type", "count"],
    ),
    "annual_citation_count": (
        parse_annual_citation_count,
        ["year", "citations"],
    ),
    "annual_articles_open_access": (
        parse_annual_articles_open_access,
        ["year", "access_type", "count"],
    ),
    "annual_articles_by_top_publishers": (
        parse_annual_articles_by_top_publishers,
        ["year", "publisher", "count"],
    ),
    "most_used_title_words": (
        parse_most_used_title_words,
        ["word", "count"],
    ),
    "articles_by_publisher": (
        parse_articles_by_publisher,
        ["publisher", "count"],
    ),
    "products_by_subject": (
        parse_products_by_subject,
        ["subject", "count"],
    ),
    "articles_by_access_route": (
        parse_articles_by_access_route,
        ["access_route", "count"],
    ),
    "active_authors_by_sex": (
        parse_active_authors_by_sex,
        ["sex", "count"],
    ),
    "active_authors_by_age_range": (
        parse_active_authors_by_age_range,
        ["age_range", "count"],
    ),
    "articles_by_scienti_category": (
        parse_articles_by_scienti_category,
        ["category", "count"],
    ),
    "articles_by_scimago_quartile": (
        parse_articles_by_scimago_quartile,
        ["quartile", "count"],
    ),
    "articles_by_publishing_institution": (
        parse_articles_by_publishing_institution,
        ["category", "count"],
    ),
    "annual_apc_expenses": (
        parse_annual_apc_expenses,
        ["year", "apc_usd"],
    ),
}


NETWORK_PLOTS = {"institutional_coauthorship_network"}


def parse_plot_to_csv(
    plot: str,
    data: Any,
) -> Iterator[str]:
    if plot in NETWORK_PLOTS:
        calculations: Calculations = data
        nodes = export_network_parser.parse_institutional_coauthorship_network_nodes(calculations)
        edges = export_network_parser.parse_institutional_coauthorship_network_edges(calculations)
        return network_csv_rows(nodes, edges)

    parser_config = PLOT_PARSERS.get(plot)

    if parser_config is None:
        raise ValueError(f"No existe un parser CSV para el plot '{plot}'.")

    parser, fieldnames = parser_config

    rows = parser(data)

    return csv_rows(
        rows,
        fieldnames,
    )