import json
import logging
import sys
from collections.abc import AsyncGenerator

from fastapi.testclient import TestClient
from google.adk.models.base_llm import BaseLlm
from google.adk.models.llm_request import LlmRequest
from google.adk.models.llm_response import LlmResponse

from aurora import cli
from aurora.agentes.app import criar_app, criar_runner
from aurora.api.conversa import ServicoConversa
from aurora.api.main import create_app
from aurora.config import Settings
from aurora.db.repositorio import RepositorioCondominio
from aurora.logs import JsonFormatter
from aurora.regulamento.indice import IndiceRegulamento


class FailingLlm(BaseLlm):
    model: str = "failing"

    async def generate_content_async(
        self, llm_request: LlmRequest, stream: bool = False
    ) -> AsyncGenerator[LlmResponse, None]:
        raise RuntimeError("quota exhausted")
        yield


def test_model_failure_returns_503_without_internal_details(paths, repositorio):
    indice = IndiceRegulamento.carregar(paths.regulamento)
    runner = criar_runner(criar_app(FailingLlm(), repositorio, indice), Settings(model="x", paths=paths))
    cliente = TestClient(create_app(ServicoConversa(runner, repositorio), repositorio))
    sessao = cliente.post("/sessoes", json={"apartamento": "101"}).json()["session_id"]

    resposta = cliente.post(f"/sessoes/{sessao}/mensagens", json={"texto": "oi"})

    assert resposta.status_code == 503
    assert "quota" not in resposta.text


def test_session_registered_but_missing_from_store_is_404(cliente, paths):
    RepositorioCondominio(paths.condominio_db).registrar_sessao("orfa", "101")

    assert cliente.get("/sessoes/orfa/eventos").status_code == 404


def test_json_formatter_includes_context_and_error():
    try:
        raise ValueError("boom")
    except ValueError:
        record = logging.LogRecord("aurora", logging.ERROR, __file__, 1, "run failed", None, sys.exc_info())
    record.session_id = "s-1"

    payload = json.loads(JsonFormatter().format(record))

    assert payload["message"] == "run failed"
    assert payload["session_id"] == "s-1"
    assert payload["level"] == "ERROR"
    assert "ValueError: boom" in payload["error"]


def test_cli_commands(monkeypatch, paths):
    chamadas = {}
    monkeypatch.setattr(cli, "DEFAULT_PATHS", paths)
    monkeypatch.setattr(cli, "configure_logging", lambda: chamadas.setdefault("logging", True))
    monkeypatch.setattr(cli.uvicorn, "run", lambda *args, **kwargs: chamadas.update(run=(args, kwargs)))

    cli.restaurar()
    cli.api()

    assert paths.condominio_db.exists()
    args, kwargs = chamadas["run"]
    assert args == ("aurora.api.main:create_app",)
    assert kwargs["factory"] and kwargs["host"] == "127.0.0.1" and kwargs["port"] == 8000 and kwargs["workers"] == 1
