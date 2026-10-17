from dataclasses import dataclass
from datetime import datetime

FORMATO_DATA = "%Y-%m-%d"


@dataclass(frozen=True)
class Area:
    id: str
    nome: str
    taxa: float

    @property
    def gera_cobranca(self) -> bool:
        return self.taxa > 0


@dataclass(frozen=True)
class Reserva:
    codigo: str
    area: str
    data: str


@dataclass(frozen=True)
class Visitante:
    nome: str
    data: str


class DataInvalida(ValueError):
    pass


def validar_data(texto: str) -> str:
    try:
        data = datetime.strptime(texto.strip(), FORMATO_DATA)
    except ValueError as erro:
        raise DataInvalida(f"data inválida: {texto!r}; use AAAA-MM-DD") from erro
    return data.strftime(FORMATO_DATA)
