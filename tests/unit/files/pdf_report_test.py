"""Los reportes PDF muestran texto que viene del archivo del usuario: debe aparecer como texto, nunca como HTML."""

import io
from typing import Any, Callable

import pytest

from quyca.files import pdf_report

ATTACK = '<img src="https://atacante.example/x.png"/>'
ERRORS = [{"columna": "tipo_documento", "detalle": f"El tipo de documento '{ATTACK}' no es válido", "total_filas": 1}]
WARNINGS = [{"columna": "idioma", "detalle": "Idioma inválido", "valor": ATTACK, "total_filas": 1}]


@pytest.fixture()
def rendered_html(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    """Captura el HTML que se convertiría en PDF."""
    pages: list[str] = []

    def create_pdf(source: io.StringIO, dest: io.BytesIO) -> None:
        pages.append(source.getvalue())
        dest.write(b"%PDF-capturado")

    monkeypatch.setattr(pdf_report.pisa, "CreatePDF", create_pdf)
    return pages


REPORTS: dict[str, Callable[..., io.BytesIO]] = {
    "staff": lambda **user_text: pdf_report.generate_quality_report(
        ERRORS, WARNINGS, [], user_text["institution"], user_text["filename"], "01/01/2026", user_text["user"]
    ),
    "ciarp": lambda **user_text: pdf_report.generate_quality_report_ciarp(
        ERRORS,
        {"total_advertencias": 1},
        [],
        user_text["institution"],
        user_text["filename"],
        "01/01/2026",
        user_text["user"],
    ),
}


@pytest.mark.parametrize("report", REPORTS.values(), ids=REPORTS.keys())
def test_text_from_the_upload_is_escaped(rendered_html: list[str], report: Any) -> None:
    report(institution="<b>Universidad</b>", filename=f"{ATTACK}.xlsx", user="<i>staff</i>")

    [html] = rendered_html
    assert "atacante.example" in html
    assert ATTACK not in html
    assert "&lt;img" in html
    assert "<b>Universidad</b>" not in html
    assert "<i>staff</i>" not in html


@pytest.mark.parametrize("report", REPORTS.values(), ids=REPORTS.keys())
def test_generates_a_real_pdf(report: Any) -> None:
    pdf = report(institution="Universidad de Antioquia", filename="archivo.xlsx", user="staff")

    assert pdf.getvalue().startswith(b"%PDF")
