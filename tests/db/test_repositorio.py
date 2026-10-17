from concurrent.futures import ThreadPoolExecutor
from itertools import chain, repeat

import pytest

from aurora.db.repositorio import (
    CodigoIndisponivel,
    RepositorioCondominio,
    gerar_codigo_reserva,
)
from aurora.dominio import Area, Reserva, Visitante

CODIGOS_INICIAIS = {"RSV-1377", "RSV-4821", "RSV-2950"}


def test_lists_only_active_reservations_of_the_apartment(repositorio):
    assert repositorio.listar_reservas("101") == [Reserva("RSV-1377", "quadra", "2030-03-09")]
    assert repositorio.listar_reservas("102") == []


def test_lists_only_visitors_of_the_apartment(repositorio):
    assert repositorio.listar_visitantes("302") == [Visitante("Marina Duarte", "2030-03-16")]
    assert repositorio.listar_visitantes("101") == []


def test_areas_come_from_seed(repositorio):
    assert repositorio.buscar_area("quadra") == Area("quadra", "Quadra poliesportiva", 0)
    assert repositorio.buscar_area("piscina") is None
    assert {a.id for a in repositorio.listar_areas()} == {"salao-de-festas", "churrasqueira", "quadra"}


def test_apartment_existence(repositorio):
    assert repositorio.apartamento_existe("101")
    assert not repositorio.apartamento_existe("999")


def test_availability_reflects_active_reservations(repositorio):
    assert not repositorio.data_livre("salao-de-festas", "2030-03-16")
    assert repositorio.data_livre("salao-de-festas", "2030-04-20")


def test_reserve_creates_active_reservation_with_new_code(repositorio):
    reserva = repositorio.reservar("101", "quadra", "2030-04-06")

    assert reserva is not None
    assert reserva.codigo.startswith("RSV-")
    assert reserva.codigo not in CODIGOS_INICIAIS
    assert reserva in repositorio.listar_reservas("101")


def test_reserve_returns_none_when_date_is_taken(repositorio):
    assert repositorio.reservar("101", "salao-de-festas", "2030-03-16") is None
    assert repositorio.listar_reservas("302") == [Reserva("RSV-4821", "salao-de-festas", "2030-03-16")]


def test_concurrent_reservations_for_same_area_and_date_have_single_winner(repositorio):
    apartamentos = ["101", "102", "201", "202", "301", "302"] * 3

    with ThreadPoolExecutor(max_workers=len(apartamentos)) as executor:
        resultados = list(
            executor.map(lambda apto: repositorio.reservar(apto, "churrasqueira", "2030-05-11"), apartamentos)
        )

    assert sum(r is not None for r in resultados) == 1
    ativas = [r for apto in set(apartamentos) for r in repositorio.listar_reservas(apto) if r.data == "2030-05-11"]
    assert len(ativas) == 1


def test_cancel_only_affects_own_reservation(repositorio):
    assert repositorio.cancelar("101", "salao-de-festas", "2030-03-16") is None
    assert repositorio.listar_reservas("302") == [Reserva("RSV-4821", "salao-de-festas", "2030-03-16")]

    cancelada = repositorio.cancelar("101", "quadra", "2030-03-09")

    assert cancelada == Reserva("RSV-1377", "quadra", "2030-03-09")
    assert repositorio.listar_reservas("101") == []
    assert repositorio.data_livre("quadra", "2030-03-09")


def test_code_of_cancelled_reservation_is_never_reused(paths, repositorio):
    repositorio.cancelar("101", "quadra", "2030-03-09")
    codigos = chain(["RSV-1377", "RSV-4821"], repeat("RSV-NOVO0001"))
    repo = RepositorioCondominio(paths.condominio_db, gerar_codigo=lambda: next(codigos))

    reserva = repo.reservar("101", "quadra", "2030-03-09")

    assert reserva is not None and reserva.codigo == "RSV-NOVO0001"


def test_gives_up_when_code_generator_keeps_colliding(paths, repositorio):
    repo = RepositorioCondominio(paths.condominio_db, gerar_codigo=lambda: "RSV-1377")

    with pytest.raises(CodigoIndisponivel):
        repo.reservar("101", "quadra", "2030-06-01")


def test_generated_codes_are_distinct():
    assert len({gerar_codigo_reserva() for _ in range(1000)}) == 1000


def test_authorize_visitor(repositorio):
    visitante = repositorio.autorizar_visitante("101", "Joana Ribeiro", "2030-04-21")

    assert visitante == Visitante("Joana Ribeiro", "2030-04-21")
    assert repositorio.listar_visitantes("101") == [visitante]


def test_session_registry(repositorio):
    repositorio.registrar_sessao("s-1", "101")

    assert repositorio.apartamento_da_sessao("s-1") == "101"
    assert repositorio.apartamento_da_sessao("s-2") is None
