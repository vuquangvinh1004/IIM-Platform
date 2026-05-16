"""test_nearest_node.py — Unit tests cho core/nearest_node.py."""
from __future__ import annotations

import pytest

from modules.logistics.pso_logistics_map.core.nearest_node import NearestNodeIndex


# --------------------------------------------------------------------------- #
#  Fixtures                                                                    #
# --------------------------------------------------------------------------- #

@pytest.fixture()
def index(simple_graph):
    return NearestNodeIndex(simple_graph)


# --------------------------------------------------------------------------- #
#  Tests                                                                       #
# --------------------------------------------------------------------------- #

def test_find_exact_node_0(simple_graph):
    """Tọa độ node 0 phải trả về node 0."""
    idx = NearestNodeIndex(simple_graph)
    lat = simple_graph.nodes[0]["y"]
    lon = simple_graph.nodes[0]["x"]
    assert idx.find(lat, lon) == 0


def test_find_exact_node_4(simple_graph):
    """Tọa độ node 4 phải trả về node 4."""
    idx = NearestNodeIndex(simple_graph)
    lat = simple_graph.nodes[4]["y"]
    lon = simple_graph.nodes[4]["x"]
    assert idx.find(lat, lon) == 4


def test_find_nearest_to_midpoint(simple_graph):
    """Điểm giữa node 1 và node 2 phải snap về node gần hơn."""
    idx = NearestNodeIndex(simple_graph)
    # Node 1: lon=106.001, Node 2: lon=106.002
    # lon=106.0015 → gần Node 1 và 2 như nhau, chọn node nhỏ hơn (KDTree first match)
    result = idx.find(10.0, 106.0015)
    assert result in (1, 2)


def test_find_off_to_the_left(simple_graph):
    """Điểm bên trái node 0 phải trả về node 0."""
    idx = NearestNodeIndex(simple_graph)
    assert idx.find(10.0, 105.99) == 0


def test_find_off_to_the_right(simple_graph):
    """Điểm bên phải node 4 phải trả về node 4."""
    idx = NearestNodeIndex(simple_graph)
    assert idx.find(10.0, 106.01) == 4


def test_find_batch_empty(simple_graph):
    idx = NearestNodeIndex(simple_graph)
    assert idx.find_batch([]) == []


def test_find_batch_all_nodes(simple_graph):
    idx = NearestNodeIndex(simple_graph)
    points = [(simple_graph.nodes[i]["y"], simple_graph.nodes[i]["x"]) for i in range(5)]
    results = idx.find_batch(points)
    assert results == list(range(5))


def test_find_batch_length(simple_graph):
    idx = NearestNodeIndex(simple_graph)
    points = [(10.0, 106.0), (10.0, 106.002), (10.0, 106.004)]
    results = idx.find_batch(points)
    assert len(results) == 3


def test_empty_graph_raises():
    import networkx as nx
    G = nx.DiGraph()
    with pytest.raises(ValueError, match="không có node"):
        NearestNodeIndex(G)
