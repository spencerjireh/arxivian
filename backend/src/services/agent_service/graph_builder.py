"""LangGraph workflow builder for agent service.

This module builds the router-based agent graph following 12-factor agent principles.

Graph flow:
    START -> guardrail -> [out_of_scope | router]
    router -> [executor | grade | generate]
    executor -> [grade | router]
    grade -> [router | generate]
    generate -> END
    out_of_scope -> END
"""

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import StateGraph, END, START
from langgraph.graph.state import CompiledStateGraph

from src.schemas.langgraph_state import AgentState
from .nodes import (
    guardrail_node,
    out_of_scope_node,
    router_node,
    executor_node,
    grade_documents_node,
    generate_answer_node,
)
from .edges import (
    continue_after_guardrail,
    route_after_router,
    route_after_executor,
    route_after_grading_new,
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
    workflow = StateGraph(AgentState)

    # Add nodes (receive context via RunnableConfig)
    workflow.add_node("guardrail", guardrail_node)
    workflow.add_node("out_of_scope", out_of_scope_node)
    workflow.add_node("router", router_node)
    workflow.add_node("executor", executor_node)
    workflow.add_node("grade_documents", grade_documents_node)
    workflow.add_node("generate", generate_answer_node)

    # Add edges
    # START -> guardrail
    workflow.add_edge(START, "guardrail")

    # guardrail -> [out_of_scope | router]
    workflow.add_conditional_edges(
        "guardrail",
        continue_after_guardrail,
        {"continue": "router", "out_of_scope": "out_of_scope"},
    )

    # out_of_scope -> END
    workflow.add_edge("out_of_scope", END)

    # router -> [executor | grade | generate]
    workflow.add_conditional_edges(
        "router",
        route_after_router,
        {"execute": "executor", "grade": "grade_documents", "generate": "generate"},
    )

    # executor -> [grade | router]
    workflow.add_conditional_edges(
        "executor",
        route_after_executor,
        {"grade": "grade_documents", "router": "router"},
    )

    # grade -> [router | generate]
    workflow.add_conditional_edges(
        "grade_documents",
        route_after_grading_new,
        {"router": "router", "generate": "generate"},
    )

    # generate -> END
    workflow.add_edge("generate", END)

    return workflow.compile(checkpointer=checkpointer)
