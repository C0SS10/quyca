import csv
import io
from typing import Tuple

from flask import Blueprint, Response, jsonify, request
from sentry_sdk import capture_exception

from quyca.domain.exceptions.not_entity_exception import NotEntityException
from quyca.domain.exceptions.reranker_unavailable_exception import RerankerUnavailableException
from quyca.domain.services import theme_service

theme_app_router = Blueprint("theme_app_router", __name__)

TOP_N_MAX = 4516  # size of the topic catalog (D-004)
RERANK_TOP_N = theme_service.RERANK_MAX_TOPICS  # default size of the list: 120 (D-097)
SEARCH_LIMIT_MAX = 100  # D-008


def _int_in_range(value: object, name: str, minimum: int, maximum: int) -> int:
    """Returns `value` as an int when it is an integer (or a string or float
    that is exactly one) within [minimum, maximum]; otherwise raises the
    ValueError that the routes turn into a 400. bool is not accepted."""
    message = f"{name} must be an integer between {minimum} and {maximum}."
    if isinstance(value, bool):
        raise ValueError(message)
    try:
        if isinstance(value, float):
            if not value.is_integer():
                raise ValueError(message)
            number = int(value)
        else:
            number = int(value)  # type: ignore[call-overload]
    except (TypeError, ValueError):
        raise ValueError(message)
    if not minimum <= number <= maximum:
        raise ValueError(message)
    return number


# NOTA: la sección 9 del documento de diseño original ubicaba estos
# endpoints bajo /api/... -- se corrigió a /app/... porque quyca reserva
# /api/ para la "API experta" (consumo externo/automatizado) y /app/ para
# lo que alimenta al frontend (Guatquyca), que es nuestro caso. También se
# consolidaron los tres grupos originales (themes, curation, topics) bajo
# un solo blueprint/prefijo "theme", siguiendo la convención de quyca de
# un blueprint por entidad.
#
# NOTA sobre errores: a diferencia del patrón exacto de otros *_app_router
# (que capturan Exception genérico -> 400 siempre), acá se distingue
# NotEntityException -> 404, por ser un caso de error claramente
# diferenciable y frecuente en estas rutas (eje no encontrado).


"""
@api {post} /app/theme/candidates Get topic candidates for a seed
@apiName GetCandidates
@apiGroup Theme
@apiVersion 1.1.0
@apiDescription FR3-FR5, fase 1 de 2 (D-097). Calcula el embedding de la semilla (con la
instrucción de consulta de Qwen3-Embedding) y devuelve el top N de tópicos más similares por coseno, con
`rank` = `cosine_rank` y `reranking_available`.

@apiParam {String} seed_text Semilla en lenguaje natural (≤4096 tokens).
@apiParam {Number} [top_n=120] Cantidad de candidatos a devolver (la interfaz ya no lo envía).
"""


@theme_app_router.route("/candidates", methods=["POST"])
def get_candidates() -> Response | Tuple[Response, int]:
    try:
        body = request.get_json(force=True) or {}
        seed_text = body.get("seed_text")
        if not seed_text:
            raise ValueError("seed_text es obligatorio.")
        top_n = _int_in_range(body.get("top_n", RERANK_TOP_N), "top_n", 1, TOP_N_MAX)
        return jsonify(theme_service.get_candidates(seed_text, top_n=top_n))
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        capture_exception(e)
        return jsonify({"error": str(e)}), 400


"""
@api {post} /app/theme/candidates/rerank Reorder the candidates with the reranker
@apiName RerankCandidates
@apiGroup Theme
@apiVersion 1.1.0
@apiDescription D-097, fase 2 de 2. Recibe la semilla y los topic_id de la fase 1 (en su orden) y devuelve los
mismos tópicos reordenados por el reranker, todos de una vez, con `rank` (posición nueva), `cosine_rank` (posición
en la fase 1) y `similarity_score` (coseno). No devuelve el puntaje del reranker. 503 `reranker_unavailable` si el
servicio no responde o tarda más de 60 s.

@apiParam {String} seed_text La misma semilla de la fase 1.
@apiParam {String[]} topic_ids De 1 a 120 topic_id distintos, en el orden de la fase 1.
"""


