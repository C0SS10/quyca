from pytest import MonkeyPatch, fixture

from quyca.config import settings


@fixture(autouse=True)
def curation_services_configured(monkeypatch: MonkeyPatch) -> None:
    """The tool is optional: its routes answer 503 unless ClickHouse and Ollama are configured. The repositories are mocked."""
    monkeypatch.setattr(settings, "CLICKHOUSE_SERVER", "clickhouse.test")
    monkeypatch.setattr(settings, "OLLAMA_URL", "http://ollama.test")
    monkeypatch.setattr(settings, "OLLAMA_MODEL", "model-test")
