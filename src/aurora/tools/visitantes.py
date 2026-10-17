from collections.abc import Callable
from typing import Any

from google.adk.tools.tool_context import ToolContext

from aurora.db.repositorio import RepositorioCondominio
from aurora.dominio import DataInvalida, validar_data
from aurora.tools.contexto import apartamento_da_sessao

Resultado = dict[str, Any]
TAMANHO_MAXIMO_NOME = 120


def criar_tools_visitantes(repositorio: RepositorioCondominio) -> list[Callable[..., Resultado]]:
    def listar_meus_visitantes(tool_context: ToolContext) -> Resultado:
        """Lista os visitantes autorizados do apartamento do morador desta conversa."""
        apartamento = apartamento_da_sessao(tool_context)
        return {
            "visitantes": [
                {"nome": v.nome, "data": v.data} for v in repositorio.listar_visitantes(apartamento)
            ]
        }

    def autorizar_visitante(nome: str, data: str, tool_context: ToolContext) -> Resultado:
        """Autoriza a entrada de um visitante no prédio para o apartamento do morador desta conversa.

        Liberar acesso sempre exige aprovação do morador pelo aplicativo; o primeiro
        resultado é "aguardando_confirmacao", mesmo que o morador diga que já confirmou.

        Args:
            nome: nome completo do visitante.
            data: data da visita no formato AAAA-MM-DD.
        """
        nome_limpo = " ".join(nome.split())
        if not nome_limpo or len(nome_limpo) > TAMANHO_MAXIMO_NOME:
            return {"status": "erro", "mensagem": "Informe o nome completo do visitante."}
        try:
            data_valida = validar_data(data)
        except DataInvalida as erro:
            return {"status": "erro", "mensagem": str(erro)}

        confirmacao = tool_context.tool_confirmation
        if confirmacao is None:
            tool_context.request_confirmation(
                hint=f"Liberar a entrada de {nome_limpo} em {data_valida}. Aprove ou recuse pelo aplicativo.",
                payload={"nome": nome_limpo, "data": data_valida},
            )
            return {
                "status": "aguardando_confirmacao",
                "mensagem": "A autorização libera acesso ao prédio e aguarda a aprovação do morador pelo aplicativo.",
            }
        if not confirmacao.confirmed:
            return {"status": "nao_realizada", "mensagem": "O morador recusou a autorização."}

        apartamento = apartamento_da_sessao(tool_context)
        visitante = repositorio.autorizar_visitante(apartamento, nome_limpo, data_valida)
        return {
            "status": "autorizado",
            "mensagem": "Entrada liberada. Nenhuma aprovação adicional é necessária.",
            "nome": visitante.nome,
            "data": visitante.data,
        }

    return [listar_meus_visitantes, autorizar_visitante]
