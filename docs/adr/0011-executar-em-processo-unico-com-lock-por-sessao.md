# ADR-0011: Executar a API em processo único com lock por sessão

| | |
|---|---|
| **Status** | Aceito |
| **Data** | 2026-09-26 |
| **Decisores** | Anderson Silva |
| **Área** | API |
| **Relacionado** | ADR-0003, ADR-0004, ADR-0005 |

## Contexto e problema

Duas requisições na **mesma** sessão ao mesmo tempo (mensagem + confirmação, ou confirmação duplicada) poderiam intercalar execuções do Runner sobre o mesmo histórico: a checagem "id está pendente" e o envio da resposta formam uma janela de corrida. Requisições em sessões **diferentes** (passo 14) precisam rodar em paralelo e responder 200.

## Critérios de decisão

- Execuções do Runner serializadas por sessão
- Paralelismo entre sessões diferentes
- Sem infraestrutura extra

## Alternativas consideradas

### Opção A — Sem controle

- ❌ Checagem de pendência e retomada podem se intercalar

### Opção B — Lock global

- ❌ Serializa o passo 14 inteiro; a disputa deixaria de ser simultânea e esconderia o teste da Garantia 5

### Opção C — `asyncio.Lock` por `session_id`, uvicorn com 1 worker

- ✅ Serializa só o que compartilha histórico
- ✅ A exclusividade de reservas continua no banco (ADR-0005), independente do lock
- ❌ Lock em memória não vale entre processos

## Decisão

**Escolhemos a Opção C.** A API sobe com um único processo uvicorn. Cada rota que executa o Runner (`mensagens`, `confirmacoes`) adquire o lock da sessão antes de ler as pendências e só o libera após o fim da execução.

## Consequências

### Positivas
- A checagem de 409 e a retomada ficam atômicas por sessão

### Negativas e riscos aceitos
- Escalar para vários workers exigiria lock distribuído; fora de escopo (ADR-0004)

### Ações decorrentes
- [x] Teste: duas confirmações simultâneas do mesmo id resultam em uma execução e um 409
