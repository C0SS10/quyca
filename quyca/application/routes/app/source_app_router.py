from typing import Tuple
from flask import Blueprint, Response, jsonify, request
from sentry_sdk import capture_exception

from quyca.domain.models.base_model import QueryParams
from quyca.domain.services import source_plot_service, source_service, work_service
from quyca.domain.services.export import export_service


source_app_router = Blueprint("source_app_router", __name__)

"""
@api {get} /source/:source_id Get Source by ID
@apiName GetSourceById
@apiGroup Source
@apiVersion 1.0.0
@apiDescription Obtiene los detalles de una fuente específica utilizando su identificador único.

@apiParam {String} source_id Identificador único de la fuente.

@apiSuccessExample {json} Respuesta exitosa:
HTTP/1.1 200 OK
{
  "data": {
    "abbreviations": [],
    "addresses": [],
    "apc": {},
    "citations_count": [
      {
        "count": 69,
        "source": "openalex"
      }
    ],
    "copyright": {},
    "external_ids": [
      {
        "id": "0196-1497",
        "source": "issn"
      },
      {
        "id": "2331-1258",
        "source": "issn"
      }
    ],
    "id": "6850c7bac2459d408de7fca0",
    "keywords": [],
    "languages": [],
    "licenses": [],
    "names": [
      {
        "lang": "en",
        "name": "US Geological Survey Open-File Report",
        "source": "scimago"
      }
    ],
    "plagiarism_detection": false,
    "products_count": 6,
    "publisher": {
      "country_code": "US",
      "name": "US Geological Survey"
    },
    "ranking": [
      {
        "from_date": 1735707600,
        "order": 19654,
        "rank": "Q3",
        "source": "scimago Best Quartile",
        "to_date": 1767157200
      }
    ],
    "relations": [],
    "subjects": [
      {
        "source": "scimago",
        "subjects": [
          {
            "external_ids": [],
            "id": "",
            "name": "Geology"
          }
        ]
      }
    ],
    "types": [
      {
        "source": "scimago",
        "type": "journal"
      }
    ],
    "updated": [
      {
        "source": "scimago",
        "time": 1750124474
      }
    ],
    "waiver": {}
  }
}

@apiError (404) SourceNotFound The source with the specified ID was not found.

@apiErrorExample {json} Respuesta de error:
HTTP/1.1 404 Not Found
{
  "error": "Source not found"
}
"""


@source_app_router.route("/<source_id>", methods=["GET"])
def get_source_by_id(source_id: str) -> Response | Tuple[Response, int]:
    try:
        data = source_service.get_source_by_id(source_id)
        return jsonify(data)
    except Exception as e:
        capture_exception(e)
        return jsonify({"error": str(e)}), 404


