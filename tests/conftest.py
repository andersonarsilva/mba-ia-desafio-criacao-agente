from pathlib import Path

import pytest

from aurora.config import DEFAULT_PATHS, Paths
from aurora.db.repositorio import RepositorioCondominio
from aurora.db.seed import restaurar


@pytest.fixture
def paths(tmp_path: Path) -> Paths:
    return Paths(dados=DEFAULT_PATHS.dados, var=tmp_path / "var")


@pytest.fixture
def repositorio(paths: Paths) -> RepositorioCondominio:
    restaurar(paths)
    return RepositorioCondominio(paths.condominio_db)
