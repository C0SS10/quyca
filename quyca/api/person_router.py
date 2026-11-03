from flask import Blueprint, Response, jsonify, request

from quyca.api.helpers import CSV_CONTENT_TYPE, XLSX_CONTENT_TYPE, file_response, parse_query_params
from quyca.api.helpers import register_error_handlers
from quyca.services import news_service
from quyca.services import export_service
from quyca.services import patent_service
from quyca.services import person_plot_service, person_service
from quyca.services import project_service
from quyca.services import work_service

person_router = Blueprint("person_app_router", __name__)
register_error_handlers(person_router)


@person_router.route("/<person_id>", methods=["GET"])
def get_person_by_id(person_id: str) -> Response:
    return jsonify(person_service.get_person_by_id(person_id, parse_query_params()))


@person_router.route("/<person_id>/research/products", methods=["GET"])
def get_person_research_products(person_id: str) -> Response:
    query_params = parse_query_params()
    if query_params.plot:
        return jsonify(person_plot_service.get_person_plot(person_id, query_params))
    return jsonify(work_service.get_works_by_person(person_id, query_params, request.url))


@person_router.route("/<person_id>/research/products/filters", methods=["GET"])
def get_person_research_products_filters(person_id: str) -> Response:
    return jsonify(work_service.get_works_filters_by_person(person_id, parse_query_params()))


@person_router.route("/<person_id>/research/products/csv", methods=["GET"])
def get_works_csv_by_person(person_id: str) -> Response:
    works_csv = export_service.get_works_csv_by_person(person_id, parse_query_params())
    return file_response(works_csv, "person_works.csv", CSV_CONTENT_TYPE)


@person_router.route("/<person_id>/research/products/excel", methods=["GET"])
def get_works_excel_by_person(person_id: str) -> Response:
    works_excel = export_service.get_works_excel_by_person(person_id, parse_query_params())
    return file_response(works_excel.getvalue(), "person_works.xlsx", XLSX_CONTENT_TYPE)


@person_router.route("/<person_id>/research/patents", methods=["GET"])
def get_person_research_patents(person_id: str) -> Response:
    return jsonify(patent_service.get_patents_by_person(person_id, parse_query_params(), request.url))


@person_router.route("/<person_id>/research/projects", methods=["GET"])
def get_person_research_projects(person_id: str) -> Response:
    return jsonify(project_service.get_projects_by_person(person_id, parse_query_params(), request.url))


@person_router.route("/<person_id>/research/news", methods=["GET"])
def get_person_research_news(person_id: str) -> Response:
    return jsonify(news_service.get_news_by_person(person_id, parse_query_params(), request.url))
