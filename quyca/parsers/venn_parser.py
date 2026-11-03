from itertools import combinations as source_combinations

VENN_SOURCES = (
    "scienti",
    "minciencias",
    "openalex",
    "scholar",
)


def parse_products_by_database(data: list[dict]) -> dict:
    counts = {"_".join(source for source in VENN_SOURCES if source in item["_id"]): item["count"] for item in data}

    venn_source = {
        "_".join(combination): counts.get("_".join(combination), 0)
        for size in range(1, len(VENN_SOURCES) + 1)
        for combination in source_combinations(VENN_SOURCES, size)
    }

    return {"plot": venn_source}
