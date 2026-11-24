"""Construye archivos .xlsx de proyectos para las pruebas, válidos o dañados a propósito."""

import io
import zipfile
from datetime import datetime
from typing import Any, Callable

from openpyxl import Workbook

VALID_PROJECT: dict[str, Any] = {
    "codigo_proyecto": "P-001",
    "titulo": "Bioprospección de la flora de Antioquia",
    "resumen": "Inventario de especies con potencial farmacéutico.",
    "tipo_proyecto": "investigación",
    "estado": "en ejecución",
    "fecha_inicio": datetime(2022, 5, 12),
    "fecha_fin": datetime(2024, 5, 12),
    "investigador_principal_id": 1017234567,
    "investigador_principal_institucion_id": "03bp5hc83",
    "investigadores_ids": "43123456; 71234567",
    "valor_total": 50_000_000,
    "valor_especie_total": 20_000_000,
    "valor_fresco_total": 30_000_000,
    "fuente_financiacion_ids": "https://ror.org/03bp5hc83; Q12345",
    "regiones_ejecucion_id": "3689815",
}


def make_xlsx(
    rows: list[dict[str, Any]], headers: list[Any] | None = None, extra_sheets: int = 0, blank_rows_before: int = 0
) -> bytes:
    """Una hoja con `headers` (por defecto, las llaves de las filas en orden de aparición) y una fila por dict."""
    if headers is None:
        headers = list(dict.fromkeys(key for row in rows for key in row))
    workbook = Workbook()
    sheet = workbook.active
    sheet.append(headers)
    for _ in range(blank_rows_before):
        sheet.append([])
    for row in rows:
        sheet.append([row.get(header) for header in headers])
    for index in range(extra_sheets):
        workbook.create_sheet(f"Extra {index + 1}")
    buffer = io.BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()


def make_excel_style_xlsx(rows: list[list[str]], doctype: str = "") -> bytes:
    """Un .xlsx con los textos en xl/sharedStrings.xml, como lo guarda Excel (openpyxl los guarda dentro de la hoja).

    `doctype` se antepone a sharedStrings.xml para probar ataques contra su lector de XML.
    """
    strings = list(dict.fromkeys(value for row in rows for value in row))
    sheet_rows = "".join(
        f'<row r="{row_index}">'
        + "".join(
            f'<c r="{chr(65 + column_index)}{row_index}" t="s"><v>{strings.index(value)}</v></c>'
            for column_index, value in enumerate(row)
        )
        + "</row>"
        for row_index, row in enumerate(rows, start=1)
    )
    shared = "".join(f"<si><t>{value}</t></si>" for value in strings)
    main = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
    relationships = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
    package = "http://schemas.openxmlformats.org/package/2006/relationships"
    members = {
        "[Content_Types].xml": (
            '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
            '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
            '<Default Extension="xml" ContentType="application/xml"/>'
            '<Override PartName="/xl/workbook.xml" '
            'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
            '<Override PartName="/xl/worksheets/sheet1.xml" '
            'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
            '<Override PartName="/xl/sharedStrings.xml" '
            'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sharedStrings+xml"/>'
            "</Types>"
        ),
        "_rels/.rels": (
            f'<Relationships xmlns="{package}"><Relationship Id="rId1" '
            f'Type="{relationships}/officeDocument" Target="xl/workbook.xml"/></Relationships>'
        ),
        "xl/workbook.xml": (
            f'<workbook xmlns="{main}" xmlns:r="{relationships}">'
            '<sheets><sheet name="Proyectos" sheetId="1" r:id="rId1"/></sheets></workbook>'
        ),
        "xl/_rels/workbook.xml.rels": (
            f'<Relationships xmlns="{package}">'
            f'<Relationship Id="rId1" Type="{relationships}/worksheet" Target="worksheets/sheet1.xml"/>'
            f'<Relationship Id="rId2" Type="{relationships}/sharedStrings" Target="sharedStrings.xml"/>'
            "</Relationships>"
        ),
        "xl/worksheets/sheet1.xml": f'<worksheet xmlns="{main}"><sheetData>{sheet_rows}</sheetData></worksheet>',
        "xl/sharedStrings.xml": f'<?xml version="1.0"?>{doctype}<sst xmlns="{main}">{shared}</sst>',
    }
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, xml in members.items():
            archive.writestr(name, xml)
    return buffer.getvalue()


def rewrite_member(xlsx: bytes, member: str, transform: Callable[[str], str]) -> bytes:
    """Copia el .xlsx cambiando el XML de uno de sus archivos internos."""
    source = zipfile.ZipFile(io.BytesIO(xlsx))
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as target:
        for item in source.infolist():
            data = source.read(item.filename)
            target.writestr(item, transform(data.decode()) if item.filename == member else data)
    return out.getvalue()


def with_doctype(xml: str, doctype: str) -> str:
    return xml.replace("?>", "?>" + doctype, 1) if xml.startswith("<?xml") else doctype + xml
