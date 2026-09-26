# ADR-0001: Fixar google-adk 2.9.1 com Python 3.12 gerenciado por uv

| | |
|---|---|
| **Status** | Aceito |
| **Data** | 2026-09-26 |
| **Decisores** | Anderson Silva |
| **Área** | IA/agentes |
| **Relacionado** | ADR-0002, ADR-0003 |

## Contexto e problema

O desafio exige Python 3.12+, projeto gerenciado por `uv` (`pyproject.toml` e `uv.lock` versionados) e Google ADK na série 2, versão 2.2.0 ou mais nova, com a versão exata fixada. O avaliador confere a versão no passo 15.

Os autores do desafio relatam que o comportamento da retomada de confirmação mudou entre 2.2.0 e 2.9.1, conforme topologia, bloqueios de transferência, configuração de retomada do App e serviço de sessão. No momento da decisão, o PyPI publica até a 2.10.0. Escolher a versão é, na prática, escolher qual comportamento do roteamento de confirmação vamos suportar.

## Critérios de decisão

- Atender à restrição: série 2, ≥ 2.2.0, versão exata
- Confiabilidade da retomada de confirmação com sessão persistida (Garantia 1)
- Disponibilidade de serviço de sessão persistente sem dependência extra (Garantia 3)

## Alternativas consideradas

### Opção A — 2.2.0 (versão do curso)

- ✅ Alinhada ao material das aulas
- ❌ Versão mais antiga citada; os autores relatam comportamento diferente da 2.9.1 na retomada
- ❌ Perde correções do roteador de agentes e da validação de confirmações

### Opção B — 2.9.1

- ✅ Versão mais recente testada pelos autores do desafio
- ✅ Código-fonte verificado: `_agent_router.find_agent_to_run` roteia ao autor da chamada com App resumível; `request_confirmation.py` valida nome e args contra o histórico; `SqliteSessionService` nativo com `aiosqlite`
- ❌ Diverge do material do curso em detalhes de API

### Opção C — 2.10.0 (mais recente)

- ✅ Correções mais novas
- ❌ Nenhum relato de teste dos autores; risco de regressão desconhecida na parte mais frágil do desafio

## Decisão

**Escolhemos a Opção B (`google-adk==2.9.1`)**, com `requires-python >=3.12` e `.python-version` 3.12. Priorizamos a versão cujo comportamento de confirmação foi validado por terceiros e cujo código lemos. Abrimos mão da versão mais nova e da paridade exata com o curso.

## Consequências

### Positivas
- O roteamento de confirmação é conhecido e documentado a partir do código-fonte
- FastAPI, uvicorn, pydantic, python-dotenv, aiosqlite e httpx vêm como dependências transitivas; não há pacote novo

### Negativas e riscos aceitos
- Exemplos do curso na 2.2.0 podem precisar de ajuste

### Ações decorrentes
- [x] Fixar `google-adk==2.9.1` no `pyproject.toml` e gerar `uv.lock`
- [ ] Validar a retomada na 2.9.1 no spike W0.4
- [ ] Revisitar só se o spike falhar numa combinação que a 2.10.x corrija
