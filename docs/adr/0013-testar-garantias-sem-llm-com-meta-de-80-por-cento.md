# ADR-0013: Testar as garantias sem LLM com meta de 80% de cobertura e no máximo 2 workers

| | |
|---|---|
| **Status** | Aceito |
| **Data** | 2026-09-26 |
| **Decisores** | Anderson Silva |
| **Área** | infra |
| **Relacionado** | ADR-0005, ADR-0006, ADR-0007, ADR-0011 |

## Contexto e problema

O enunciado deixa testes automatizados fora do escopo da avaliação, mas as garantias precisam valer em todos os passos, e o comportamento do modelo varia entre execuções. A convenção do autor pede 80% de cobertura e testes sem serviços reais. A máquina é compartilhada por vários agentes: nenhuma execução de testes pode passar de 2 workers.

## Critérios de decisão

- Provar as partes determinísticas das garantias sem depender do modelo
- Não consumir cota do Gemini nem CPU além de 2 workers
- Validar o fluxo real do avaliador antes da entrega

## Alternativas consideradas

### Opção A — Só o script E2E

- ✅ Mínimo esforço, segue o enunciado à risca
- ❌ Regressões nas garantias só aparecem com chamadas reais ao modelo, que são lentas, custam cota e não são determinísticas

### Opção B — Testes só das garantias críticas

- ✅ Cobre o essencial
- ❌ Sem meta, rotas e bordas ficam descobertas

### Opção C — pytest sem LLM com meta de 80% em `src/`, mais o script E2E

- ✅ Repositório, concorrência, tools com `ToolContext` falso, rotas com runner falso, parser do regulamento
- ✅ E2E cobre o que depende do modelo
- ❌ `pytest-cov` como dependência nova de desenvolvimento

## Decisão

**Escolhemos a Opção C.**

- `pytest` + `pytest-asyncio` + `pytest-cov` no grupo `dev`. `pytest-cov` é justificado pela meta de cobertura e não entra na imagem de execução.
- Execução serial (1 processo) com `-p no:xdist` em `addopts`. Se `pytest-xdist` for adotado, fixar `-n 2`.
- Meta: 80% em statements e branches de `src/aurora`, medida por `uv run pytest --cov=aurora --cov-branch`.
- Testes em `tests/`, espelhando `src/aurora/`, sem chamadas ao Gemini (modelo e runner substituídos por fakes).
- `scripts/fluxo_avaliador.py` reproduz os passos 1–14 contra a API real e roda manualmente antes da entrega.

## Consequências

### Positivas
- Garantias 2, 4 e 5 e o 409 da Garantia 1 protegidos contra regressão sem custo de cota

### Negativas e riscos aceitos
- A retomada real da confirmação pelo modelo só é validada no E2E

### Ações decorrentes
- [x] Adicionar `pytest-cov` ao grupo `dev` na Wave 1
- [x] E2E executado 1× (passos 1–14 aprovados com `gemini-3.1-flash-lite`); as 3 execuções previstas foram reduzidas para preservar a cota do free tier, já que a suíte sem LLM reproduz o mesmo fluxo
