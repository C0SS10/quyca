from typing import Tuple

from flask import Blueprint, request, Response, jsonify, stream_with_context
from sentry_sdk import capture_exception

from quyca.domain.models.base_model import QueryParams
from quyca.domain.services import (
    work_service,
    person_service,
    project_service,
    person_plot_service,
    patent_service,
    news_service,
)
from quyca.domain.services.export import export_service

person_app_router = Blueprint("person_app_router", __name__)

"""
@api {get} /app/person/:person_id Get person by id
@apiName GetPersonById
@apiGroup Person
@apiVersion 1.0.0
@apiDescription Obtiene un autor por su ID.

@apiParam {String} person_id ID del autor.
"""


@person_app_router.route("/<person_id>", methods=["GET"])
def get_person_by_id(person_id: str, pipeline_params: dict = {}) -> Response | Tuple[Response, int]:
    try:
        data = person_service.get_person_by_id(person_id, pipeline_params)
        return jsonify(data)
    except Exception as e:
        capture_exception(e)
        return jsonify({"error": str(e)}), 400


"""
@api {get} /app/person/:person_id/research/products Get person research products
@apiName GetPersonResearchProducts
@apiGroup Person
@apiVersion 1.0.0
@apiDescription Obtiene los productos bibliográficos de un autor.

@apiParam {String} person_id ID del autor.
"""


@person_app_router.route("/<person_id>/research/products", methods=["GET"])
def get_person_research_products(person_id: str) -> Response | Tuple[Response, int]:
    try:
        query_params = QueryParams(**request.args)
        if query_params.plot:
            data = person_plot_service.get_person_plot(person_id, query_params)
            return jsonify(data)
        data = work_service.get_works_by_person(person_id, query_params)
        return jsonify(data)
    except Exception as e:
        capture_exception(e)
        return jsonify({"error": str(e)}), 400


"""
@api {get} /app/person/:person_id/research/products/filters Get person research products filters
@apiName GetPersonResearchProductsFilters
@apiGroup Person
@apiVersion 1.0.0
@apiDescription Obtiene los filtros disponibles en los productos bibliográficos de un autor.

@apiParam {String} person_id ID del autor.
"""


@person_app_router.route("/<person_id>/research/products/filters", methods=["GET"])
def get_person_research_products_filters(person_id: str) -> Response | Tuple[Response, int]:
    try:
        query_params = QueryParams(**request.args)
        data = work_service.get_works_filters_by_person(person_id, query_params)
        return jsonify(data)
    except Exception as e:
        capture_exception(e)
        return jsonify({"error": str(e)}), 400


"""
@api {get} /app/person/:person_id/research/products/csv Get person research products csv
@apiName GetPersonResearchProductsCsv
@apiGroup Person
@apiVersion 1.0.0
@apiDescription Obtiene los productos bibliográficos de un autor en formato CSV.

@apiParam {String} person_id ID del autor.
"""


@person_app_router.route("/<person_id>/research/products/csv", methods=["GET"])
def get_works_csv_by_person(person_id: str) -> Response | Tuple[Response, int]:
    try:
        query_params = QueryParams(**request.args)
        data = export_service.get_works_csv_by_person(person_id, query_params)
        response = Response(stream_with_context(data), content_type="text/csv")
        response.headers["Content-Disposition"] = "attachment; filename=person_works.csv"
        return response
    except Exception as e:
        capture_exception(e)
        return jsonify({"error": str(e)}), 400


"""
@api {get} /app/person/:person_id/research/products/excel Get person research products excel
@apiName GetPersonResearchProductsExcel
@apiGroup Person
@apiVersion 1.0.0
@apiDescription Obtiene los productos bibliográficos de un autor en formato EXCEL.

@apiParam {String} person_id ID del autor.
"""


@person_app_router.route("/<person_id>/research/products/excel", methods=["GET"])
def get_works_excel_by_person(person_id: str) -> Response | Tuple[Response, int]:
    try:
        query_params = QueryParams(**request.args)
        data = export_service.get_works_excel_by_person(person_id, query_params)
        response = Response(
            data.getvalue(),
            content_type=("application/vnd.openxmlformats-officedocument." "spreadsheetml.sheet"),
        )
        response.headers["Content-Disposition"] = "attachment; filename=person_works.xlsx"
        return response
    except Exception as e:
        capture_exception(e)
        return jsonify({"error": str(e)}), 400


"""
@api {get} /app/person/:person_id/research/patents Get person research patents
@apiName GetPersonResearchPatents
@apiGroup Person
@apiVersion 1.0.0
@apiDescription Obtiene las patentes de un autor.

@apiParam {String} person_id ID del autor.
"""


@person_app_router.route("/<person_id>/research/patents", methods=["GET"])
def get_person_research_patents(person_id: str) -> Response | Tuple[Response, int]:
    try:
        query_params = QueryParams(**request.args)
        data = patent_service.get_patents_by_person(person_id, query_params)
        return jsonify(data)
    except Exception as e:
        capture_exception(e)
        return jsonify({"error": str(e)}), 400


"""
@api {get} /app/person/:person_id/research/projects Get person research projects
@apiName GetPersonResearchProjects
@apiGroup Person
@apiVersion 1.0.0
@apiDescription Obtiene los proyectos de un autor.

@apiParam {String} person_id ID del autor.
"""


@person_app_router.route("/<person_id>/research/projects", methods=["GET"])
def get_person_research_projects(person_id: str) -> Response | Tuple[Response, int]:
    try:
        query_params = QueryParams(**request.args)
        data = project_service.get_projects_by_person(person_id, query_params)
        return jsonify(data)
    except Exception as e:
        capture_exception(e)
        return jsonify({"error": str(e)}), 400


"""
@api {get} /app/person/:person_id/research/news Get person research news
@apiName GetPersonResearchNews
@apiGroup Person
@apiVersion 1.0.0
@apiDescription Obtiene las noticias relacionadas con un autor.
@apiParam {String} person_id ID del autor.
"""


@person_app_router.route("/<person_id>/research/news")
def news_for_person_app(person_id: str) -> Response:
    """
    Flask route to retrieve news for a given person ID.

    Validates and parses query parameters, invokes the service layer to get the
    related news data, and returns a JSON response.

    Route:
    ------
    GET /<person_id>/research/news

    Parameters:
    -----------
    person_id : str
        The ID of the person whose news entries are to be retrieved.

    Returns:
    --------
    Response
        Flask JSON response containing news data and total result count.
    """
    qp = QueryParams.model_validate(
        request.args.to_dict(),
        context={"default_max": 25},
    )
    return jsonify(news_service.get_news_by_person(person_id, qp))
