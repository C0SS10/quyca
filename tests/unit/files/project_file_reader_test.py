import io
import re
import time
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any
import pytest
from support.project_files import VALID_PROJECT, make_excel_style_xlsx, make_xlsx, rewrite_member, with_doctype
from quyca.exceptions import ProjectFileException
from quyca.files import project_file_reader
from quyca.files.project_file_reader import clean_value, read_project_file


def _read(xlsx: bytes, filename: str = "proyectos.xlsx") -> Any:
    return read_project_file(io.BytesIO(xlsx), filename)


class TestHeaders:
    def test_maps_every_column_of_the_format(self) -> None:
        content = _read(make_xlsx([VALID_PROJECT]))

        assert content.columns == list(VALID_PROJECT)
        assert content.ignored_columns == []
        assert content.duplicated_columns == []

    @pytest.mark.parametrize(
        "header, column",
        [
            pytest.param("código_bpin", "codigo_bpin", id="con-tilde-como-en-el-pdf"),
            pytest.param("fuente_financiación_ids", "fuente_financiacion_ids", id="tilde-en-medio"),
            pytest.param("Codigo Proyecto", "codigo_proyecto", id="mayusculas-y-espacio"),
            pytest.param("  titulo  ", "titulo", id="espacios-alrededor"),
            pytest.param("codigo_proyecto*", "codigo_proyecto", id="asterisco-copiado-del-pdf"),
            pytest.param("fecha_inicio *", "fecha_inicio", id="espacio-y-asterisco"),
        ],
    )
    def test_accepts_the_spellings_people_use(self, header: str, column: str) -> None:
        content = _read(make_xlsx([{header: "x"}]))

        assert content.columns == [column]

    def test_unknown_and_duplicated_columns_are_reported(self) -> None:
        content = _read(make_xlsx([{"titulo": "a", "Título": "b", "observaciones": "c", 2024: "d"}]))

        assert content.columns == ["titulo"]
        assert content.duplicated_columns == ["titulo"]
        assert content.ignored_columns == ["observaciones", "2024"]

    def test_empty_header_cells_are_skipped(self) -> None:
        content = _read(make_xlsx([{"titulo": "a"}], headers=[None, "titulo", "   "]))

        assert content.columns == ["titulo"]
        assert content.rows[0].values == {"titulo": "a"}

    @pytest.mark.parametrize("headers", [[], [None, "  ", ""]], ids=["sin-fila", "fila-en-blanco"])
    def test_first_row_must_have_headers(self, headers: list) -> None:
        with pytest.raises(ProjectFileException, match="encabezados"):
            _read(make_xlsx([], headers=headers))


class TestRows:
    def test_keeps_the_excel_row_number_and_skips_blank_rows(self) -> None:
        content = _read(make_xlsx([VALID_PROJECT, {"codigo_proyecto": "P-002"}], blank_rows_before=2))

        assert [row.row_number for row in content.rows] == [4, 5]

    def test_cleans_text_and_keeps_native_types(self) -> None:
        row = _read(make_xlsx([{**VALID_PROJECT, "titulo": "  Título  ", "resumen": "   "}])).rows[0].values

        assert row["titulo"] == "Título"
        assert row["resumen"] is None
        assert row["fecha_inicio"] == datetime(2022, 5, 12)
        assert row["valor_total"] == 50_000_000

    def test_only_reads_the_columns_of_the_format(self) -> None:
        headers = ["titulo"] + [f"ruido_{index}" for index in range(300)]
        rows = [{"titulo": "a", **{f"ruido_{index}": index for index in range(300)}}]

        content = _read(make_xlsx(rows, headers=headers))

        assert content.rows[0].values == {"titulo": "a"}

    def test_counts_the_sheets(self) -> None:
        assert _read(make_xlsx([VALID_PROJECT], extra_sheets=2)).sheet_count == 3

    def test_a_short_row_fills_the_missing_cells_with_none(self) -> None:
        values = project_file_reader.read_rows(iter([("a",)]), {0: "titulo", 5: "resumen"})[0].values

        assert values == {"titulo": "a", "resumen": None}


