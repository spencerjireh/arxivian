"""Builder for the Stage 2 scoring graph: a fixed fan-out/fan-in DAG.

START -> fetch_and_extract -> [4 parallel dimension nodes] -> compose_and_persist -> END.
Mirrors `agent_service/graph_builder.py`, but with only plain edges (no router). Each
dimension node writes a DISTINCT state key, so the parallel superstep needs no reducers. No
checkpointer: the graph has no HITL interrupts or resume.
"""

from __future__ import annotations

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from src.schemas.scoring_state import PaperScoreState
from src.services.scoring_service.nodes import (
    compose_and_persist_node,
    fetch_and_extract_node,
    score_data_availability_node,
    score_demand_node,
    score_method_clarity_node,
    score_resource_feasibility_node,
)

# Dimension node name -> node fn. Adding code gap in v1.1 is one more entry here.
_DIMENSION_NODES = {
    "score_method_clarity": score_method_clarity_node,
    "score_resource_feasibility": score_resource_feasibility_node,
    "score_data_availability": score_data_availability_node,
    "score_demand": score_demand_node,
}


def build_scoring_graph(checkpointer: BaseCheckpointSaver | None = None) -> CompiledStateGraph:
    """Compile the Stage 2 scoring DAG."""
    workflow = StateGraph(PaperScoreState)  # type: ignore[invalid-argument-type]

    workflow.add_node("fetch_and_extract", fetch_and_extract_node)
    for name, fn in _DIMENSION_NODES.items():
        workflow.add_node(name, fn)
    workflow.add_node("compose_and_persist", compose_and_persist_node)

    workflow.add_edge(START, "fetch_and_extract")
    for name in _DIMENSION_NODES:
        workflow.add_edge("fetch_and_extract", name)  # fan-out (parallel superstep)
        workflow.add_edge(name, "compose_and_persist")  # fan-in (join runs once)
    workflow.add_edge("compose_and_persist", END)

    return workflow.compile(checkpointer=checkpointer)
