import re
from dataclasses import dataclass
from pathlib import Path

CABECALHO_CAPITULO = re.compile(r"^## Capítulo ([IVXLC]+): (.+)$", re.MULTILINE)
ROMANOS = {"I": 1, "V": 5, "X": 10, "L": 50, "C": 100}


def romano_para_int(romano: str) -> int:
    total = 0
    for atual, seguinte in zip(romano, romano[1:] + " "):
        valor = ROMANOS[atual]
        total += -valor if ROMANOS.get(seguinte, 0) > valor else valor
    return total


@dataclass(frozen=True)
class Capitulo:
    numero: str
    titulo: str
    texto: str


class IndiceRegulamento:
    def __init__(self, capitulos: list[Capitulo]) -> None:
        self._capitulos = capitulos
        self._por_numero = {romano_para_int(c.numero): c for c in capitulos}

    @classmethod
    def carregar(cls, caminho: Path) -> "IndiceRegulamento":
        conteudo = caminho.read_text(encoding="utf-8")
        cabecalhos = list(CABECALHO_CAPITULO.finditer(conteudo))
        fins = [c.start() for c in cabecalhos[1:]] + [len(conteudo)]
        capitulos = [
            Capitulo(
                numero=cabecalho.group(1),
                titulo=cabecalho.group(2).strip(),
                texto=conteudo[cabecalho.start() : fim].strip(),
            )
            for cabecalho, fim in zip(cabecalhos, fins)
        ]
        return cls(capitulos)

    def sumario(self) -> list[tuple[str, str]]:
        return [(c.numero, c.titulo) for c in self._capitulos]

    def capitulo(self, referencia: str) -> Capitulo | None:
        chave = referencia.strip().upper().removeprefix("CAPÍTULO").strip()
        if chave.isdigit():
            return self._por_numero.get(int(chave))
        if chave and all(letra in ROMANOS for letra in chave):
            return self._por_numero.get(romano_para_int(chave))
        return None
