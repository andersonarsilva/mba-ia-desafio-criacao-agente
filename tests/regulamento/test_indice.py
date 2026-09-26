import pytest

from aurora.config import DEFAULT_PATHS
from aurora.regulamento.indice import IndiceRegulamento, romano_para_int


@pytest.fixture(scope="module")
def indice() -> IndiceRegulamento:
    return IndiceRegulamento.carregar(DEFAULT_PATHS.regulamento)


def test_summary_lists_the_fourteen_chapters(indice):
    sumario = indice.sumario()

    assert len(sumario) == 14
    assert sumario[0] == ("I", "Disposições gerais")
    assert sumario[3] == ("IV", "Piscina")
    assert sumario[-1] == ("XIV", "Disposições finais")


@pytest.mark.parametrize("referencia", ["IV", "iv", "4", "Capítulo IV", " capítulo 4 "])
def test_finds_chapter_by_roman_or_arabic_reference(indice, referencia):
    capitulo = indice.capitulo(referencia)

    assert capitulo is not None
    assert capitulo.titulo == "Piscina"


def test_pool_chapter_contains_sunday_hours_and_nothing_from_other_chapters(indice):
    texto = indice.capitulo("IV").texto
    outros = [c for c in indice.sumario() if c[0] != "IV"]

    assert "Aos domingos e feriados, a piscina funciona das 9h às 20h." in texto
    assert texto.startswith("## Capítulo IV: Piscina")
    for numero, titulo in outros:
        assert f"## Capítulo {numero}: {titulo}" not in texto
    assert "**Art. 20.**" not in texto
    assert "**Art. 29.**" not in texto


@pytest.mark.parametrize("referencia", ["XV", "0", "", "piscina", "Capítulo"])
def test_unknown_reference_returns_none(indice, referencia):
    assert indice.capitulo(referencia) is None


@pytest.mark.parametrize(("romano", "valor"), [("I", 1), ("IV", 4), ("IX", 9), ("XIV", 14), ("XL", 40)])
def test_roman_conversion(romano, valor):
    assert romano_para_int(romano) == valor
