# Agentic Data Analyst

Implementação do Desafio Técnico 1 para Engenheiro(a) de IA (Pleno): um assistente que recebe perguntas de negócio em linguagem natural, investiga um banco SQLite e devolve uma resposta fundamentada nos dados.

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

## Executar localmente

Requisitos: Python 3.12 e o arquivo SQLite fornecido com o desafio.

```bash
python -m venv .venv
pip install -e ".[dev]"
```

Ative o ambiente virtual, copie `.env.example` para `.env` e preencha:

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

Coloque o banco em `data/anexo_desafio_1.db`. Ele não é versionado.

Inicie a API:

```bash
python -m uvicorn data_analyst.api.main:app --app-dir src --reload
```

Em outro terminal, inicie a interface:

```bash
python -m streamlit run ui/streamlit_app.py
```

A documentação interativa da API fica disponível em `http://localhost:8000/docs`.

### Google AI Studio e nível gratuito

O provider padrão é a Gemini Developer API via Google AI Studio, usando
`gemini-3.5-flash-lite`. O projeto limita localmente a frequência de chamadas
e não faz retries automáticos agressivos. O valor padrão de
`GEMINI_REQUESTS_PER_MINUTE=6` é conservador. Um burst curto e configurável
(`GEMINI_MAX_BURST_REQUESTS=5`) permite que etapas sequenciais de uma mesma
investigação usem crédito acumulado sem remover o limite sustentado. A resposta
também expõe tokens de entrada, saída e total agregados em toda a investigação.

Os limites oficiais variam por projeto e modelo. Em caso de `429`, a API
retorna uma mensagem controlada em vez de repetir indefinidamente a chamada.

Antes do teste ponta a ponta, valide apenas a integração do modelo:

```bash
python scripts/smoke_gemini.py
```

Esse comando faz uma única chamada estruturada e não consulta o SQLite. O pequeno burst inicial evita impor espera artificial à primeira etapa, enquanto o limitador continua repondo créditos na taxa sustentada configurada.

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

Esses valores são usados apenas como oráculos de avaliação; não são respostas fixas da aplicação.

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

## Decisões de projeto

- [Especificação](docs/SPEC-001-agentic-data-analyst.md)
- [Descoberta do banco real](docs/DESCOBERTA-BANCO.md)
- [ADRs](docs/adr/)
- [Arquitetura proposta para o Desafio 2](docs/ARQUITETURA-DESAFIO-2.md)

O banco real diverge parcialmente do esquema descrito no enunciado. Essa diferença é uma das razões para a descoberta dinâmica do esquema.

## Estado atual

O fluxo principal, API, visualização e testes determinísticos estão implementados. Os cinco casos oficiais foram validados ponta a ponta com modelo real. Essa validação permanece manual e fora do CI para evitar dependência de credenciais, custo e variabilidade externa.

## Possíveis evoluções

- observabilidade externa com LangSmith ou ferramenta equivalente;
- fallback entre modelos/provedores;
- seleção de relevância para esquemas muito maiores;
- cache de metadados e consultas seguras;
- persistência opcional de histórico e métricas de avaliação.
