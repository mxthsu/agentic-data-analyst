from __future__ import annotations

import os

import altair as alt
import httpx
import pandas as pd
import streamlit as st

API_URL = os.getenv("API_URL", "http://localhost:8000").rstrip("/")

NODE_LABELS = {
    "discover_schema": "Descoberta do banco",
    "interpret_question": "Interpretação da pergunta",
    "resolve_temporal_context": "Contexto temporal",
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


def _metric_label(column: str) -> str:
    normalized = column.strip().lower()
    prefixes = (
        ("total_", "Total de "),
        ("media_", "Média de "),
        ("quantidade_", "Quantidade de "),
        ("qtd_", "Quantidade de "),
        ("contagem_", "Contagem de "),
    )
    for prefix, label in prefixes:
        if normalized.startswith(prefix):
            remainder = normalized[len(prefix):].replace("_", " ")
            return f"{label}{remainder}"

    return normalized.replace("_", " ").capitalize()


def _render_visualization(result: dict | None, visualization: dict | None) -> None:
    frame = _dataframe(result)
    if frame.empty:
        return

    kind = (visualization or {}).get("kind", "table")
    x = (visualization or {}).get("x")
    y = (visualization or {}).get("y")
    series = (visualization or {}).get("series")

    if kind == "metric" and y in frame.columns:
        st.metric(_metric_label(y), frame.iloc[0][y])
        return

    if kind == "bar" and x in frame.columns and y in frame.columns:
        x_encoding = alt.X(
            x,
            sort=None,
            axis=alt.Axis(labelAngle=0, labelLimit=180),
            title=_metric_label(x),
        )
        y_encoding = alt.Y(y, title=_metric_label(y))

        chart = alt.Chart(frame).mark_bar().encode(
            x=x_encoding,
            y=y_encoding,
            tooltip=[x, y],
        )

        if series in frame.columns:
            chart = chart.encode(
                color=alt.Color(series, title=_metric_label(series)),
                tooltip=[x, series, y],
            )

        st.altair_chart(chart, use_container_width=True)
        return

    if kind == "line" and x in frame.columns and y in frame.columns:
        x_encoding = alt.X(
            x,
            sort=None,
            axis=alt.Axis(labelAngle=0, labelLimit=180),
            title=_metric_label(x),
        )
        y_encoding = alt.Y(y, title=_metric_label(y))

        chart = alt.Chart(frame).mark_line(point=True).encode(
            x=x_encoding,
            y=y_encoding,
            tooltip=[x, y],
        )

        if series in frame.columns:
            chart = chart.encode(
                color=alt.Color(series, title=_metric_label(series)),
                tooltip=[x, series, y],
            )

        st.altair_chart(chart, use_container_width=True)
        return

    st.dataframe(frame, use_container_width=True, hide_index=True)


def _render_execution_summary(
    trace: list[dict],
    token_usage: dict | None,
) -> None:
    usage = token_usage or {}
    input_tokens = int(usage.get("input_tokens", 0) or 0)
    output_tokens = int(usage.get("output_tokens", 0) or 0)
    total_tokens = int(usage.get("total_tokens", 0) or 0)

    duration_ms = sum(
        float(event.get("duration_ms") or 0)
        for event in trace
    )
    query_count = sum(
        1
        for event in trace
        if event.get("node") == "execute_sql" and event.get("status") == "ok"
    )
    repair_count = sum(
        1 for event in trace if event.get("node") == "repair_sql"
    )

    st.caption("Execução")
    duration_col, tokens_col, queries_col, repairs_col = st.columns(4)
    duration_col.metric("Tempo da análise", f"{duration_ms / 1000:.1f} s")
    tokens_col.metric(
        "Tokens totais",
        f"{total_tokens:,}".replace(",", "."),
    )
    queries_col.metric("Consultas SQL", query_count)
    repairs_col.metric("Reparos", repair_count)

    if total_tokens > 0:
        st.caption(
            "Tokens do modelo: "
            f"{input_tokens:,} entrada · {output_tokens:,} saída".replace(",", ".")
        )


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

with st.container():
    question = st.chat_input(
        "Faça uma pergunta de negócio...",
    )

if question:
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
        trace = payload.get("trace", [])
        _render_execution_summary(trace, payload.get("token_usage"))
        _render_trace(trace)

        if payload.get("trace_id"):
            st.caption(f"Execução: {payload['trace_id']}")
