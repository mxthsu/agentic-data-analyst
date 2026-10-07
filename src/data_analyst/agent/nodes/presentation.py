from data_analyst.agent.models import TraceEvent
from data_analyst.agent.state import AgentState
from data_analyst.visualization.policy import choose_visualization


def select_visualization(state: AgentState) -> dict:
    visualization = choose_visualization(
        state["question"],
        state.get("evidence", []),
    )
    trace = list(state.get("trace", []))
    trace.append(
        TraceEvent(
            node="select_visualization",
            status="ok",
            detail=f"Visualização selecionada: {visualization.kind}.",
        )
    )
    return {
        "visualization": visualization,
        "trace": trace,
    }
