from flask import Blueprint, Response, jsonify, request

from quyca.api.helpers import CSV_CONTENT_TYPE, XLSX_CONTENT_TYPE, file_response, parse_query_params
from quyca.api.helpers import register_error_handlers
from quyca.services import work_service
from quyca.services import export_service
from quyca.services import source_plot_service, source_service

source_router = Blueprint("source_app_router", __name__)
register_error_handlers(source_router)


@source_router.route("/<source_id>", methods=["GET"])
def get_source_by_id(source_id: str) -> Response:
    return jsonify(source_service.get_source_by_id(source_id, parse_query_params()))


@source_router.route("/<source_id>/products", methods=["GET"])
def get_source_products(source_id: str) -> Response:
    query_params = parse_query_params()
    if query_params.plot:
        return jsonify(source_plot_service.get_source_products_plot(source_id, query_params))
    return jsonify(work_service.get_works_by_source(source_id, query_params, request.url))


@source_router.route("/<source_id>/products/filters", methods=["GET"])
def get_source_products_filters(source_id: str) -> Response:
    return jsonify(work_service.get_works_filters_by_source(source_id, parse_query_params()))


@source_router.route("/<source_id>/products/csv", methods=["GET"])
def get_works_csv_by_source(source_id: str) -> Response:
    works_csv = export_service.get_works_csv_by_source(source_id, parse_query_params())
    return file_response(works_csv, "source_works.csv", CSV_CONTENT_TYPE)


@source_router.route("/<source_id>/products/excel", methods=["GET"])
def get_works_excel_by_source(source_id: str) -> Response:
    works_excel = export_service.get_works_excel_by_source(source_id, parse_query_params())
    return file_response(works_excel.getvalue(), "source_works.xlsx", XLSX_CONTENT_TYPE)
