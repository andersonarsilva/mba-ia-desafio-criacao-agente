# Architecture Decision Records

| ADR | Decisão | Área | Status |
|---|---|---|---|
| [0001](0001-fixar-google-adk-2-9-1-com-python-3-12-e-uv.md) | Fixar google-adk 2.9.1 com Python 3.12 gerenciado por uv | IA/agentes | Aceito |
| [0002](0002-usar-root-roteador-com-especialistas-por-transferencia-e-agenttool.md) | Agente principal roteador com especialistas por transferência e regulamento via AgentTool | IA/agentes | Aceito |
| [0003](0003-usar-confirmacao-nativa-do-adk-com-app-resumivel.md) | Confirmação nativa do ADK com App resumível e pendências derivadas dos eventos | IA/agentes | Aceito |
| [0004](0004-persistir-sessoes-e-dados-em-sqlite.md) | Persistir sessões e dados do condomínio em SQLite, em arquivos separados | dados | Aceito |
| [0005](0005-garantir-exclusividade-com-indice-unico-parcial.md) | Exclusividade da reserva com índice único parcial e cancelamento lógico | dados | Aceito |
| [0006](0006-derivar-apartamento-do-user-id-da-sessao.md) | Apartamento derivado do user_id da sessão, nunca de parâmetro de tool | segurança | Aceito |
| [0007](0007-consultar-regulamento-por-capitulo-sem-rag-vetorial.md) | Regulamento consultado por capítulo em especialista isolado, sem RAG vetorial | IA/agentes | Aceito |
| [0008](0008-restaurar-dados-e-sessoes-e-semear-so-banco-novo.md) | Restauração de dados e sessões; boot semeia só banco inexistente | dados | Aceito |
| [0009](0009-usar-gemini-configuravel-com-retry-e-backoff.md) | Modelo Gemini configurável por ambiente com retry e backoff | IA/agentes | Aceito |
| [0010](0010-definir-comportamentos-livres-do-contrato-da-api.md) | Comportamentos que o contrato da API deixa livres | API | Aceito |
| [0011](0011-executar-em-processo-unico-com-lock-por-sessao.md) | Processo único com lock por sessão | API | Aceito |
| [0012](0012-nomear-dominio-em-portugues-e-infraestrutura-em-ingles.md) | Domínio em português, infraestrutura em inglês | API | Aceito |
| [0013](0013-testar-garantias-sem-llm-com-meta-de-80-por-cento.md) | Testes sem LLM, meta de 80%, no máximo 2 workers | infra | Aceito |
