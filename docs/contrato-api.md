# Contrato da API

Base: `http://localhost:8000`. Todas as rotas recebem e devolvem JSON. Rotas com `{session_id}` respondem 404 quando a sessão não existe. Comportamentos que o enunciado deixa livres seguem o [ADR-0010](adr/0010-definir-comportamentos-livres-do-contrato-da-api.md).

## Conversa

### `POST /sessoes`

```json
{"apartamento": "101"}
```

| Status | Corpo |
|---|---|
| 201 | `{"session_id": "..."}` |
| 404 | Apartamento inexistente em `dados/apartamentos.json` |
| 422 | Corpo inválido |

### `POST /sessoes/{session_id}/mensagens`

```json
{"texto": "Quero reservar o salão de festas para 2030-04-20"}
```

| Status | Corpo |
|---|---|
| 200 | `RespostaConversa` |
| 404 | Sessão inexistente |
| 503 | Modelo indisponível após as tentativas (cota, timeout), sem detalhes internos |

`RespostaConversa`:

```json
{
  "resposta": "",
  "confirmacoes_pendentes": [
    {
      "id": "adk-9de1790a-41d7-423d-8dc6-1b61321e24c5",
      "acao": "reservar_area",
      "detalhes": {"area": "salao-de-festas", "data": "2030-04-20", "taxa": 150.0}
    }
  ]
}
```

- `resposta` concatena os textos finais dos agentes naquela execução e é `""` quando a execução parou esperando confirmação.
- `confirmacoes_pendentes` lista **todas** as pendências da sessão no momento da resposta.
- `acao` é o nome da tool: `reservar_area` ou `autorizar_visitante`.
- `detalhes` é o payload da confirmação: `{area, data, taxa}` ou `{nome, data}`.
- Uma nova mensagem com pendência aberta segue a conversa normalmente; a pendência continua listada e nada executa sem a rota de confirmações.

### `POST /sessoes/{session_id}/confirmacoes`

```json
{"id": "adk-9de1790a-...", "confirmado": true}
```

| Status | Corpo |
|---|---|
| 200 | `RespostaConversa` |
| 404 | Sessão inexistente |
| 409 | O id não é uma confirmação pendente **nesta** sessão (inexistente, já respondida ou de outra sessão). Nada é executado |
| 422 | Corpo inválido (`confirmado` precisa ser booleano) |
| 503 | Modelo indisponível |

### `GET /sessoes/{session_id}/eventos`

200 com a lista de todos os eventos da sessão, em ordem, no formato do ADK: `Event.model_dump(mode="json", by_alias=True, exclude_none=True)`, o mesmo do `adk api_server`. 404 se a sessão não existe.

## Verificação

Leem o banco direto, sem passar pelo modelo.

### `GET /apartamentos/{numero}/reservas`

200 com as reservas **ativas** do apartamento:

```json
[{"codigo": "RSV-1377", "area": "quadra", "data": "2030-03-09"}]
```

### `GET /apartamentos/{numero}/visitantes`

200 com os visitantes autorizados:

```json
[{"nome": "Marina Duarte", "data": "2030-03-16"}]
```

Apartamento inexistente devolve lista vazia.
