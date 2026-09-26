# ADR-0008: Restaurar dados e sessões por comando e semear no boot só banco inexistente

| | |
|---|---|
| **Status** | Aceito |
| **Data** | 2026-09-26 |
| **Decisores** | Anderson Silva |
| **Área** | dados |
| **Relacionado** | ADR-0004 |

## Contexto e problema

O enunciado exige um comando que volte reservas e visitantes ao estado de `dados/*.json`. Se ele também apaga as sessões é decisão nossa. O avaliador restaura no passo 1 e, no passo 13, reinicia a API **sem** restaurar, esperando que tudo continue lá.

## Critérios de decisão

- Passo 1 com estado inicial exato
- Passo 13 sem perda: o boot nunca pode re-semear dados existentes
- Consistência entre sessões e dados após a restauração

## Alternativas consideradas

### Opção A — Restaurar só reservas e visitantes

- ✅ Preserva histórico de conversas
- ❌ Sessões antigas mantêm confirmações pendentes e referências a reservas que deixaram de existir

### Opção B — Restaurar dados e apagar `var/sessions.db`

- ✅ Estado equivalente a um clone recém-baixado
- ❌ Conversas anteriores são descartadas

### Opção C — Semear sempre no boot

- ❌ Viola o passo 13

## Decisão

**Escolhemos a Opção B**, com boot conservador.

- `uv run aurora-restaurar` apaga `var/condominio.db` e `var/sessions.db`, recria o schema e carrega `dados/apartamentos.json`, `areas.json`, `reservas.json` (status `ativa`) e `visitantes.json`.
- O boot da API (`uv run aurora-api`) cria e semeia o banco só se `var/condominio.db` não existir. Se existir, só abre.

## Consequências

### Positivas
- O passo 1 funciona mesmo que o avaliador pule a restauração num clone limpo
- Reinício nunca altera dados

### Negativas e riscos aceitos
- Restaurar com a API rodando deixa conexões apontando para arquivos apagados; o README orienta parar a API antes

### Ações decorrentes
- [ ] Documentar a ordem no README: restaurar → subir
