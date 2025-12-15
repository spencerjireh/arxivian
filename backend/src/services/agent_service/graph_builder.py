"""LangGraph workflow builder for agent service."""

from langgraph.graph import StateGraph, END, START
from langgraph.prebuilt import ToolNode

from src.schemas.langgraph_state import AgentState
from src.clients.base_llm_client import BaseLLMClient
from src.services.search_service import SearchService
from .context import AgentContext
from .nodes import (
    guardrail_node,
    out_of_scope_node,
    retrieve_node,
    grade_documents_node,
    rewrite_query_node,
    generate_answer_node,
)
from .edges import continue_after_guardrail, continue_after_grading
from .tools import create_retrieve_tool


def build_agent_graph(
    llm_client: BaseLLMClient,
    search_service: SearchService,
    guardrail_threshold: int = 75,
    top_k: int = 3,
    max_retrieval_attempts: int = 3,
    temperature: float = 0.3,
):
    """
    Build and compile the agent workflow graph.

    Returns:
        Compiled LangGraph workflow
    """
    # Create context
    context = AgentContext(
        llm_client=llm_client,
        search_service=search_service,
        guardrail_threshold=guardrail_threshold,
        top_k=top_k,
        max_retrieval_attempts=max_retrieval_attempts,
        temperature=temperature,
    )

    # Create workflow
    workflow = StateGraph(AgentState)

    # Create tools
    retrieve_tool = create_retrieve_tool(search_service)
    tool_node = ToolNode([retrieve_tool])

    # Add nodes (with context binding)
    workflow.add_node("guardrail", lambda s: guardrail_node(s, context))
    workflow.add_node("out_of_scope", lambda s: out_of_scope_node(s, context))
    workflow.add_node("retrieve", lambda s: retrieve_node(s, context))
    workflow.add_node("tool_retrieve", tool_node)
    workflow.add_node("grade_documents", lambda s: grade_documents_node(s, context))
    workflow.add_node("rewrite_query", lambda s: rewrite_query_node(s, context))
    workflow.add_node("generate_answer", lambda s: generate_answer_node(s, context))

    # Add edges
    workflow.add_edge(START, "guardrail")

    workflow.add_conditional_edges(
        "guardrail", continue_after_guardrail, {"continue": "retrieve", "out_of_scope": "out_of_scope"}
    )

    workflow.add_edge("out_of_scope", END)

    # After retrieve, always go to tool_retrieve
    workflow.add_edge("retrieve", "tool_retrieve")

    # After tool_retrieve, always grade
    workflow.add_edge("tool_retrieve", "grade_documents")

    workflow.add_conditional_edges(
        "grade_documents",
        continue_after_grading,
        {"generate_answer": "generate_answer", "rewrite_query": "rewrite_query"},
    )

    # After rewrite, go back to retrieve
    workflow.add_edge("rewrite_query", "retrieve")

    # After generate_answer, done
    workflow.add_edge("generate_answer", END)

    # Compile
    return workflow.compile()
