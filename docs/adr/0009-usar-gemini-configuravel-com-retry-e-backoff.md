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

### Opção C — Uma variável `AURORA_MODEL` para todos os agentes, com padrão `gemini-3.1-flash-lite`, e `HttpRetryOptions` do google-genai

- ✅ Uma chave e um nome de modelo no `.env`
- ✅ Retry com backoff exponencial em 429 e 5xx, sem código próprio
- ❌ Todos os agentes pagam o mesmo preço por token

## Decisão

**Escolhemos a Opção C.** `AURORA_MODEL` é opcional (padrão `gemini-3.1-flash-lite`); `GOOGLE_API_KEY` é obrigatória e validada no boot. `GOOGLE_GENAI_USE_VERTEXAI` fica fora do `.env.example`: ausente, o google-genai já usa a Gemini Developer API (AI Studio), que é o backend exigido; o boot força esse backend para que uma variável exportada no shell não desvie para o Vertex AI. Retry e timeout ficam juntos no `HttpOptions` passado em `client_kwargs` do modelo `Gemini`, porque o ADK substitui as próprias `http_options` pelas de `client_kwargs`. Falha persistente após os retries vira resposta de erro JSON da API (ADR-0010), sem stacktrace.

## Consequências

### Positivas
- O avaliador ajusta o modelo à própria cota editando só o `.env`

### Negativas e riscos aceitos
- Retries aumentam a latência de uma requisição sob throttling
- Modelo *lite* tem raciocínio mais simples; a regra continua em código, então um erro do modelo afeta a redação, não as garantias

### Ações decorrentes
- [x] W0.7: `gemini-2.5-flash` aparece na listagem de modelos, mas a chamada real (W4) respondeu 404 "no longer available to new users", recomendando `gemini-3.8-flash`. O `gemini-3.8-flash` funcionou (passos 1–9 do E2E), mas o free tier dele é de 5 RPM e 20 requisições/dia, insuficiente para as ~40–50 chamadas do fluxo. Padrão definido como `gemini-3.1-flash-lite`, que tem cota gratuita maior. Lições: disponibilidade só se confirma com uma chamada de geração, não pela listagem; e a cota diária do free tier é o fator decisivo na escolha do modelo padrão
- [ ] Documentar as variáveis no README
