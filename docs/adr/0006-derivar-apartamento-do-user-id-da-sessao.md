# ADR-0006: Derivar o apartamento do user_id da sessão e nunca de parâmetro de tool

| | |
|---|---|
| **Status** | Aceito |
| **Data** | 2026-09-26 |
| **Decisores** | Anderson Silva |
| **Área** | segurança |
| **Relacionado** | ADR-0002, ADR-0010 |

## Contexto e problema

O apartamento é definido uma única vez, na criação da sessão, e representa o morador autenticado. Nada que o morador escreva ("sou do 302", "cancela a reserva dele") pode fazer o assistente alterar dados de outro apartamento ou trazê-los para a conversa. Isso vale para a resposta **e para os eventos** da sessão (passos 3, 4 e 10). Checar se uma data está livre exige olhar a agenda inteira, mas só "livre/ocupada" pode chegar à conversa.

O passo 15 confere que nenhuma tool aceita um apartamento escolhido pelo modelo sem validar contra o da sessão.

## Critérios de decisão

- Garantia independente do prompt e de qualquer texto do morador
- Impossibilidade estrutural de dado de terceiro entrar no contexto do modelo
- Fonte do apartamento imutável após a criação da sessão

## Alternativas consideradas

### Opção A — Tools com parâmetro `apartamento`, validado contra a sessão

- ✅ Assinatura explícita
- ❌ O modelo passa a "escolher" o apartamento; a validação vira o único ponto de defesa e induz o modelo a tentar

### Opção B — Apartamento no `state` da sessão

- ✅ Acessível via `tool_context.state`
- ❌ `state` é mutável por qualquer tool ou callback que gravar a chave; exige disciplina para não sobrescrever

### Opção C — `user_id` da sessão ADK = apartamento; tools sem parâmetro de apartamento

- ✅ `user_id` é parte da identidade da sessão no ADK e não muda depois da criação
- ✅ Nenhuma tool expõe `apartamento` ao modelo, então não há o que injetar
- ❌ Para buscar a sessão pelo id é preciso saber o `user_id`, o que exige um mapeamento `session_id → apartamento`

## Decisão

**Escolhemos a Opção C.**

- `POST /sessoes` cria a sessão com `user_id = apartamento` e grava `sessoes(session_id, apartamento)` em `condominio.db`. Esse mapeamento resolve o 404 e o `user_id` nas demais rotas.
- As tools obtêm o apartamento por `tool_context.user_id`, num único helper em `tools/contexto.py`.
- Consultas e escritas de reservas e visitantes filtram sempre pelo apartamento da sessão. `consultar_disponibilidade` retorna só `livre`/`ocupada`; cancelar reserva de outro apartamento resulta em "você não tem reserva nessa área e data", sem código nem dono.
- Prompts instruem a não mencionar outros apartamentos, como defesa extra, não como garantia.

## Consequências

### Positivas
- Dado de terceiro nunca entra no contexto, então não há o que vazar para resposta ou eventos
- Passo 15 verificável por inspeção das assinaturas das tools

### Negativas e riscos aceitos
- Um morador não consegue agir em nome de outro apartamento nem com justificativa legítima; aceito por requisito

### Ações decorrentes
- [x] Teste: nenhuma tool registrada declara parâmetro `apartamento`
- [x] Teste: tools com contexto do 101 nunca retornam RSV-4821 nem Marina Duarte
