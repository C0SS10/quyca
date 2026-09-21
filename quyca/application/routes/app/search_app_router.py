from typing import Tuple

from flask import Blueprint, request, jsonify, Response
from sentry_sdk import capture_exception

from quyca.domain.models.base_model import QueryParams
from quyca.domain.services.search import search_service

search_app_router = Blueprint("search_app_router", __name__)

"""
@api {get} /app/search/person Search persons
@apiName SearchPersons
@apiGroup Search
@apiVersion 1.0.0

@apiDescription Busca personas/autores por palabra clave y retorna información bibliográfica, identificadores externos, afiliaciones, métricas de citación y cantidad de productos asociados.

@apiSuccess {Object[]} data Lista de personas que coinciden con la búsqueda.
@apiSuccess {String} data.id Identificador único de la persona.
@apiSuccess {String} data.full_name Nombre completo de la persona.
@apiSuccess {Number} data.products_count Cantidad de productos asociados.
@apiSuccess {Number} data.h_index Índice H de la persona.
@apiSuccess {Number} data.h5_index Índice H5 de la persona.
@apiSuccess {Object[]} data.affiliations Lista de afiliaciones de la persona.
@apiSuccess {Object[]} data.citations_count Métricas de citación agrupadas por fuente.
@apiSuccess {Object[]} data.external_ids Identificadores externos asociados a la persona.
@apiSuccess {Number} total_results Cantidad total de resultados encontrados.

@apiError {Object} 400 Error en los parámetros de búsqueda o durante el procesamiento de la solicitud.
@apiError {String} 400.error Descripción del error.

@apiErrorExample {json} BadRequest:
{
  "error": "Invalid query parameters"
}
"""


@search_app_router.route("/person", methods=["GET"])
def search_persons() -> Response | Tuple[Response, int]:
    try:
        query_params = QueryParams(**request.args)
        data = search_service.search_persons(query_params)
        return jsonify(data)
    except Exception as e:
        capture_exception(e)
        return jsonify({"error": str(e)}), 400


"""
@api {get} /app/search/works Search works
@apiName SearchWorks
@apiGroup Search
@apiVersion 1.0.0

@apiDescription Busca productos bibliográficos por palabra clave y retorna información bibliográfica, autores, fuentes, identificadores externos, métricas de citación, acceso abierto, tipos de producto y clasificación temática.

@apiSuccess {Object[]} data Lista de productos bibliográficos que coinciden con los criterios de búsqueda.
@apiSuccess {String} data.id Identificador único del producto bibliográfico.
@apiSuccess {String} data.title Título del producto bibliográfico.
@apiSuccess {Number|null} data.year_published Año de publicación.
@apiSuccess {Number} data.authors_count Cantidad de autores asociados al producto.
@apiSuccess {Object[]} data.authors Lista de autores asociados al producto.
@apiSuccess {Object[]} data.citations_count Cantidad de citaciones agrupadas por fuente.
@apiSuccess {Object[]} data.external_ids Identificadores externos asociados al producto.
@apiSuccess {Object} data.open_access Información relacionada con el acceso abierto al producto.
@apiSuccess {Object[]} data.product_types Tipos de producto bibliográfico identificados por las diferentes fuentes.
@apiSuccess {Object} data.source Fuente bibliográfica principal asociada al producto.
@apiSuccess {Object[]} data.ranking Información de ranking asociada al producto.
@apiSuccess {Object[]} data.topics Temas o áreas de conocimiento asociados al producto bibliográfico.

@apiError {Object} 400 Error en los parámetros de búsqueda o durante el procesamiento de la solicitud.
@apiError {String} 400.error Descripción del error.
@apiErrorExample {json} BadRequest:
{
  "error": "Invalid query parameters"
}
"""


@search_app_router.route("/works", methods=["GET"])
def search_works() -> Response | Tuple[Response, int]:
    try:
        query_params = QueryParams(**request.args)
        data = search_service.search_works(query_params)
        return jsonify(data)
    except Exception as e:
        capture_exception(e)
        return jsonify({"error": str(e)}), 400


