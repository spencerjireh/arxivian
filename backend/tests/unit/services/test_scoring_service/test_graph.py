"""Wiring tests for the Stage 2 scoring graph topology."""

from src.services.scoring_service.scoring_graph_builder import build_scoring_graph

_DIMENSIONS = {
    "score_method_clarity",
    "score_resource_feasibility",
    "score_data_availability",
    "score_demand",
}


def test_graph_compiles_with_expected_nodes():
    graph = build_scoring_graph()
    nodes = set(graph.get_graph().nodes)
    assert {"fetch_and_extract", "compose_and_persist"} <= nodes
    assert _DIMENSIONS <= nodes


def test_fan_out_and_fan_in_edges():
    graph = build_scoring_graph()
    edges = {(e.source, e.target) for e in graph.get_graph().edges}
    for dim in _DIMENSIONS:
        assert ("fetch_and_extract", dim) in edges  # fan-out
        assert (dim, "compose_and_persist") in edges  # fan-in
