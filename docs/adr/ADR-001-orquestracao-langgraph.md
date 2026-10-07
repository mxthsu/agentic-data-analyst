# ADR-001 — LangGraph para orquestração agentiva

**Status:** Aceito
**Data:** 2026-10-06

## Contexto

O desafio exige múltiplas etapas, recuperação de SQL inválido, transparência e tratamento de incerteza. O fluxo possui decisões condicionais reais e precisa ser fácil de demonstrar e testar.

## Decisão

Usar LangGraph `StateGraph` como orquestrador principal. O estado carrega pergunta, esquema, plano, tentativas, resultados, erros, suposições, rastro de execução e resposta. Os nós executam responsabilidades pequenas, enquanto as transições condicionais controlam sucesso, nova investigação, esclarecimento e reparo.

## Alternativas consideradas

- Loop manual em Python: mais simples, mas esconde a topologia do fluxo e reduz a aderência à proposta do desafio.
- Executor de agente genérico: rápido de montar, porém oferece menos controle sobre limites, segurança e recuperação.

## Consequências

A arquitetura fica explicitamente agentiva e auditável. Em contrapartida, o roteamento do grafo também precisa ser testado, além das funções determinísticas.
