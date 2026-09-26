# ADR-0003: Usar a confirmação nativa do ADK com App resumível e pendências derivadas dos eventos

| | |
|---|---|
| **Status** | Aceito |
| **Data** | 2026-09-26 |
| **Decisores** | Anderson Silva |
| **Área** | IA/agentes |
| **Relacionado** | ADR-0002, ADR-0004, ADR-0010, ADR-0011 |

## Contexto e problema

Toda ação que gera cobrança (reserva de área com taxa > 0) ou libera acesso (autorização de visitante) fica pendente até o morador responder por `POST /sessoes/{id}/confirmacoes`. A pendência aparece em `confirmacoes_pendentes` com os detalhes. Aprovar executa uma única vez; negar não muda nada. Qualquer id que não esteja pendente naquela sessão, inclusive um já respondido, recebe 409 sem executar nada. Texto como "já estou confirmando aqui" não pode valer como confirmação.

O curso mostra a confirmação só no `adk web`. Numa API própria precisamos descobrir como devolver a resposta e retomar a execução. O enunciado alerta para a falha silenciosa: a rota aceita, nada executa, porque a resposta não chegou ao agente que pediu.

## Critérios de decisão

- Confirmação vinda do sistema (rota HTTP), nunca do texto da conversa
- Execução única e 409 determinístico para ids não pendentes
- Sobreviver ao reinício da API com a pendência aberta
- Decisão de pedir confirmação tomada em código, não pelo modelo

## Alternativas consideradas

### Opção A — `FunctionTool(require_confirmation=True)` estático

- ✅ Menos código
- ❌ Pediria confirmação também para a quadra (taxa 0), o que viola "ação sem cobrança não pede confirmação"; `require_confirmation` callable resolveria, mas retornaria o erro genérico "rejected" ao negar, sem controle da mensagem

### Opção B — `tool_context.request_confirmation(payload=...)` dentro da tool, com App resumível

- ✅ A tool decide em código: taxa > 0 ou visitante → pede confirmação; taxa 0 → grava direto
- ✅ O `payload` carrega os `detalhes` do contrato; a pausa fica gravada nos eventos da sessão persistida
- ✅ Com `ResumabilityConfig(is_resumable=True)`, `find_agent_to_run` roteia a `FunctionResponse` ao autor da chamada original
- ❌ Depende do comportamento do roteador do ADK (mitigado pelo spike)

### Opção C — Registro próprio de ações pendentes, executadas pela rota sem passar pelo ADK

- ✅ Totalmente determinístico e independente do roteador
- ❌ Não usa o conceito de confirmação de tools exigido pelo desafio; a execução ficaria fora do fluxo do agente e dos eventos da sessão

## Decisão

**Escolhemos a Opção B.**

- As tools `reservar_area` e `autorizar_visitante` chamam `request_confirmation` na primeira execução e retornam "pendente". Na retomada, leem `tool_context.tool_confirmation`: `confirmed=False` retorna "não realizada" sem gravar; `confirmed=True` grava.
- O `App` usa `ResumabilityConfig(is_resumable=True)`.
- **Pendência** = chamada `adk_request_confirmation` na sessão sem `FunctionResponse` de mesmo id. Os eventos são a fonte única de verdade, persistida e reconstruída após o reinício sem tabela extra.
- `id` exposto = id da chamada `adk_request_confirmation`; `acao` = nome da tool original; `detalhes` = `payload`.
- A rota de confirmações verifica se o id está entre as pendências **daquela** sessão (senão 409) e envia ao Runner um `Content(role="user")` com `FunctionResponse(id=<id>, name="adk_request_confirmation", response={"confirmed": <bool>})`.
- Depois de respondido, o id deixa de ser pendente, e o reenvio recebe 409 por construção.

## Consequências

### Positivas
- Nenhum texto do morador consegue produzir a `FunctionResponse` de confirmação: ela só é criada pela rota
- Reinício não perde pendências nem respostas

### Negativas e riscos aceitos
- Retomada em modo resumível garante "pelo menos uma vez"; a gravação precisa ser idempotente por natureza (índice único do ADR-0005)
- Duas respostas simultâneas para a mesma confirmação estão fora de escopo; o lock por sessão (ADR-0011) as serializa mesmo assim

### Ações decorrentes
- [ ] Spike W0.4: aprovar, negar, reenviar e aprovar após reinício, com `SqliteSessionService`
- [ ] Registrar no spike se a retomada exige `invocation_id` explícito no `run_async`
- [ ] Plano B: se a retomada falhar, novo ADR adotando a Opção D do ADR-0002
