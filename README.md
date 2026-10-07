# Agentic Data Analyst

Assistente agentivo de dados que recebe perguntas de negócio em linguagem natural, investiga um banco SQLite e produz respostas fundamentadas, com geração e validação de SQL, visualizações e rastreabilidade da execução.

## O que a solução faz

- descobre tabelas, colunas, chaves estrangeiras, cobertura temporal e valores categóricos de baixa cardinalidade em tempo de execução;
- interpreta a pergunta e cria um plano de investigação;
- gera SQL dinamicamente, sem consultas de negócio fixas na aplicação;
- valida e executa SQL somente leitura;
- corrige consultas inválidas com número limitado de tentativas;
- pode executar mais de uma consulta antes de responder;
- trata ambiguidades temporais de forma explícita;
- escolhe indicador, tabela, barras ou linha de forma determinística;
- expõe consultas, etapas, erros, duração e consumo de tokens no rastro operacional;
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

### Tecnologias

- **Python 3.12**
- **LangGraph**
- **LangChain Core + langchain-google-genai**
- **Gemini Developer API (Google AI Studio)**
- **FastAPI + Uvicorn**
- **SQLite + sqlglot**
- **Pydantic + pydantic-settings**
- **Streamlit + pandas + httpx**
- **pytest + Ruff + GitHub Actions**

As versões e demais dependências estão declaradas em `pyproject.toml`.

### Fluxo do agente

1. A aplicação lê o schema do SQLite e identifica tabelas, colunas, relações, datas e alguns valores categóricos úteis.
2. A pergunta é interpretada e convertida em uma intenção estruturada.
3. O contexto temporal é resolvido. Quando existe mais de uma interpretação possível, a aplicação pede esclarecimento antes de consultar o banco.
4. O agente cria um plano e gera a próxima consulta SQL.
5. A consulta passa pela validação de segurança antes da execução.
6. Se houver erro de SQL, o fluxo tenta corrigir a consulta e valida novamente.
7. Depois de cada consulta, o agente avalia se já existe informação suficiente. Se faltar evidência, uma nova consulta pode ser gerada.
8. Ao final, a resposta é produzida a partir dos resultados obtidos e a interface escolhe a visualização adequada.

A interface mostra as consultas executadas e as etapas do fluxo no painel de rastreabilidade.

## Início rápido em outro computador (Windows / PowerShell)

### 1. Pré-requisitos

Instale **Git** e **Python 3.12**. Tenha também o arquivo SQLite fornecido no desafio e uma chave da Gemini Developer API / Google AI Studio.

### 2. Clone o repositório

```powershell
git clone https://github.com/mxthsu/agentic-data-analyst.git
cd agentic-data-analyst
```

### 3. Crie e ative o ambiente virtual

```powershell
py -3.12 -m venv .venv
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -e .
```

### 4. Configure o ambiente

```powershell
Copy-Item .env.example .env
notepad .env
```

No arquivo `.env`, preencha `GOOGLE_API_KEY`. Os demais valores podem permanecer com os padrões do projeto. Se o banco estiver com outro nome ou em outro caminho, ajuste `DATABASE_PATH`.

### 5. Coloque o banco no projeto

Crie a pasta `data` se necessário e copie o arquivo fornecido para:

```text
data/anexo_desafio_1.db
```

O banco não é versionado no Git.

### 6. Inicie a API

No primeiro PowerShell, a partir da raiz do projeto:

```powershell
.\.venv\Scripts\Activate.ps1
python -m uvicorn data_analyst.api.main:app --app-dir src --reload
```

A API fica em `http://localhost:8000` e o Swagger em `http://localhost:8000/docs`.

### 7. Inicie a interface

Abra um segundo PowerShell na raiz do projeto:

```powershell
.\.venv\Scripts\Activate.ps1
python -m streamlit run ui/streamlit_app.py
```

Abra a URL exibida pelo Streamlit, normalmente `http://localhost:8501`.

### Próximas execuções

Depois da primeira instalação, basta abrir dois terminais, ativar `.venv` nos dois e executar novamente os comandos da API e do Streamlit. Não é necessário reinstalar as dependências.

## Configuração

O arquivo `.env.example` contém as configurações disponíveis:

