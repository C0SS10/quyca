from flask import Blueprint, Response, jsonify, request

from quyca.api.helpers import register_error_handlers
from quyca.config import settings
from quyca.exceptions import ObservatoryNotLoadedException
from quyca.services import observatory_service

observatory_router = Blueprint("observatory_router", __name__)
register_error_handlers(observatory_router)


def _unavailable(message: str, code: str) -> tuple[Response, int]:
    return jsonify({"error": message, "code": code}), 503


@observatory_router.errorhandler(ObservatoryNotLoadedException)
def handle_not_loaded(error: ObservatoryNotLoadedException) -> tuple[Response, int]:
    return _unavailable(str(error), "observatory_not_loaded")


@observatory_router.before_request
def require_observatory_service() -> tuple[Response, int] | None:
    """The observatory reads the same optional ClickHouse as the curation tool: without it the routes answer 503."""
    if not settings.CLICKHOUSE_SERVER:
        return _unavailable("The observatory service is not configured.", "observatory_not_configured")
    return None


@observatory_router.route("/<slug>/boards/<int:board>/bundle", methods=["GET"])
def get_bundle(slug: str, board: int) -> Response:
    bundle = observatory_service.get_bundle(slug, board)
    headers = {
        "ETag": bundle["etag"],
        "Cache-Control": "no-cache",
        "Vary": "Accept-Encoding",
    }
    if observatory_service.etag_matches(request.headers.get("If-None-Match"), bundle["etag"]):
        return Response(status=304, headers=headers)
    if "gzip" in request.headers.get("Accept-Encoding", "").lower():
        return Response(
            bundle["gzip"],
            content_type="application/json",
            headers={**headers, "Content-Encoding": "gzip"},
        )
    return Response(
        observatory_service.gunzip(bundle["gzip"]),
        content_type="application/json",
        headers=headers,
    )


@observatory_router.route("/<slug>/cut", methods=["GET"])
def get_cut(slug: str) -> Response:
    return jsonify({"data": observatory_service.get_cut(slug)})
