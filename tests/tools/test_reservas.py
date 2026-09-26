import json

import pytest

from aurora.tools.reservas import criar_tools_reservas

from .conftest import FakeConfirmation, FakeToolContext


@pytest.fixture
def tools(repositorio):
    return {tool.__name__: tool for tool in criar_tools_reservas(repositorio)}


def test_list_areas_flags_which_require_confirmation(tools):
    areas = {a["id"]: a["exige_confirmacao"] for a in tools["listar_areas"]()["areas"]}

    assert areas == {"salao-de-festas": True, "churrasqueira": True, "quadra": False}


def test_availability_never_reveals_owner(tools):
    resultado = tools["consultar_disponibilidade"]("salao-de-festas", "2030-03-16")

    assert resultado == {"area": "salao-de-festas", "data": "2030-03-16", "disponivel": False}
    assert "302" not in json.dumps(resultado) and "RSV-4821" not in json.dumps(resultado)


def test_list_my_reservations_uses_session_apartment(tools, contexto_101):
    resultado = tools["listar_minhas_reservas"](contexto_101)

    assert resultado == {"reservas": [{"codigo": "RSV-1377", "area": "quadra", "data": "2030-03-09"}]}


def test_free_area_is_reserved_without_confirmation(tools, repositorio, contexto_101):
    resultado = tools["reservar_area"]("quadra", "2030-04-06", contexto_101)

    assert resultado["status"] == "reservada"
    assert resultado["cobranca"] == 0
    assert contexto_101.requested == []
    assert any(r.data == "2030-04-06" for r in repositorio.listar_reservas("101"))


def test_paid_area_requests_confirmation_and_writes_nothing(tools, repositorio, contexto_101):
    resultado = tools["reservar_area"]("salao-de-festas", "2030-04-20", contexto_101)

    assert resultado["status"] == "aguardando_confirmacao"
    assert contexto_101.requested[0]["payload"] == {
        "area": "salao-de-festas",
        "data": "2030-04-20",
        "taxa": 150.0,
    }
    assert repositorio.data_livre("salao-de-festas", "2030-04-20")


def test_denied_confirmation_writes_nothing(tools, repositorio):
    contexto = FakeToolContext(user_id="101", tool_confirmation=FakeConfirmation(confirmed=False))

    assert tools["reservar_area"]("salao-de-festas", "2030-04-20", contexto)["status"] == "nao_realizada"
    assert repositorio.data_livre("salao-de-festas", "2030-04-20")


def test_approved_confirmation_writes_once(tools, repositorio):
    contexto = FakeToolContext(user_id="101", tool_confirmation=FakeConfirmation(confirmed=True))

    resultado = tools["reservar_area"]("salao-de-festas", "2030-04-20", contexto)

    assert resultado["status"] == "reservada"
    assert [r.area for r in repositorio.listar_reservas("101")].count("salao-de-festas") == 1


def test_approval_loses_race_with_normal_answer(tools, repositorio):
    repositorio.reservar("201", "salao-de-festas", "2030-05-11")
    contexto = FakeToolContext(user_id="101", tool_confirmation=FakeConfirmation(confirmed=True))

    resultado = tools["reservar_area"]("salao-de-festas", "2030-05-11", contexto)

    assert resultado["status"] == "indisponivel"
    assert "201" not in json.dumps(resultado, ensure_ascii=False)


def test_taken_date_is_refused_before_confirmation_without_leaking_owner(tools, contexto_101):
    resultado = tools["reservar_area"]("salao-de-festas", "2030-03-16", contexto_101)

    assert resultado["status"] == "indisponivel"
    assert contexto_101.requested == []
    texto = json.dumps(resultado, ensure_ascii=False)
    assert "302" not in texto and "RSV-4821" not in texto


@pytest.mark.parametrize(
    ("area", "data"),
    [("piscina", "2030-04-20"), ("quadra", "20/04/2030")],
)
def test_invalid_input_returns_error(tools, contexto_101, area, data):
    for nome in ("reservar_area", "cancelar_reserva"):
        assert tools[nome](area, data, contexto_101)["status"] == "erro"
    assert tools["consultar_disponibilidade"](area, data)["status"] == "erro"


def test_cancel_own_reservation(tools, repositorio, contexto_101):
    resultado = tools["cancelar_reserva"]("quadra", "2030-03-09", contexto_101)

    assert resultado == {"status": "cancelada", "codigo": "RSV-1377", "area": "quadra", "data": "2030-03-09"}
    assert repositorio.listar_reservas("101") == []


def test_cancel_other_apartment_reservation_is_not_found_and_leaks_nothing(tools, repositorio, contexto_101):
    resultado = tools["cancelar_reserva"]("salao-de-festas", "2030-03-16", contexto_101)

    assert resultado["status"] == "nao_encontrada"
    assert "RSV-4821" not in json.dumps(resultado)
    assert [r.codigo for r in repositorio.listar_reservas("302")] == ["RSV-4821"]
