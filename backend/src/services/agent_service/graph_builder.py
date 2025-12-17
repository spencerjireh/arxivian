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

from langgraph.graph import StateGraph, END, START

from src.schemas.langgraph_state import AgentState
from src.clients.base_llm_client import BaseLLMClient
from src.services.search_service import SearchService
from .context import AgentContext
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


def create_node_wrapper(node_func, context):
    """Wrap async node functions with context binding."""

    async def wrapper(state):
        return await node_func(state, context)

    return wrapper


def build_agent_graph(
    llm_client: BaseLLMClient,
    search_service: SearchService,
    guardrail_threshold: int = 75,
    top_k: int = 3,
    max_retrieval_attempts: int = 3,
    max_iterations: int = 5,
    temperature: float = 0.3,
):
    """
    Build and compile the agent workflow graph with router architecture.

    The graph uses a dynamic router pattern that allows the LLM to decide
    which tools to call based on the query and context, rather than
    following a static DAG.

    Args:
        llm_client: LLM client for generating responses
        search_service: Search service for document retrieval
        guardrail_threshold: Minimum score for query to be in scope
        top_k: Number of relevant chunks needed for generation
        max_retrieval_attempts: Legacy parameter (kept for compatibility)
        max_iterations: Maximum router iterations to prevent infinite loops
        temperature: Temperature for answer generation

    Returns:
        Compiled LangGraph workflow
    """
    # Create context with tool registry
    context = AgentContext(
        llm_client=llm_client,
        search_service=search_service,
        guardrail_threshold=guardrail_threshold,
        top_k=top_k,
        max_retrieval_attempts=max_retrieval_attempts,
        max_iterations=max_iterations,
        temperature=temperature,
    )

    # Create workflow
    workflow = StateGraph(AgentState)

    # Add nodes (with context binding)
    workflow.add_node("guardrail", create_node_wrapper(guardrail_node, context))
    workflow.add_node("out_of_scope", create_node_wrapper(out_of_scope_node, context))
    workflow.add_node("router", create_node_wrapper(router_node, context))
    workflow.add_node("executor", create_node_wrapper(executor_node, context))
    workflow.add_node("grade_documents", create_node_wrapper(grade_documents_node, context))
    workflow.add_node("generate", create_node_wrapper(generate_answer_node, context))

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

    # Compile
    return workflow.compile()
