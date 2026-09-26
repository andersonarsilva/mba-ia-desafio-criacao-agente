# ADR-0010: Definir os comportamentos que o contrato da API deixa livres

| | |
|---|---|
| **Status** | Aceito |
| **Data** | 2026-09-26 |
| **Decisores** | Anderson Silva |
| **Área** | API |
| **Relacionado** | ADR-0003, ADR-0006, ADR-0009 |

## Contexto e problema

O contrato fixa rotas, campos e status principais, mas deixa livres alguns comportamentos: apartamento inexistente, nova mensagem com confirmação pendente, conteúdo de `acao` e `detalhes`, formato dos eventos e falhas do modelo. São decisões baratas de reverter, agrupadas aqui de propósito para que o README e o código tenham uma referência única.

## Critérios de decisão

- Nunca executar ação sem confirmação
- Respostas previsíveis para o avaliador e para quem lê os eventos
- Nenhum 500 genérico no fluxo avaliado

## Alternativas consideradas

| Ponto | Alternativas | Escolha |
|---|---|---|
| Apartamento inexistente em `POST /sessoes` | Aceitar (sessão órfã) · 404 | **404** com `{"detail": ...}` |
| Apartamento inexistente nas rotas de verificação | 404 · lista vazia | **Lista vazia** (200), leitura direta sem efeito |
| Nova mensagem com confirmação pendente | Recusar com 409 · seguir a conversa | **Seguir**: a pendência continua listada até a rota de confirmações; nada executa sem ela |
| `acao` | Texto livre · nome da tool | **Nome da tool**: `reservar_area`, `autorizar_visitante` |
| `detalhes` | Args brutos · payload da tool | **Payload**: `{area, data, taxa}` ou `{nome, data}` |
| `resposta` | Último texto · textos finais da execução | **Concatenação dos textos finais** dos agentes na execução; `""` quando pausada |
| `GET /eventos` | Formato próprio · formato do ADK | **`Event.model_dump(mode="json", by_alias=True, exclude_none=True)`**, o mesmo do `adk api_server` |
| Falha do modelo após retries | 500 · 503 JSON | **503** com `{"detail": ...}`, sem stacktrace |
| Entrada inválida | 422 padrão do FastAPI | **422** padrão |
| Endereço | `0.0.0.0` · `127.0.0.1` | **`127.0.0.1:8000`**, que atende a `localhost:8000` |

## Decisão

**Adotamos as escolhas da tabela.** Priorizamos previsibilidade e aderência ao formato nativo do ADK nos eventos.

## Consequências

### Positivas
- O contrato fica completo e documentado em `docs/contrato-api.md`

### Negativas e riscos aceitos
- API em `127.0.0.1` não é acessível de fora da máquina; aceitável para o desafio

### Ações decorrentes
- [x] Refletir a tabela em `docs/contrato-api.md`
