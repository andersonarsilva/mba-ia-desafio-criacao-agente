from typing import Any

from pydantic import BaseModel, Field, StrictBool


class CriarSessaoEntrada(BaseModel):
    apartamento: str = Field(min_length=1, max_length=10)


class CriarSessaoSaida(BaseModel):
    session_id: str


class MensagemEntrada(BaseModel):
    texto: str = Field(min_length=1, max_length=4000)


class ConfirmacaoEntrada(BaseModel):
    id: str = Field(min_length=1)
    confirmado: StrictBool


class ConfirmacaoPendente(BaseModel):
    id: str
    acao: str
    detalhes: dict[str, Any]


class RespostaConversa(BaseModel):
    resposta: str
    confirmacoes_pendentes: list[ConfirmacaoPendente]


class ReservaSaida(BaseModel):
    codigo: str
    area: str
    data: str


class VisitanteSaida(BaseModel):
    nome: str
    data: str
