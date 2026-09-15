from typing import Any, Dict, Tuple

from flask import Blueprint, url_for, redirect, request, Response, jsonify
from werkzeug.wrappers.response import Response as WerkzeugResponse
from sentry_sdk import capture_exception

from quyca.domain.models.base_model import QueryParams
from quyca.domain.services import api_expert_service

search_api_router = Blueprint("search_api_router", __name__)


"""
@api {get} /person Buscar personas
@apiName SearchPersons
@apiGroup Search
@apiDescription Redirige la búsqueda de personas al router principal.

@apiParam (Query Params) {String} [keywords] Palabras clave de búsqueda (nombre o parte del nombre de la persona).
@apiParam (Query Params) {String} [countries] País de afiliación o nacionalidad.
@apiParam (Query Params) {String} [subjects] Área de conocimiento o disciplina.
@apiParam (Query Params) {Number{1..250}} [limit] Límite de resultados por página.
@apiParam (Query Params) {Number} [page] Página de resultados a obtener.

@apiSuccess (Redirect) 302 Redirección hacia `/router/search_app_router/search_persons` con los mismos parámetros.
"""


@search_api_router.route("/person", methods=["GET"])
def search_persons() -> WerkzeugResponse:
    query_params: Dict[str, Any] = request.args.to_dict()
    return redirect(url_for("router.search_app_router.search_persons", **query_params))


"""
@api {get} /works Buscar productos
@apiName SearchWorks
@apiGroup Search
@apiDescription Busca productos en el sistema según los filtros y parámetros definidos.

@apiParam (Query Params) {Number{1..250}} [limit] Límite máximo de resultados (alias: `max`).
@apiParam (Query Params) {Number} [page] Número de página a consultar.
@apiParam (Query Params) {String} [keywords] Palabras clave para filtrar productos.
@apiParam (Query Params) {String} [sort] Criterio de ordenamiento (por ejemplo: `year:desc`).
@apiParam (Query Params) {String} [product_types] Tipos de producto asociados al producto.
@apiParam (Query Params) {String} [years] Años de publicación (rango o lista separada por comas).
@apiParam (Query Params) {String} [topics] Tópicos de investigación o categorías.
@apiParam (Query Params) {String} [countries] Países asociados al trabajo o sus autores.
@apiParam (Query Params) {String} [authors_ranking] Ranking de autores.

@apiSuccessExample {json} Success-Response:
    HTTP/1.1 200 OK
    {
      "data": [
        {
          "authors": [
            {
              "full_name": "C E Gonzalez",
              "affiliations": [
                {
                  "id": "03bp5hc83",
                  "name": "Universidad de Antioquia",
                  "addresses": [
                    { "city": "Medellín", "country": "Colombia", "country_code": "CO" }
                  ]
                }
              ]
            }
          ],
          "doi": "https://doi.org/10.3133/ofr7397",
          "id": "68ade9918c9a28c93c2696ac",
          "source": {
            "name": "Antarctica A Keystone in a Changing World",
            "external_ids": [
              { "id": "0196-1497", "source": "issn" },
              { "id": "https://openalex.org/S4210194219", "source": "openalex" }
            ]
          },
          "titles": [
            {
              "lang": "en",
              "source": "openalex",
              "title": "Api expert work example"
            }
          ],
          "year_published": 2025
        }
      ]
    }

@apiError (400) {String} error Mensaje de error en caso de fallo o parámetros inválidos.
"""


@search_api_router.route("/works", methods=["GET"])
def search_works() -> Response | Tuple[Response, int]:
    try:
        query_params = QueryParams(**request.args)
        data = api_expert_service.search_works(query_params, request.url)
        return jsonify(data)
    except Exception as e:
        capture_exception(e)
        return jsonify({"error": str(e)}), 400


