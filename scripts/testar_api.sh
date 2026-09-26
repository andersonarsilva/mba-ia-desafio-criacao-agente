#!/usr/bin/env bash
# Shell interativo para testar a API do Residencial Aurora sob demanda.
# Uso: ./scripts/testar_api.sh [--restaurar]
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BASE_URL="${AURORA_BASE_URL:-http://localhost:8000}"
API_LOG="$ROOT/var/testar_api.log"
API_PID=""

declare -A SESSION_APARTMENT=()
declare -A SESSION_PENDING=()
CURRENT_SESSION=""

bold() { printf '\033[1m%s\033[0m\n' "$*"; }
info() { printf '\033[36m%s\033[0m\n' "$*"; }
ok() { printf '\033[32m%s\033[0m\n' "$*"; }
warn() { printf '\033[33m%s\033[0m\n' "$*"; }
fail() { printf '\033[31m%s\033[0m\n' "$*"; }

ask() {
  local prompt="$1" default="${2:-}" answer
  if [[ -n "$default" ]]; then
    read -r -p "$prompt [$default]: " answer
    echo "${answer:-$default}"
  else
    read -r -p "$prompt: " answer
    echo "$answer"
  fi
}

confirm() {
  local answer
  read -r -p "$1 [s/N]: " answer
  [[ "$answer" =~ ^[sSyY]$ ]]
}

