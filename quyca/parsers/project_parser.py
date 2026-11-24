from quyca.models.project_model import Project


def parse_projects_by_entity(projects: list) -> list:
    return [project.model_dump(exclude_none=True) for project in projects]


def parse_project(project: Project) -> dict:
    return project.model_dump()
