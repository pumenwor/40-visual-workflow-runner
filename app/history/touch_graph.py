"""Tests for graph.py (owner: Person 3, test skeletons by Person 5).

These call get_execution_order(nodes, edges) from graph.py.
They will FAIL until graph.py exists. That is expected.
"""
import pytest

from graph import get_execution_order


def make_nodes(*ids):
    return [{"id": i, "name": i.upper(), "type": "emit_json", "config": {}} for i in ids]


def test_cycle_is_rejected():
    nodes = make_nodes("a", "b")
    edges = [("a", "b"), ("b", "a")]
    with pytest.raises(ValueError) as error:
        get_execution_order(nodes, edges)
    assert "cycle" in str(error.value).lower()


def test_tasks_run_in_dependency_order():
    nodes = make_nodes("a", "b", "c")
    edges = [("a", "c"), ("b", "c")]
    order = get_execution_order(nodes, edges)
    assert order[-1] == "c"
    assert set(order) == {"a", "b", "c"}


def test_single_node_workflow():
    nodes = make_nodes("a")
    assert get_execution_order(nodes, []) == ["a"]


def test_unconnected_nodes_are_all_included():
    nodes = make_nodes("a", "b")
    order = get_execution_order(nodes, [])
    assert set(order) == {"a", "b"}


def test_chain_order_is_exact():
    nodes = make_nodes("a", "b", "c")
    edges = [("a", "b"), ("b", "c")]
    assert get_execution_order(nodes, edges) == ["a", "b", "c"]


# --- Validation checks (names depend on what Person 3 builds) ---
# Uncomment once validate_workflow(nodes, edges) exists and raises ValueError.
#
# from graph import validate_workflow
#
# def test_edge_to_missing_node_is_rejected():
#     with pytest.raises(ValueError):
#         validate_workflow(make_nodes("a"), [("a", "zzz")])
#
# def test_self_connection_is_rejected():
#     with pytest.raises(ValueError):
#         validate_workflow(make_nodes("a"), [("a", "a")])
#
# def test_duplicate_connection_is_rejected():
#     with pytest.raises(ValueError):
#         validate_workflow(make_nodes("a", "b"), [("a", "b"), ("a", "b")])