"""
@api {get} /app/search/works/filters Search works filters
@apiName SearchWorksFilters
@apiGroup Search
@apiVersion 1.0.0

@apiDescription Obtiene los filtros disponibles para la búsqueda de productos bibliográficos. Los filtros retornados dependen de los criterios de búsqueda y filtros aplicados en la solicitud.

@apiParam {String} [product_types] Filtra por tipos de producto bibliográfico.
@apiParam {String} [years] Filtra por años de publicación.
@apiParam {String} [status] Filtra por estado del producto bibliográfico.
@apiParam {String} [subjects] Filtra por áreas o materias asociadas al producto.
@apiParam {String} [topics] Filtra por temas asociados al producto.
@apiParam {String} [countries] Filtra por países asociados al producto.
@apiParam {String} [groups_ranking] Filtra por rankings relacionados con grupos de investigación.
@apiParam {String} [authors_ranking] Filtra por rankings relacionados con autores.

@apiSuccess {Object} product_types Tipos de productos bibliográficos disponibles como filtro.
@apiSuccess {Object[]} years Años de publicación disponibles como filtro.
@apiSuccess {Object} status Estados disponibles para filtrar los productos.
@apiSuccess {Object} topics Temas disponibles como filtro.
@apiSuccess {Object} countries Países disponibles como filtro.
@apiSuccess {Object} groups_ranking Rankings disponibles relacionados con grupos de investigación.
@apiSuccess {Object} authors_ranking Rankings disponibles relacionados con autores.

@apiError {Object} 400 Error en los parámetros de búsqueda o durante el procesamiento de la solicitud.
@apiError {String} 400.error Descripción del error.
@apiErrorExample {json} BadRequest:
{ 
    "error": "Invalid query parameters" 
}
"""


@search_app_router.route("/works/filters", methods=["GET"])
def get_search_works_filters() -> Response | Tuple[Response, int]:
    try:
        query_params = QueryParams(**request.args)
        data = search_service.search_works_available_filters(query_params)
        return jsonify(data)
    except Exception as e:
        capture_exception(e)
        return jsonify({"error": str(e)}), 400


"""
@api {get} /app/search/affiliations/:affiliation_type Search affiliations
@apiName SearchAffiliations
@apiGroup Search
@apiVersion 1.0.0

@apiDescription Busca afiliaciones por palabra clave y tipo de afiliación. El tipo determina la categoría de afiliación que se desea consultar. Los tipos de afiliación disponibles son: 
    - institution: Instituciones u organizaciones. 
    - department: Departamentos. 
    - faculty: Facultades.
    - group: Grupos de investigación.

@apiParam {String} affiliation_type Tipo de afiliación que se desea consultar. Valores permitidos: "institution", "department", "faculty", "group". 
@apiParam {String} [query] Palabra clave utilizada para buscar afiliaciones.

@apiSuccess {Object[]} data Lista de afiliaciones que coinciden con los criterios de búsqueda.
@apiSuccess {String} data.id Identificador único de la afiliación.
@apiSuccess {String} data.name Nombre de la afiliación.
@apiSuccess {String|null} data.logo URL del logo de la afiliación.
@apiSuccess {Number} data.products_count Cantidad de productos asociados a la afiliación.
@apiSuccess {Number} data.h_index Índice H asociado a la afiliación.
@apiSuccess {Number} data.h5_index Índice H5 asociado a la afiliación.
@apiSuccess {Object[]} data.affiliations Afiliaciones relacionadas con la entidad.
@apiSuccess {Object[]} data.citations_count Cantidad de citaciones agrupadas por fuente.
@apiSuccess {Object[]} data.external_ids Identificadores externos asociados a la afiliación.
@apiSuccess {Object[]} data.external_urls URLs externas asociadas a la afiliación.
@apiSuccess {Object[]} data.ranking Información de ranking asociada a la afiliación.
@apiSuccess {Object[]} data.types Tipos de afiliación identificados por las diferentes fuentes.
@apiSuccess {Number} total_results Cantidad total de resultados encontrados.
"""


@search_app_router.route("/affiliations/<affiliation_type>", methods=["GET"])
def search_affiliations(affiliation_type: str) -> Response | Tuple[Response, int]:
    try:
        query_params = QueryParams(**request.args)
        data = search_service.search_affiliations(affiliation_type, query_params)
        return jsonify(data)
    except Exception as e:
        capture_exception(e)
        return jsonify({"error": str(e)}), 400


"""
@api {get} /app/search/affiliations/:affiliation_type/filters Get affiliation filters
@apiName GetSearchAffiliationsFilters
@apiGroup Search
@apiVersion 1.0.0

@apiDescription Get available state and city filters for affiliations by affiliation type.
@apiParam {String} affiliation_type Affiliation type (e.g. "institution", "faculty", "group", "department").

@apiSuccess {Object[]} states List of available state filters.
@apiSuccess {Number} states.count Number of affiliations associated with the state.
@apiSuccess {String} states.label Normalized state name displayed to the user.
@apiSuccess {String} states.value State value used by the filter.
@apiSuccess {Object[]} cities List of available city filters.
@apiSuccess {Number} cities.count Number of affiliations associated with the city.
@apiSuccess {String} cities.label Normalized city name displayed to the user.
@apiSuccess {String} cities.value City value used by the filter.
"""


