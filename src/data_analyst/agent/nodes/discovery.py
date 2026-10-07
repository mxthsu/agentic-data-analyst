from __future__ import annotations

import time
from pathlib import Path

from data_analyst.agent.models import TraceEvent
from data_analyst.agent.state import AgentState
from data_analyst.database.inspector import inspect_database


def discover_schema(state: AgentState, db_path: Path) -> dict:
    started = time.perf_counter()
    schema = inspect_database(db_path)
    trace = list(state.get("trace", []))
    trace.append(
        TraceEvent(
            node="discover_schema",
            status="ok",
            duration_ms=(time.perf_counter() - started) * 1000,
            detail=f"{len(schema.tables)} tabelas de negócio descobertas.",
        )
    )
    return {
        "schema": schema,
        "trace": trace,
        "graph_steps": state.get("graph_steps", 0) + 1,
    }
