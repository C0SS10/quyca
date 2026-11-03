from flask import Blueprint, Response, jsonify

from quyca.api.helpers import register_error_handlers
from quyca.repositories import completer_repository

completer_router = Blueprint("completer_app_router", __name__)
register_error_handlers(completer_router)


@completer_router.route("/person/<text>", methods=["GET"])
def get_person_completion(text: str) -> Response:
    return jsonify(completer_repository.get_person_completions(text))


@completer_router.route("/affiliations/<any(institution, faculty, department, group):affiliation_type>/<text>")
def get_affiliation_completion(affiliation_type: str, text: str) -> Response:
    return jsonify(completer_repository.get_affiliation_completions(affiliation_type, text))


@completer_router.route("/sources/<text>", methods=["GET"])
def get_source_completion(text: str) -> Response:
    return jsonify(completer_repository.get_source_completions(text))
