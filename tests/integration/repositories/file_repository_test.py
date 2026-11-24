"""Guardado de archivos subidos: primero Drive (falso aquí) y, si falla, el almacenamiento local de la prueba."""

import io
from pathlib import Path
from typing import Any

import pytest
from flask import Flask
from openpyxl import Workbook, load_workbook
from werkzeug.datastructures import FileStorage

from quyca.clients import google_drive
from quyca.files import excel_cleaner
from quyca.repositories import file_repository

ROR_ID = "03bp5hc83"
INSTITUTION = "Universidad de Antioquia"


def _file(content: bytes = b"contenido", filename: str = "dump.zip") -> FileStorage:
    return FileStorage(io.BytesIO(content), filename=filename)


def _save(app: Flask, file: FileStorage, ror_id: str = ROR_ID, **kwargs: Any) -> dict:
    with app.app_context():
        return file_repository.save_file(file, ror_id, INSTITUTION, "scienti", **kwargs)


@pytest.fixture()
def drive(monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    """Drive falso que registra las carpetas pedidas y lo que se sube."""
    record: dict[str, Any] = {"folders": []}

    def get_or_create_folder(service: Any, name: str, parent_id: str | None = None) -> str:
        record["folders"].append((name, parent_id))
        return f"id-{name}"

    def upload_file(service: Any, path: str, filename: str, folder_id: str) -> str:
        record.update(path=Path(path), content=Path(path).read_bytes(), filename=filename, folder=folder_id)
        return "https://drive/archivo"

    monkeypatch.setattr(google_drive, "get_service", lambda: "servicio")
    monkeypatch.setattr(google_drive, "get_or_create_folder", get_or_create_folder)
    monkeypatch.setattr(google_drive, "upload_file", upload_file)
    return record


def test_uploads_to_drive_inside_the_type_and_institution_folders(app: Flask, drive: dict) -> None:
    result = _save(app, _file())

    assert result["success"] is True
    assert drive["folders"] == [("scienti", None), (f"{ROR_ID}_Universidad-de-Antioquia", "id-scienti")]
    assert drive["folder"] == f"id-{ROR_ID}_Universidad-de-Antioquia"
    assert drive["content"] == b"contenido"
    assert drive["filename"].startswith(f"scienti_{ROR_ID}_") and drive["filename"].endswith(".zip")
    assert drive["filename"] in result["msg"]
    assert not drive["path"].exists(), "El archivo temporal debe borrarse después de subirlo"


def test_the_prefix_goes_before_the_name(app: Flask, drive: dict) -> None:
    _save(app, _file(), filename_prefix="ORIGINAL_")

    assert drive["filename"].startswith(f"ORIGINAL_scienti_{ROR_ID}_")


def test_falls_back_to_local_storage_when_drive_fails(app: Flask) -> None:
    result = _save(app, _file())

    assert result["success"] is True
    assert "almacenamiento local" in result["msg"]
    saved = Path(result["path"])
    assert saved.parent == Path(app.config["LOCAL_STORAGE_PATH"]) / "scienti" / f"{ROR_ID}_Universidad-de-Antioquia"
    assert saved.read_bytes() == b"contenido"


def test_reports_a_failure_when_no_storage_works(app: Flask) -> None:
    app.config["LOCAL_STORAGE_PATH"] = ""

    result = _save(app, _file())

    assert result["success"] is False
    assert "LOCAL_STORAGE_PATH" in result["msg"]


def _annotated_xlsx() -> bytes:
    workbook = Workbook()
    workbook.active.append(["identificación", "estado_de_validación", "observación"])
    workbook.active.append(["123", "Error", "Campo vacío"])
    buffer = io.BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()


def test_excel_files_are_stored_without_the_report_columns(app: Flask) -> None:
    result = _save(app, _file(_annotated_xlsx(), "staff.xlsx"))

    stored = load_workbook(result["path"]).active
    assert list(stored.iter_rows(values_only=True)) == [("identificación",), ("123",)]


def test_a_cleaning_failure_does_not_stop_the_save(
    app: Flask, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    def broken_clean(path: str) -> None:
        raise ValueError("libro dañado")

    monkeypatch.setattr(excel_cleaner, "clean", broken_clean)

    result = _save(app, _file(_annotated_xlsx(), "staff.xlsx"))

    assert result["success"] is True
    assert "ExcelCleaner" in caplog.text


def test_an_institution_id_with_slashes_is_saved(app: Flask) -> None:
    # Al crear usuarios se acepta cualquier ror_id, por ejemplo la URL completa del ROR.
    result = _save(app, _file(), ror_id="https://ror.org/03bp5hc83")

    assert result["success"] is True
    saved = Path(result["path"])
    assert saved.parent.parent == Path(app.config["LOCAL_STORAGE_PATH"]) / "scienti"
    assert saved.read_bytes() == b"contenido"