@search_app_router.route("/affiliations/<affiliation_type>/filters", methods=["GET"])
def get_search_affiliations_filters(affiliation_type: str) -> Response | Tuple[Response, int]:
    try:
        query_params = QueryParams(**request.args)
        data = search_service.search_affiliations_available_filters(affiliation_type, query_params)
        return jsonify(data), 200
    except Exception as e:
        capture_exception(e)
        return jsonify({"error": str(e)}), 400


"""
@api {get} /app/search/patents Search patents
@apiName SearchPatents
@apiGroup Search
@apiVersion 1.0.0

@apiDescription Busca patentes por palabra clave y retorna información básica de la patente, autores, tipos de producto e identificadores externos asociados. 

@apiSuccess {Object[]} data Lista de patentes que coinciden con los criterios de búsqueda.
@apiSuccess {String} data.id Identificador único de la patente.
@apiSuccess {String} data.title Título de la patente.
@apiSuccess {Number} data.authors_count Cantidad de autores asociados a la patente.
@apiSuccess {Object[]} data.authors Lista de autores asociados a la patente.
@apiSuccess {Object[]} data.external_ids Identificadores externos asociados a la patente.
@apiSuccess {Object[]} data.external_urls URLs externas asociadas a la patente.
@apiSuccess {Object[]} data.product_types Tipos de producto bibliográfico o tecnológico asociados a la patente.
@apiSuccess {Number} total_results Cantidad total de resultados encontrados.
"""


@search_app_router.route("/patents", methods=["GET"])
def search_patents() -> Response | Tuple[Response, int]:
    try:
        query_params = QueryParams(**request.args)
        data = search_service.search_patents(query_params)
        return jsonify(data)
    except Exception as e:
        capture_exception(e)
        return jsonify({"error": str(e)}), 400


"""
@api {get} /app/search/projects Search projects
@apiName SearchProjects
@apiGroup Search
@apiVersion 1.0.0

@apiDescription Busca proyectos por palabra clave y retorna información básica del proyecto, autores, tipos de producto, identificadores externos y periodo de ejecución.

@apiSuccess {Object[]} data Lista de proyectos que coinciden con los criterios de búsqueda.
@apiSuccess {String} data.id Identificador único del proyecto.
@apiSuccess {String} data.title Título del proyecto.
@apiSuccess {Number} data.authors_count Cantidad de autores asociados al proyecto.
@apiSuccess {Object[]} data.authors Lista de autores asociados al proyecto.
@apiSuccess {Object[]} data.external_ids Identificadores externos asociados al proyecto.
@apiSuccess {Object[]} data.external_urls URLs externas asociadas al proyecto.
@apiSuccess {Object[]} data.product_types Tipos de producto asociados al proyecto.
@apiSuccess {Number|null} data.year_init Año de inicio del proyecto.
@apiSuccess {Number|null} data.year_end Año de finalización del proyecto.
@apiSuccess {Number} total_results Cantidad total de resultados encontrados.
"""


@search_app_router.route("/projects", methods=["GET"])
def search_projects() -> Response | Tuple[Response, int]:
    try:
        query_params = QueryParams(**request.args)
        data = search_service.search_projects(query_params)
        return jsonify(data)
    except Exception as e:
        capture_exception(e)
        return jsonify({"error": str(e)}), 400


