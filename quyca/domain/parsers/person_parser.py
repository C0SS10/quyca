from quyca.domain.models.person_model import Person


def parse_person(person: Person, include: list = []) -> dict:
    if not include:
        include = [
            "id",
            "full_name",
            "affiliations",
            "external_ids",
            "products_count",
            "citations_count",
            "logo",
            "h_index",
            "h5_index",
        ]
    return person.model_dump(include=set(include), exclude_none=True)
