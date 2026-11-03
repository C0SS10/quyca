from typing import Any, Literal

from pydantic import BaseModel

Severity = Literal["error", "warning"]


class ValidationIssue(BaseModel):
    row: int | None = None
    column: str | None = None
    code: str
    severity: Severity
    message: str
    value: str | None = None


class ProjectFileRow(BaseModel):
    row_number: int
    values: dict[str, Any]


class ProjectFileContent(BaseModel):
    sheet_count: int
    columns: list[str]
    ignored_columns: list[str]
    duplicated_columns: list[str]
    rows: list[ProjectFileRow]


class ProjectFileReport(BaseModel):
    schema_version: str
    valid: bool
    total_rows: int
    total_projects: int | None = None
    errors_count: int
    warnings_count: int
    issues_truncated: bool = False
    issues: list[ValidationIssue]
