from typing import Any, List, Dict

from quyca.constants.geo_states_cities import GEO_RELATED_FIELDS
from quyca.exceptions import NotEntityException
from quyca.models.geo_model import Geo
from quyca.generators import geo_generator
from quyca.clients.mongo import database


def get_geo_by_id(geo_type: str, geo_id: str, projection: Dict | None = None) -> Geo:
    pipeline: List[Dict[str, Any]] = [{"$match": {"_id": geo_id, "type": geo_type}}]
    if projection:
        pipeline.append({"$project": projection})
    geo = next(geo_generator.get(database["geo"].aggregate(pipeline)), None)
    if geo is None:
        raise NotEntityException(f"The geolocation with id {geo_id} does not exist.")
    return geo


def build_works_geo_match(geo_type: str, geo_id: str) -> Dict:
    return {"authors.affiliations.id": {"$in": get_geo_institution_ids(geo_type, geo_id)}}


def get_geo_institution_ids(geo_type: str, geo_id: str) -> List[str]:
    geo = get_geo_by_id(geo_type, geo_id, {"institutions.id": 1})
    return [institution.id for institution in geo.institutions or []]


def get_geo_affiliations(geo_type: str, geo_id: str) -> Geo:
    return get_geo_by_id(geo_type, geo_id, GEO_RELATED_FIELDS)