"""
@api {get} /affiliations/:affiliation_type Buscar afiliaciones
@apiName SearchAffiliations
@apiGroup Search
@apiDescription Redirige la búsqueda de afiliaciones según el tipo especificado.

@apiParam (Path) {String} affiliation_type Tipo de afiliación (por ejemplo: `institution`, `faculty`, `department`).
@apiParam (Query Params) {String} [keywords] Palabras clave de búsqueda.
@apiParam (Query Params) {String} [countries] País o región de la afiliación.
@apiParam (Query Params) {String} [sort] Criterio de ordenamiento (por ejemplo: `name:asc`).
@apiParam (Query Params) {Number{1..250}} [limit] Límite de resultados por página.
@apiParam (Query Params) {Number} [page] Página actual de la búsqueda.

@apiSuccess (Redirect) 302 Redirección hacia `/app/search/affiliation/:affiliation_type`.
"""


@search_api_router.route("/affiliations/<affiliation_type>", methods=["GET"])
def search_affiliations(affiliation_type: str) -> WerkzeugResponse:
    query_params: Dict[str, Any] = request.args.to_dict()
    return redirect(
        url_for(
            "router.search_app_router.search_affiliations",
            affiliation_type=affiliation_type,
            **query_params,
        )
    )


"""
@api {get} /sources Buscar fuentes
@apiName SearchSources
@apiGroup Search
@apiDescription Redirige la búsqueda de fuentes (journals, libros, conferencias, etc.) al router principal.

@apiParam (Query Params) {String} [source_types] Tipo de fuente (por ejemplo: `journal`, `book`, `conference`).
@apiParam (Query Params) {String} [keywords] Palabras clave de búsqueda.
@apiParam (Query Params) {String} [countries] País o región.
@apiParam (Query Params) {Number{1..250}} [limit] Límite máximo de resultados por página.
@apiParam (Query Params) {Number} [page] Página de resultados.

@apiSuccess (Redirect) 302 Redirección hacia `/app/search/source`.
"""


@search_api_router.route("/sources", methods=["GET"])
def search_sources() -> WerkzeugResponse:
    query_params: Dict[str, Any] = request.args.to_dict()
    return redirect(url_for("router.search_app_router.search_sources", **query_params))


""" 
@api {get} /patents Buscar patentes
@apiName SearchPatents
@apiGroup Search
@apiDescription Busca patentes en el sistema según los filtros y parámetros definidos.

@apiParam (Query Params) {Number{1..250}} [limit] Límite máximo de resultados (alias: `max`).
@apiParam (Query Params) {Number} [page] Número de página a consultar.
@apiParam (Query Params) {String} [keywords] Palabras clave para filtrar patentes.
@apiParam (Query Params) {String} [sort] Criterio de ordenamiento (por ejemplo: `year:desc`).

@apiSuccessExample {json} Success-Response:
  HTTP/1.1 200 OK
"""


@search_api_router.route("/patents", methods=["GET"])
def search_patents() -> WerkzeugResponse | Tuple[Response, int]:
    try:
        query_params = QueryParams(**request.args)
        data = api_expert_service.search_patents(query_params, request.url)
        return jsonify(data)
    except Exception as e:
        capture_exception(e)
        return jsonify({"error": str(e)}), 400


""" 
@api {get} /projects Buscar proyectos
@apiName SearchProjects
@apiGroup Search
@apiDescription Busca proyectos en el sistema según los filtros y parámetros definidos.

@apiParam (Query Params) {Number{1..250}} [limit] Límite máximo de resultados (alias: `max`).
@apiParam (Query Params) {Number} [page] Número de página a consultar.
@apiParam (Query Params) {String} [keywords] Palabras clave para filtrar proyectos.
@apiParam (Query Params) {String} [sort] Criterio de ordenamiento (por ejemplo: `year:desc`).

@apiSuccessExample {json} Success-Response:
  HTTP/1.1 200 OK
"""


@search_api_router.route("/projects", methods=["GET"])
def search_projects() -> WerkzeugResponse | Tuple[Response, int]:
    try:
        query_params = QueryParams(**request.args)
        data = api_expert_service.search_projects(query_params, request.url)
        return jsonify(data)
    except Exception as e:
        capture_exception(e)
        return jsonify({"error": str(e)}), 400