class TestRejectedFiles:
    @pytest.mark.parametrize(
        "filename, extension",
        [
            pytest.param("proyectos.xls", ".xls", id="xls"),
            pytest.param("proyectos.csv", ".csv", id="csv"),
            pytest.param("proyectos.xlsm", ".xlsm", id="con-macros"),
            pytest.param("proyectos", "desconocida", id="sin-extension"),
            pytest.param("", "desconocida", id="sin-nombre"),
        ],
    )
    def test_only_xlsx_is_accepted(self, filename: str, extension: str) -> None:
        with pytest.raises(ProjectFileException, match=re.escape(f"'{extension}' no soportada")) as error:
            _read(make_xlsx([VALID_PROJECT]), filename)

        assert "guárdelo como .xlsx" in str(error.value)

    def test_the_extension_is_case_insensitive(self) -> None:
        assert _read(make_xlsx([VALID_PROJECT]), "PROYECTOS.XLSX").rows

    @pytest.mark.parametrize(
        "content",
        [
            pytest.param(b"", id="vacio"),
            pytest.param(b"codigo_proyecto,titulo\nP1,x\n", id="csv-renombrado"),
            pytest.param(b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1" + b"\0" * 504, id="xls-renombrado"),
            pytest.param(b"PK\x03\x04 truncado", id="zip-truncado"),
        ],
    )
    def test_content_that_is_not_an_xlsx(self, content: bytes) -> None:
        with pytest.raises(ProjectFileException, match="no es un libro de Excel"):
            _read(content)

    def test_a_zip_that_is_not_a_workbook(self) -> None:
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w") as archive:
            archive.writestr("hola.txt", "no soy un libro")

        with pytest.raises(ProjectFileException, match="no es un libro de Excel"):
            _read(buffer.getvalue())

    @pytest.mark.parametrize(
        "member, transform",
        [
            pytest.param("xl/worksheets/sheet1.xml", lambda xml: xml[: len(xml) // 2], id="hoja-cortada"),
            pytest.param(
                "xl/worksheets/sheet1.xml", lambda xml: xml.replace("</row>", "</fila>", 1), id="hoja-mal-cerrada"
            ),
            pytest.param("xl/workbook.xml", lambda xml: "no es xml", id="libro-dañado"),
        ],
    )
    def test_a_damaged_workbook_is_a_bad_file_not_a_server_error(self, member: str, transform: Any) -> None:
        with pytest.raises(ProjectFileException, match="no es un libro de Excel"):
            _read(rewrite_member(make_xlsx([VALID_PROJECT]), member, transform))

    def test_damaged_shared_strings(self) -> None:
        xlsx = make_excel_style_xlsx([["codigo_proyecto"], ["P1"]])

        with pytest.raises(ProjectFileException, match="no es un libro de Excel"):
            _read(rewrite_member(xlsx, "xl/sharedStrings.xml", lambda xml: "<sst><si><t>"))

    def test_a_workbook_without_sheets(self, monkeypatch: pytest.MonkeyPatch) -> None:
        class EmptyWorkbook:
            worksheets: list = []

            def close(self) -> None:
                pass

        monkeypatch.setattr(project_file_reader, "load_workbook", lambda *args, **kwargs: EmptyWorkbook())

        with pytest.raises(ProjectFileException, match="no tiene hojas"):
            _read(make_xlsx([VALID_PROJECT]))


class TestLimits:
    def test_too_many_rows(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(project_file_reader, "MAX_PROJECT_ROWS", 3)

        assert len(_read(make_xlsx([VALID_PROJECT] * 3)).rows) == 3
        with pytest.raises(ProjectFileException, match="máximo de 3 filas"):
            _read(make_xlsx([VALID_PROJECT] * 4))

    def test_content_that_expands_too_much(self, monkeypatch: pytest.MonkeyPatch) -> None:
        xlsx = make_xlsx([VALID_PROJECT])
        uncompressed = sum(member.file_size for member in zipfile.ZipFile(io.BytesIO(xlsx)).infolist())

        monkeypatch.setattr(project_file_reader, "MAX_UNCOMPRESSED_BYTES", uncompressed)
        assert _read(xlsx).rows

        monkeypatch.setattr(project_file_reader, "MAX_UNCOMPRESSED_BYTES", uncompressed - 1)
        with pytest.raises(ProjectFileException, match="al descomprimirse"):
            _read(xlsx)

    def test_the_stream_is_rewound_after_the_size_check(self) -> None:
        stream = io.BytesIO(make_xlsx([VALID_PROJECT]))

        assert read_project_file(stream, "proyectos.xlsx").rows


def test_reads_files_saved_by_excel() -> None:
    """Excel guarda los textos aparte, en xl/sharedStrings.xml; openpyxl no, así que se arma a mano."""
    content = _read(make_excel_style_xlsx([["Código Proyecto*", "titulo"], ["P-001", "Bioprospección"]]))

    assert [row.values for row in content.rows] == [{"codigo_proyecto": "P-001", "titulo": "Bioprospección"}]


EXTERNAL_ENTITY = '<!DOCTYPE x [<!ENTITY e SYSTEM "file://{path}">]>'
ENTITY_EXPANSION = "<!DOCTYPE x [{}]>".format(
    "".join(f'<!ENTITY l{i} "' + (f"&l{i - 1};" * 10 if i else "lol" * 10) + '">' for i in range(10))
)


def _excel_style_attack(doctype: str, entity: str) -> bytes:
    return make_excel_style_xlsx([["codigo_proyecto", "titulo"], ["P1", entity]], doctype)


def _inline_text_attack(doctype: str, entity: str) -> bytes:
    xlsx = make_xlsx([{**VALID_PROJECT, "titulo": "MARCA"}])
    return rewrite_member(
        xlsx, "xl/worksheets/sheet1.xml", lambda xml: with_doctype(xml, doctype).replace("MARCA", entity)
    )


@pytest.mark.parametrize(
    "build", [_excel_style_attack, _inline_text_attack], ids=["textos-compartidos", "texto-en-la-hoja"]
)
class TestMaliciousXml:
    """Archivos armados a mano para atacar el lector de XML: se rechazan sin filtrar datos ni tumbar el servidor."""

    def test_external_entities_never_read_server_files(self, build: Any, tmp_path: Path) -> None:
        secret = tmp_path / "secreto.txt"
        secret.write_text("JWT_SECRET_KEY=no-deberia-salir")

        with pytest.raises(ProjectFileException, match="no es un libro de Excel") as error:
            _read(build(EXTERNAL_ENTITY.format(path=secret), "&e;"))

        assert "no-deberia-salir" not in str(error.value)

    def test_entity_expansion_is_cut_short(self, build: Any) -> None:
        start = time.monotonic()

        with pytest.raises(ProjectFileException, match="no es un libro de Excel"):
            _read(build(ENTITY_EXPANSION, "&l9;"))

        assert time.monotonic() - start < 5


@pytest.mark.parametrize(
    "value, expected",
    [
        pytest.param("  texto  ", "texto", id="recorta"),
        pytest.param("   ", None, id="solo-espacios"),
        pytest.param("", None, id="vacio"),
        pytest.param(0, 0, id="cero-se-conserva"),
        pytest.param(None, None, id="none"),
    ],
)
def test_clean_value(value: Any, expected: Any) -> None:
    assert clean_value(value) == expected
