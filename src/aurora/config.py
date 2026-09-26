import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MODEL = "gemini-3.8-flash"


@dataclass(frozen=True)
class Paths:
    dados: Path
    var: Path

    @property
    def condominio_db(self) -> Path:
        return self.var / "condominio.db"

    @property
    def sessions_db(self) -> Path:
        return self.var / "sessions.db"

    @property
    def regulamento(self) -> Path:
        return self.dados / "regulamento.md"


DEFAULT_PATHS = Paths(dados=PROJECT_ROOT / "dados", var=PROJECT_ROOT / "var")


@dataclass(frozen=True)
class Settings:
    model: str
    paths: Paths


class ConfigError(RuntimeError):
    pass


def load_settings(paths: Paths = DEFAULT_PATHS) -> Settings:
    load_dotenv(PROJECT_ROOT / ".env")
    if not os.environ.get("GOOGLE_API_KEY", "").strip():
        raise ConfigError("GOOGLE_API_KEY is required; copy .env.example to .env and fill it in")
    # The challenge requires Google AI Studio keys; a shell-exported flag must not switch to Vertex AI.
    os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "false"
    model = os.environ.get("AURORA_MODEL", "").strip() or DEFAULT_MODEL
    return Settings(model=model, paths=paths)
