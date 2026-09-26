# Planejamento de entrega — Assistente do Residencial Aurora

Objetivo: entregar **exatamente** o que o desafio exige, com as cinco garantias implementadas em código e verificáveis pelo fluxo do avaliador (passos 1–15). Nada além disso entra no escopo.

## 1. Análise do desafio

### 1.1 O que será avaliado

| Bloco | O que o avaliador confere | Onde falha na prática |
|---|---|---|
| Execução | `uv sync`, restauração, API em `localhost:8000`, `dados/` intacto, sem chaves | ADK não fixado exato; escrita acidental em `dados/` |
| Arquitetura | Agente principal + ≥ 2 especialistas; dados só via tools | Especialista "de fachada" sem responsabilidade própria |
| G1 Confirmação | Pendência em `confirmacoes_pendentes`; aprovar executa 1×; negar não muda nada; 409 para id não pendente/reenviado | **Retomada silenciosa**: rota aceita, ação não executa (resposta não chega ao agente autor) |
| G2 Apartamento | Nada do 302 em respostas **nem em eventos** da sessão do 101 | Tool que aceita `apartamento` como parâmetro; tool de disponibilidade que devolve o dono |
| G3 Reinício | Mesmos eventos após restart; nova mensagem funciona; dados e códigos preservados | Sessão em memória; reseed no boot; código reiniciando sequência |
| G4 Regulamento | Resposta correta (piscina domingo: **20h**); nenhum evento com trecho de outro capítulo; root sem regulamento | Tool que devolve o arquivo inteiro; subagente rodando na mesma sessão |
| G5 Concorrência | Duas aprovações simultâneas → ambas 200, exatamente 1 reserva | Check-then-insert; `database is locked` virando 500 |
| Contrato/README | Rotas, campos, status; README com Arquitetura/Garantias/Como rodar apontando trechos reais | Referência de linha desatualizada no README |

### 1.2 Dados relevantes

- Áreas: `salao-de-festas` (150,00), `churrasqueira` (80,00) → **exigem confirmação**; `quadra` (0) → **sem confirmação**.
- Reservas iniciais: `RSV-1377` (101, quadra, 2030-03-09), `RSV-4821` (302, salão, 2030-03-16), `RSV-2950` (201, churrasqueira, 2030-03-23).
- Visitantes iniciais: Marina Duarte (302), Paulo Nogueira (201).
- Regulamento: 14 capítulos `## Capítulo …` (~44 KB). Piscina = Capítulo IV (Art. 22, II: domingos e feriados 9h–20h).

### 1.3 Evidências do código-fonte do ADK (2.9.1) que definem o desenho

| Evidência | Consequência no projeto |
|---|---|
| `agents/_agent_router.py::find_agent_to_run` — com `ResumabilityConfig(is_resumable=True)` a resposta de função é roteada ao **autor** da chamada correspondente; sem isso, cai no "último agente transferível" | App **resumível** e especialistas que pedem confirmação como `sub_agents` (transferência), nunca dentro de `AgentTool` |
| `flows/llm_flows/request_confirmation.py` — ignora confirmação cuja chamada original foi feita por outro agente; valida nome e args contra o histórico | A `FunctionResponse` de `adk_request_confirmation` precisa chegar ao especialista autor; não podemos alterar args |
| `tools/agent_tool.py::AgentTool.run_async` — roda o subagente com `InMemorySessionService` próprio | Regulamento via `AgentTool` explícito: o capítulo lido nunca entra nos eventos da sessão principal |
| `_SingleTurnAgentTool` (`mode='single_turn'`) usa `run_node` na **mesma sessão** | Não usar `mode='single_turn'` para o especialista de regulamento |
| `sessions/sqlite_session_service.py` nativo, dependência `aiosqlite` já inclusa | Sessão persistida em SQLite sem serviço externo nem dependência nova |
| `ToolContext.request_confirmation(hint, payload)` e `tool_context.tool_confirmation` | Confirmação **condicional decidida em código** (taxa > 0) dentro da tool |

## 2. Decisões de arquitetura (viram ADRs em `docs/adr/`)

