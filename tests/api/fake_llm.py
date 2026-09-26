import json
import re
from collections.abc import AsyncGenerator

from google.adk.models.base_llm import BaseLlm
from google.adk.models.llm_request import LlmRequest
from google.adk.models.llm_response import LlmResponse
from google.genai import types

DATA = re.compile(r"\d{4}-\d{2}-\d{2}")
VISITANTE = re.compile(r"entrada d[ao] (.+?) no dia")
AREAS = {"salão": "salao-de-festas", "quadra": "quadra", "churrasqueira": "churrasqueira"}


def _texto(resposta: str) -> LlmResponse:
    return LlmResponse(content=types.Content(role="model", parts=[types.Part(text=resposta)]))


def _chamada(nome: str, args: dict) -> LlmResponse:
    chamada = types.FunctionCall(name=nome, args=args)
    return LlmResponse(content=types.Content(role="model", parts=[types.Part(function_call=chamada)]))


def _ultima_mensagem_do_morador(request: LlmRequest) -> str:
    for conteudo in reversed(request.contents):
        textos = [p.text for p in conteudo.parts or [] if p.text]
        if conteudo.role == "user" and textos and not textos[0].startswith("For context"):
            return " ".join(textos)
    return ""


class FakeLlm(BaseLlm):
    """LLM roteirizado que escolhe a ação pelo conjunto de tools do agente que o chama."""

    model: str = "fake"

    async def generate_content_async(
        self, llm_request: LlmRequest, stream: bool = False
    ) -> AsyncGenerator[LlmResponse, None]:
        yield self._decidir(llm_request)

    def _decidir(self, request: LlmRequest) -> LlmResponse:
        ultima = request.contents[-1]
        respostas = [p.function_response for p in ultima.parts or [] if p.function_response]
        if respostas and respostas[0].name != "transfer_to_agent":
            return _texto(json.dumps(respostas[0].response, ensure_ascii=False))

        texto = _ultima_mensagem_do_morador(request)
        tools = request.tools_dict
        if "ler_capitulo" in tools:
            return _chamada("ler_capitulo", {"capitulo": "IV"})
        if "regulamento" in tools:
            if "piscina" in texto.lower():
                return _chamada("regulamento", {"request": texto})
            agente = "visitantes" if "entrada" in texto.lower() else "reservas"
            return _chamada("transfer_to_agent", {"agent_name": agente})
        if "autorizar_visitante" in tools:
            nome = VISITANTE.search(texto)
            data = DATA.search(texto)
            return _chamada("autorizar_visitante", {"nome": nome.group(1), "data": data.group(0)})
        return self._reservas(texto)

    def _reservas(self, texto: str) -> LlmResponse:
        minusculo = texto.lower()
        data = DATA.search(texto)
        area = next((id_ for chave, id_ in AREAS.items() if chave in minusculo), None)
        if data is None or area is None:
            return _chamada("listar_minhas_reservas", {})
        acao = "cancelar_reserva" if "cancel" in minusculo else "reservar_area"
        return _chamada(acao, {"area": area, "data": data.group(0)})
