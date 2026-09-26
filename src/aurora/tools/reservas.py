from collections.abc import Callable
from typing import Any

from google.adk.tools.tool_context import ToolContext

from aurora.db.repositorio import RepositorioCondominio
from aurora.dominio import Area, DataInvalida, validar_data
from aurora.tools.contexto import apartamento_da_sessao

Resultado = dict[str, Any]


def _indisponivel(area: Area, data: str) -> Resultado:
    return {
        "status": "indisponivel",
        "mensagem": f"{area.nome} já está reservado(a) em {data}. Escolha outra data.",
    }


def criar_tools_reservas(repositorio: RepositorioCondominio) -> list[Callable[..., Resultado]]:
    def _validar(area_id: str, data: str) -> tuple[Area, str] | Resultado:
        area = repositorio.buscar_area(area_id.strip())
        if area is None:
            return {
                "status": "erro",
                "mensagem": f"Área desconhecida: {area_id!r}.",
                "areas_validas": [a.id for a in repositorio.listar_areas()],
            }
        try:
            return area, validar_data(data)
        except DataInvalida as erro:
            return {"status": "erro", "mensagem": str(erro)}

    def _gravar(apartamento: str, area: Area, data: str) -> Resultado:
        reserva = repositorio.reservar(apartamento, area.id, data)
        if reserva is None:
            return _indisponivel(area, data)
        return {
            "status": "reservada",
            "codigo": reserva.codigo,
            "area": area.id,
            "data": data,
            "cobranca": area.taxa,
        }

    def listar_areas() -> Resultado:
        """Lista as áreas comuns reserváveis, com id, nome, taxa e se a reserva exige confirmação."""
        return {
            "areas": [
                {"id": a.id, "nome": a.nome, "taxa": a.taxa, "exige_confirmacao": a.gera_cobranca}
                for a in repositorio.listar_areas()
            ]
        }

    def consultar_disponibilidade(area: str, data: str) -> Resultado:
        """Informa se uma área está livre numa data (AAAA-MM-DD). Nunca revela de quem é a reserva.

        Args:
            area: id da área (ex.: salao-de-festas, churrasqueira, quadra).
            data: data no formato AAAA-MM-DD.
        """
        validado = _validar(area, data)
        if isinstance(validado, dict):
            return validado
        area_encontrada, data_valida = validado
        livre = repositorio.data_livre(area_encontrada.id, data_valida)
        return {"area": area_encontrada.id, "data": data_valida, "disponivel": livre}

    def listar_minhas_reservas(tool_context: ToolContext) -> Resultado:
        """Lista as reservas ativas do apartamento do morador desta conversa."""
        apartamento = apartamento_da_sessao(tool_context)
        return {
            "reservas": [
                {"codigo": r.codigo, "area": r.area, "data": r.data}
                for r in repositorio.listar_reservas(apartamento)
            ]
        }

    def reservar_area(area: str, data: str, tool_context: ToolContext) -> Resultado:
        """Reserva uma área comum para o apartamento do morador desta conversa.

        Áreas com taxa geram cobrança e só são reservadas depois que o morador aprovar
        pelo aplicativo; nesse caso o resultado é "aguardando_confirmacao".

        Args:
            area: id da área (ex.: salao-de-festas, churrasqueira, quadra).
            data: data no formato AAAA-MM-DD.
        """
        validado = _validar(area, data)
        if isinstance(validado, dict):
            return validado
        area_encontrada, data_valida = validado
        apartamento = apartamento_da_sessao(tool_context)
        confirmacao = tool_context.tool_confirmation

        if confirmacao is not None:
            if not confirmacao.confirmed:
                return {"status": "nao_realizada", "mensagem": "O morador recusou a reserva."}
            return _gravar(apartamento, area_encontrada, data_valida)

        if not repositorio.data_livre(area_encontrada.id, data_valida):
            return _indisponivel(area_encontrada, data_valida)
        if not area_encontrada.gera_cobranca:
            return _gravar(apartamento, area_encontrada, data_valida)

        tool_context.request_confirmation(
            hint=(
                f"Reserva de {area_encontrada.nome} em {data_valida} gera cobrança de "
                f"R$ {area_encontrada.taxa:.2f}. Aprove ou recuse pelo aplicativo."
            ),
            payload={"area": area_encontrada.id, "data": data_valida, "taxa": area_encontrada.taxa},
        )
        return {
            "status": "aguardando_confirmacao",
            "mensagem": "A reserva gera cobrança e aguarda a aprovação do morador pelo aplicativo.",
        }

    def cancelar_reserva(area: str, data: str, tool_context: ToolContext) -> Resultado:
        """Cancela uma reserva ativa do apartamento do morador desta conversa.

        Args:
            area: id da área (ex.: salao-de-festas, churrasqueira, quadra).
            data: data da reserva no formato AAAA-MM-DD.
        """
        validado = _validar(area, data)
        if isinstance(validado, dict):
            return validado
        area_encontrada, data_valida = validado
        apartamento = apartamento_da_sessao(tool_context)
        cancelada = repositorio.cancelar(apartamento, area_encontrada.id, data_valida)
        if cancelada is None:
            return {
                "status": "nao_encontrada",
                "mensagem": "Não há reserva ativa do seu apartamento nessa área e data.",
            }
        return {"status": "cancelada", "codigo": cancelada.codigo, "area": cancelada.area, "data": cancelada.data}

    return [listar_areas, consultar_disponibilidade, listar_minhas_reservas, reservar_area, cancelar_reserva]