```env
DATABASE_PATH=data/anexo_desafio_1.db
GOOGLE_API_KEY=sua_chave
GEMINI_MODEL=gemini-3.5-flash-lite
GEMINI_REQUESTS_PER_MINUTE=6
GEMINI_MAX_BURST_REQUESTS=5
GEMINI_REQUEST_TIMEOUT_SECONDS=30
GEMINI_MAX_OUTPUT_TOKENS=1024
API_URL=http://localhost:8000
```

### Modelo, limites e tokens

O modelo padrão é o `gemini-3.5-flash-lite`, acessado pela Gemini Developer API do Google AI Studio. O projeto aplica limite local de chamadas e timeout configurável. Em caso de limite do provider, a API retorna um erro controlado.

A interface mostra o consumo de tokens da execução. O valor vem do `usage_metadata` retornado pelo modelo. O `get_usage_metadata_callback()`, do `langchain-core`, coleta esses dados e o serviço soma `input_tokens`, `output_tokens` e `total_tokens` de todas as chamadas LLM feitas para responder à pergunta.

Antes do teste ponta a ponta, valide apenas a integração do modelo:

```bash
python scripts/smoke_gemini.py
```

Esse comando faz uma única chamada ao modelo e não consulta o SQLite.

O rastro da execução também registra duração por etapa, SQL executado, quantidade de linhas, número de consultas e reparos.

## Testes e avaliações

```bash
pytest -q
ruff check src tests ui
```

Os testes cobrem descoberta dinâmica do esquema, SQL somente leitura, timeout, limite de linhas, recuperação de consulta inválida, múltiplas consultas, ambiguidade temporal, API e política de visualização.

A validação com modelo real fica isolada em `tests/e2e`. Ela só é executada quando `RUN_E2E=1` estiver definido e houver banco e credenciais locais, evitando consumo da cota gratuita e variabilidade no CI.

As cinco perguntas do enunciado possuem resultados de referência independentes em `tests/evals/test_reference_queries.py`, incluindo:

1. estados com maior número de clientes que compraram via App em maio;
2. clientes que interagiram com WhatsApp em 2024;
3. categorias com maior média de compras por cliente;
4. reclamações não resolvidas por canal;
5. tendência de reclamações por canal no último ano disponível.

Esses valores ficam apenas nos testes como referência. A aplicação não usa respostas fixas.

### Validação ponta a ponta

As cinco perguntas do enunciado também foram executadas manualmente com o provider real. Os resultados observados foram compatíveis com os oráculos independentes:

| Caso | Resultado validado | Visualização |
| --- | --- | --- |
| Top 5 estados via App em maio | São Paulo 6, Minas Gerais 3, Santa Catarina 3, Alagoas 2, Espírito Santo 2 | barras |
| Interações com WhatsApp em 2024 | 17 clientes distintos | indicador |
| Média de compras por cliente e categoria | Roupas 2,211; Viagens 2,162; Livros 1,976; Serviços 1,962; Eletrônicos 1,923; Alimentos 1,882 | barras |
| Reclamações não resolvidas por canal | Telefone 19, Chat 18, E-mail 14 | barras |
| Tendência de reclamações no último ano | janela mensal de 2024-08 a 2025-07; Chat 34, E-mail 27, Telefone 33 no período | linha |

O rastro da interface também expõe duração por etapa, consultas SQL, reparos e consumo agregado de tokens de entrada e saída.

## Documentação

- [Especificação](docs/SPEC-001-agentic-data-analyst.md)
- [Descoberta do banco real](docs/DESCOBERTA-BANCO.md)
- [ADRs](docs/adr/)
- [Arquitetura proposta para o Desafio 2](docs/ARQUITETURA-DESAFIO-2.md)

O banco real diverge parcialmente do esquema descrito no enunciado. A aplicação descobre o schema em tempo de execução.

## Possíveis evoluções

- usar Vertex AI em uma implantação na GCP;
- adicionar tracing externo em ambiente de produção;
- ampliar o conjunto de avaliações automatizadas;
- cachear metadados do schema em bancos maiores;
- guardar histórico de sessões quando houver necessidade;
- permitir fallback entre modelos ou providers.
