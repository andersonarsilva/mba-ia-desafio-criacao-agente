from google.adk.tools.tool_context import ToolContext


def apartamento_da_sessao(tool_context: ToolContext) -> str:
    """O apartamento é o user_id fixado na criação da sessão; nunca vem de argumento do modelo."""
    return tool_context.user_id
