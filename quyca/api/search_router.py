from flask import Blueprint, request, jsonify
from werkzeug.wrappers.response import Response

from quyca.api.helpers import parse_query_params, register_error_handlers
from quyca.services import search_service

search_router = Blueprint("search_router", __name__)
register_error_handlers(search_router)


@search_router.route("/person", methods=["GET"])
def search_persons() -> Response:
    return jsonify(search_service.search_persons(parse_query_params(), request.url))


@search_router.route("/works", methods=["GET"])
def search_works() -> Response:
    return jsonify(search_service.search_works(parse_query_params(), request.url))


@search_router.route("/affiliations/<affiliation_type>", methods=["GET"])
def search_affiliations(affiliation_type: str) -> Response:
    return jsonify(search_service.search_affiliations(parse_query_params(), affiliation_type, request.url))


@search_router.route("/sources", methods=["GET"])
def search_sources() -> Response:
    return jsonify(search_service.search_sources(parse_query_params(), request.url))


@search_router.route("/patents", methods=["GET"])
def search_patents() -> Response:
    return jsonify(search_service.search_patents(parse_query_params(), request.url))


@search_router.route("/projects", methods=["GET"])
def search_projects() -> Response:
    return jsonify(search_service.search_projects(parse_query_params(), request.url))


@search_router.route("/geo/<geo_type>", methods=["GET"])
def search_geo(geo_type: str) -> Response:
    return jsonify(search_service.search_geo(parse_query_params(), geo_type, request.url))


@search_router.route("/works/filters", methods=["GET"])
def get_search_works_filters() -> Response:
    return jsonify(search_service.search_works_available_filters(parse_query_params()))


@search_router.route("/affiliations/<affiliation_type>/filters", methods=["GET"])
def get_search_affiliations_filters(affiliation_type: str) -> Response:
    return jsonify(search_service.search_affiliations_available_filters(affiliation_type, parse_query_params()))


@search_router.route("/sources/filters", methods=["GET"])
def get_search_sources_filters() -> Response:
    return jsonify(search_service.search_sources_available_filters(parse_query_params()))
