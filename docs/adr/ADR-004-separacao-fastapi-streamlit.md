# ADR-004 — Separação entre FastAPI e Streamlit

**Status:** Aceito
**Data:** 2026-10-06

## Contexto

O enunciado pede um backend Python e uma interface simples. Concentrar toda a lógica no Streamlit dificultaria os testes e esconderia o contrato do agente.

## Decisão

Expor o agente por FastAPI, inicialmente com `POST /ask` e `GET /health`. O Streamlit atua como cliente da API e apresenta resposta, dados, visualização e rastro de execução.

## Alternativas consideradas

- Streamlit chamando o grafo diretamente: menos arquivos e execução mais simples, porém maior acoplamento.
- Frontend separado completo: custo desnecessário para um desafio de cinco dias.

## Consequências

Backend e interface podem ser testados independentemente, e o projeto demonstra uma fronteira de serviço clara. A execução local exige iniciar API e Streamlit, procedimento que deve ser documentado em um único fluxo.
