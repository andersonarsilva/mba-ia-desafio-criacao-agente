from importlib.resources import files

from google.adk.agents import LlmAgent
from google.adk.agents.readonly_context import ReadonlyContext
from google.adk.models.base_llm import BaseLlm
from google.adk.tools.agent_tool import AgentTool

from aurora.db.repositorio import RepositorioCondominio
from aurora.regulamento.indice import IndiceRegulamento
from aurora.tools.regulamento import criar_tool_regulamento
from aurora.tools.reservas import criar_tools_reservas
from aurora.tools.visitantes import criar_tools_visitantes

MARCADOR_SUMARIO = "<<SUMARIO>>"


def carregar_prompt(nome: str) -> str:
    return files("aurora.agentes").joinpath("prompts", f"{nome}.md").read_text(encoding="utf-8")


def _instrucao_fixa(texto: str):
    # An InstructionProvider bypasses ADK state injection, so braces in prompts are never templated.
    def provider(_: ReadonlyContext) -> str:
        return texto

    return provider


def criar_agente_regulamento(modelo: BaseLlm, indice: IndiceRegulamento) -> LlmAgent:
    sumario = "\n".join(f"- Capítulo {numero}: {titulo}" for numero, titulo in indice.sumario())
    return LlmAgent(
        name="regulamento",
        description="Responde dúvidas sobre o regulamento interno do condomínio.",
        model=modelo,
        instruction=_instrucao_fixa(carregar_prompt("regulamento").replace(MARCADOR_SUMARIO, sumario)),
        tools=[criar_tool_regulamento(indice)],
    )


def criar_agente_reservas(modelo: BaseLlm, repositorio: RepositorioCondominio) -> LlmAgent:
    return LlmAgent(
        name="reservas",
        description="Consulta disponibilidade, lista, reserva e cancela reservas de áreas comuns do morador.",
        model=modelo,
        instruction=_instrucao_fixa(carregar_prompt("reservas")),
        tools=criar_tools_reservas(repositorio),
    )


def criar_agente_visitantes(modelo: BaseLlm, repositorio: RepositorioCondominio) -> LlmAgent:
    return LlmAgent(
        name="visitantes",
        description="Lista e autoriza a entrada de visitantes do morador.",
        model=modelo,
        instruction=_instrucao_fixa(carregar_prompt("visitantes")),
        tools=criar_tools_visitantes(repositorio),
    )


def criar_agente_raiz(
    modelo: BaseLlm, repositorio: RepositorioCondominio, indice: IndiceRegulamento
) -> LlmAgent:
    """Agente principal: só encaminha.

    Reservas e visitantes são sub_agents (transferência) porque pedem confirmação, e a
    retomada precisa chegar ao agente autor na sessão persistida. O regulamento é um
    AgentTool porque roda em sessão isolada e só a resposta final entra nos eventos.
    """
    return LlmAgent(
        name="assistente_aurora",
        description="Assistente virtual do Residencial Aurora.",
        model=modelo,
        instruction=_instrucao_fixa(carregar_prompt("assistente_aurora")),
        tools=[AgentTool(agent=criar_agente_regulamento(modelo, indice))],
        sub_agents=[
            criar_agente_reservas(modelo, repositorio),
            criar_agente_visitantes(modelo, repositorio),
        ],
    )
