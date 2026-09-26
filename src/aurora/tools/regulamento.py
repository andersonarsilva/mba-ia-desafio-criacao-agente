from collections.abc import Callable
from typing import Any

from aurora.regulamento.indice import IndiceRegulamento


def criar_tool_regulamento(indice: IndiceRegulamento) -> Callable[[str], dict[str, Any]]:
    def ler_capitulo(capitulo: str) -> dict[str, Any]:
        """Devolve o texto de um único capítulo do regulamento interno.

        Args:
            capitulo: número do capítulo em romano (ex.: IV) ou arábico (ex.: 4).
        """
        encontrado = indice.capitulo(capitulo)
        if encontrado is None:
            return {"erro": f"Capítulo inexistente: {capitulo!r}."}
        return {"capitulo": encontrado.numero, "titulo": encontrado.titulo, "texto": encontrado.texto}

    return ler_capitulo
