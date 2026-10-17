from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.responses import JSONResponse

from aurora.agentes.app import criar_app, criar_modelo, criar_runner
from aurora.api.conversa import (
    ApartamentoInexistente,
    ConfirmacaoNaoPendente,
    ModeloIndisponivel,
    ServicoConversa,
    SessaoInexistente,
)
from aurora.api.esquemas import (
    ConfirmacaoEntrada,
    CriarSessaoEntrada,
    CriarSessaoSaida,
    MensagemEntrada,
    ReservaSaida,
    RespostaConversa,
    VisitanteSaida,
)
from aurora.config import load_settings
from aurora.db.repositorio import RepositorioCondominio
from aurora.db.seed import ensure_database
from aurora.regulamento.indice import IndiceRegulamento


@asynccontextmanager
async def _producao(app: FastAPI) -> AsyncIterator[None]:
    settings = load_settings()
    ensure_database(settings.paths)
    repositorio = RepositorioCondominio(settings.paths.condominio_db)
    indice = IndiceRegulamento.carregar(settings.paths.regulamento)
    runner = criar_runner(criar_app(criar_modelo(settings), repositorio, indice), settings)
    app.state.repositorio = repositorio
    app.state.servico = ServicoConversa(runner, repositorio)
    yield
    await runner.close()


def create_app(servico: ServicoConversa | None = None, repositorio: RepositorioCondominio | None = None) -> FastAPI:
    app = FastAPI(title="Assistente do Residencial Aurora", lifespan=None if servico else _producao)
    if servico is not None:
        app.state.servico = servico
        app.state.repositorio = repositorio

    @app.exception_handler(SessaoInexistente)
    async def _sessao_inexistente(_: Request, __: SessaoInexistente) -> JSONResponse:
        return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content={"detail": "sessão não encontrada"})

    @app.exception_handler(ModeloIndisponivel)
    async def _modelo_indisponivel(_: Request, __: ModeloIndisponivel) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"detail": "assistente temporariamente indisponível; tente novamente"},
        )

    def _servico(request: Request) -> ServicoConversa:
        return request.app.state.servico

    def _repositorio(request: Request) -> RepositorioCondominio:
        return request.app.state.repositorio

    @app.post("/sessoes", status_code=status.HTTP_201_CREATED, response_model=CriarSessaoSaida)
    async def criar_sessao(entrada: CriarSessaoEntrada, request: Request) -> CriarSessaoSaida:
        try:
            session_id = await _servico(request).criar_sessao(entrada.apartamento)
        except ApartamentoInexistente:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "apartamento não encontrado") from None
        return CriarSessaoSaida(session_id=session_id)

    @app.post("/sessoes/{session_id}/mensagens", response_model=RespostaConversa)
    async def enviar_mensagem(session_id: str, entrada: MensagemEntrada, request: Request) -> RespostaConversa:
        return await _servico(request).enviar_mensagem(session_id, entrada.texto)

    @app.post("/sessoes/{session_id}/confirmacoes", response_model=RespostaConversa)
    async def responder_confirmacao(
        session_id: str, entrada: ConfirmacaoEntrada, request: Request
    ) -> RespostaConversa:
        try:
            return await _servico(request).responder_confirmacao(session_id, entrada.id, entrada.confirmado)
        except ConfirmacaoNaoPendente:
            raise HTTPException(
                status.HTTP_409_CONFLICT, "não existe confirmação pendente com esse id nesta sessão"
            ) from None

    @app.get("/sessoes/{session_id}/eventos")
    async def listar_eventos(session_id: str, request: Request) -> list[dict]:
        return await _servico(request).eventos(session_id)

    @app.get("/apartamentos/{numero}/reservas", response_model=list[ReservaSaida])
    def listar_reservas(numero: str, request: Request) -> list[ReservaSaida]:
        return [ReservaSaida(**vars(r)) for r in _repositorio(request).listar_reservas(numero)]

    @app.get("/apartamentos/{numero}/visitantes", response_model=list[VisitanteSaida])
    def listar_visitantes(numero: str, request: Request) -> list[VisitanteSaida]:
        return [VisitanteSaida(**vars(v)) for v in _repositorio(request).listar_visitantes(numero)]

    return app
