import sqlite3
import uuid
from collections.abc import Callable
from pathlib import Path

from aurora.db.connection import connect
from aurora.dominio import Area, Reserva, Visitante

MAX_TENTATIVAS_CODIGO = 5
CODIGO_DUPLICADO = "reservas.codigo"


def gerar_codigo_reserva() -> str:
    return f"RSV-{uuid.uuid4().hex[:8].upper()}"


class CodigoIndisponivel(RuntimeError):
    pass


class RepositorioCondominio:
    def __init__(
        self,
        db_path: Path,
        gerar_codigo: Callable[[], str] = gerar_codigo_reserva,
    ) -> None:
        self._db_path = db_path
        self._gerar_codigo = gerar_codigo

    def apartamento_existe(self, numero: str) -> bool:
        with connect(self._db_path) as connection:
            row = connection.execute(
                "SELECT 1 FROM apartamentos WHERE numero = ?", (numero,)
            ).fetchone()
        return row is not None

    def listar_areas(self) -> list[Area]:
        with connect(self._db_path) as connection:
            rows = connection.execute("SELECT id, nome, taxa FROM areas ORDER BY nome").fetchall()
        return [Area(**row) for row in rows]

    def buscar_area(self, area_id: str) -> Area | None:
        with connect(self._db_path) as connection:
            row = connection.execute(
                "SELECT id, nome, taxa FROM areas WHERE id = ?", (area_id,)
            ).fetchone()
        return Area(**row) if row else None

    def data_livre(self, area_id: str, data: str) -> bool:
        with connect(self._db_path) as connection:
            row = connection.execute(
                "SELECT 1 FROM reservas WHERE area = ? AND data = ? AND status = 'ativa'",
                (area_id, data),
            ).fetchone()
        return row is None

    def listar_reservas(self, apartamento: str) -> list[Reserva]:
        with connect(self._db_path) as connection:
            rows = connection.execute(
                "SELECT codigo, area, data FROM reservas"
                " WHERE apartamento = ? AND status = 'ativa' ORDER BY data, area",
                (apartamento,),
            ).fetchall()
        return [Reserva(**row) for row in rows]

    def reservar(self, apartamento: str, area_id: str, data: str) -> Reserva | None:
        """Grava a reserva; devolve None quando a área já está reservada na data.

        A exclusividade é garantida pelo índice único parcial no instante do INSERT.
        """
        for _ in range(MAX_TENTATIVAS_CODIGO):
            codigo = self._gerar_codigo()
            try:
                with connect(self._db_path) as connection, connection:
                    connection.execute(
                        "INSERT INTO reservas (codigo, apartamento, area, data, status)"
                        " VALUES (?, ?, ?, ?, 'ativa')",
                        (codigo, apartamento, area_id, data),
                    )
                return Reserva(codigo=codigo, area=area_id, data=data)
            except sqlite3.IntegrityError as erro:
                if CODIGO_DUPLICADO not in str(erro):
                    return None
        raise CodigoIndisponivel("could not generate a unique reservation code")

    def cancelar(self, apartamento: str, area_id: str, data: str) -> Reserva | None:
        with connect(self._db_path) as connection, connection:
            row = connection.execute(
                "UPDATE reservas SET status = 'cancelada'"
                " WHERE apartamento = ? AND area = ? AND data = ? AND status = 'ativa'"
                " RETURNING codigo, area, data",
                (apartamento, area_id, data),
            ).fetchone()
        return Reserva(**row) if row else None

    def listar_visitantes(self, apartamento: str) -> list[Visitante]:
        with connect(self._db_path) as connection:
            rows = connection.execute(
                "SELECT nome, data FROM visitantes WHERE apartamento = ? ORDER BY data, id",
                (apartamento,),
            ).fetchall()
        return [Visitante(**row) for row in rows]

    def autorizar_visitante(self, apartamento: str, nome: str, data: str) -> Visitante:
        with connect(self._db_path) as connection, connection:
            connection.execute(
                "INSERT INTO visitantes (apartamento, nome, data) VALUES (?, ?, ?)",
                (apartamento, nome, data),
            )
        return Visitante(nome=nome, data=data)

    def registrar_sessao(self, session_id: str, apartamento: str) -> None:
        with connect(self._db_path) as connection, connection:
            connection.execute(
                "INSERT INTO sessoes (session_id, apartamento) VALUES (?, ?)",
                (session_id, apartamento),
            )

    def apartamento_da_sessao(self, session_id: str) -> str | None:
        with connect(self._db_path) as connection:
            row = connection.execute(
                "SELECT apartamento FROM sessoes WHERE session_id = ?", (session_id,)
            ).fetchone()
        return row["apartamento"] if row else None
