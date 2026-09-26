# ADR-0007: Consultar o regulamento por capítulo em especialista isolado, sem RAG vetorial

| | |
|---|---|
| **Status** | Aceito |
| **Data** | 2026-09-26 |
| **Decisores** | Anderson Silva |
| **Área** | IA/agentes |
| **Relacionado** | ADR-0002 |

## Contexto e problema

O regulamento (`dados/regulamento.md`, ~44 KB, 14 capítulos marcados por `## Capítulo`) é longo. Se o texto inteiro entrar no histórico, ele acompanha todas as chamadas seguintes e encarece cada uma. O requisito tem três partes:

1. responder com base no regulamento (passo 12: piscina aos domingos fecha às 20h, Capítulo IV, Art. 22, II);
2. **nenhum evento da sessão** pode conter trechos de capítulos que tratam de outros assuntos;
3. o agente principal não recebe o regulamento nas instruções.

O tema é isolamento de contexto e custo de tokens, não qualidade de busca semântica.

## Critérios de decisão

- Nenhum trecho de outro capítulo nos eventos persistidos, por construção
- Determinismo da recuperação
- Custo de tokens por pergunta e cota do Gemini
- Nenhuma infraestrutura ou dependência nova

## Alternativas consideradas

### Opção A — Regulamento nas instruções de um especialista por transferência

- ✅ Simples
- ❌ O texto não entra nos eventos, mas é reenviado inteiro a cada chamada do especialista; não atende ao espírito de "consultado, não carregado"

### Opção B — RAG vetorial (chunks + embeddings + top-k)

- ✅ Padrão para bases grandes e sem estrutura
- ❌ Chunks de tamanho fixo atravessam o limite entre capítulos; top-k pode trazer "Silêncio" junto com "Piscina" (ambos tratam de domingos) e violar o item 2
- ❌ Chamadas de embedding consomem cota; exige índice e dependências novas
- ❌ Recuperação não determinística

### Opção C — Capítulo como unidade de recuperação + especialista em `AgentTool` isolado

- ✅ O índice é a estrutura do próprio documento: parse por `## Capítulo`, determinístico
- ✅ Duas barreiras: a tool devolve um capítulo só, e o `AgentTool` roda numa sessão em memória separada, então nem esse capítulo entra nos eventos da sessão do morador
- ✅ Zero dependência nova
- ❌ Uma pergunta que atravesse capítulos exige mais de uma leitura pelo especialista

## Decisão

**Escolhemos a Opção C.**

- `regulamento/indice.py` parseia o arquivo por capítulo (número romano, título, texto) em memória no boot. Só lê `dados/`, nunca escreve.
- O especialista `regulamento` tem nas instruções apenas o sumário (números e títulos) e a tool `ler_capitulo(capitulo)`, que devolve um único capítulo.
- O root o aciona via `AgentTool`. Na sessão persistida ficam só a chamada com a pergunta e a resposta final curta.
- O prompt do especialista exige resposta objetiva à pergunta, sem citar outros capítulos. A resposta final é a única saída que entra nos eventos.

## Consequências

### Positivas
- Garantia 4 por mecanismo, não por instrução
- Custo por pergunta limitado a um capítulo mais o sumário

### Negativas e riscos aceitos
- Se o especialista escolher o capítulo errado, a resposta sai errada, mas nada vaza
- A resposta final do especialista entra nos eventos; ela é o único vetor residual, coberto por prompt e por teste E2E

### Ações decorrentes
- [x] Teste: `ler_capitulo("IV")` não contém texto de nenhum outro capítulo
- [x] Teste: prompt do root não contém texto do regulamento
- [x] E2E W4.3: varrer `GET /eventos` por trechos de outros capítulos
- [ ] Revisitar (busca vetorial) só se o regulamento perder a estrutura por capítulos ou crescer além de um capítulo por chamada
