from aurora.config import DEFAULT_PATHS
from aurora.regulamento.indice import IndiceRegulamento
from aurora.tools.regulamento import criar_tool_regulamento

ler_capitulo = criar_tool_regulamento(IndiceRegulamento.carregar(DEFAULT_PATHS.regulamento))


def test_returns_single_requested_chapter():
    resultado = ler_capitulo("IV")

    assert resultado["titulo"] == "Piscina"
    assert "Capítulo V" not in resultado["texto"]


def test_unknown_chapter_returns_error_without_text():
    assert set(ler_capitulo("XX")) == {"erro"}
