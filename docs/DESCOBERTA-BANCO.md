# Descoberta do banco de dados

**Data:** 2026-10-06
**Fonte:** cópia local de `anexo_desafio_1.db` fornecida com o desafio. O arquivo não é versionado.

## Objetivo

Inspecionar o SQLite real antes de definir prompts, ferramentas e geração de SQL. A implementação deve trabalhar com o esquema descoberto em tempo de execução, sem tratar a descrição do PDF como contrato exato.

## Inventário

| Tabela | Registros | Observações |
| --- | ---: | --- |
| `clientes` | 100 | Contém `valor_total_gasto` e `data_ultima_compra`, colunas não listadas no enunciado. |
| `compras` | 946 | FK `cliente_id -> clientes.id`; datas de compra armazenadas como texto ISO. |
| `suporte` | 273 | FK para clientes; `resolvido` armazenado como booleano/inteiro. |
| `campanhas_marketing` | 248 | FK para clientes; `interagiu` armazenado como booleano/inteiro. |

O SQLite também contém a tabela interna `sqlite_sequence`, que não deve ser apresentada ao agente como fonte de negócio.

## Integridade e formato

- `PRAGMA integrity_check` retornou `ok`;
- não foram encontradas referências órfãs de `cliente_id` em compras, suporte ou campanhas;
- não foram encontrados e-mails duplicados em clientes;
- o banco fornecido não possui índices secundários explícitos;
- não foram observados valores nulos nas colunas inspecionadas das quatro tabelas de negócio.

## Cobertura temporal

| Fonte | Data mínima | Data máxima |
| --- | --- | --- |
| `clientes.data_ultima_compra` | 2024-07-24 | 2025-07-22 |
| `compras.data_compra` | 2024-07-22 | 2025-07-22 |
| `suporte.data_contato` | 2024-07-23 | 2025-07-22 |
| `campanhas_marketing.data_envio` | 2024-07-24 | 2025-07-11 |

Expressões relativas como “último ano” devem usar uma política baseada nas datas do conjunto de dados, e não no relógio atual do sistema.

## Verificações de domínio

- Canais de compra: App 337, Loja Física 313, Site 296.
- Categorias de compra: Livros 164, Alimentos 160, Viagens 160, Roupas 157, Serviços 155, Eletrônicos 150.
- Canais de suporte: Chat 95, Telefone 92, E-mail 86.
- Tipos de suporte: Reclamação 97, Dúvida 97, Sugestão 79.
- Canais de marketing: SMS 86, WhatsApp 81, E-mail 81.

## Resultados de referência independentes

Os valores abaixo servem apenas como oráculos de avaliação. Eles nunca devem ser codificados como respostas fixas da aplicação.

| Pergunta / interpretação | Resultado verificado de forma independente |
| --- | --- |
| Clientes distintos que interagiram com campanhas de WhatsApp em 2024 | 17 |
| Reclamações não resolvidas por canal | Telefone 19; Chat 18; E-mail 14 |
| Clientes distintos por estado com compras via App em maio de 2025 | São Paulo 6; Minas Gerais 3; Santa Catarina 3; depois há empate triplo com 2 |
| Média de compras por cliente distinto, por categoria | Roupas 2,211; Viagens 2,162; Livros 1,976; Serviços 1,962; Eletrônicos 1,923; Alimentos 1,882 |

A resposta de top 5 para maio de 2025 cruza um empate: Alagoas, Espírito Santo e Paraná possuem 2 clientes distintos cada. O sistema deve aplicar ordenação secundária determinística ou explicar o empate.

## Consequências para o projeto

1. A descoberta dinâmica do esquema é necessária porque o banco real diverge do enunciado.
2. A semântica das métricas importa: “clientes” normalmente indica clientes distintos, não quantidade de eventos.
3. Ambiguidades temporais devem ser explícitas. Um mês sem ano pode exigir esclarecimento ou inferência documentada a partir dos dados disponíveis.
4. Períodos relativos devem se ancorar na maior data da fonte relevante neste conjunto histórico.
5. O SQL deve ser gerado dinamicamente, executado somente para leitura e possuir recuperação limitada para consultas inválidas.
6. A avaliação deve comparar a semântica dos resultados com SQL independente, e não o texto exato do SQL gerado.
7. O rastro de execução deve exibir consultas executadas, etapas, erros e suposições sem expor raciocínio interno do modelo nem dados pessoais desnecessários.
