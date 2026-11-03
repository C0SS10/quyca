from typing import Any
from unittest.mock import patch
from quyca.files import pdf_report


def test_pdf_report_includes_normalization_section() -> None:
    captured: dict[str, str] = {}

    def fake_create_pdf(src: Any, dest: Any) -> Any:
        captured["html"] = src.getvalue()
        dest.write(b"pdf-bytes")
        return type("Result", (), {"err": False})()

    with patch("quyca.files.pdf_report.pisa.CreatePDF", side_effect=fake_create_pdf):
        pdf_report.generate_quality_report(
            errors=[],
            warnings=[],
            duplicados=[],
            institution="TestInstitution",
            filename="staff.xlsx",
            upload_date="27/05/2026 12:00",
            user="admin",
            normalized_changes=[
                {
                    "columna": "categoría_laboral",
                    "valor_original": "Profesor Titular",
                    "valor_normalizado": "profesor titular",
                    "fila": 0,
                    "fila_excel": 2,
                }
            ],
        )

    html_content = captured.get("html", "")
    assert "Normalizaciones aplicadas" in html_content
    assert "contacta al equipo de desarrollo" in html_content
    assert "Profesor Titular" in html_content
    assert "profesor titular" in html_content
