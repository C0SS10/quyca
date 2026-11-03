from quyca.models.person_model import Person


def parse_person(person: Person, fields: list[str] | None = None) -> dict:
    """`fields` limits the response to the summary view; by default every field of the model is returned."""
    include = {"id" if field == "_id" else field for field in fields} if fields else None
    return person.model_dump(include=include, exclude_none=True)