"""
@api {get} /app/search/sources Search sources
@apiName SearchSources
@apiGroup Search
@apiVersion 1.0.0

@apiDescription Busca fuentes bibliográficas por nombre y retorna información de identificación, publicación, métricas, acceso abierto, clasificación temática y rankings asociados a cada fuente.

@apiSuccess {Object[]} data Lista de fuentes que coinciden con los criterios de búsqueda.
@apiSuccess {String} data.id Identificador único de la fuente.
@apiSuccess {String} data.type Tipo de fuente.
@apiSuccess {Object[]} data.names Nombres de la fuente registrados en diferentes fuentes de información.
@apiSuccess {Object[]} data.abbreviations Abreviaturas asociadas a la fuente.
@apiSuccess {Object[]} data.addresses Direcciones asociadas a la fuente.
@apiSuccess {Object} data.publisher Información del editor o entidad responsable de la publicación.
@apiSuccess {Object[]} data.external_ids Identificadores externos asociados a la fuente.
@apiSuccess {Object[]} data.external_urls URLs externas asociadas a la fuente.
@apiSuccess {Number} data.products_count Cantidad de productos asociados a la fuente.
@apiSuccess {Number} data.global_products_count Cantidad global de productos asociados a la fuente.
@apiSuccess {Number} data.global_citations_count Cantidad global de citaciones asociadas a la fuente.
@apiSuccess {Object[]} data.citations_count Cantidad de citaciones agrupadas por fuente de información.
@apiSuccess {Object} data.apc Información relacionada con los cargos por procesamiento de artículos.
@apiSuccess {Object} data.copyright Información relacionada con los derechos de autor.
@apiSuccess {String|null} data.open_access_status Estado de acceso abierto de la fuente.
@apiSuccess {Number|null} data.open_access_start_year Año de inicio del acceso abierto.
@apiSuccess {Object[]} data.licenses Licencias asociadas a la fuente.
@apiSuccess {Object[]} data.keywords Palabras clave asociadas a la fuente.
@apiSuccess {Object[]} data.languages Idiomas asociados a la fuente.
@apiSuccess {Object[]} data.ranking Rankings asociados a la fuente.
@apiSuccess {String|null} data.scimago_best_quartile Mejor cuartil registrado en SCImago.
@apiSuccess {Object[]} data.subjects Materias o áreas temáticas asociadas a la fuente.
@apiSuccess {Object[]} data.topics Temas asociados a la fuente.
@apiSuccess {Object[]} data.relations Relaciones con otras fuentes.
@apiSuccess {Object|null} data.review_process Información sobre el proceso de revisión de la fuente.
@apiSuccess {Number|null} data.publication_time_weeks Tiempo estimado de publicación expresado en semanas.
@apiSuccess {Boolean} data.plagiarism_detection Indica si la fuente cuenta con detección de plagio.
@apiSuccess {Object} data.waiver Información relacionada con exenciones de cargos.
@apiSuccess {Object[]} data.updated Información sobre las últimas actualizaciones provenientes de las diferentes fuentes.
@apiSuccess {Number} total_results Cantidad total de resultados encontrados.
"""


@search_app_router.route("/sources", methods=["GET"])
def search_sources() -> Response | Tuple[Response, int]:
    try:
        query_params = QueryParams(**request.args)
        data = search_service.search_sources(query_params)
        return jsonify(data), 200
    except Exception as e:
        capture_exception(e)
        return jsonify({"error": str(e)}), 400


"""
@api {get} /app/search/sources/filters Search source filters
@apiName SearchWorksFilters
@apiGroup Search
@apiVersion 1.0.0

@apiDescription Obtiene los filtros disponibles para la búsqueda de fuentes bibliográficas, incluyendo tipos de fuente, cuartiles SCImago, rangos de APC, estado de acceso abierto, tiempo de publicación, tipos de licencia y temas.

@apiParam {String} [source_types] Tipos de fuente utilizados para filtrar los resultados.
@apiParam {String} [scimago_quartiles] Cuartiles SCImago utilizados para filtrar las fuentes.
@apiParam {String} [apc_range] Rango de cargos por procesamiento de artículos (APC).
@apiParam {String} [status] Estado de acceso abierto utilizado para filtrar las fuentes.
@apiParam {String} [publication_time] Tiempo de publicación utilizado como filtro.
@apiParam {String} [license_type] Tipo de licencia utilizado para filtrar las fuentes.
@apiParam {String} [topics] Temas utilizados para filtrar las fuentes.

@apiSuccess {Object} source_types Tipos de fuente disponibles para filtrar.
@apiSuccess {Object} scimago_quartiles Cuartiles SCImago disponibles.
@apiSuccess {Object} apc_range Rango de cargos por procesamiento de artículos disponible.
@apiSuccess {Object} status Estados de acceso abierto disponibles.
@apiSuccess {Object} publication_time Rangos de tiempo de publicación disponibles.
@apiSuccess {Object} license_type Tipos de licencia disponibles.
@apiSuccess {Object} topics Temas disponibles para filtrar.
"""


@search_app_router.route("/sources/filters", methods=["GET"])
def get_search_sources_filters() -> Response | Tuple[Response, int]:
    try:
        query_params = QueryParams(**request.args)
        data = search_service.search_sources_available_filters(query_params)
        return jsonify(data), 200
    except Exception as e:
        capture_exception(e)
        return jsonify({"error": str(e)}), 400


""" 
@api {get} /app/search/geo/<location_type> Search sources by location
@apiName SearchSourcesByLocation
@apiGroup Search
@apiVersion 1.0.0

@apiDescription Búsqueda de ubicación geográfica por tipo de ubicación (ej. "states", "cities").
"""


@search_app_router.route("/geo/<location_type>", methods=["GET"])
def search_geolocation(location_type: str) -> Response | Tuple[Response, int]:
    try:
        query_params = QueryParams(**request.args)
        data = search_service.search_geolocation(query_params, location_type)
        return jsonify(data), 200
    except Exception as e:
        capture_exception(e)
        return jsonify({"error": str(e)}), 400
