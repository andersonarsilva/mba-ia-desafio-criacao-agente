from collections.abc import Callable

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from aurora.agentes.app import criar_app, criar_runner
from aurora.api.conversa import ServicoConversa
from aurora.api.main import create_app
from aurora.config import Settings
from aurora.db.repositorio import RepositorioCondominio
from aurora.regulamento.indice import IndiceRegulamento

from .fake_llm import FakeLlm


@pytest.fixture
def montar_api(paths, repositorio) -> Callable[[], FastAPI]:
    """Cada chamada monta uma API nova sobre os mesmos arquivos, como um reinício do processo."""

    def montar() -> FastAPI:
        repo = RepositorioCondominio(paths.condominio_db)
        indice = IndiceRegulamento.carregar(paths.regulamento)
        runner = criar_runner(criar_app(FakeLlm(), repo, indice), Settings(model="fake", paths=paths))
        return create_app(ServicoConversa(runner, repo), repo)

    return montar


@pytest.fixture
def cliente(montar_api) -> TestClient:
    return TestClient(montar_api())
