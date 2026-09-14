from typing import Tuple

from flask import Blueprint, jsonify, request, Response
from sentry_sdk import capture_exception

from quyca.domain.models.base_model import QueryParams
from quyca.domain.services import api_expert_service

affiliation_api_router = Blueprint("affiliation_api_router", __name__)


"""
@api {get} /affiliation/:affiliation_type/:affiliation_id/research/products Get works by affiliation
@apiName GetWorksByAffiliation
@apiGroup API Expert
@apiVersion 1.0.0
@apiDescription Obtiene los productos bibliográficos asociados a una afiliación específica.

@apiParam {String} affiliation_type Tipo de afiliación (ej. "institution", "department").
@apiParam {String} affiliation_id ID de la afiliación.

@apiSuccessExample {json} Respuesta exitosa:
    HTTP/1.1 200 OK
    {
    "data": [
    {
      "apc": {
        "paid": {
          "currency": "EUR",
          "provenance": "openalex",
          "source": "doaj",
          "value": 3690,
          "value_usd": 4790
        }
      },
      "authors": [
        {
          "affiliations": [
            {
              "end_date": -1,
              "geo": {
                "city": "Darlinghurst",
                "country": "Australia",
                "country_code": "AU",
                "latitude": -33.878359,
                "longitude": 151.221653,
                "region": "New South Wales"
              },
              "id": "66f6f3ac99b6ea475f3a499e",
              "name": "Garvan Institute of Medical Research",
              "ror": "https://ror.org/01b3dvp57",
              "start_date": -1,
              "types": [
                {
                  "source": "ror",
                  "type": "Nonprofit"
                },
                {
                  "source": "openalex",
                  "type": "nonprofit"
                }
              ]
            },
            {
              "end_date": -1,
              "geo": {},
              "id": "66f6f3df99b6ea475f3bcc04",
              "name": "Universidad de Nueva Gales del Sur",
              "start_date": -1,
              "types": [
                {
                  "source": "ror",
                  "type": "Education"
                },
                {
                  "source": "openalex",
                  "type": "education"
                }
              ]
            }
          ],
          "countries": [
            "Australia"
          ],
          "external_ids": [
            {
              "id": "https://openalex.org/A5077913296",
              "provenance": "openalex",
              "source": "openalex"
            },
            {
              "id": "https://orcid.org/0000-0002-5360-5180",
              "provenance": "openalex",
              "source": "orcid"
            }
          ],
          "first_names": [],
          "full_name": "Stuart G. Tangye",
          "id": "66f7c83a2046a15c590070a1",
          "last_names": [],
          "ranking": [],
          "sex": ""
        }
      ],
      "authors_count": 17,
      "bibliographic_info": {
        "end_page": "64",
        "issue": "1",
        "start_page": "24",
        "volume": "40"
      },
      "citations": [],
      "citations_by_year": [
        {
          "cited_by_count": 47,
          "year": 2024
        },
      ],
      "citations_count": [
        {
          "count": 958,
          "source": "openalex"
        },
        {
          "count": 1154,
          "provenance": "scholar",
          "source": "scholar"
        }
      ],
      "date_published": 1577854800,
      "doi": "https://doi.org/10.1007/s10875-019-00737-x",
      "external_ids": [
        {
          "id": "https://openalex.org/W3000301584",
          "provenance": "openalex",
          "source": "openalex"
        },
      ],
      "external_urls": [
        {
          "provenance": "openalex",
          "source": "open_access",
          "url": "https://link.springer.com/content/pdf/10.1007/s10875-019-00737-x.pdf"
        },
      ],
      "groups": [
        {
          "id": "66f7001199b6ea475f3be61f",
          "name": "Errores Innatos de la Inmunidad (Inmunodeficiencias Primarias)"
        }
      ],
      "id": "66fb7fd5cbfde71a09a2d66f",
      "keywords": [],
      "open_access": {
        "has_repository_fulltext": true,
        "is_open_access": true,
        "open_access_status": "hybrid",
        "url": "https://link.springer.com/content/pdf/10.1007/s10875-019-00737-x.pdf"
      },
      "ranking": [],
      "references": [],
      "scholar_citations_count": 1154,
      "source": {
        "id": "66f6eb6a99b6ea475f357b0d",
        "is_in_doaj": false,
        "name": "Journal of Clinical Immunology",
        "types": [
          {
            "source": "scimago",
            "type": "journal"
          },
        ]
      },
      "subjects": [
        {
          "source": "openalex",
          "subjects": [
            {
              "id": "66f6f03d99b6ea475f393a18",
              "level": 3,
              "name": "Immunity"
            },
          ]
        }
      ],
      "titles": [
        {
          "lang": "en",
          "source": "openalex",
          "title": "Human Inborn Errors of Immunity: 2019 Update on the Classification from the International Union of Immunological Societies Expert Committee"
        },
      ],
      "types": [
        {
          "code": "111",
          "level": 2,
          "provenance": "scienti",
          "source": "scienti",
          "type": "Publicado en revista especializada"
        },
      ],
      "updated": [
        {
          "source": "openalex",
          "time": 1727758293
        },
      ],
      "year_published": 2020
    }
    ]
    }
@apiError {String} error Mensaje de error en caso de fallo.
@apiErrorExample {json} Error en la solicitud:
    HTTP/1.1 400 Bad Request
    {
      "error": "Invalid affiliation ID"
    }
"""


@affiliation_api_router.route("/<affiliation_type>/<affiliation_id>/research/products", methods=["GET"])
def get_works_by_affiliation_api_expert(affiliation_type: str, affiliation_id: str) -> Response | Tuple[Response, int]:
    try:
        query_params = QueryParams(**request.args)
        data = api_expert_service.get_works_by_affiliation(affiliation_id, query_params, affiliation_type, request.url)
        return jsonify(data)
    except Exception as e:
        capture_exception(e)
        return jsonify({"error": str(e)}), 400
