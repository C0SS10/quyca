import pytest

from quyca.models.base_model import ExternalId
from quyca.models.patent_model import Patent

OCCURRENCE = {"source_kind": "gruplac", "source_id": "COL0062428", "occurrence_id": "2d9c57e0"}


@pytest.mark.parametrize(
    "external_id, expected",
    [
        (OCCURRENCE, "COL0062428-2d9c57e0"),
        ({"COD_RH": "0000000678", "COD_PRODUCTO": "5"}, "0000000678-5"),
        ({"COD_RH": "0000000678"}, "0000000678"),
        ("PE-0000000678-5", "PE-0000000678-5"),
    ],
)
def test_external_ids_are_flattened_to_a_string(external_id: object, expected: str) -> None:
    assert ExternalId.model_validate({"source": "minciencias", "id": external_id}).id == expected


def test_patent_of_the_minciencias_etl_is_parsed() -> None:
    document = {
        "_id": "0001a389b5f19b45fd3b213bad7867bfd2a6bf12aa26973befce382040592f74",
        "external_ids": [{"provenance": "minciencias", "source": "minciencias", "id": OCCURRENCE}],
    }

    patent = Patent.model_validate(document)

    assert patent.id == document["_id"]
    assert patent.external_ids and patent.external_ids[0].id == "COL0062428-2d9c57e0"
