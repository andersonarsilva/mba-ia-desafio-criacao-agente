# ADR-0004: Persistir sessões e dados do condomínio em SQLite, em arquivos separados

| | |
|---|---|
| **Status** | Aceito |
| **Data** | 2026-09-26 |
| **Decisores** | Anderson Silva |
| **Área** | dados |
| **Relacionado** | ADR-0005, ADR-0008 |

## Contexto e problema

Reiniciar a API não pode apagar conversas nem dados (Garantia 3). Os arquivos de `dados/` são o estado inicial e não podem ser alterados, então as mudanças precisam de outro armazenamento. O armazenamento é livre, mas qualquer serviço externo precisa subir com um comando documentado. A disputa do passo 14 exige exclusividade no instante da gravação (Garantia 5) e escrita concorrente sem erro de servidor.

## Critérios de decisão

- Setup do avaliador com o menor número de passos
- Exclusividade garantida pelo próprio armazenamento
- Suporte nativo do ADK para persistir sessões
- Nenhuma dependência nova sem justificativa

## Alternativas consideradas

### Opção A — PostgreSQL em container

- ✅ Concorrência robusta; `DatabaseSessionService` do ADK suporta
- ❌ Exige Docker e um comando extra; mais um ponto de falha no passo 1
- ❌ Exige driver e SQLAlchemy (extra `all` do ADK), ou seja, dependências novas

### Opção B — Arquivos JSON próprios em `var/`

- ✅ Trivial
- ❌ Sem atomicidade nem exclusividade na gravação; teria de ser reimplementada com locks de arquivo

### Opção C — SQLite: `var/sessions.db` via `SqliteSessionService` e `var/condominio.db` para os dados

- ✅ Zero serviço externo; `aiosqlite` já vem com o ADK
- ✅ Índices únicos parciais e transações garantem exclusividade no instante da gravação
- ✅ Arquivos separados evitam que a escrita de eventos concorra pelo mesmo lock da escrita de reservas
- ❌ Um escritor por arquivo por vez; carga alta geraria `database is locked`

## Decisão

**Escolhemos a Opção C**, com `journal_mode=WAL` e `busy_timeout` no banco de dados do condomínio. Os bancos ficam em `var/`, que não é versionado. Para o volume do desafio (dezenas de requisições), um escritor por vez é suficiente. Abrimos mão de escala horizontal em troca de setup zero.

## Consequências

### Positivas
- `uv sync` + restaurar + subir: nenhum container
- A exclusividade é uma restrição do banco, não uma checagem em código

### Negativas e riscos aceitos
- Não escala para múltiplas instâncias da API; aceitável fora de produção
- Contenção no `sessions.db` sob escrita simultânea de duas sessões (passo 14)

### Ações decorrentes
- [ ] Spike W0.6: duas sessões gravando em paralelo no `SqliteSessionService`; se houver lock, configurar WAL/busy_timeout nele também
- [ ] Revisitar (PostgreSQL) se a API precisar de mais de um processo
