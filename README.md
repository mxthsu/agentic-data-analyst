# Agentic Data Analyst

Implementação do Desafio Técnico 1 para Engenheiro(a) de IA (Pleno): um assistente que recebe perguntas de negócio em linguagem natural, investiga um banco SQLite e devolve uma resposta fundamentada nos dados.

## O que a solução faz

- descobre tabelas, colunas, chaves estrangeiras e cobertura temporal em tempo de execução;
- interpreta a pergunta e cria um plano de investigação;
- gera SQL dinamicamente, sem consultas de negócio fixas na aplicação;
- valida e executa SQL somente leitura;
- corrige consultas inválidas com número limitado de tentativas;
- pode executar mais de uma consulta antes de responder;
- trata ambiguidades temporais de forma explícita;
- escolhe indicador, tabela, barras ou linha de forma determinística;
- expõe consultas, etapas, erros e duração no rastro operacional;
- disponibiliza uma API FastAPI e uma interface Streamlit.

## Arquitetura

```text
Streamlit
   |
   v
FastAPI
   |
   v
LangGraph
   |
   +--> descoberta do esquema
   +--> interpretação + contexto temporal
   +--> planejamento
   +--> geração SQL
   +--> validação -----> reparo
   +--> execução ------> reparo
   +--> avaliação de evidência
   |       |
   |       +--> nova consulta
   |       +--> esclarecimento
   |       +--> resposta
   |
   +--> síntese + visualização
   |
   v
SQLite somente leitura
```

O modelo de linguagem lida com interpretação, planejamento, geração, reparo, avaliação de evidência e síntese. Segurança, limites, execução SQL, política temporal e escolha da visualização permanecem determinísticos.

## Executar localmente

Requisitos: Python 3.12 e o arquivo SQLite fornecido com o desafio.

```bash
python -m venv .venv
pip install -e ".[dev]"
```

Ative o ambiente virtual, copie `.env.example` para `.env` e preencha:

```env
DATABASE_PATH=data/anexo_desafio_1.db
OPENROUTER_API_KEY=sua_chave
OPENROUTER_MODEL=provedor/modelo
API_URL=http://localhost:8000
```

Coloque o banco em `data/anexo_desafio_1.db`. Ele não é versionado.

Inicie a API:

```bash
uvicorn data_analyst.api.main:app --app-dir src --reload
```

Em outro terminal, inicie a interface:

```bash
streamlit run ui/streamlit_app.py
```

A documentação interativa da API fica disponível em `http://localhost:8000/docs`.

## Testes e avaliações

```bash
pytest -q
ruff check src tests ui
```

Os testes cobrem descoberta dinâmica do esquema, SQL somente leitura, timeout, limite de linhas, recuperação de consulta inválida, múltiplas consultas, ambiguidade temporal, API e política de visualização.

A validação com modelo real fica isolada em `tests/e2e`. Ela só é executada quando `RUN_E2E=1` estiver definido e houver banco e credenciais locais, evitando custo e variabilidade no CI.

As cinco perguntas do enunciado possuem resultados de referência independentes em `tests/evals/test_reference_queries.py`, incluindo:

1. estados com maior número de clientes que compraram via App em maio;
2. clientes que interagiram com WhatsApp em 2024;
3. categorias com maior média de compras por cliente;
4. reclamações não resolvidas por canal;
5. tendência de reclamações por canal no último ano disponível.

Esses valores são usados apenas como oráculos de avaliação; não são respostas fixas da aplicação.

## Decisões de projeto

- [Especificação](docs/SPEC-001-agentic-data-analyst.md)
- [Descoberta do banco real](docs/DESCOBERTA-BANCO.md)
- [ADRs](docs/adr/)
- [Arquitetura proposta para o Desafio 2](docs/ARQUITETURA-DESAFIO-2.md)

O banco real diverge parcialmente do esquema descrito no enunciado. Essa diferença é uma das razões para a descoberta dinâmica do esquema.

## Estado atual

O fluxo principal, API, visualização e testes determinísticos estão implementados. A execução ponta a ponta com um modelo real é uma validação manual e não faz parte do CI para evitar dependência de credenciais, custo e variabilidade externa.

## Possíveis evoluções

- observabilidade externa com LangSmith ou ferramenta equivalente;
- fallback entre modelos/provedores;
- seleção de relevância para esquemas muito maiores;
- cache de metadados e consultas seguras;
- persistência opcional de histórico e métricas de avaliação.
