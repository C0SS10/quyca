TYPE_DISPLAY_MAPPING = {
    "journal": "Revista",
    "book series": "Serie de libros",
    "conference": "Conferencia",
    "ebook platform": "Plataforma de libros electrónicos",
    "metadata": "Metadatos",
    "other": "Otro",
    "repository": "Repositorio",
    "not_specified": "No especificado",
}

NORMALIZED_TYPE_MAPPING = {
    # Scienti types
    "E": "journal",
    "EL": "journal",
    "IE": "journal",
    "IM": "journal",
    "L": "journal",
    "P": "journal",
    # OpenAlex types
    "journal": "journal",
    "book series": "book series",
    "conference": "conference",
    "ebook platform": "ebook platform",
    "metadata": "metadata",
    "repository": "repository",
    "other": "other",
    # Scimago types
    "trade journal": "journal",
    "conference and proceedings": "conference",
}


QUARTILE_MAPPING = {"-": "Sin cuartil"}


def normalize_source_type(raw_type: str | None) -> str:
    if not raw_type:
        return "not_specified"
    return NORMALIZED_TYPE_MAPPING.get(raw_type, "not_specified")
