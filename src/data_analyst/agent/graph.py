from __future__ import annotations

from pathlib import Path

from langchain_core.language_models import BaseChatModel
from langgraph.graph import END, START, StateGraph

from data_analyst.agent.nodes.discovery import discover_schema
from data_analyst.agent.nodes.planning import interpret_question, plan_investigation
from data_analyst.agent.state import AgentState


def build_graph(db_path: Path, model: BaseChatModel):
    graph = StateGraph(AgentState)

    graph.add_node("discover_schema", lambda state: discover_schema(state, db_path))
    graph.add_node("interpret_question", lambda state: interpret_question(state, model))
    graph.add_node("plan_investigation", lambda state: plan_investigation(state, model))

    graph.add_edge(START, "discover_schema")
    graph.add_edge("discover_schema", "interpret_question")
    graph.add_edge("interpret_question", "plan_investigation")
    graph.add_edge("plan_investigation", END)

    return graph.compile()
