from flask import Blueprint

ping_router = Blueprint("ping_router", __name__)


@ping_router.route("/ping", methods=["GET"])
def ping() -> dict:
    """Ping the API."""
    return {"ping": "pong"}
