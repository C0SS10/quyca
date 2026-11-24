from functools import wraps
from typing import Any

from flask import Blueprint, Response, jsonify, request
from sentry_sdk import capture_exception

from quyca.api.helpers import CSV_CONTENT_TYPE, file_response, parse_json_object, register_error_handlers
from quyca.api.permissions import View
from quyca.config import settings
from quyca.exceptions import RerankerUnavailableException
from quyca.services import theme_service
from quyca.validators import theme_validator

theme_router = Blueprint("theme_router", __name__)
register_error_handlers(theme_router)


def _unavailable(message: str, code: str) -> tuple[Response, int]:
    return jsonify({"error": message, "code": code}), 503


@theme_router.errorhandler(RerankerUnavailableException)
def handle_reranker_unavailable(error: RerankerUnavailableException) -> tuple[Response, int]:
    # The interface keeps the cosine list when the second phase fails.
    capture_exception(error)
    return _unavailable("El servicio de reordenamiento no está disponible.", "reranker_unavailable")


@theme_router.before_request
def require_curation_service() -> tuple[Response, int] | None:
    """The curation tool is optional: without ClickHouse configured its routes answer 503 and the rest of the API works."""
    if not settings.CLICKHOUSE_SERVER:
        return _unavailable("The topic curation service is not configured.", "curation_not_configured")
    return None


def require_embeddings(view: View) -> View:
    """The candidate routes also need Ollama to embed the seed."""

    @wraps(view)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        if not (settings.OLLAMA_URL and settings.OLLAMA_MODEL):
            return _unavailable("The embedding service is not configured.", "embeddings_not_configured")
        return view(*args, **kwargs)

    return wrapper


@theme_router.route("/candidates", methods=["POST"])
@require_embeddings
def get_candidates() -> Response:
    data = parse_json_object(force=True)
    seed_text = theme_validator.validate_text(data.get("seed_text"), "seed_text")
    top_n = theme_validator.validate_int_in_range(
        data.get("top_n", theme_validator.RERANK_MAX_TOPICS), "top_n", 1, theme_validator.TOP_N_MAX
    )
    return jsonify(theme_service.get_candidates(seed_text, top_n))


@theme_router.route("/candidates/rerank", methods=["POST"])
@require_embeddings
def rerank_candidates() -> Response:
    data = parse_json_object(force=True)
    seed_text = theme_validator.validate_text(data.get("seed_text"), "seed_text")
    topic_ids = theme_validator.validate_topic_ids(data.get("topic_ids"))
    return jsonify(theme_service.rerank_candidates(seed_text, topic_ids))


@theme_router.route("/search", methods=["GET"])
def search_topics() -> Response:
    query_text = theme_validator.validate_text(request.args.get("q"), "q")
    limit = theme_validator.validate_int_in_range(
        request.args.get("limit", 50), "limit", 1, theme_validator.SEARCH_LIMIT_MAX
    )
    return jsonify(theme_service.search_topics(query_text, limit))


@theme_router.route("", methods=["POST"])
def create_theme() -> tuple[Response, int]:
    data = parse_json_object(force=True)
    name = theme_validator.validate_text(data.get("name"), "name")
    seed_text = theme_validator.validate_text(data.get("seed_text"), "seed_text")
    curator = theme_validator.validate_text(data.get("curator"), "curator")
    return jsonify(theme_service.create_theme(name, data.get("description"), seed_text, curator)), 201


@theme_router.route("", methods=["GET"])
def get_themes() -> Response:
    return jsonify(theme_service.get_themes())


@theme_router.route("/<theme_id>", methods=["GET"])
def get_theme_by_id(theme_id: str) -> Response:
    return jsonify(theme_service.get_theme_by_id(theme_id))


@theme_router.route("/<theme_id>/topics/<topic_id>", methods=["PATCH"])
def classify_topic(theme_id: str, topic_id: str) -> Response:
    data = parse_json_object(force=True)
    theme_topic = theme_service.classify_topic(
        theme_id,
        topic_id,
        data.get("status"),
        data.get("method", "automatic"),
        data.get("similarity_score"),
        data.get("justification"),
    )
    return jsonify(theme_topic)


@theme_router.route("/<theme_id>/topics", methods=["POST"])
def add_manual_topic(theme_id: str) -> tuple[Response, int]:
    data = parse_json_object(force=True)
    topic_id = theme_validator.validate_text(data.get("topic_id"), "topic_id")
    theme_topic = theme_service.classify_topic(
        theme_id, topic_id, data.get("status", "included"), "manual", None, data.get("justification")
    )
    return jsonify(theme_topic), 201


@theme_router.route("/<theme_id>/topics/bulk", methods=["POST"])
def classify_topics_bulk(theme_id: str) -> Response:
    topics = theme_validator.validate_topics(parse_json_object(force=True).get("topics"))
    return jsonify(theme_service.classify_topics_bulk(theme_id, topics))


@theme_router.route("/<theme_id>/export", methods=["GET"])
def get_theme_export(theme_id: str) -> Response:
    if request.args.get("format") == "csv":
        return file_response(theme_service.get_theme_csv(theme_id), f"eje_{theme_id}.csv", CSV_CONTENT_TYPE)
    return jsonify(theme_service.get_theme_export(theme_id))
