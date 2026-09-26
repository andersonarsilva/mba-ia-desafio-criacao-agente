# ADR-0012: Nomear o domínio em português e a infraestrutura em inglês

| | |
|---|---|
| **Status** | Aceito |
| **Data** | 2026-09-26 |
| **Decisores** | Anderson Silva |
| **Área** | API |
| **Relacionado** | — |

## Contexto e problema

A convenção padrão do autor é código em inglês, exceto quando o padrão do projeto for outro. Neste projeto, o contrato da API (`sessoes`, `texto`, `resposta`, `confirmacoes_pendentes`) e os dados (`numero`, `morador`, `codigo`, `area`, `data`) são obrigatoriamente em português. Os nomes das tools também são lidos pelo modelo e aparecem nos eventos.

## Critérios de decisão

- Linguagem ubíqua: o mesmo termo no contrato, nos dados, nas tools e no banco
- Aderência à convenção do autor onde o domínio não impõe
- Legibilidade para o avaliador

## Alternativas consideradas

### Opção A — Tudo em inglês, exceto campos obrigatórios

- ✅ Segue a convenção global
- ❌ Traduções entre camadas (`reservation` ↔ `reserva`) espalhadas pelo código e pelos eventos

### Opção B — Tudo em português

- ✅ Uniforme
- ❌ Contraria a convenção do autor sem necessidade

### Opção C — Domínio em português, infraestrutura em inglês

- ✅ Tools, tabelas, colunas, esquemas da API e módulos de domínio usam o vocabulário do enunciado
- ✅ Funções e variáveis de infraestrutura (`build_runner`, `get_connection`) seguem a convenção
- ❌ Fronteira precisa ser respeitada com critério

## Decisão

**Escolhemos a Opção C.** Regra: nome que o modelo, a API ou o banco expõem, ou que representa conceito do condomínio, fica em português; mecânica técnica fica em inglês. Documentação em português; mensagens de commit em inglês (Conventional Commits).

## Consequências

### Negativas e riscos aceitos
- Arquivos com identificadores dos dois idiomas

### Ações decorrentes
- [ ] Aplicar na estrutura `src/aurora/` do planejamento
