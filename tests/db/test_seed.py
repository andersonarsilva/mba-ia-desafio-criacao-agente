import hashlib

from aurora.db.repositorio import RepositorioCondominio
from aurora.db.seed import ensure_database, restaurar


def _hash_dir(path):
    return {f.name: hashlib.sha256(f.read_bytes()).hexdigest() for f in sorted(path.iterdir())}


def test_restore_resets_data_and_removes_sessions(paths, repositorio):
    repositorio.cancelar("101", "quadra", "2030-03-09")
    repositorio.autorizar_visitante("101", "Joana Ribeiro", "2030-04-21")
    paths.sessions_db.write_text("stale")

    restaurar(paths)

    assert [r.codigo for r in repositorio.listar_reservas("101")] == ["RSV-1377"]
    assert repositorio.listar_visitantes("101") == []
    assert not paths.sessions_db.exists()


def test_ensure_database_seeds_only_when_missing(paths):
    ensure_database(paths)
    repositorio = RepositorioCondominio(paths.condominio_db)
    repositorio.cancelar("101", "quadra", "2030-03-09")

    ensure_database(paths)

    assert repositorio.listar_reservas("101") == []


def test_seed_never_writes_to_dados(paths):
    before = _hash_dir(paths.dados)

    restaurar(paths)

    assert _hash_dir(paths.dados) == before