| ADR | Decisão | Motivo |
|---|---|---|
| 0001 | ADK fixado em `google-adk==2.9.1`; Python 3.12; `uv` | Versão testada pelos autores do desafio; série 2 ≥ 2.2.0 |
| 0002 | Topologia: `assistente_aurora` (root, só roteia) → `sub_agents=[reservas, visitantes]` por transferência; `regulamento` via `AgentTool` | Confirmação exige que o especialista seja autor da chamada na sessão persistida; regulamento precisa de isolamento de contexto |
| 0003 | Confirmação nativa do ADK (`request_confirmation`) + `App(resumability_config=is_resumable=True)`; pendências derivadas dos eventos da sessão; rota de confirmação envia `FunctionResponse(name="adk_request_confirmation", id=<id>, response={"confirmed": bool})` | Confirmação vem do sistema (rota), não do texto; pendência = chamada sem resposta nos eventos (fonte única de verdade, sobrevive ao restart) |
| 0004 | Persistência em SQLite: `var/sessions.db` (SqliteSessionService) e `var/condominio.db` (dados), WAL + `busy_timeout` | Zero serviço externo; arquivos separados reduzem contenção de lock |
| 0005 | Exclusividade por índice único parcial `UNIQUE(area, data) WHERE status='ativa'`; cancelamento lógico; código `RSV-<hex>` com `UNIQUE` em todas as linhas | Exclusividade no instante da gravação; códigos de canceladas nunca reutilizados |
| 0006 | Apartamento = `user_id` da sessão ADK (imutável), gravado só em `POST /sessoes`; nenhuma tool recebe `apartamento` | G2 independe do prompt |
| 0007 | Regulamento indexado por capítulo; tool `ler_capitulo(capitulo)` devolve **um** capítulo; especialista isolado em `AgentTool` devolve só a resposta | G4 por construção, com duas barreiras |
| 0008 | Restauração recria `condominio.db` a partir de `dados/*.json` e apaga `sessions.db`; boot só semeia se o banco não existir | Estado limpo e previsível; restart nunca re-semeia |
| 0009 | Modelo Gemini configurável por env (`AURORA_MODEL`, padrão `gemini-3.1-flash-lite`), retry com backoff em 429/5xx via `HttpRetryOptions` | Limites do AI Studio mudam; o fluxo faz dezenas de chamadas |
| 0010 | Pontos livres do contrato: apto inexistente → 404 na criação; nova mensagem com pendência segue a conversa; `acao` = nome da tool; `detalhes` = payload; eventos no formato do ADK; falha do modelo → 503; `127.0.0.1:8000` | Previsibilidade e nenhum 500 genérico |
| 0011 | Processo uvicorn único com `asyncio.Lock` por sessão | Checagem de 409 e retomada atômicas por sessão, sem serializar sessões diferentes |
| 0012 | Domínio em português (tools, tabelas, API), infraestrutura em inglês | Linguagem ubíqua com o contrato e `dados/` |
| 0013 | pytest sem LLM, meta de 80% em `src/aurora`, serial (≤ 2 workers), mais script E2E | Garantias protegidas sem gastar cota |

Índice completo em [`docs/adr/README.md`](adr/README.md). Todas as decisões estão fechadas; os spikes da Wave 0 só validam as decisões 0002–0004 e, se falharem, geram um ADR substituto.

## 3. Desenho da solução

### 3.1 Agentes e tools

```
assistente_aurora (root, LlmAgent)       instrução: roteamento + políticas; SEM regulamento
├── tools: [AgentTool(regulamento)]      isolado, só a resposta volta
├── sub_agent: reservas (LlmAgent)
│     listar_areas()                     sem confirmação
│     consultar_disponibilidade(area, data) → "livre" | "ocupada" (nunca o dono)
│     listar_minhas_reservas()           filtra pelo apartamento da sessão
│     reservar_area(area, data)          taxa > 0 → request_confirmation; taxa 0 → grava direto
│     cancelar_reserva(area, data)       só do próprio apartamento, sem confirmação
└── sub_agent: visitantes (LlmAgent)
      listar_meus_visitantes()
      autorizar_visitante(nome, data)    sempre request_confirmation
regulamento (LlmAgent, fora da árvore)   instrução contém só o sumário de capítulos
      ler_capitulo(capitulo)             devolve um único capítulo
```

Regras-chave em código (não no prompt):

- `apartamento = tool_context.user_id` em todas as tools.
- `reservar_area`: 1ª chamada sem `tool_confirmation` → valida área/data, verifica disponibilidade (sem dono), se taxa > 0 chama `request_confirmation(payload={area, data, taxa})` e retorna pendente. 2ª chamada (retomada) → `confirmed=False` retorna "não realizada"; `confirmed=True` faz `INSERT` e trata `IntegrityError` como "data já ocupada" (resposta normal, G5).
- `autorizar_visitante`: mesmo padrão, sempre com confirmação.

