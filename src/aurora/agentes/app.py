from google.adk.apps import App, ResumabilityConfig
from google.adk.models.base_llm import BaseLlm
from google.adk.models.google_llm import Gemini
from google.adk.runners import Runner
from google.adk.sessions.sqlite_session_service import SqliteSessionService
from google.genai import types

from aurora.agentes.arvore import criar_agente_raiz
from aurora.config import Settings
from aurora.db.repositorio import RepositorioCondominio
from aurora.regulamento.indice import IndiceRegulamento

APP_NAME = "aurora"
LLM_TIMEOUT_MS = 60_000
RETRY_OPTIONS = types.HttpRetryOptions(
    attempts=5,
    initial_delay=2.0,
    max_delay=30.0,
    exp_base=2.0,
    http_status_codes=[429, 500, 502, 503, 504],
)


def criar_modelo(settings: Settings) -> Gemini:
    # Gemini replaces its own http_options with client_kwargs, so retry and timeout travel together.
    return Gemini(
        model=settings.model,
        client_kwargs={
            "http_options": types.HttpOptions(retry_options=RETRY_OPTIONS, timeout=LLM_TIMEOUT_MS)
        },
    )


def criar_app(modelo: BaseLlm, repositorio: RepositorioCondominio, indice: IndiceRegulamento) -> App:
    return App(
        name=APP_NAME,
        root_agent=criar_agente_raiz(modelo, repositorio, indice),
        resumability_config=ResumabilityConfig(is_resumable=True),
    )


def criar_runner(app: App, settings: Settings) -> Runner:
    settings.paths.var.mkdir(parents=True, exist_ok=True)
    return Runner(app=app, session_service=SqliteSessionService(str(settings.paths.sessions_db)))
