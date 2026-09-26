# ADR-0002: Usar agente principal roteador com especialistas por transferência e regulamento via AgentTool

| | |
|---|---|
| **Status** | Aceito |
| **Data** | 2026-09-26 |
| **Decisores** | Anderson Silva |
| **Área** | IA/agentes |
| **Relacionado** | ADR-0003, ADR-0006, ADR-0007 |

## Contexto e problema

O morador fala com um agente principal que distribui o trabalho entre no mínimo dois especialistas. Reservas e visitantes são lidos e gravados só por tools. Quantos especialistas criar e como cada um é acionado (transferência, `AgentTool`, modo `single_turn`) é decisão nossa e precisa estar justificada no README.

A forma de acionar tem efeitos que não são estéticos no ADK 2.9.1:

- A retomada de uma confirmação só executa a tool se a resposta chegar ao **agente autor** da chamada original (`flows/llm_flows/request_confirmation.py` ignora confirmações de outro autor).
- `AgentTool` explícito roda o subagente num `InMemorySessionService` próprio (`tools/agent_tool.py`): eventos internos não chegam à sessão persistida.
- Subagente com `mode='single_turn'` roda via `run_node` na **mesma** sessão.

## Critérios de decisão

- Retomada de confirmação funcionando com sessão persistida e após reinício (Garantia 1 e 3)
- Isolamento de contexto do regulamento (Garantia 4)
- Especialistas com responsabilidade real e fronteira clara de tools

## Alternativas consideradas

### Opção A — Todos os especialistas como `AgentTool`

- ✅ Root mantém o controle da conversa; contexto isolado para todos
- ❌ Confirmação pedida dentro do `AgentTool` fica na sessão em memória do subagente: some no reinício e a rota de confirmações não tem como retomá-la

### Opção B — Todos como `sub_agents` por transferência

- ✅ Confirmação é autorada pelo especialista na sessão persistida; o roteador do Runner a devolve a ele
- ❌ As tool responses do regulamento entrariam nos eventos da sessão, dependendo só do recorte da tool para cumprir a Garantia 4

### Opção C — Híbrido: reservas e visitantes por transferência; regulamento via `AgentTool`

- ✅ Cada mecanismo usado onde sua propriedade é necessária: persistência da pausa para quem pede confirmação, isolamento para quem lê o regulamento
- ❌ Duas formas de acionamento para explicar e testar

### Opção D — Tools de escrita no root, especialistas só consultivos

- ✅ Autor da confirmação é sempre o root; roteamento trivial
- ❌ Esvazia os especialistas; mantida só como plano B se o spike W0.4 falhar

## Decisão

**Escolhemos a Opção C.**

| Agente | Responsabilidade | Acionamento | Tools |
|---|---|---|---|
| `assistente_aurora` (root) | Entender a intenção e encaminhar; não acessa dados nem regulamento | Recebe toda mensagem | `AgentTool(regulamento)` |
| `reservas` | Consultar disponibilidade, listar, reservar e cancelar reservas do próprio apartamento | Transferência (`sub_agents`) | `listar_areas`, `consultar_disponibilidade`, `listar_minhas_reservas`, `reservar_area`, `cancelar_reserva` |
| `visitantes` | Listar e autorizar visitantes do próprio apartamento | Transferência (`sub_agents`) | `listar_meus_visitantes`, `autorizar_visitante` |
| `regulamento` | Responder dúvidas lendo um capítulo por vez | `AgentTool` explícito, fora da árvore de `sub_agents` | `ler_capitulo` |

Os especialistas por transferência podem voltar ao root (transferência ao pai permitida), para que a mensagem seguinte sobre outro assunto seja reencaminhada. Prompts ficam em arquivos `.md` versionados em `src/aurora/agentes/prompts/`.

## Consequências

### Positivas
- Garantias 1 e 4 apoiadas no mecanismo de acionamento, não em instrução ao modelo
- Fronteira de tools por especialista reduz a superfície de erro de cada um

### Negativas e riscos aceitos
- Uma transferência custa uma chamada extra ao modelo por mensagem que muda de assunto
- O comportamento depende do roteador do ADK 2.9.1 (ADR-0001)

### Ações decorrentes
- [ ] Spike W0.4: pausa e retomada no especialista com `SqliteSessionService` e reinício de processo
- [ ] Spike W0.5: confirmar que eventos do `AgentTool` não aparecem na sessão pai
- [ ] Se W0.4 falhar, registrar novo ADR adotando a Opção D
