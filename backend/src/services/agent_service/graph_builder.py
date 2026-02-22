"""LangGraph workflow builder for agent service.

This module builds the agent graph following 12-factor agent principles.

Graph flow:
    START -> classify_and_route -> [out_of_scope | executor | evaluate_batch | generate]
    executor -> [confirm_ingest | evaluate_batch | classify_and_route]
    confirm_ingest -> classify_and_route
    evaluate_batch -> [generate | classify_and_route]
    generate -> END
    out_of_scope -> END
"""

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import StateGraph, END, START
from langgraph.graph.state import CompiledStateGraph

from src.schemas.langgraph_state import AgentState
from .nodes import (
    classify_and_route_node,
    out_of_scope_node,
    executor_node,
    evaluate_batch_node,
    generate_answer_node,
    confirm_ingest_node,
)
from .edges import (
    route_after_classify,
    route_after_executor,
    route_after_eval,
)


def build_graph(checkpointer: BaseCheckpointSaver | None = None) -> CompiledStateGraph:
    """Build and compile the agent workflow graph.

    Called once during application lifespan startup. The compiled graph
    is stored on app.state and injected into AgentService via DI.

    The graph uses a dynamic router pattern that allows the LLM to decide
    which tools to call based on the query and context, rather than
    following a static DAG. Context is passed per-request via
    RunnableConfig["configurable"]["context"].
    """
    workflow = StateGraph(AgentState)  # type: ignore[invalid-argument-type]

    # Add nodes
    workflow.add_node("classify_and_route", classify_and_route_node)
    workflow.add_node("out_of_scope", out_of_scope_node)
    workflow.add_node("executor", executor_node)
    workflow.add_node("evaluate_batch", evaluate_batch_node)
    workflow.add_node("generate", generate_answer_node)
    workflow.add_node("confirm_ingest", confirm_ingest_node)

    # START -> classify_and_route
    workflow.add_edge(START, "classify_and_route")

    # classify_and_route -> [out_of_scope | executor | evaluate_batch | generate]
    workflow.add_conditional_edges(
        "classify_and_route",
        route_after_classify,
        {
            "out_of_scope": "out_of_scope",
            "execute": "executor",
            "evaluate": "evaluate_batch",
            "generate": "generate",
        },
    )

    # out_of_scope -> END
    workflow.add_edge("out_of_scope", END)

    # executor -> [confirm_ingest | evaluate_batch | classify_and_route]
    workflow.add_conditional_edges(
        "executor",
        route_after_executor,
        {
            "confirm": "confirm_ingest",
            "evaluate": "evaluate_batch",
            "classify": "classify_and_route",
        },
    )

    # confirm_ingest -> classify_and_route
    workflow.add_edge("confirm_ingest", "classify_and_route")

    # evaluate_batch -> [generate | classify_and_route]
    workflow.add_conditional_edges(
        "evaluate_batch",
        route_after_eval,
        {"generate": "generate", "classify": "classify_and_route"},
    )

    # generate -> END
    workflow.add_edge("generate", END)

    return workflow.compile(checkpointer=checkpointer)
