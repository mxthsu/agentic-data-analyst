# SPEC-001 — Agentic Data Analyst

**Status:** Pronta
**Data:** 2026-10-06
**Escopo:** Desafio Técnico 1 — Engenheiro(a) de IA (Pleno)

## 1. Problema e objetivo

A diretoria precisa obter respostas de negócio sem depender de SQL escrito manualmente para cada pergunta. A solução deve receber uma pergunta em português, investigar o SQLite fornecido e responder como um analista júnior: interpretar a intenção, planejar a investigação, consultar os dados, lidar com incerteza e erros e apresentar uma conclusão com dados, visualização e transparência operacional.

O sistema não será apenas um tradutor de linguagem natural para SQL. Perguntas podem exigir múltiplas consultas, avaliação da evidência disponível e correção automática de consultas inválidas.

## 2. Requisitos do desafio

| ID | Requisito |
| --- | --- |
| REQ-001 | O backend Python recebe uma pergunta e retorna uma resposta baseada no SQLite. |
| REQ-002 | Esquema, colunas e relações são descobertos dinamicamente em tempo de execução. |
| REQ-003 | Perguntas complexas podem gerar múltiplas consultas e etapas intermediárias. |
| REQ-004 | SQL inválido ou erro recuperável segue para correção automática com limite de tentativas. |
| REQ-005 | O agente avalia se os resultados atuais são suficientes antes de responder. |
| REQ-006 | A resposta final usa linguagem de negócio e somente evidências produzidas na execução. |
| REQ-007 | A visualização é escolhida conforme os dados e a intenção: indicador, tabela, barras ou linha. |
| REQ-008 | A interface mostra etapas operacionais e consultas executadas sem expor raciocínio interno do modelo. |
| REQ-009 | Perguntas sem suporte nos dados retornam uma limitação ou pedido de esclarecimento, sem invenção. |

## 3. Arquitetura

```text
Streamlit
    |
    v
FastAPI
    |
    v
LangGraph
    |
    +-- descoberta do esquema
    +-- interpretação da pergunta
    +-- contexto temporal determinístico
    +-- plano de investigação
    +-- geração / validação / execução SQL
    +-- avaliação de evidência
    +-- recuperação
    +-- síntese baseada em evidências
    +-- política de visualização
    |
    v
SQLite somente leitura
```

**Tecnologias principais:** Python 3.12, LangGraph, LangChain, Google AI Studio / Gemini API, FastAPI, SQLite, sqlglot, Streamlit, Pydantic e pytest.

LangGraph controla estado e transições. LangChain fornece a abstração de modelo e a saída estruturada. Segurança, limites e execução SQL permanecem determinísticos.

## 4. Estado e fluxo do agente

### Estado

`AgentState` mantém apenas informações necessárias à execução:

- pergunta e identificador da execução;
- esquema;
- intenção estruturada;
- plano de investigação;
- SQL atual;
- tentativas e resultados;
- erros e suposições;
- rastro operacional;
- resposta e visualização finais.

O estado não armazena raciocínio interno do modelo.

### Fluxo

```text
discover_schema
      ↓
interpret_question
      ↓
resolve_temporal_context
      ↓
plan_investigation
      ↓
generate_sql
      ↓
validate_sql
   ↙         ↘
repair     execute_sql
   ↑            ↓
   └── erro ────┘
                ↓
        assess_evidence
        ↙             ↘
   more_data       sufficient
      ↓                ↓
 generate_sql       synthesize
                         ↓
                  visualization
```

Os nomes acima são identificadores de implementação. A documentação e a interface permanecem em português.

### Contratos dos nós

| Nó | Responsabilidade |
| --- | --- |
| `discover_schema` | Ler tabelas, colunas, chaves estrangeiras e cobertura temporal. |
| `interpret_question` | Estruturar objetivo, métrica, dimensões, filtros e ambiguidade. |
| `resolve_temporal_context` | Inferir período quando houver uma única interpretação segura ou pedir esclarecimento. |
| `plan_investigation` | Definir os passos necessários para responder. |
| `generate_sql` | Produzir a próxima consulta a partir do plano e das evidências. |
| `validate_sql` | Aplicar a política determinística de SQL. |
| `execute_sql` | Executar consulta válida no SQLite somente leitura. |
| `assess_evidence` | Decidir se deve consultar novamente, responder ou encerrar. |
| `repair_sql` | Corrigir uma consulta inválida usando SQL, erro e esquema. |
| `synthesize_answer` | Produzir a resposta executiva baseada nas evidências. |
| `select_visualization` | Selecionar uma visualização compatível com o resultado. |

## 5. Regras e limites

### Semântica de negócio

