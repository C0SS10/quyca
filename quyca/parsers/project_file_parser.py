from quyca.models.project_file_model import ProjectFileReport


def parse_project_file_report(report: ProjectFileReport) -> dict:
    return report.model_dump(mode="json")
