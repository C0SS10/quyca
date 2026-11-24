from io import BytesIO
from typing import IO

from quyca.constants.project_file_schema import MAX_REPORTED_ISSUES, SCHEMA_VERSION
from quyca.models.project_file_model import ProjectFileReport, ValidationIssue
from quyca.parsers import project_file_parser
from quyca.validators import project_file_validator
from quyca.files import project_file_reader


def validate_project_file(file_stream: BytesIO | IO[bytes], filename: str) -> dict:
    content = project_file_reader.read_project_file(file_stream, filename)
    issues = project_file_validator.validate_structure(content)
    total_projects = None
    if not any(issue.severity == "error" for issue in issues):
        row_issues, normalized_rows = project_file_validator.validate_rows(content)
        issues += row_issues
        issues += project_file_validator.validate_project_consistency(normalized_rows)
        total_projects = len(
            {values["codigo_proyecto"] for _, values in normalized_rows if values.get("codigo_proyecto")}
        )
    issues.sort(key=_issue_sort_key)
    errors_count = sum(issue.severity == "error" for issue in issues)
    report = ProjectFileReport(
        schema_version=SCHEMA_VERSION,
        valid=errors_count == 0,
        total_rows=len(content.rows),
        total_projects=total_projects,
        errors_count=errors_count,
        warnings_count=len(issues) - errors_count,
        issues_truncated=len(issues) > MAX_REPORTED_ISSUES,
        issues=issues[:MAX_REPORTED_ISSUES],
    )
    return {"data": project_file_parser.parse_project_file_report(report)}


def _issue_sort_key(issue: ValidationIssue) -> tuple:
    return issue.row or 0, issue.column or ""
