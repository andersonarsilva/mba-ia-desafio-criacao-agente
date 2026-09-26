# ADR-0009: Usar modelo Gemini configurável por ambiente com retry e backoff

| | |
|---|---|
| **Status** | Aceito |
| **Data** | 2026-09-26 |
| **Decisores** | Anderson Silva |
| **Área** | IA/agentes |
| **Relacionado** | ADR-0010 |

## Contexto e problema

Os modelos são Gemini com chave do Google AI Studio. Os modelos disponíveis e os limites de requisição (RPM/RPD) mudam com frequência e variam por projeto. O fluxo do avaliador faz algumas dezenas de chamadas; um 429 no meio do fluxo reprova o passo.

## Critérios de decisão

- Trocar de modelo sem mudar código
- Tolerância a 429/5xx transitórios
- Qualidade suficiente de roteamento e tool calling

## Alternativas consideradas

### Opção A — Modelo fixo no código, sem retry

- ❌ Qualquer mudança de cota ou descontinuação exige commit; 429 derruba o passo

### Opção B — Um modelo por agente, cada um em uma variável

- ✅ Otimização fina de custo
- ❌ Mais configuração para o avaliador sem ganho relevante nesta escala

### Opção C — Uma variável `AURORA_MODEL` para todos os agentes, com padrão `gemini-2.5-flash`, e `HttpRetryOptions` do google-genai

- ✅ Uma chave e um nome de modelo no `.env`
- ✅ Retry com backoff exponencial em 429 e 5xx, sem código próprio
- ❌ Todos os agentes pagam o mesmo preço por token

## Decisão

**Escolhemos a Opção C.** `AURORA_MODEL` é opcional (padrão `gemini-2.5-flash`); `GOOGLE_API_KEY` é obrigatória e validada no boot; `GOOGLE_GENAI_USE_VERTEXAI=FALSE`. O retry fica nas `http_options` do `generate_content_config` de cada agente. Falha persistente após os retries vira resposta de erro JSON da API (ADR-0010), sem stacktrace.

## Consequências

### Positivas
- O avaliador ajusta o modelo à própria cota editando só o `.env`

### Negativas e riscos aceitos
- Retries aumentam a latência de uma requisição sob throttling

### Ações decorrentes
- [ ] Confirmar no AI Studio que `gemini-2.5-flash` está disponível na conta antes do E2E
- [ ] Documentar as variáveis no README