@theme_app_router.route("/candidates/rerank", methods=["POST"])
def rerank_candidates() -> Response | Tuple[Response, int]:
    try:
        body = request.get_json(force=True) or {}
        seed_text = body.get("seed_text")
        if not seed_text or not isinstance(seed_text, str):
            raise ValueError("seed_text es obligatorio.")
        topic_ids = body.get("topic_ids")
        if not isinstance(topic_ids, list) or not topic_ids:
            raise ValueError("topic_ids debe ser un arreglo no vacío.")
        if len(topic_ids) > theme_service.RERANK_MAX_TOPICS:
            raise ValueError(f"topic_ids admite como máximo {theme_service.RERANK_MAX_TOPICS} elementos.")
        if not all(isinstance(t, str) and t for t in topic_ids):
            raise ValueError("topic_ids debe contener solo cadenas no vacías.")
        if len(set(topic_ids)) != len(topic_ids):
            raise ValueError("topic_ids no admite repetidos.")
        return jsonify(theme_service.rerank_candidates(seed_text, topic_ids))
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except RerankerUnavailableException as e:
        capture_exception(e)
        return (
            jsonify({"error": "El servicio de reordenamiento no está disponible.", "code": "reranker_unavailable"}),
            503,
        )
    except Exception as e:
        capture_exception(e)
        return jsonify({"error": str(e)}), 400


"""
@api {get} /app/theme/search Search topics manually
@apiName SearchTopics
@apiGroup Theme
@apiVersion 1.0.0
@apiDescription FR8. Búsqueda léxica manual en el catálogo completo de
4.516 tópicos (no semántica -- complementa a /candidates).

@apiParam {String} q Texto de búsqueda.
@apiParam {Number} [limit=50] Cantidad máxima de resultados.
"""


@theme_app_router.route("/search", methods=["GET"])
def search_topics() -> Response | Tuple[Response, int]:
    try:
        q = request.args.get("q")
        if not q:
            raise ValueError("El parámetro 'q' es obligatorio.")
        limit = _int_in_range(request.args.get("limit", 50), "limit", 1, SEARCH_LIMIT_MAX)
        return jsonify(theme_service.search_topics(q, limit=limit))
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        capture_exception(e)
        return jsonify({"error": str(e)}), 400


"""
@api {post} /app/theme Create a theme
@apiName CreateTheme
@apiGroup Theme
@apiVersion 1.0.0
@apiDescription FR10. Crea un nuevo Eje Temático.

@apiParam {String} name Nombre del eje.
@apiParam {String} seed_text Semilla usada para la curación.
@apiParam {String} curator Nombre del curador (texto libre, sin cuentas).
@apiParam {String} [description] Descripción pública del eje.
"""


@theme_app_router.route("", methods=["POST"])
def create_theme() -> Response | Tuple[Response, int]:
    try:
        body = request.get_json(force=True) or {}
        for field in ("name", "seed_text", "curator"):
            if not body.get(field):
                raise ValueError(f"{field} es obligatorio.")
        result = theme_service.create_theme(
            name=body["name"],
            description=body.get("description"),
            seed_text=body["seed_text"],
            curator=body["curator"],
        )
        return jsonify(result), 201
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        capture_exception(e)
        return jsonify({"error": str(e)}), 400


"""
@api {get} /app/theme List themes
@apiName ListThemes
@apiGroup Theme
@apiVersion 1.0.0
@apiDescription FR11. Lista los Ejes Temáticos ya guardados.
"""


@theme_app_router.route("", methods=["GET"])
def list_themes() -> Response | Tuple[Response, int]:
    try:
        return jsonify(theme_service.list_themes())
    except Exception as e:
        capture_exception(e)
        return jsonify({"error": str(e)}), 400


"""
@api {get} /app/theme/:theme_id Get theme detail
@apiName GetTheme
@apiGroup Theme
@apiVersion 1.0.0
@apiDescription FR11. Detalle de un eje: metadatos + tópicos clasificados
+ resumen (incluidos/excluidos/frontera/manuales).

@apiParam {String} theme_id ID del eje.
"""


@theme_app_router.route("/<theme_id>", methods=["GET"])
def get_theme(theme_id: str) -> Response | Tuple[Response, int]:
    try:
        return jsonify(theme_service.get_theme(theme_id))
    except NotEntityException as e:
        return jsonify({"error": str(e)}), 404
    except Exception as e:
        capture_exception(e)
        return jsonify({"error": str(e)}), 400


"""
@api {patch} /app/theme/:theme_id/topics/:topic_id Classify a candidate topic
@apiName ClassifyTopic
@apiGroup Theme
@apiVersion 1.0.0
@apiDescription FR6/FR7. Clasifica o reclasifica un tópico candidato dentro
de un eje. justification es obligatoria si status='borderline'.

@apiParam {String} theme_id ID del eje.
@apiParam {String} topic_id ID del tópico.
@apiParam {String="included","excluded","borderline"} status
@apiParam {Number} [similarity_score] Score del candidato original.
@apiParam {String} [justification] Obligatoria si status='borderline'.
"""


