"""
Person identifiers the API may publish. Every other source is an identity document
(cédula, pasaporte, tarjeta de identidad...) or one the ETL added later that nobody
has reviewed, so it never leaves the API.
"""

PUBLIC_PERSON_ID_SOURCES = frozenset(
    {"linkedin", "openalex", "orcid", "publons", "researchgate", "scholar", "scienti", "scopus", "ssrn", "wos"}
)
