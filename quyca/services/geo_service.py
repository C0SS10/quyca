import time

from quyca.constants.geo_states_cities import GEO_RELATED_FIELDS
from quyca.parsers.base_parser import build_entity_metadata
from quyca.repositories import geo_repository


def get_geo_by_id(geo_type: str, geo_id: str) -> dict:
    start_time = time.time()
    geo = geo_repository.get_geo_by_id(geo_type, geo_id, {field: 0 for field in GEO_RELATED_FIELDS})
    return build_entity_metadata(geo.model_dump(exclude_none=True), start_time)


def get_related_affiliations_by_geo(geo_type: str, geo_id: str) -> dict:
    geo = geo_repository.get_geo_affiliations(geo_type, geo_id)
    data = {
        "institutions": [institution.model_dump() for institution in geo.institutions or []],
        "groups": [group.model_dump() for group in geo.groups or []],
    }
    if geo_type == "state":
        data["cities"] = [city.model_dump() for city in geo.cities or []]
    return data
