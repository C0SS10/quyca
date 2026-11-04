"""Parámetros de la herramienta de curación: tipos, límites y el mensaje de cada error."""

import pytest

from quyca.exceptions import InvalidParamException
from quyca.validators import theme_validator


@pytest.mark.parametrize(
    "value, expected",
    [
        pytest.param(1, 1, id="minimo"),
        pytest.param(100, 100, id="maximo"),
        pytest.param("7", 7, id="texto"),
        pytest.param(" 7 ", 7, id="texto-con-espacios"),
        pytest.param(7.0, 7, id="decimal-exacto"),
    ],
)
def test_accepts_integers_in_range(value: object, expected: int) -> None:
    assert theme_validator.validate_int_in_range(value, "limit", 1, 100) == expected


@pytest.mark.parametrize(
    "value",
    [
        pytest.param(0, id="bajo-el-minimo"),
        pytest.param(101, id="sobre-el-maximo"),
        pytest.param(True, id="booleano"),
        pytest.param(7.5, id="decimal"),
        pytest.param(float("inf"), id="infinito"),
        pytest.param(float("nan"), id="nan"),
        pytest.param("7.0", id="texto-decimal"),
        pytest.param("siete", id="texto-no-numerico"),
        pytest.param(None, id="none"),
        pytest.param([7], id="lista"),
    ],
)
def test_rejects_values_that_are_not_integers_in_range(value: object) -> None:
    with pytest.raises(InvalidParamException, match=r"^limit must be an integer between 1 and 100\.$"):
        theme_validator.validate_int_in_range(value, "limit", 1, 100)


def test_accepts_a_text() -> None:
    assert theme_validator.validate_text("energía solar", "seed_text") == "energía solar"


@pytest.mark.parametrize(
    "value",
    [
        pytest.param("", id="vacio"),
        pytest.param(None, id="none"),
        pytest.param(5, id="numero"),
        pytest.param(["a"], id="lista"),
    ],
)
def test_rejects_what_is_not_a_text(value: object) -> None:
    with pytest.raises(InvalidParamException, match=r"^seed_text es obligatorio\.$"):
        theme_validator.validate_text(value, "seed_text")


def test_accepts_the_whole_candidate_list() -> None:
    topic_ids = [str(position) for position in range(theme_validator.RERANK_MAX_TOPICS)]

    assert theme_validator.validate_topic_ids(topic_ids) == topic_ids


@pytest.mark.parametrize(
    "topic_ids, message",
    [
        pytest.param("1", "debe ser un arreglo no vacío", id="texto"),
        pytest.param([], "debe ser un arreglo no vacío", id="vacia"),
        pytest.param([str(i) for i in range(121)], "como máximo 120", id="una-de-mas"),
        pytest.param(["1", 2], "solo cadenas no vacías", id="numero"),
        pytest.param(["1", ""], "solo cadenas no vacías", id="cadena-vacia"),
        pytest.param(["1", "1"], "no admite repetidos", id="repetidos"),
    ],
)
def test_rejects_invalid_topic_ids(topic_ids: object, message: str) -> None:
    with pytest.raises(InvalidParamException, match=message):
        theme_validator.validate_topic_ids(topic_ids)


@pytest.mark.parametrize(
    "topics", [pytest.param(None, id="none"), pytest.param([], id="vacia"), pytest.param({}, id="objeto")]
)
def test_rejects_a_bulk_without_topics(topics: object) -> None:
    with pytest.raises(InvalidParamException, match="topics es obligatorio"):
        theme_validator.validate_topics(topics)


@pytest.mark.parametrize(
    "status, method, justification",
    [
        pytest.param("included", "automatic", None, id="incluido"),
        pytest.param("excluded", "manual", None, id="excluido-manual"),
        pytest.param("borderline", "automatic", "Solo en parte", id="frontera-justificado"),
    ],
)
def test_accepts_valid_classifications(status: str, method: str, justification: str | None) -> None:
    theme_validator.validate_classification(status, method, justification)


@pytest.mark.parametrize(
    "status, method, justification, message",
    [
        pytest.param("maybe", "automatic", None, "status debe ser", id="estado-desconocido"),
        pytest.param(None, "automatic", None, "status debe ser", id="sin-estado"),
        pytest.param("included", "invented", None, "method debe ser", id="metodo-desconocido"),
        pytest.param("borderline", "automatic", None, "justification es obligatoria", id="frontera-sin-justificacion"),
        pytest.param("borderline", "automatic", "", "justification es obligatoria", id="frontera-justificacion-vacia"),
    ],
)
def test_rejects_invalid_classifications(status: object, method: object, justification: object, message: str) -> None:
    with pytest.raises(InvalidParamException, match=message):
        theme_validator.validate_classification(status, method, justification)
