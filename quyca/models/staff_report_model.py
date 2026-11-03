from typing import Any, Dict, List

from pydantic import BaseModel


class StaffReport(BaseModel):
    """Validation result of an uploaded Excel file (Staff or CIARP): errors, warnings and duplicates."""

    total_errors: int
    total_duplicates: int
    errors: List[Dict[str, Any]]
    grouped_errors: List[Dict[str, Any]]
    warnings: List[Dict[str, Any]]
    grouped_warnings: List[Dict[str, Any]]
    duplicates: List[Dict[str, Any]]
