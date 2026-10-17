import pytest

from aurora import config
from aurora.config import DEFAULT_MODEL, ConfigError, load_settings
from aurora.dominio import Area, DataInvalida, validar_data


@pytest.fixture
def no_dotenv(monkeypatch):
    monkeypatch.setattr(config, "load_dotenv", lambda *_: None)


def test_settings_require_api_key(monkeypatch, no_dotenv):
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)

    with pytest.raises(ConfigError):
        load_settings()


def test_settings_force_ai_studio_and_default_model(monkeypatch, no_dotenv):
    monkeypatch.setenv("GOOGLE_API_KEY", "test-key")
    monkeypatch.setenv("GOOGLE_GENAI_USE_VERTEXAI", "true")
    monkeypatch.delenv("AURORA_MODEL", raising=False)

    settings = load_settings()

    assert settings.model == DEFAULT_MODEL
    assert config.os.environ["GOOGLE_GENAI_USE_VERTEXAI"] == "false"


def test_settings_use_configured_model(monkeypatch, no_dotenv):
    monkeypatch.setenv("GOOGLE_API_KEY", "test-key")
    monkeypatch.setenv("AURORA_MODEL", "gemini-3.5-flash")

    assert load_settings().model == "gemini-3.5-flash"


@pytest.mark.parametrize("texto", ["2030-04-20", " 2030-04-20 "])
def test_valid_date(texto):
    assert validar_data(texto) == "2030-04-20"


@pytest.mark.parametrize("texto", ["20/04/2030", "2030-02-30", "amanhã", "20300420"])
def test_invalid_date(texto):
    with pytest.raises(DataInvalida):
        validar_data(texto)


def test_area_charges_only_with_positive_fee():
    assert Area("salao-de-festas", "Salão", 150.0).gera_cobranca
    assert not Area("quadra", "Quadra", 0).gera_cobranca
