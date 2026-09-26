import asyncio
import logging
from collections import defaultdict
from typing import Any

from google.adk.runners import Runner
from google.adk.sessions.session import Session
from google.genai import types

from aurora.agentes.app import APP_NAME
from aurora.api.confirmacoes import listar_pendentes, resposta_de_confirmacao
from aurora.api.esquemas import RespostaConversa
from aurora.db.repositorio import RepositorioCondominio

logger = logging.getLogger(__name__)


class SessaoInexistente(LookupError):
    pass


class ApartamentoInexistente(LookupError):
    pass


class ConfirmacaoNaoPendente(LookupError):
    pass


class ModeloIndisponivel(RuntimeError):
    pass


class ServicoConversa:
    def __init__(self, runner: Runner, repositorio: RepositorioCondominio) -> None:
        self._runner = runner
        self._repositorio = repositorio
        self._locks: defaultdict[str, asyncio.Lock] = defaultdict(asyncio.Lock)

    async def criar_sessao(self, apartamento: str) -> str:
        if not self._repositorio.apartamento_existe(apartamento):
            raise ApartamentoInexistente(apartamento)
        sessao = await self._runner.session_service.create_session(app_name=APP_NAME, user_id=apartamento)
        self._repositorio.registrar_sessao(sessao.id, apartamento)
        return sessao.id

    async def enviar_mensagem(self, session_id: str, texto: str) -> RespostaConversa:
        async with self._locks[session_id]:
            sessao = await self._carregar(session_id)
            mensagem = types.Content(role="user", parts=[types.Part(text=texto)])
            return await self._executar(sessao, mensagem)

    async def responder_confirmacao(self, session_id: str, confirmacao_id: str, confirmado: bool) -> RespostaConversa:
        # The ADK re-executes a tool for every confirmation response it receives, so the
        # pending check and the resume must happen atomically under the session lock.
        async with self._locks[session_id]:
            sessao = await self._carregar(session_id)
            if confirmacao_id not in {p.id for p in listar_pendentes(sessao.events)}:
                raise ConfirmacaoNaoPendente(confirmacao_id)
            return await self._executar(sessao, resposta_de_confirmacao(confirmacao_id, confirmado))

    async def eventos(self, session_id: str) -> list[dict[str, Any]]:
        sessao = await self._carregar(session_id)
        return [evento.model_dump(mode="json", by_alias=True, exclude_none=True) for evento in sessao.events]

    async def _carregar(self, session_id: str) -> Session:
        apartamento = self._repositorio.apartamento_da_sessao(session_id)
        if apartamento is None:
            raise SessaoInexistente(session_id)
        sessao = await self._runner.session_service.get_session(
            app_name=APP_NAME, user_id=apartamento, session_id=session_id
        )
        if sessao is None:
            raise SessaoInexistente(session_id)
        return sessao

    async def _executar(self, sessao: Session, mensagem: types.Content) -> RespostaConversa:
        textos: list[str] = []
        try:
            async for evento in self._runner.run_async(
                user_id=sessao.user_id, session_id=sessao.id, new_message=mensagem
            ):
                if evento.author == "user" or evento.partial or not evento.content:
                    continue
                textos.extend(p.text for p in evento.content.parts or [] if p.text and not p.thought)
        except Exception as erro:
            logger.exception("agent run failed", extra={"session_id": sessao.id})
            raise ModeloIndisponivel("the assistant is temporarily unavailable") from erro
        atualizada = await self._carregar(sessao.id)
        return RespostaConversa(
            resposta="\n".join(textos).strip(),
            confirmacoes_pendentes=listar_pendentes(atualizada.events),
        )
