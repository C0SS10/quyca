import unicodedata
from dataclasses import dataclass

SCHEMA_VERSION = "1.0"
LIST_SEPARATOR = ";"
ALLOWED_EXTENSIONS = (".xlsx",)
MAX_REPORTED_ISSUES = 500

PROJECT_TYPE_ROYALTIES = "regalías"
PROJECT_STATE_FINISHED = "finalizado"
PROJECT_TYPES = ("investigación", "extensión", PROJECT_TYPE_ROYALTIES, "innovación", "consultoría")
PROJECT_STATES = ("propuesta", "en ejecución", PROJECT_STATE_FINISHED, "suspendido")


@dataclass(frozen=True)
class ColumnSpec:
    name: str
    kind: str = "text"
    required: bool = False
    recommended: bool = False
    multi: bool = False
    allowed: tuple[str, ...] = ()


PROJECT_FILE_COLUMNS: tuple[ColumnSpec, ...] = (
    ColumnSpec("codigo_proyecto", required=True),
    ColumnSpec("titulo", required=True),
    ColumnSpec("resumen", recommended=True),
    ColumnSpec("objetivos"),
    ColumnSpec("tipo_proyecto", kind="enum", allowed=PROJECT_TYPES),
    ColumnSpec("estado", kind="enum", allowed=PROJECT_STATES),
    ColumnSpec("fecha_inicio", kind="date", required=True),
    ColumnSpec("fecha_fin", kind="date"),
    ColumnSpec("investigador_principal_id", kind="document_id", required=True),
    ColumnSpec("investigador_principal_institucion_id", kind="ror"),
    ColumnSpec("investigadores_ids", kind="document_id", multi=True),
    ColumnSpec("valor_total", kind="money"),
    ColumnSpec("valor_especie_total", kind="money"),
    ColumnSpec("valor_fresco_total", kind="money"),
    ColumnSpec("fuente_financiacion_ids", kind="ror_or_wikidata", multi=True),
    ColumnSpec("instituciones_participantes_ids", kind="ror_or_wikidata", multi=True),
    ColumnSpec("codigo_minciencias"),
    ColumnSpec("codigo_bpin"),
    ColumnSpec("convocatoria"),
    ColumnSpec("regiones_ejecucion_id", kind="geonames", multi=True),
    ColumnSpec("unidad_academica_ids", multi=True),
    ColumnSpec("grupos_id", multi=True),
    ColumnSpec("productos_asociados_ids", multi=True),
)


def normalize_token(value: str) -> str:
    decomposed = unicodedata.normalize("NFD", value)
    without_accents = "".join(char for char in decomposed if unicodedata.category(char) != "Mn")
    return " ".join(without_accents.lower().split())


def normalize_header(value: str) -> str:
    return normalize_token(value).replace(" ", "_")
