import inspect

import pytest
from google.adk.models.google_llm import Gemini
from google.adk.sessions.sqlite_session_service import SqliteSessionService
from google.adk.tools.agent_tool import AgentTool

from aurora.agentes.app import RETRY_OPTIONS, criar_app, criar_modelo, criar_runner
from aurora.agentes.arvore import criar_agente_raiz
from aurora.config import DEFAULT_PATHS, Settings
from aurora.regulamento.indice import IndiceRegulamento

INDICE = IndiceRegulamento.carregar(DEFAULT_PATHS.regulamento)


@pytest.fixture
def raiz(repositorio):
    return criar_agente_raiz(Gemini(model="gemini-2.5-flash"), repositorio, INDICE)


def _instrucao(agente) -> str:
    return agente.instruction(None)


def _todas_as_tools(agente):
    for tool in agente.tools:
        if isinstance(tool, AgentTool):
            yield from _todas_as_tools(tool.agent)
        else:
            yield tool
    for sub in agente.sub_agents:
        yield from _todas_as_tools(sub)


def test_topology_has_root_with_two_transfer_specialists_and_isolated_regulation(raiz):
    assert raiz.name == "assistente_aurora"
    assert [sub.name for sub in raiz.sub_agents] == ["reservas", "visitantes"]
    agent_tools = [t for t in raiz.tools if isinstance(t, AgentTool)]
    assert [t.agent.name for t in agent_tools] == ["regulamento"]


def test_root_instruction_contains_no_regulation_content(raiz):
    instrucao = _instrucao(raiz)

    assert "Art." not in instrucao
    for numero, _ in INDICE.sumario():
        corpo = INDICE.capitulo(numero).texto.split("\n", 1)[1].strip()
        assert corpo[:80] not in instrucao


def test_regulation_agent_gets_only_the_summary(raiz):
    regulamento = next(t.agent for t in raiz.tools if isinstance(t, AgentTool))
    instrucao = _instrucao(regulamento)

    assert "- Capítulo IV: Piscina" in instrucao
    assert "Art." not in instrucao
    assert "<<SUMARIO>>" not in instrucao


def test_no_tool_accepts_an_apartment_argument(raiz):
    tools = list(_todas_as_tools(raiz))

    assert len(tools) == 8
    for tool in tools:
        parametros = inspect.signature(tool).parameters
        assert not any("apartamento" in nome for nome in parametros), tool.__name__


def test_model_has_retry_and_timeout(monkeypatch):
    modelo = criar_modelo(Settings(model="gemini-x", paths=DEFAULT_PATHS))
    http_options = modelo.client_kwargs["http_options"]

    assert modelo.model == "gemini-x"
    assert http_options.retry_options == RETRY_OPTIONS
    assert http_options.timeout > 0


def test_app_is_resumable_and_runner_persists_in_sqlite(paths, repositorio):
    app = criar_app(Gemini(model="gemini-2.5-flash"), repositorio, INDICE)
    runner = criar_runner(app, Settings(model="gemini-2.5-flash", paths=paths))

    assert app.resumability_config.is_resumable
    assert isinstance(runner.session_service, SqliteSessionService)