@theme_app_router.route("/<theme_id>/topics/<topic_id>", methods=["PATCH"])
def classify_topic(theme_id: str, topic_id: str) -> Response | Tuple[Response, int]:
    try:
        body = request.get_json(force=True) or {}
        status = body.get("status")
        if status not in ("included", "excluded", "borderline"):
            raise ValueError("status debe ser 'included', 'excluded' o 'borderline'.")
        result = theme_service.classify_topic(
            theme_id=theme_id,
            topic_id=topic_id,
            status=status,
            method=body.get("method", "automatic"),
            similarity_score=body.get("similarity_score"),
            justification=body.get("justification"),
        )
        return jsonify(result)
    except NotEntityException as e:
        return jsonify({"error": str(e)}), 404
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        capture_exception(e)
        return jsonify({"error": str(e)}), 400


"""
@api {post} /app/theme/:theme_id/topics Add a manually found topic
@apiName AddManualTopic
@apiGroup Theme
@apiVersion 1.0.0
@apiDescription FR9. Agrega al eje un tópico encontrado por búsqueda
manual (/app/theme/search). Mismo mecanismo que classify_topic, con
method='manual' y sin similarity_score.

@apiParam {String} theme_id ID del eje.
@apiParam {String} topic_id ID del tópico a agregar.
@apiParam {String="included","excluded","borderline"} [status=included]
@apiParam {String} [justification] Obligatoria si status='borderline'.
"""


@theme_app_router.route("/<theme_id>/topics", methods=["POST"])
def add_manual_topic(theme_id: str) -> Response | Tuple[Response, int]:
    try:
        body = request.get_json(force=True) or {}
        topic_id = body.get("topic_id")
        if not topic_id:
            raise ValueError("topic_id es obligatorio.")
        result = theme_service.classify_topic(
            theme_id=theme_id,
            topic_id=topic_id,
            status=body.get("status", "included"),
            method="manual",
            similarity_score=None,
            justification=body.get("justification"),
        )
        return jsonify(result), 201
    except NotEntityException as e:
        return jsonify({"error": str(e)}), 404
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        capture_exception(e)
        return jsonify({"error": str(e)}), 400


"""
@api {post} /app/theme/:theme_id/topics/bulk Classify topics in bulk
@apiName ClassifyTopicsBulk
@apiGroup Theme
@apiVersion 1.0.0
@apiDescription Persiste muchas clasificaciones en un solo INSERT a
ClickHouse -- pensado para "guardar eje" (pantalla 3), donde un eje puede
tener 100-150+ tópicos clasificados y una petición HTTP por tópico no
escala. Soporta éxito parcial: un ítem inválido no aborta los demás.

@apiParam {String} theme_id ID del eje.
@apiParam {Object[]} topics Lista de clasificaciones.
@apiParam {String} topics.topic_id
@apiParam {String="included","excluded","borderline"} topics.status
@apiParam {String="automatic","manual"} [topics.method=automatic] "manual" fuerza similarity_score=null.
@apiParam {Number} [topics.similarity_score] Ignorado si method='manual'.
@apiParam {String} [topics.justification] Obligatoria si status='borderline'.
"""


@theme_app_router.route("/<theme_id>/topics/bulk", methods=["POST"])
def classify_topics_bulk(theme_id: str) -> Response | Tuple[Response, int]:
    try:
        body = request.get_json(force=True) or {}
        topics = body.get("topics")
        if not isinstance(topics, list) or not topics:
            raise ValueError("topics es obligatorio y debe ser un arreglo no vacío.")
        return jsonify(theme_service.classify_topics_bulk(theme_id, topics))
    except NotEntityException as e:
        return jsonify({"error": str(e)}), 404
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        capture_exception(e)
        return jsonify({"error": str(e)}), 400


"""
@api {get} /app/theme/:theme_id/export Export theme topics
@apiName ExportTheme
@apiGroup Theme
@apiVersion 1.0.0
@apiDescription FR12. Exporta los tópicos del eje, calculado al vuelo (no
se persiste el historial de exportaciones).

@apiParam {String} theme_id ID del eje.
@apiParam {String="json","csv"} [format=json]
"""


@theme_app_router.route("/<theme_id>/export", methods=["GET"])
def export_theme(theme_id: str) -> Response | Tuple[Response, int]:
    try:
        export_format = request.args.get("format", "json")
        result = theme_service.export_theme(theme_id)
        if export_format == "csv":
            rows = result["data"]
            output = io.StringIO()
            if rows:
                writer = csv.DictWriter(output, fieldnames=list(rows[0].keys()))
                writer.writeheader()
                writer.writerows(rows)
            response = Response(output.getvalue(), mimetype="text/csv")
            response.headers["Content-Disposition"] = f"attachment; filename=eje_{theme_id}.csv"
            return response
        return jsonify(result)
    except NotEntityException as e:
        return jsonify({"error": str(e)}), 404
    except Exception as e:
        capture_exception(e)
        return jsonify({"error": str(e)}), 400
