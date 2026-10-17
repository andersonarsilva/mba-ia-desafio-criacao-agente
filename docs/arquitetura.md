# Arquitetura

Visão geral e responsabilidades de cada agente estão no [README](../README.md#arquitetura). Este documento detalha os fluxos e a organização do código. As decisões estão nos [ADRs](adr/README.md).

## Componentes

| Camada | Módulo | Responsabilidade |
|---|---|---|
| API | `src/aurora/api/main.py` | Rotas FastAPI, mapeamento de exceções para 404/409/503 |
| API | `src/aurora/api/conversa.py` | `ServicoConversa`: cria sessões, executa o Runner sob trava por sessão, valida confirmações |
| API | `src/aurora/api/confirmacoes.py` | Deriva pendências dos eventos; monta a `FunctionResponse` de confirmação |
| Agentes | `src/aurora/agentes/arvore.py` | Árvore de agentes e forma de acionamento |
| Agentes | `src/aurora/agentes/app.py` | `App` resumível, modelo Gemini com retry/timeout, `Runner` com `SqliteSessionService` |
| Agentes | `src/aurora/agentes/prompts/*.md` | Prompts versionados |
| Tools | `src/aurora/tools/` | Únicas portas de leitura e escrita de reservas e visitantes; apartamento sempre da sessão |
| Domínio | `src/aurora/dominio.py` | Entidades e validação de datas |
| Dados | `src/aurora/db/` | Schema, restauração, repositório com exclusividade no banco |
| Regulamento | `src/aurora/regulamento/indice.py` | Índice por capítulo de `dados/regulamento.md` |
| CLI | `src/aurora/cli.py` | `aurora-restaurar` e `aurora-api` |

## Fluxo de uma reserva com cobrança

```mermaid
sequenceDiagram
    autonumber
    actor M as Morador
    participant API as API
    participant R as Runner (App resumível)
    participant A as assistente_aurora
    participant RS as reservas
    participant DB as condominio.db
    participant S as sessions.db

    M->>API: POST /mensagens "Reserve o salão para 2030-04-20"
    API->>R: run_async(texto)
    R->>A: mensagem
    A->>RS: transfer_to_agent(reservas)
    RS->>DB: data_livre(salão, 2030-04-20)?
    RS->>R: request_confirmation(payload={area, data, taxa})
    R->>S: grava adk_request_confirmation e pausa
    API-->>M: 200 {resposta: "", confirmacoes_pendentes: [{id, acao, detalhes}]}

    M->>API: POST /confirmacoes {id, confirmado: true}
    API->>S: id está pendente nesta sessão? (sob trava da sessão)
    alt não pendente
        API-->>M: 409
    else pendente
        API->>R: FunctionResponse(adk_request_confirmation, id, confirmed=true)
        R->>RS: reexecuta reservar_area com tool_confirmation
        RS->>DB: INSERT (índice único parcial)
        alt data ocupada no instante da gravação
            DB-->>RS: IntegrityError
            RS-->>API: "indisponivel" (resposta normal)
        else gravou
            RS-->>API: "reservada" + código
        end
        API-->>M: 200 {resposta, confirmacoes_pendentes: []}
    end
```

## Fluxo de uma dúvida sobre o regulamento

```mermaid
sequenceDiagram
    actor M as Morador
    participant A as assistente_aurora
    participant AT as AgentTool (sessão em memória isolada)
    participant RG as regulamento
    participant S as sessions.db

    M->>A: "Até que horas a piscina funciona aos domingos?"
    A->>AT: regulamento(request=pergunta)
    AT->>RG: executa em sessão própria
    RG->>RG: ler_capitulo("IV")  ← só dentro da sessão isolada
    RG-->>AT: "Aos domingos, das 9h às 20h (Art. 22, II)"
    AT-->>A: resposta final
    A->>S: grava apenas a chamada e a resposta final
    A-->>M: resposta
```

## Validações realizadas

| Validação | Resultado | Registro |
|---|---|---|
| Spike de confirmação com reinício de processo | Aprovar e negar funcionam após reinício; reenvio sem a checagem da API reexecuta a tool | ADR-0003 |
| Spike de isolamento do `AgentTool` | Texto do capítulo ausente dos eventos da sessão pai | ADR-0002 |
| Spike de concorrência | Duas aprovações simultâneas, sempre 1 reserva ativa | ADR-0004 |
| Testes sem LLM (`uv run pytest`) | 88 testes, cobertura ≥ 80% | ADR-0013 |
| Fluxo do avaliador com Gemini real (`scripts/fluxo_avaliador.py`) | Passos 1–14 aprovados com `gemini-3.1-flash-lite` | ADR-0009 |