- “clientes” significa clientes distintos quando a pergunta não indicar contagem de eventos;
- mês sem ano usa o único ano disponível na fonte relevante e registra a suposição; se houver mais de um ano plausível, pede esclarecimento;
- “último ano” usa os 12 meses-calendário até o mês da maior data disponível da fonte relevante;
- rankings usam ordenação secundária determinística e sinalizam empates que afetem o corte solicitado.

### Segurança de SQL

A execução usa defesa em profundidade:

1. SQLite em `mode=ro`;
2. `PRAGMA query_only=ON`;
3. análise e validação estrutural com `sqlglot`;
4. somente uma consulta de leitura por etapa;
5. autorizador do SQLite;
6. limite de tempo e limite de linhas;
7. toda correção passa novamente pela validação.

### Limites padrão

- até 4 consultas executadas por pergunta;
- até 2 reparos de SQL;
- até 12 passos no ciclo investigativo; pré e pós-processamentos determinísticos não consomem esse orçamento;
- limite de 5 segundos por consulta;
- até 500 linhas por consulta;
- modelo padrão `gemini-3.5-flash-lite`;
- até 6 chamadas ao Gemini por minuto, por processo, configurável conforme o limite ativo do projeto;
- timeout de 30 segundos por chamada ao modelo;
- sem retries automáticos agressivos do SDK;
- até 1.024 tokens de saída por chamada.

## 6. Fundamentação, privacidade e rastro de execução

O modelo recebe apenas o esquema, a pergunta, as evidências necessárias e erros sanitizados. Dados pessoais, como nome e e-mail, não entram no contexto quando não forem necessários.

A resposta final pode usar um modelo de linguagem para transformar evidência tabular em linguagem executiva, mas não pode introduzir métricas ausentes nos resultados.

Cada execução possui `trace_id`. O rastro registra nó, estado, duração, SQL, quantidade de linhas, suposições e categoria de erro quando aplicável.

## 7. Testes e avaliações

A validação separa comportamento determinístico da qualidade do modelo:

- **unitários:** descoberta do esquema, proteção de SQL, política temporal, visualização e roteamento;
- **integração:** SQLite real em modo somente leitura, múltiplas etapas e ciclo de reparo com modelo simulado;
- **avaliações de referência:** perguntas do enunciado comparadas com SQL independente;
- **adversariais:** tentativa de escrita, múltiplas instruções, coluna inexistente, pergunta impossível e limite de execução esgotado;
- **ponta a ponta com modelo real:** conjunto pequeno executado manualmente, fora do CI obrigatório.

Perguntas mínimas de referência:

1. cinco estados com maior número de clientes que compraram via App em maio;
2. clientes que interagiram com campanhas de WhatsApp em 2024;
3. categorias com maior média de compras por cliente;
4. reclamações não resolvidas por canal;
5. tendência de reclamações por canal no último ano disponível.

## 8. Critérios de aceite e entregáveis

| Critério | Evidência esperada |
| --- | --- |
| AC-001 | Avaliações de referência compatíveis com SQL independente. |
| AC-002 | Uma coluna nova aparece no esquema sem alteração de código. |
| AC-003 | Um caso de múltiplas etapas percorre mais de um ciclo de consulta. |
| AC-004 | SQL inválido entra no caminho de reparo e conclui após correção válida. |
| AC-005 | Operações fora da política de leitura não alteram o banco. |
| AC-006 | Ambiguidade temporal gera suposição explícita ou pedido de esclarecimento. |
| AC-007 | Indicador, tabela, barras e linha são escolhidos corretamente. |
| AC-008 | A interface mostra resposta, dados e rastro operacional. |
| AC-009 | Falhas do modelo ou do banco são tratadas de forma controlada. |
| AC-010 | Execução ponta a ponta com modelo real é registrada antes de marcar a SPEC como validada. |

Entregáveis finais: repositório público no GitHub, README em português com instruções de execução e arquitetura, exemplos testados, melhorias futuras e um documento curto com a arquitetura proposta para o Desafio 2.

## 9. Fora do escopo e decisões abertas

Ficam fora do escopo: autenticação, múltiplos locatários, memória persistente, banco vetorial, RAG, filas, Redis e infraestrutura distribuída.

Decisões ainda abertas para a implementação:

1. uso de atalho determinístico em `assess_evidence` para resultados simples, caso os testes mostrem ganho real;
2. observabilidade externa permanece opcional.

**Provider decidido:** Google AI Studio / Gemini API, com `gemini-3.5-flash-lite` como modelo padrão da validação gratuita. A integração permanece isolada em `model_provider.py` para permitir troca futura sem alterar o grafo.

**Marco concluído:** SPEC promovida de rascunho para pronta após revisão e aceite explícito em 2026-10-06.
