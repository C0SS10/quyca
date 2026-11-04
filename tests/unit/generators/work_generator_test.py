import pytest
from pydantic import ValidationError
from quyca.generators.work_generator import get


def test_an_invalid_document_raises_instead_of_being_skipped() -> None:
    generator = get(iter([{}]))  # type: ignore[arg-type]

    with pytest.raises(ValidationError):
        next(generator)
