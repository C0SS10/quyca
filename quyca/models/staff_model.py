from dataclasses import dataclass

"""Domain entity representing a staff member with identity and HR attributes."""


@dataclass
class Staff:
    """Represents a staff member with identification and employment data."""

    document_type: str
    identification: str
    last_name_1: str
    last_name_2: str | None = None
    first_names: str = ""
    orcid: str | None = None
    cvlac: str | None = None
    scholar: str | None = None
    academic_level: str | None = None
    contract_type: str | None = None
    work_schedule: str | None = None
    job_category: str | None = None
    gender: str | None = None
    birth_date: str | None = None
    start_link_date: str | None = None
    end_link_date: str | None = None
    academic_unit_code: str | None = None
    academic_unit: str | None = None
    academic_subunit_code: str | None = None
    academic_subunit: str | None = None