### 3.2 API (FastAPI)

| Rota | Implementação |
|---|---|
| `POST /sessoes` | `create_session(app, user_id=apartamento)`; grava `sessoes(session_id, apartamento)` em `condominio.db` para resolver o `user_id` depois → 201 |
| `POST /sessoes/{id}/mensagens` | 404 se não existe; lock por sessão; `runner.run_async`; `resposta` = textos finais dos agentes da execução; `confirmacoes_pendentes` derivadas dos eventos |
| `POST /sessoes/{id}/confirmacoes` | 404/409 (id ∉ pendentes da sessão); envia `FunctionResponse` de `adk_request_confirmation`; mesmo formato de saída |
| `GET /sessoes/{id}/eventos` | `event.model_dump(mode="json", by_alias=True, exclude_none=True)` em ordem |
| `GET /apartamentos/{n}/reservas` | reservas **ativas**: `codigo, area, data` |
| `GET /apartamentos/{n}/visitantes` | `nome, data` |

Pendência: `adk_request_confirmation` sem `FunctionResponse` de mesmo id nos eventos. `acao` = nome da tool original; `detalhes` = `payload` (`area`, `data` / `nome`, `data`).

### 3.3 Estrutura de pastas

```
pyproject.toml, uv.lock, .env.example, README.md
src/aurora/
  config.py                     env validado no boot
  db/ schema.sql, conexao.py, seed.py (restauração), repositorio.py
  regulamento/ indice.py        parser por capítulo
  agentes/ root.py, reservas.py, visitantes.py, regulamento.py, app.py
  agentes/prompts/*.md          prompts versionados
  tools/ reservas.py, visitantes.py, regulamento.py, contexto.py
  api/ main.py, rotas.py, esquemas.py, confirmacoes.py, eventos.py
  cli.py                        aurora-api / aurora-restaurar
tests/                          espelha src/ (pytest, sem LLM)
scripts/fluxo_avaliador.py      E2E dos passos 1–14 contra a API real
docs/ planejamento.md, arquitetura.md, contrato-api.md, adr/000N-*.md
var/                            (gitignored) sessions.db, condominio.db
```

Comandos finais: `uv run aurora-restaurar` e `uv run aurora-api` (uvicorn em `localhost:8000`).

## 4. Waves e tasks

Regras de execução: cada task fecha com commit atômico (Conventional Commits, padrão do histórico) na branch `develop`; `docs/desafio.md` nunca é commitado; testes rodam com **no máximo 2 workers** (pytest serial por padrão; se `pytest-xdist` for usado, `-n 2` fixo em `addopts`); testes nunca chamam o Gemini.

### Wave 0 — Fundação e spike de risco (bloqueante)

| ID | Task | Pronto quando |
|---|---|---|
| W0.1 | Instalar `uv` (pré-requisito da máquina, fora do repo) | `uv --version` ok ✅ feito |
| W0.2 | `.gitignore` (`docs/desafio.md`, `.claude/`, `var/`, `.env`) | `git status` não lista `desafio.md` ✅ feito |
| W0.3 | `uv init` com `requires-python>=3.12`, `google-adk==2.9.1`, `.env.example` (`GOOGLE_API_KEY`, `AURORA_MODEL`) | `uv sync` sem erro; `uv.lock` gerado ✅ feito |
| W0.4 | ✅ **Spike confirmação**: root + 1 sub_agent com tool que chama `request_confirmation`, `SqliteSessionService`, App resumível. Cenários: aprovar, negar, reenviar, **aprovar após reiniciar o processo** | Tool executa exatamente 1× em todos os cenários; matriz resumível on/off registrada |
| W0.5 | ✅ **Spike isolamento**: `AgentTool(regulamento)` — confirmar que eventos da sessão pai só têm `function_call`/`function_response` com a resposta final | Nenhum texto do capítulo nos eventos pai |
| W0.6 | ✅ **Spike concorrência**: 2 sessões gravando em paralelo no `SqliteSessionService` | Sem `database is locked`; se houver, aplicar WAL/busy_timeout |
| W0.7 | Confirmar com uma chamada real o modelo padrão (`gemini-3.1-flash-lite`; o `gemini-2.5-flash` foi recusado para contas novas e o `gemini-3.8-flash` tem só 20 requisições/dia no free tier) | ADR-0009 validado ✅ feito |
| W0.8 | Registrar os ADRs 0001–0013 e atualizar 0002–0004 com o resultado dos spikes | ✅ ADRs escritos e atualizados com os spikes |

