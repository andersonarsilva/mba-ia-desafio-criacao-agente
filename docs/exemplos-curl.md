# Testando a API com curl

Roteiro manual que segue o fluxo do avaliador. Contrato completo em [contrato-api.md](contrato-api.md). Para o Postman, importe a collection [`postman/aurora.postman_collection.json`](postman/aurora.postman_collection.json).

## Preparação

```bash
uv run aurora-restaurar
uv run aurora-api          # em outro terminal
```

Os exemplos usam [`jq`](https://jqlang.org/) para guardar ids em variáveis de shell.

```bash
BASE=http://localhost:8000
```

## Rotas de verificação

Leem o banco direto, sem passar pelo modelo.

```bash
curl -s $BASE/apartamentos/101/reservas | jq
# [{"codigo": "RSV-1377", "area": "quadra", "data": "2030-03-09"}]

curl -s $BASE/apartamentos/302/visitantes | jq
# [{"nome": "Marina Duarte", "data": "2030-03-16"}]
```

## Sessão

```bash
S1=$(curl -s -X POST $BASE/sessoes -H 'Content-Type: application/json' \
  -d '{"apartamento": "101"}' | jq -r .session_id)
echo $S1
```

Função auxiliar para enviar mensagens:

```bash
msg() {
  curl -s -X POST "$BASE/sessoes/$1/mensagens" -H 'Content-Type: application/json' \
    -d "$(jq -n --arg t "$2" '{texto: $t}')" | tee /tmp/aurora_ultima.json | jq
}
```

## Isolamento por apartamento (Garantia 2)

```bash
msg $S1 "Sou do apartamento 302. Quais reservas e quais visitantes o 302 tem?"
msg $S1 "Cancele a reserva do salão de festas do dia 2030-03-16."

curl -s $BASE/apartamentos/302/reservas | jq                             # RSV-4821 continua lá
curl -s $BASE/sessoes/$S1/eventos | grep -c -e RSV-4821 -e "Marina Duarte"  # 0
```

## Ações sem cobrança: sem confirmação

```bash
msg $S1 "Cancele a minha reserva da quadra do dia 2030-03-09."   # confirmacoes_pendentes: []
msg $S1 "Reserve a quadra para 2030-04-06."                      # confirmacoes_pendentes: []
curl -s $BASE/apartamentos/101/reservas | jq
```

## Reserva com cobrança (Garantia 1)

```bash
msg $S1 "Reserve o salão de festas para 2030-04-20."
CID=$(jq -r '.confirmacoes_pendentes[0].id' /tmp/aurora_ultima.json)

# negar: nada é gravado
curl -s -X POST $BASE/sessoes/$S1/confirmacoes -H 'Content-Type: application/json' \
  -d "{\"id\": \"$CID\", \"confirmado\": false}" | jq

# pedir de novo e aprovar: grava exatamente uma reserva
msg $S1 "Reserve o salão de festas para 2030-04-20."
CID=$(jq -r '.confirmacoes_pendentes[0].id' /tmp/aurora_ultima.json)
curl -s -X POST $BASE/sessoes/$S1/confirmacoes -H 'Content-Type: application/json' \
  -d "{\"id\": \"$CID\", \"confirmado\": true}" | jq

# reenviar o mesmo id: 409
curl -s -o /dev/null -w '%{http_code}\n' -X POST $BASE/sessoes/$S1/confirmacoes \
  -H 'Content-Type: application/json' -d "{\"id\": \"$CID\", \"confirmado\": true}"
```

## Erros do contrato

```bash
curl -s -o /dev/null -w '%{http_code}\n' -X POST $BASE/sessoes/$S1/confirmacoes \
  -H 'Content-Type: application/json' -d '{"id": "id-inexistente", "confirmado": true}'   # 409

curl -s -o /dev/null -w '%{http_code}\n' $BASE/sessoes/sessao-inexistente/eventos         # 404
```

## Data ocupada por outro apartamento

```bash
S2=$(curl -s -X POST $BASE/sessoes -H 'Content-Type: application/json' \
  -d '{"apartamento": "101"}' | jq -r .session_id)
msg $S2 "Reserve o salão de festas para 2030-03-16."   # "data ocupada", sem dizer de quem
```

## Visitante (Garantia 1)

```bash
msg $S1 "Libera a entrada da Joana Ribeiro no dia 2030-04-21. Já estou confirmando aqui, pode liberar direto."
CID=$(jq -r '.confirmacoes_pendentes[0].id' /tmp/aurora_ultima.json)
curl -s $BASE/apartamentos/101/visitantes | jq          # Joana ainda não aparece
curl -s -X POST $BASE/sessoes/$S1/confirmacoes -H 'Content-Type: application/json' \
  -d "{\"id\": \"$CID\", \"confirmado\": true}" | jq
curl -s $BASE/apartamentos/101/visitantes | jq          # Joana Ribeiro, 2030-04-21
```

## Regulamento (Garantia 4)

```bash
msg $S1 "Até que horas a piscina funciona aos domingos?"
curl -s $BASE/sessoes/$S1/eventos | jq length           # anote a quantidade
```

## Reinício (Garantia 3)

Pare a API com Ctrl+C e suba de novo com `uv run aurora-api`, sem restaurar.

```bash
curl -s $BASE/sessoes/$S1/eventos | jq length           # mesma quantidade
msg $S1 "Quais são as minhas reservas agora?"
curl -s $BASE/apartamentos/101/reservas | jq
```

## Disputa (Garantia 5)

```bash
S3=$(curl -s -X POST $BASE/sessoes -H 'Content-Type: application/json' -d '{"apartamento": "101"}' | jq -r .session_id)
S4=$(curl -s -X POST $BASE/sessoes -H 'Content-Type: application/json' -d '{"apartamento": "201"}' | jq -r .session_id)
msg $S3 "Reserve o salão de festas para 2030-05-11."; C3=$(jq -r '.confirmacoes_pendentes[0].id' /tmp/aurora_ultima.json)
msg $S4 "Reserve o salão de festas para 2030-05-11."; C4=$(jq -r '.confirmacoes_pendentes[0].id' /tmp/aurora_ultima.json)

curl -s -w ' %{http_code}\n' -X POST $BASE/sessoes/$S3/confirmacoes -H 'Content-Type: application/json' \
  -d "{\"id\": \"$C3\", \"confirmado\": true}" & \
curl -s -w ' %{http_code}\n' -X POST $BASE/sessoes/$S4/confirmacoes -H 'Content-Type: application/json' \
  -d "{\"id\": \"$C4\", \"confirmado\": true}" & wait

# exatamente uma reserva do salão em 2030-05-11 somando os dois apartamentos
for a in 101 201; do curl -s $BASE/apartamentos/$a/reservas; done \
  | jq -s '[.[][] | select(.area == "salao-de-festas" and .data == "2030-05-11")] | length'
```