"""
@api {get} /app/source/:source_id/products Get works by source
@apiName GetSourceProducts
@apiGroup Source
@apiVersion 1.0.0
@apiDescription Obtiene los productos bibliográficos de una fuente.

@apiParam {String} source_id ID de la fuente.

@apiQuery {Number} [page=1] Número de la página.
@apiQuery {Number} [max=10] Número máximo de resultados.
@apiQuery {String} [sort] Campo a ordenar (citations, products, alphabetical). dirección del ordenamiento (asc/desc).

@apiSuccessExample {json} Respues exitosa:
HTTP/1.1 200 OK
{
  "data": [
    {
      "authors": [
        {
          "affiliations": [
            {
              "id": "0108mwc04",
              "name": "Universidad del Rosario",
              "types": [
                {
                  "source": "ror",
                  "type": "Education"
                },
                {
                  "source": "openalex",
                  "type": "funder"
                }
              ]
            }
          ],
          "full_name": "Freddy Eduardo Cante Maldonado",
          "id": "0000143421"
        }
      ],
      "authors_count": 1,
      "citations_count": [
        {
          "count": 1344,
          "source": "openalex"
        }
      ],
      "external_ids": [
        {
          "id": "https://openalex.org/W1742378130",
          "provenance": "openalex",
          "source": "openalex"
        },
        {
          "id": "https://repositorio.unal.edu.co/handle/unal/23716",
          "provenance": "dspace",
          "source": "uri"
        }
      ],
      "id": "68ae71ffdda5d8cc7eb14949",
      "open_access": {
        "has_repository_fulltext": false,
        "is_open_access": false,
        "open_access_status": "closed"
      },
      "product_types": [
        {
          "name": "article",
          "source": "openalex"
        },
        {
          "name": "journal-article",
          "source": "crossref"
        },
        {
          "name": "Artículo de revista",
          "source": "impactu"
        }
      ],
      "ranking": [],
      "source": {
        "apc": {},
        "external_ids": [
          {
            "id": "https://openalex.org/S4306401280",
            "source": "openalex"
          }
        ],
        "external_urls": [
          {
            "source": "site",
            "url": "https://doaj.org"
          }
        ],
        "id": "6850c94ec2459d408de875af",
        "name": "DOAJ (DOAJ: Directory of Open Access Journals)",
        "names": [
          {
            "lang": "en",
            "name": "DOAJ (DOAJ: Directory of Open Access Journals)",
            "source": "openalex"
          }
        ],
        "publisher": {
          "country_code": "GB",
          "name": "DOAJ: Directory of Open Access Journals"
        },
        "ranking": [],
        "types": [
          {
            "source": "openalex",
            "type": "repository"
          }
        ],
        "updated": [
          {
            "source": "openalex",
            "time": 1750124878
          }
        ]
      },
      "subjects": [
        {
          "source": "openalex",
          "subjects": [
            {
              "id": "6850ca3fc2459d408debff8b",
              "level": 2,
              "name": "Strategic interaction"
            },
            {
              "id": "6850ca17c2459d408deb6653",
              "level": 2,
              "name": "Game theory"
            },
            {
              "id": "6850ca15c2459d408deb5acf",
              "level": 0,
              "name": "Computer science"
            }
          ]
        }
      ],
      "title": "Behavioral game theory, experiments in strategic interaction",
      "topics": [
        {
          "display_name": "Business, Education, Mathematics Research",
          "domain": {
            "display_name": "Social Sciences",
            "id": "https://openalex.org/domains/2"
          },
          "field": {
            "display_name": "Business, Management and Accounting",
            "id": "https://openalex.org/fields/14"
          },
          "id": "https://openalex.org/T14239",
          "score": 0.3811,
          "subfield": {
            "display_name": "Accounting",
            "id": "https://openalex.org/subfields/1402"
          }
        }
      ],
      "year_published": 2004
    }
  ],
  "total_results": 29243
}
"""


@source_app_router.route("/<source_id>/products", methods=["GET"])
def get_source_products(source_id: str) -> Response | Tuple[Response, int]:
    try:
        query_params = QueryParams(**request.args)
        if query_params.plot:
            data = source_plot_service.get_source_products_plot(source_id, query_params)
            return jsonify(data)
        data = work_service.get_works_by_source(source_id, query_params)
        return jsonify(data)
    except Exception as e:
        capture_exception(e)
        return jsonify({"error": str(e)}), 400