Saída da wave: risco nº 1 (retomada silenciosa) eliminado antes de escrever o produto. Se W0.4 falhar, plano B documentado no ADR-0003: tools-folha de confirmação no root (autor único), mantendo especialistas para leitura/negócio.

### Wave 1 — Domínio e persistência (sem LLM)

| ID | Task | Pronto quando |
|---|---|---|
| W1.1 | `config.py`: env validado no boot (pydantic), caminhos `var/` | Boot falha claro sem `GOOGLE_API_KEY` |
| W1.2 | `schema.sql`: `apartamentos`, `areas`, `reservas(status, UNIQUE codigo, índice único parcial)`, `visitantes`, `sessoes` | Schema idempotente |
| W1.3 | `seed.py` + `aurora-restaurar`: recria `condominio.db` de `dados/*.json`, apaga `sessions.db` | Rotas mostram RSV-1377 e Marina Duarte |
| W1.4 | `repositorio.py`: disponibilidade (bool), listar por apto, reservar atômico, cancelar lógico por apto, autorizar visitante | Testes unitários passando |
| W1.5 | Gerador de código `RSV-<8 hex>` com retry em colisão | Teste de unicidade inclusive contra canceladas |
| W1.6 | `regulamento/indice.py`: parse por `## Capítulo`, busca por número/título | "piscina" → só Capítulo IV |
| W1.7 | Adicionar `pytest-cov` ao grupo `dev`; testes: concorrência (N inserts simultâneos → 1 vence), isolamento por apto, parser | `uv run pytest` verde, serial (≤ 2 workers) |

### Wave 2 — Agentes e tools

| ID | Task | Pronto quando |
|---|---|---|
| W2.1 | `tools/contexto.py`: apartamento a partir de `tool_context.user_id` | Nenhuma assinatura de tool com `apartamento` |
| W2.2 | Tools de reservas (seção 3.1) com confirmação condicional por taxa | Testes com `ToolContext` fake: taxa 0 grava, taxa > 0 pede confirmação, negado não grava |
| W2.3 | Tools de visitantes com confirmação obrigatória | Idem |
| W2.4 | Tool `ler_capitulo` + agente regulamento em `AgentTool` | Teste: retorno contém só o capítulo pedido |
| W2.5 | Prompts em `agentes/prompts/*.md`; root sem regulamento; instrução de não revelar dados de terceiros | Teste que garante que o prompt do root não contém texto do regulamento |
| W2.6 | `app.py`: `App` resumível + `Runner` + `SqliteSessionService` + retry do genai | Conversa ponta a ponta via script local |

### Wave 3 — API

| ID | Task | Pronto quando |
|---|---|---|
| W3.1 | Esquemas pydantic do contrato (entrada validada) | Campos idênticos ao enunciado |
| W3.2 | `POST /sessoes`, `GET /eventos`, rotas de verificação | 201/200/404 conforme contrato |
| W3.3 | `POST /mensagens`: lock por sessão, extração de `resposta`, pendências | Resposta vazia quando pausada |
| W3.4 | `POST /confirmacoes`: 409 para id fora das pendências da sessão; retomada no agente autor | Aprovar 1×; reenvio 409; `id-inexistente` 409 |
| W3.5 | Tratamento de erro: falha do LLM → JSON de erro, sem stacktrace; logs JSON sem PII/chave | Nenhum 500 genérico no fluxo feliz |
| W3.6 | `aurora-api` (uvicorn `127.0.0.1:8000`), init do banco no boot sem re-seed | Restart preserva tudo |
| W3.7 | Testes de rota com runner mockado (409/404/formato) | Verde, ≤ 2 workers |

### Wave 4 — Validação E2E (fluxo do avaliador)

| ID | Task | Pronto quando |
|---|---|---|
| W4.1 ✅ | `scripts/fluxo_avaliador.py` (httpx) com asserts dos passos 1–14, pausa para restart manual no 13, aprovações simultâneas no 14 | Script verde |
| W4.2 ✅ | Executar o fluxo em clone limpo | 1/1 verde com `gemini-3.1-flash-lite` (execuções limitadas para economizar cota do free tier; as garantias são cobertas sem LLM pela suíte `tests/api/test_fluxo.py`) |
| W4.3 ✅ | Varredura de vazamento: `grep` de `RSV-4821`, `Marina Duarte`, trechos de outros capítulos em `GET /eventos` | Zero ocorrências |
| W4.4 ✅ | Endurecimento de prompts apenas onde o E2E falhar (redação), nunca movendo regra para o prompt | Sem regressão |

