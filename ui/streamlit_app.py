from __future__ import annotations

import os

import httpx
import pandas as pd
import streamlit as st

API_URL = os.getenv("API_URL", "http://localhost:8000").rstrip("/")

NODE_LABELS = {
    "discover_schema": "Descoberta do banco",
    "interpret_question": "Interpretação da pergunta",
    "plan_investigation": "Plano de investigação",
    "generate_sql": "Geração da consulta",
    "validate_sql": "Validação da consulta",
    "execute_sql": "Execução da consulta",
    "assess_evidence": "Avaliação das evidências",
    "repair_sql": "Reparo da consulta",
    "synthesize_answer": "Síntese da resposta",
    "select_visualization": "Seleção da visualização",
    "request_clarification": "Pedido de esclarecimento",
    "fail_gracefully": "Encerramento controlado",
}


def _dataframe(result: dict | None) -> pd.DataFrame:
    if not result:
        return pd.DataFrame()

    columns = result.get("columns", [])
    rows = result.get("rows", [])
    return pd.DataFrame(rows, columns=columns)


def _render_visualization(result: dict | None, visualization: dict | None) -> None:
    frame = _dataframe(result)
    if frame.empty:
        return

    kind = (visualization or {}).get("kind", "table")
    x = (visualization or {}).get("x")
    y = (visualization or {}).get("y")
    series = (visualization or {}).get("series")

    if kind == "metric" and y in frame.columns:
        st.metric(y.replace("_", " ").title(), frame.iloc[0][y])
        return

    if kind == "bar" and x in frame.columns and y in frame.columns:
        st.bar_chart(frame.set_index(x)[[y]])
        return

    if kind == "line" and x in frame.columns and y in frame.columns:
        if series in frame.columns:
            chart = frame.pivot_table(
                index=x,
                columns=series,
                values=y,
                aggfunc="sum",
            )
            st.line_chart(chart)
        else:
            st.line_chart(frame.set_index(x)[[y]])
        return

    st.dataframe(frame, use_container_width=True, hide_index=True)


def _render_token_usage(token_usage: dict | None) -> None:
    usage = token_usage or {}
    total_tokens = int(usage.get("total_tokens", 0) or 0)
    if total_tokens <= 0:
        return

    input_tokens = int(usage.get("input_tokens", 0) or 0)
    output_tokens = int(usage.get("output_tokens", 0) or 0)

    st.caption("Uso do modelo")
    input_col, output_col, total_col = st.columns(3)
    input_col.metric("Tokens de entrada", f"{input_tokens:,}".replace(",", "."))
    output_col.metric("Tokens de saída", f"{output_tokens:,}".replace(",", "."))
    total_col.metric("Tokens totais", f"{total_tokens:,}".replace(",", "."))


def _render_trace(trace: list[dict]) -> None:
    with st.expander("Como a resposta foi obtida"):
        for index, event in enumerate(trace, start=1):
            label = NODE_LABELS.get(event.get("node"), event.get("node", "Etapa"))
            status = event.get("status", "")
            st.markdown(f"**{index}. {label}** · {status}")

            if event.get("detail"):
                st.caption(event["detail"])

            if event.get("sql"):
                st.code(event["sql"], language="sql")

            metadata = []
            if event.get("row_count") is not None:
                metadata.append(f"{event['row_count']} linha(s)")
            if event.get("duration_ms") is not None:
                metadata.append(f"{event['duration_ms']:.1f} ms")
            if metadata:
                st.caption(" · ".join(metadata))


def _ask(question: str) -> dict:
    response = httpx.post(
        f"{API_URL}/ask",
        json={"question": question},
        timeout=httpx.Timeout(
            connect=5,
            read=150,
            write=10,
            pool=5,
        ),
    )
    response.raise_for_status()
    return response.json()


st.set_page_config(
    page_title="Agentic Data Analyst",
    page_icon="📊",
    layout="wide",
)

st.title("Agentic Data Analyst")
st.caption("Faça uma pergunta de negócio sobre o banco de dados fornecido.")

question = st.text_area(
    "Pergunta",
    placeholder="Ex.: Quais estados tiveram mais clientes que compraram via App em maio?",
    height=100,
)

if st.button("Analisar", type="primary", disabled=not question.strip()):
    try:
        with st.spinner("Investigando os dados..."):
            payload = _ask(question.strip())
    except httpx.ConnectError:
        st.error("A API não está disponível. Inicie o backend antes de continuar.")
    except httpx.TimeoutException:
        st.error(
            "A análise excedeu o tempo limite da interface. "
            "Verifique o terminal da API e tente novamente."
        )
    except httpx.HTTPStatusError as exc:
        try:
            detail = exc.response.json().get("detail")
        except ValueError:
            detail = None
        st.error(detail or "Não foi possível concluir a análise.")
    else:
        st.subheader("Resposta")
        st.write(payload["answer"])

        assumptions = payload.get("assumptions") or []
        if assumptions:
            with st.expander("Suposições consideradas"):
                for assumption in assumptions:
                    st.write(f"- {assumption}")

        _render_visualization(
            payload.get("result"),
            payload.get("visualization"),
        )
        _render_token_usage(payload.get("token_usage"))
        _render_trace(payload.get("trace", []))

        if payload.get("trace_id"):
            st.caption(f"Execução: {payload['trace_id']}")