require_dependencies() {
  local missing=()
  for cmd in uv curl jq; do
    command -v "$cmd" >/dev/null 2>&1 || missing+=("$cmd")
  done
  if ((${#missing[@]})); then
    fail "Dependências ausentes: ${missing[*]}"
    exit 1
  fi
  if [[ ! -f "$ROOT/.env" ]]; then
    fail "Arquivo .env não encontrado. Rode: cp .env.example .env e preencha GOOGLE_API_KEY"
    exit 1
  fi
}

api_is_up() {
  curl -s -o /dev/null --max-time 2 "$BASE_URL/apartamentos/101/reservas"
}

start_api() {
  if api_is_up; then
    info "API já está respondendo em $BASE_URL (não foi iniciada por este script)."
    return
  fi
  mkdir -p "$ROOT/var"
  info "Subindo a API (log em ${API_LOG#"$ROOT"/})..."
  "$ROOT/.venv/bin/aurora-api" >>"$API_LOG" 2>&1 &
  API_PID=$!
  for _ in $(seq 1 60); do
    if api_is_up; then
      ok "API no ar em $BASE_URL (pid $API_PID)."
      return
    fi
    sleep 0.5
  done
  fail "A API não respondeu. Últimas linhas do log:"
  tail -n 20 "$API_LOG"
  exit 1
}

stop_api() {
  [[ -z "$API_PID" ]] && return
  info "Parando a API (pid $API_PID)..."
  kill -INT "$API_PID" 2>/dev/null
  wait "$API_PID" 2>/dev/null
  API_PID=""
}

restore_data() {
  (cd "$ROOT" && uv run --quiet aurora-restaurar)
  SESSION_APARTMENT=()
  SESSION_PENDING=()
  CURRENT_SESSION=""
}

prepare() {
  require_dependencies
  info "Sincronizando dependências..."
  (cd "$ROOT" && uv sync --quiet) || { fail "uv sync falhou"; exit 1; }
  if [[ "${1:-}" == "--restaurar" ]] || confirm "Restaurar os dados iniciais (apaga sessões e mudanças)?"; then
    if api_is_up && [[ -z "$API_PID" ]]; then
      warn "Há uma API rodando fora deste script; pare-a antes de restaurar."
    else
      restore_data
    fi
  fi
  start_api
}

print_http_result() {
  local status="$1" body="$2"
  if [[ "$status" =~ ^2 ]]; then ok "HTTP $status"; else warn "HTTP $status"; fi
  echo "$body" | jq . 2>/dev/null || echo "$body"
}

request() {
  local method="$1" path="$2" data="${3:-}" output status
  if [[ -n "$data" ]]; then
    output=$(curl -s -w '\n%{http_code}' -X "$method" "$BASE_URL$path" -H 'Content-Type: application/json' -d "$data")
  else
    output=$(curl -s -w '\n%{http_code}' -X "$method" "$BASE_URL$path")
  fi
  HTTP_STATUS="${output##*$'\n'}"
  HTTP_BODY="${output%$'\n'*}"
}

require_session() {
  if [[ -z "$CURRENT_SESSION" ]]; then
    warn "Nenhuma sessão ativa. Crie uma sessão primeiro (opção 1)."
    return 1
  fi
}

show_conversation_result() {
  local session="$1"
  if [[ "$HTTP_STATUS" != "200" ]]; then
    print_http_result "$HTTP_STATUS" "$HTTP_BODY"
    return
  fi
  SESSION_PENDING[$session]=$(echo "$HTTP_BODY" | jq -c '.confirmacoes_pendentes')
  local resposta
  resposta=$(echo "$HTTP_BODY" | jq -r '.resposta')
  bold "Assistente:"
  if [[ -n "$resposta" ]]; then echo "$resposta"; else info "(sem texto: execução aguardando confirmação)"; fi
  local count
  count=$(echo "${SESSION_PENDING[$session]}" | jq 'length')
  if ((count > 0)); then
    warn "Confirmações pendentes ($count) — responda pela opção 4:"
    echo "${SESSION_PENDING[$session]}" | jq -r '.[] | "  id=\(.id)\n  acao=\(.acao) detalhes=\(.detalhes | tojson)"'
  else
    info "Nenhuma confirmação pendente."
  fi
}

create_session() {
  local apartment
  apartment=$(ask "Apartamento" "101")
  request POST /sessoes "$(jq -n --arg a "$apartment" '{apartamento: $a}')"
  if [[ "$HTTP_STATUS" == "201" ]]; then
    CURRENT_SESSION=$(echo "$HTTP_BODY" | jq -r .session_id)
    SESSION_APARTMENT[$CURRENT_SESSION]="$apartment"
    SESSION_PENDING[$CURRENT_SESSION]="[]"
    ok "Sessão $CURRENT_SESSION criada para o apartamento $apartment e definida como ativa."
  else
    print_http_result "$HTTP_STATUS" "$HTTP_BODY"
  fi
}

switch_session() {
  if ((${#SESSION_APARTMENT[@]} == 0)); then
    warn "Nenhuma sessão criada ainda."
    return
  fi
  local ids=("${!SESSION_APARTMENT[@]}") i
  for i in "${!ids[@]}"; do
    printf '  %d) %s (apto %s)%s\n' "$((i + 1))" "${ids[$i]}" "${SESSION_APARTMENT[${ids[$i]}]}" \
      "$([[ "${ids[$i]}" == "$CURRENT_SESSION" ]] && echo ' ← ativa')"
  done
  echo "  Ou cole um session_id existente."
  local choice
  choice=$(ask "Escolha")
  if [[ "$choice" =~ ^[0-9]+$ ]] && ((choice >= 1 && choice <= ${#ids[@]})); then
    CURRENT_SESSION="${ids[$((choice - 1))]}"
  elif [[ -n "$choice" ]]; then
    CURRENT_SESSION="$choice"
    SESSION_APARTMENT[$CURRENT_SESSION]="${SESSION_APARTMENT[$CURRENT_SESSION]:-?}"
    SESSION_PENDING[$CURRENT_SESSION]="${SESSION_PENDING[$CURRENT_SESSION]:-[]}"
  fi
  ok "Sessão ativa: $CURRENT_SESSION"
}

send_message() {
  require_session || return
  local text
  text=$(ask "Mensagem para o assistente (apto ${SESSION_APARTMENT[$CURRENT_SESSION]})")
  [[ -z "$text" ]] && return
  info "Enviando... (pode levar alguns segundos)"
  request POST "/sessoes/$CURRENT_SESSION/mensagens" "$(jq -n --arg t "$text" '{texto: $t}')"
  show_conversation_result "$CURRENT_SESSION"
}

answer_confirmation() {
  require_session || return
  local pending="${SESSION_PENDING[$CURRENT_SESSION]:-[]}" count id
  count=$(echo "$pending" | jq 'length')
  if ((count > 0)); then
    echo "$pending" | jq -r 'to_entries[] | "  \(.key + 1)) \(.value.acao) \(.value.detalhes | tojson)\n     id=\(.value.id)"'
  else
    info "Nenhuma pendência conhecida na última resposta desta sessão."
  fi
  echo "  Digite o número, cole um id ou use um id qualquer para testar o 409."
  local choice
  choice=$(ask "Confirmação" "$([[ $count -gt 0 ]] && echo 1)")
  if [[ "$choice" =~ ^[0-9]+$ ]] && ((choice >= 1 && choice <= count)); then
    id=$(echo "$pending" | jq -r ".[$((choice - 1))].id")
  else
    id="$choice"
  fi
  [[ -z "$id" ]] && return
  local approved=false
  confirm "Aprovar (s) ou negar (N)?" && approved=true
  info "Enviando confirmacao=$approved para $id..."
  request POST "/sessoes/$CURRENT_SESSION/confirmacoes" "$(jq -n --arg id "$id" --argjson c "$approved" '{id: $id, confirmado: $c}')"
  if [[ "$HTTP_STATUS" == "409" ]]; then
    warn "HTTP 409: não existe confirmação pendente com esse id nesta sessão (nada foi executado)."
    return
  fi
  show_conversation_result "$CURRENT_SESSION"
}

show_events() {
  local session
  session=$(ask "Sessão" "${CURRENT_SESSION:-sessao-inexistente}")
  request GET "/sessoes/$session/eventos"
  if [[ "$HTTP_STATUS" != "200" ]]; then
    print_http_result "$HTTP_STATUS" "$HTTP_BODY"
    return
  fi
  ok "HTTP 200 — $(echo "$HTTP_BODY" | jq length) eventos"
  echo "$HTTP_BODY" | jq -r '.[] | "  [\(.author)] " + (
      [.content.parts[]? | if .text then "texto: \(.text | .[0:120])"
       elif .functionCall then "chamada: \(.functionCall.name) \(.functionCall.args | tojson | .[0:120])"
       elif .functionResponse then "resposta: \(.functionResponse.name) \(.functionResponse.response | tojson | .[0:120])"
       else empty end] | join(" | "))'
  local term
  term=$(ask "Procurar um termo nos eventos (ex.: RSV-4821, Enter para pular)" "")
  if [[ -n "$term" ]]; then
    local hits
    hits=$(echo "$HTTP_BODY" | grep -o -- "$term" | wc -l)
    if ((hits == 0)); then ok "'$term' não aparece nos eventos."; else warn "'$term' aparece $hits vez(es)."; fi
  fi
}

show_reservations() {
  local apartment
  apartment=$(ask "Apartamento" "${SESSION_APARTMENT[$CURRENT_SESSION]:-101}")
  request GET "/apartamentos/$apartment/reservas"
  print_http_result "$HTTP_STATUS" "$HTTP_BODY"
}

show_visitors() {
  local apartment
  apartment=$(ask "Apartamento" "${SESSION_APARTMENT[$CURRENT_SESSION]:-101}")
  request GET "/apartamentos/$apartment/visitantes"
  print_http_result "$HTTP_STATUS" "$HTTP_BODY"
}

first_pending_id() {
  echo "$1" | jq -r '.confirmacoes_pendentes[0].id // empty'
}

run_dispute() {
  local apt_a apt_b text
  apt_a=$(ask "Primeiro apartamento" "101")
  apt_b=$(ask "Segundo apartamento" "201")
  text=$(ask "Mensagem enviada nas duas sessões" "Reserve o salão de festas para 2030-05-11.")
  local sessions=() ids=() apt body
  for apt in "$apt_a" "$apt_b"; do
    request POST /sessoes "$(jq -n --arg a "$apt" '{apartamento: $a}')"
    [[ "$HTTP_STATUS" != "201" ]] && { print_http_result "$HTTP_STATUS" "$HTTP_BODY"; return; }
    local session
    session=$(echo "$HTTP_BODY" | jq -r .session_id)
    SESSION_APARTMENT[$session]="$apt"
    info "Apto $apt (sessão $session): enviando pedido..."
    request POST "/sessoes/$session/mensagens" "$(jq -n --arg t "$text" '{texto: $t}')"
    body="$HTTP_BODY"
    SESSION_PENDING[$session]=$(echo "$body" | jq -c '.confirmacoes_pendentes // []')
    local id
    id=$(first_pending_id "$body")
    if [[ -z "$id" ]]; then
      warn "Apto $apt não ficou com confirmação pendente:"
      print_http_result "$HTTP_STATUS" "$body"
      return
    fi
    sessions+=("$session")
    ids+=("$id")
  done
  info "Disparando as duas aprovações ao mesmo tempo..."
  local tmp
  tmp=$(mktemp -d)
  for i in 0 1; do
    curl -s -o "$tmp/body$i" -w '%{http_code}' -X POST "$BASE_URL/sessoes/${sessions[$i]}/confirmacoes" \
      -H 'Content-Type: application/json' -d "$(jq -n --arg id "${ids[$i]}" '{id: $id, confirmado: true}')" >"$tmp/status$i" &
  done
  wait
  for i in 0 1; do
    bold "Apto ${SESSION_APARTMENT[${sessions[$i]}]}: HTTP $(cat "$tmp/status$i")"
    jq -r '.resposta // .' "$tmp/body$i"
    SESSION_PENDING[${sessions[$i]}]=$(jq -c '.confirmacoes_pendentes // []' "$tmp/body$i")
  done
  rm -rf "$tmp"
  local area date total=0
  area=$(ask "Área para contar (id)" "salao-de-festas")
  date=$(ask "Data para contar" "2030-05-11")
  for apt in "$apt_a" "$apt_b"; do
    request GET "/apartamentos/$apt/reservas"
    total=$((total + $(echo "$HTTP_BODY" | jq --arg a "$area" --arg d "$date" '[.[] | select(.area == $a and .data == $d)] | length')))
  done
  if ((total == 1)); then ok "Exatamente 1 reserva de $area em $date somando $apt_a e $apt_b."; else fail "$total reservas de $area em $date (esperado: 1)."; fi
}

restart_api() {
  if [[ -z "$API_PID" ]]; then
    warn "A API não foi iniciada por este script; reinicie-a manualmente."
    return
  fi
  stop_api
  start_api
  ok "API reiniciada sem restaurar dados. Sessões continuam válidas."
}

restore_and_restart() {
  if [[ -z "$API_PID" ]] && api_is_up; then
    warn "A API não foi iniciada por este script; pare-a antes de restaurar."
    return
  fi
  confirm "Isso apaga todas as sessões e volta reservas e visitantes ao estado inicial. Continuar?" || return
  stop_api
  restore_data
  start_api
}

show_menu() {
  echo
  bold "=== Residencial Aurora — teste da API ($BASE_URL) ==="
  if [[ -n "$CURRENT_SESSION" ]]; then
    echo "Sessão ativa: $CURRENT_SESSION (apto ${SESSION_APARTMENT[$CURRENT_SESSION]:-?})"
  else
    echo "Sessão ativa: nenhuma"
  fi
  cat <<'MENU'
  1) Criar sessão
  2) Trocar sessão ativa
  3) Enviar mensagem ao assistente
  4) Responder confirmação pendente
  5) Ver eventos de uma sessão
  6) Ver reservas de um apartamento
  7) Ver visitantes de um apartamento
  8) Disputa: dois apartamentos aprovando ao mesmo tempo
  9) Reiniciar a API (sem restaurar)
 10) Restaurar dados e reiniciar a API
  0) Sair
MENU
}

main() {
  trap stop_api EXIT
  trap 'echo; exit 130' INT
  prepare "${1:-}"
  while true; do
    show_menu
    local option
    read -r -p "Opção: " option || break
    case "$option" in
      1) create_session ;;
      2) switch_session ;;
      3) send_message ;;
      4) answer_confirmation ;;
      5) show_events ;;
      6) show_reservations ;;
      7) show_visitors ;;
      8) run_dispute ;;
      9) restart_api ;;
      10) restore_and_restart ;;
      0) break ;;
      *) warn "Opção inválida." ;;
    esac
  done
}

main "$@"