### Wave 5 — Documentação e entrega

| ID | Task | Pronto quando |
|---|---|---|
| W5.1 | `README.md` substituindo o enunciado: **Arquitetura**, **Garantias** (arquivo + trecho + por que não depende do modelo), **Como rodar** | Toda referência aponta para código existente |
| W5.2 | `docs/arquitetura.md` (diagramas Mermaid: componentes, sequência de confirmação), `docs/contrato-api.md` (inclui ADR-0010), revisão final dos ADRs | Docs completos |
| W5.3 | Checklist do passo 15: `git diff --exit-code be87e1d -- dados/`, `secrets scan`, versão ADK exata no `uv.lock` | Tudo ok |
| W5.4 | Clone limpo → `.env` → `uv sync` → restaurar → subir → fluxo E2E | Verde |
| W5.5 | Merge `develop` → `main`, push, confirmar fork **público** | Link do fork entregue |

## 5. Rastreabilidade: passo do avaliador → garantia → task

| Passo | Verificação | Garantia | Tasks |
|---|---|---|---|
| 1 | Setup + dados iniciais | Execução | W0.3, W1.3, W3.6 |
| 2 | 201 na criação | Contrato | W3.2 |
| 3 | Sem RSV-4821/Marina ao pedir dados do 302 | G2 | W2.1, W1.4 |
| 4 | Cancelar reserva do 302 não afeta nem vaza | G2 | W1.4, W2.2 |
| 5 | Cancela a própria, sem confirmação | Regra 4 | W2.2 |
| 6 | Quadra sem confirmação | G1 | W2.2 |
| 7 | Salão → pendente com área/data; negar não grava | G1 | W2.2, W3.4 |
| 8 | Aprovar grava 1×; reenvio 409 | G1 | W3.4, W0.4 |
| 9 | `id-inexistente` 409; sessão inexistente 404 | Contrato | W3.2, W3.4 |
| 10 | Data do 302 ocupada, sem vazar dono | G2 | W1.4, W2.2, W2.5 |
| 11 | Visitante pendente mesmo com "já confirmo" | G1 | W2.3 |
| 12 | Piscina 20h; eventos sem outros capítulos | G4 | W1.6, W2.4 |
| 13 | Restart preserva eventos, dados e códigos | G3 | W0.4, W1.5, W3.6 |
| 14 | Aprovações simultâneas → 200/200 e 1 reserva | G5 | W0.6, W1.4, W1.7 |
| 15 | Revisão do repositório | Todas | W5.x |

## 6. Riscos e mitigação

| Risco | Prob. | Impacto | Mitigação |
|---|---|---|---|
| Retomada da confirmação não chega ao agente autor | Alta | Crítico | Spike W0.4 com restart; App resumível; especialistas em `sub_agents`; teste E2E após restart |
| Cota do Gemini (429) no meio do fluxo | Média | Alto | Retry com backoff; modelo configurável; E2E espaçado |
| `database is locked` na disputa do passo 14 | Média | Alto | WAL + busy_timeout; bancos separados; spike W0.6 |
| LLM vaza dado de terceiro | Baixa | Crítico | Tools nunca retornam dados de outro apto (impossível vazar o que não entra no contexto) |
| Capítulo errado/múltiplos no regulamento | Média | Alto | `ler_capitulo` devolve um só; `AgentTool` isolado |
| LLM "confirma" pelo texto | Baixa | Crítico | Confirmação só via `FunctionResponse` enviada pela rota |
| README com referência quebrada | Média | Médio | Revisão final W5.1/W5.3 após último commit de código |
| `dados/` alterado | Baixa | Crítico | Código só lê `dados/`; verificação por `git diff` |

## 7. Definition of Done

- [ ] Todos os critérios de aceite do enunciado marcados.
- [ ] `scripts/fluxo_avaliador.py` verde 3× em clone limpo, incluindo restart e disputa.
- [ ] `uv run pytest --cov=aurora --cov-branch` verde, ≥ 80%, serial (≤ 2 workers), sem chamadas reais ao LLM.
- [ ] `dados/` idêntico ao commit base; nenhuma chave versionada; `docs/desafio.md` fora do Git.
- [ ] README com as três seções e referências válidas; `docs/` com arquitetura, contrato e ADRs.
- [ ] Tudo em `main` no fork público.
