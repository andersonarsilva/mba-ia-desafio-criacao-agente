import json
from importlib.resources import files
from pathlib import Path
from typing import Any

from aurora.config import Paths
from aurora.db.connection import connect

SQLITE_COMPANION_SUFFIXES = ("", "-wal", "-shm", "-journal")


def _read_json(path: Path) -> list[dict[str, Any]]:
    return json.loads(path.read_text(encoding="utf-8"))


def _remove_sqlite_files(db_path: Path) -> None:
    for suffix in SQLITE_COMPANION_SUFFIXES:
        db_path.with_name(db_path.name + suffix).unlink(missing_ok=True)


def _create_and_seed(paths: Paths) -> None:
    paths.var.mkdir(parents=True, exist_ok=True)
    schema = files("aurora.db").joinpath("schema.sql").read_text(encoding="utf-8")
    with connect(paths.condominio_db) as connection:
        connection.execute("PRAGMA journal_mode = WAL")
        connection.executescript(schema)
        with connection:
            connection.executemany(
                "INSERT INTO apartamentos (numero, morador) VALUES (:numero, :morador)",
                _read_json(paths.dados / "apartamentos.json"),
            )
            connection.executemany(
                "INSERT INTO areas (id, nome, taxa) VALUES (:id, :nome, :taxa)",
                _read_json(paths.dados / "areas.json"),
            )
            connection.executemany(
                "INSERT INTO reservas (codigo, apartamento, area, data, status)"
                " VALUES (:codigo, :apartamento, :area, :data, 'ativa')",
                _read_json(paths.dados / "reservas.json"),
            )
            connection.executemany(
                "INSERT INTO visitantes (apartamento, nome, data) VALUES (:apartamento, :nome, :data)",
                _read_json(paths.dados / "visitantes.json"),
            )


def restaurar(paths: Paths) -> None:
    _remove_sqlite_files(paths.condominio_db)
    _remove_sqlite_files(paths.sessions_db)
    _create_and_seed(paths)


def ensure_database(paths: Paths) -> None:
    if not paths.condominio_db.exists():
        _create_and_seed(paths)