"""
@api {get} /app/source/:source_id/products/filters Get works filters by source
@apiName GetSourceProductsFilters
@apiGroup Source
@apiVersion 1.0.0
@apiDescription Obtiene los filtros disponibles en los productos bibliográficos de una fuente.

@apiParam {String} source_id ID de la fuente.

@apiQuery {Number} [page=1] Número de la página.
@apiQuery {Number} [max=10] Número máximo de resultados.
@apiQuery {String} [sort] Campo a ordenar (citations, products, alphabetical). dirección del ordenamiento (asc/desc).

@apiSuccessExample {json} Respues exitosa:
HTTP/1.1 200 OK
{
  "authors_ranking": [
    {
      "label": "Investigador Asociado",
      "value": "Investigador Asociado"
    },
    {
      "label": "Investigador Emérito",
      "value": "Investigador Emérito"
    },
    {
      "label": "Investigador Junior",
      "value": "Investigador Junior"
    },
    {
      "label": "Investigador Sénior",
      "value": "Investigador Sénior"
    }
  ],
  "countries": [
    {
      "count": 26509,
      "label": "Colombia",
      "value": "CO"
    }
  ],
  "groups_ranking": [
    {
      "label": "A",
      "value": "A"
    },
    {
      "label": "A1",
      "value": "A1"
    },
    {
      "label": "B",
      "value": "B"
    },
    {
      "label": "C",
      "value": "C"
    },
    {
      "label": "D",
      "value": "D"
    },
    {
      "label": "Reconocido",
      "value": "Reconocido"
    }
  ],
  "product_types": [
    {
      "children": [
        {
          "count": 29070,
          "title": "article",
          "value": "openalex_article"
        },
        {
          "count": 84,
          "title": "editorial",
          "value": "openalex_editorial"
        }
      ]
    }
  ],
  "topics": [
    {
      "count": 948,
      "label": "History and Politics in Latin America",
      "value": "https://openalex.org/T12563"
    },
    {
      "count": 587,
      "label": "Comparative constitutional jurisprudence studies",
      "value": "https://openalex.org/T12332"
    }
  ],
  "years": {
    "max_year": 2023,
    "min_year": 1068
  }
}
"""


@source_app_router.route("/<source_id>/products/filters", methods=["GET"])
def get_source_products_filters(source_id: str) -> Response | Tuple[Response, int]:
    try:
        query_params = QueryParams(**request.args)
        data = work_service.get_works_filters_by_source(source_id, query_params)
        return jsonify(data)
    except Exception as e:
        capture_exception(e)
        return jsonify({"error": str(e)}), 400


"""
@api {get} /app/source/:source_id/products/csv Get works csv by Source
@apiName GetSourceProductsCSV
@apiGroup Source
@apiVersion 1.0.0
@apiDescription Obtiene los productos bibliográficos de una fuente en formato CSV.

@apiParam {String} source_id ID de la afiliación.

@apiSuccessExample {csv} Success-Response:
HTTP/1.1 200 OK
Content-Type: text/csv
Content-Disposition: attachment; filename=source.csv
"""


@source_app_router.route("/<source_id>/products/csv", methods=["GET"])
def get_works_csv_by_source(source_id: str) -> Response | Tuple[Response, int]:
    try:
        query_params = QueryParams(**request.args)
        data = export_service.get_works_csv_by_source(source_id, query_params)
        response = Response(data, content_type="text/csv")
        response.headers["Content-Disposition"] = "attachment; filename=source_works.csv"
        return response
    except Exception as e:
        capture_exception(e)
        return jsonify({"error": str(e)}), 400


"""
@api {get} /app/source/:source_id/products/excel Get works excel by Source
@apiName GetSourceProductsExcel
@apiGroup Source
@apiVersion 1.0.0
@apiDescription Obtiene los productos bibliográficos de una fuente en formato Excel.

@apiParam {String} source_id ID de la fuente.

@apiSuccessExample {excel} Success-Response:
HTTP/1.1 200 OK
Content-Type: application/vnd.openxmlformats-officedocument.spreadsheetml.sheet
Content-Disposition: attachment; filename=source_works.xlsx
"""


@source_app_router.route("/<source_id>/products/excel", methods=["GET"])
def get_works_excel_by_source(source_id: str) -> Response | Tuple[Response, int]:
    try:
        query_params = QueryParams(**request.args)
        data = export_service.get_works_excel_by_source(source_id, query_params)
        response = Response(
            data.getvalue(),
            content_type=("application/vnd.openxmlformats-officedocument." "spreadsheetml.sheet"),
        )
        response.headers["Content-Disposition"] = "attachment; filename=source_works.xlsx"
        return response
    except Exception as e:
        capture_exception(e)
        return jsonify({"error": str(e)}), 400
