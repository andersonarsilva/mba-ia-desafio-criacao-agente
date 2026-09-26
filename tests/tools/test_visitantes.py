import pytest

from aurora.tools.visitantes import criar_tools_visitantes

from .conftest import FakeConfirmation, FakeToolContext


@pytest.fixture
def tools(repositorio):
    return {tool.__name__: tool for tool in criar_tools_visitantes(repositorio)}


def test_list_my_visitors_uses_session_apartment(tools):
    assert tools["listar_meus_visitantes"](FakeToolContext(user_id="101")) == {"visitantes": []}
    assert tools["listar_meus_visitantes"](FakeToolContext(user_id="302")) == {
        "visitantes": [{"nome": "Marina Duarte", "data": "2030-03-16"}]
    }


def test_authorization_always_requests_confirmation_first(tools, repositorio, contexto_101):
    resultado = tools["autorizar_visitante"]("  Joana   Ribeiro ", "2030-04-21", contexto_101)

    assert resultado["status"] == "aguardando_confirmacao"
    assert contexto_101.requested[0]["payload"] == {"nome": "Joana Ribeiro", "data": "2030-04-21"}
    assert repositorio.listar_visitantes("101") == []


def test_denied_authorization_writes_nothing(tools, repositorio):
    contexto = FakeToolContext(user_id="101", tool_confirmation=FakeConfirmation(confirmed=False))

    assert tools["autorizar_visitante"]("Joana Ribeiro", "2030-04-21", contexto)["status"] == "nao_realizada"
    assert repositorio.listar_visitantes("101") == []


def test_approved_authorization_writes_for_session_apartment(tools, repositorio):
    contexto = FakeToolContext(user_id="101", tool_confirmation=FakeConfirmation(confirmed=True))

    resultado = tools["autorizar_visitante"]("Joana Ribeiro", "2030-04-21", contexto)

    assert resultado == {"status": "autorizado", "nome": "Joana Ribeiro", "data": "2030-04-21"}
    assert [v.nome for v in repositorio.listar_visitantes("101")] == ["Joana Ribeiro"]


@pytest.mark.parametrize(("nome", "data"), [("", "2030-04-21"), ("x" * 121, "2030-04-21"), ("Joana", "amanhã")])
def test_invalid_input_returns_error(tools, contexto_101, nome, data):
    assert tools["autorizar_visitante"](nome, data, contexto_101)["status"] == "erro"
    assert contexto_101.requested == []
