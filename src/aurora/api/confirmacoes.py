from collections.abc import Sequence

from google.adk.events.event import Event
from google.adk.flows.llm_flows.functions import REQUEST_CONFIRMATION_FUNCTION_CALL_NAME
from google.genai import types

from aurora.api.esquemas import ConfirmacaoPendente


def listar_pendentes(eventos: Sequence[Event]) -> list[ConfirmacaoPendente]:
    """Uma confirmação está pendente enquanto o pedido do ADK não tem resposta nos eventos.

    Os eventos persistidos são a única fonte de verdade: a lista sobrevive ao reinício
    e um id já respondido deixa de ser pendente por construção.
    """
    respondidas = {
        resposta.id
        for evento in eventos
        for resposta in evento.get_function_responses()
        if resposta.name == REQUEST_CONFIRMATION_FUNCTION_CALL_NAME
    }
    pendentes = []
    for evento in eventos:
        for chamada in evento.get_function_calls():
            if chamada.name != REQUEST_CONFIRMATION_FUNCTION_CALL_NAME or chamada.id in respondidas:
                continue
            args = chamada.args or {}
            original = args.get("originalFunctionCall") or {}
            confirmacao = args.get("toolConfirmation") or {}
            pendentes.append(
                ConfirmacaoPendente(
                    id=chamada.id,
                    acao=original.get("name", ""),
                    detalhes=confirmacao.get("payload") or original.get("args") or {},
                )
            )
    return pendentes


def resposta_de_confirmacao(confirmacao_id: str, confirmado: bool) -> types.Content:
    return types.Content(
        role="user",
        parts=[
            types.Part(
                function_response=types.FunctionResponse(
                    id=confirmacao_id,
                    name=REQUEST_CONFIRMATION_FUNCTION_CALL_NAME,
                    response={"confirmed": confirmado},
                )
            )
        ],
    )
