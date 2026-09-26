# ADR-0005: Garantir exclusividade da reserva com índice único parcial e cancelamento lógico

| | |
|---|---|
| **Status** | Aceito |
| **Data** | 2026-09-26 |
| **Decisores** | Anderson Silva |
| **Área** | dados |
| **Relacionado** | ADR-0003, ADR-0004 |

## Contexto e problema

Cada área aceita no máximo uma reserva por data. Dois moradores podem aprovar a mesma área e data ao mesmo tempo (passo 14): uma vence, a outra recebe resposta normal, e nunca podem coexistir duas reservas ativas. Conferir a agenda antes de gravar não basta, porque a outra reserva pode entrar entre a conferência e a gravação.

Também: o código de uma reserva nova é gerado pelo sistema e nunca repete o de outra reserva, **inclusive cancelada** (passo 13 confere contra RSV-1377, RSV-4821 e RSV-2950).

## Critérios de decisão

- Exclusividade no instante da gravação, não numa checagem anterior
- Perdedor da disputa recebe resposta de negócio, não HTTP 500
- Códigos nunca reutilizados, mesmo após cancelamento e restauração

## Alternativas consideradas

### Opção A — Checagem + insert sob lock em memória (`asyncio.Lock` global)

- ✅ Simples
- ❌ A exclusividade vive no processo, não no dado; quebra com mais de um worker e não é o que o passo 15 pede

### Opção B — `UNIQUE(area, data)` e cancelamento por DELETE

- ✅ Exclusividade no banco
- ❌ Apagar a linha apaga o código; a unicidade de códigos passaria a depender de outro mecanismo

### Opção C — Índice único parcial `ON reservas(area, data) WHERE status = 'ativa'`, cancelamento lógico e `codigo UNIQUE`

- ✅ O banco rejeita a segunda reserva ativa no `INSERT`, sem janela de corrida
- ✅ Canceladas continuam na tabela, e `UNIQUE(codigo)` impede reutilização
- ❌ Consultas de agenda precisam filtrar `status = 'ativa'`

## Decisão

**Escolhemos a Opção C.**

- `reservar` faz `INSERT` direto; `sqlite3.IntegrityError` no índice parcial vira o resultado de negócio "data já ocupada", que a tool devolve ao modelo como resposta normal.
- A checagem prévia de disponibilidade existe só para evitar pedir confirmação de uma data já ocupada (passo 10); a garantia é o índice.
- Código = `RSV-` + 8 hexadecimais de `uuid4`, com retry em colisão de `codigo`. Não usa sequência, que reiniciaria após a restauração.

## Consequências

### Positivas
- Garantia 5 demonstrável num único trecho de SQL
- Histórico de reservas canceladas preservado

### Negativas e riscos aceitos
- Formato do código difere do `RSV-NNNN` inicial; o enunciado deixa o formato livre

### Ações decorrentes
- [ ] Teste de concorrência: N gravações simultâneas da mesma área/data resultam em exatamente 1 ativa
- [ ] Teste: código novo nunca coincide com código de reserva cancelada
