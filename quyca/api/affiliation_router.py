import json

from flask import Blueprint, Response, jsonify, request

from quyca.api.helpers import CSV_CONTENT_TYPE, XLSX_CONTENT_TYPE, file_response, parse_query_params
from quyca.api.helpers import register_error_handlers
from quyca.services import news_service
from quyca.services import affiliation_plot_service, affiliation_service
from quyca.services import export_affiliation_plot_service, export_service
from quyca.services import patent_service
from quyca.services import project_service
from quyca.services import work_service

affiliation_router = Blueprint("affiliation_app_router", __name__)
register_error_handlers(affiliation_router)


@affiliation_router.route("/<affiliation_type>/<affiliation_id>", methods=["GET"])
def get_affiliation_by_id(affiliation_type: str, affiliation_id: str) -> Response:
    return jsonify(affiliation_service.get_affiliation_by_id(affiliation_id, affiliation_type, parse_query_params()))


@affiliation_router.route("/<affiliation_type>/<affiliation_id>/affiliations", methods=["GET"])
def get_affiliation_affiliations(affiliation_type: str, affiliation_id: str) -> Response:
    data = affiliation_service.get_related_affiliations_by_affiliation(affiliation_id, affiliation_type)
    return Response(json.dumps(data), mimetype="application/json")


@affiliation_router.route("/<affiliation_type>/<affiliation_id>/research/products", methods=["GET"])
def get_affiliation_research_products(affiliation_type: str, affiliation_id: str) -> Response:
    query_params = parse_query_params()
    if query_params.plot:
        return jsonify(affiliation_plot_service.get_affiliation_plot(affiliation_id, affiliation_type, query_params))
    return jsonify(work_service.get_works_by_affiliation(affiliation_id, query_params, request.url))


@affiliation_router.route("/<affiliation_type>/<affiliation_id>/research/products/filters", methods=["GET"])
def get_affiliation_research_products_filters(affiliation_type: str, affiliation_id: str) -> Response:
    return jsonify(work_service.get_works_filters_by_affiliation(affiliation_id, parse_query_params()))


@affiliation_router.route("/<affiliation_type>/<affiliation_id>/research/products/csv", methods=["GET"])
def get_works_csv_by_affiliation(affiliation_type: str, affiliation_id: str) -> Response:
    query_params = parse_query_params()
    if query_params.plot:
        plot_csv = export_affiliation_plot_service.get_plot_csv(affiliation_id, affiliation_type, query_params)
        return file_response(plot_csv, f"{query_params.plot}.csv", CSV_CONTENT_TYPE)
    works_csv = export_service.get_works_csv_by_affiliation(affiliation_id, query_params)
    return file_response(works_csv, "affiliations.csv", CSV_CONTENT_TYPE)


@affiliation_router.route("/<affiliation_type>/<affiliation_id>/research/products/excel", methods=["GET"])
def get_works_excel_by_affiliation(affiliation_type: str, affiliation_id: str) -> Response:
    works_excel = export_service.get_works_excel_by_affiliation(affiliation_id, parse_query_params())
    return file_response(works_excel.getvalue(), "affiliations.xlsx", XLSX_CONTENT_TYPE)


@affiliation_router.route("/<affiliation_type>/<affiliation_id>/research/patents", methods=["GET"])
def get_affiliation_research_patents(affiliation_type: str, affiliation_id: str) -> Response:
    query_params = parse_query_params()
    return jsonify(
        patent_service.get_patents_by_affiliation(affiliation_id, affiliation_type, query_params, request.url)
    )


@affiliation_router.route("/<affiliation_type>/<affiliation_id>/research/projects", methods=["GET"])
def get_affiliation_research_projects(affiliation_type: str, affiliation_id: str) -> Response:
    query_params = parse_query_params()
    return jsonify(
        project_service.get_projects_by_affiliation(affiliation_id, affiliation_type, query_params, request.url)
    )


@affiliation_router.route("/<affiliation_type>/<affiliation_id>/research/news", methods=["GET"])
def get_affiliation_research_news(affiliation_type: str, affiliation_id: str) -> Response:
    return jsonify(news_service.get_news_by_affiliation(affiliation_id, parse_query_params(), request.url))
