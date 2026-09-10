from quyca.domain.models.staff_model import Staff


def test_staff_creation_with_all_fields() -> None:
    staff = Staff(
        document_type="CC",
        identification="123456789",
        last_name_1="Pérez",
        last_name_2="Gómez",
        first_names="Juan Carlos",
        orcid="0000-0001-2345-6789",
        cvlac="https://scienti.minciencias.gov.co/cvlac/123",
        scholar="https://scholar.google.com/citations?user=123",
        academic_level="Maestría",
        contract_type="Tiempo completo",
        work_schedule="40 horas",
        job_category="Docente",
        gender="M",
        birth_date="1990-01-01",
        start_link_date="2020-01-01",
        end_link_date="2025-12-31",
        academic_unit_code="FAC001",
        academic_unit="Facultad de Ingeniería",
        academic_subunit_code="DEP001",
        academic_subunit="Departamento de Sistemas",
    )

    assert staff.document_type == "CC"
    assert staff.identification == "123456789"
    assert staff.last_name_1 == "Pérez"
    assert staff.last_name_2 == "Gómez"
    assert staff.first_names == "Juan Carlos"
    assert staff.orcid == "0000-0001-2345-6789"
    assert staff.cvlac == "https://scienti.minciencias.gov.co/cvlac/123"
    assert staff.scholar == "https://scholar.google.com/citations?user=123"
    assert staff.academic_level == "Maestría"
    assert staff.contract_type == "Tiempo completo"
    assert staff.work_schedule == "40 horas"
    assert staff.job_category == "Docente"
    assert staff.gender == "M"
    assert staff.birth_date == "1990-01-01"
    assert staff.start_link_date == "2020-01-01"
    assert staff.end_link_date == "2025-12-31"
    assert staff.academic_unit_code == "FAC001"
    assert staff.academic_unit == "Facultad de Ingeniería"
    assert staff.academic_subunit_code == "DEP001"
    assert staff.academic_subunit == "Departamento de Sistemas"