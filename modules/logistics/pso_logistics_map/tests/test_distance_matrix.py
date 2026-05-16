"""test_distance_matrix.py — Unit tests cho core/distance_matrix.py."""
from __future__ import annotations

import numpy as np
import pytest

from modules.logistics.pso_logistics_map.core.distance_matrix import build_matrix


# --------------------------------------------------------------------------- #
#  Tests trên simple_graph (fixture từ conftest.py)                            #
# --------------------------------------------------------------------------- #

def test_matrix_shape(simple_graph):
    node_ids = list(simple_graph.nodes)
    mat = build_matrix(simple_graph, node_ids)
    n = len(node_ids)
    assert mat.shape == (n, n)


def test_matrix_diagonal_zero(simple_graph):
    node_ids = list(simple_graph.nodes)
    mat = build_matrix(simple_graph, node_ids)
    np.testing.assert_array_equal(np.diag(mat), 0.0)


def test_matrix_no_inf_on_bidirectional(simple_graph):
    """Graph hai chiều liên thông hoàn toàn — không có inf."""
    node_ids = list(simple_graph.nodes)
    mat = build_matrix(simple_graph, node_ids)
    assert not np.any(np.isinf(mat))


def test_matrix_known_path(simple_graph):
    """Node 0→2: weight 100+200=300, node 0→4: 100+200+300+400=1000."""
    node_ids = [0, 1, 2, 3, 4]
    mat = build_matrix(simple_graph, node_ids)
    assert mat[0, 2] == pytest.approx(300.0)
    assert mat[0, 4] == pytest.approx(1000.0)


def test_matrix_symmetry_bidirectional(simple_graph):
    """Graph hai chiều → ma trận phải đối xứng."""
    node_ids = list(simple_graph.nodes)
    mat = build_matrix(simple_graph, node_ids)
    np.testing.assert_allclose(mat, mat.T)


def test_matrix_triangle_one_way(triangle_graph):
    """Graph một chiều: 0→1→2→0.
    0→1 = 100, 0→2 = 250 (qua 1), 1→0 = 450 (qua 2), 2→0 = 200.
    """
    node_ids = [0, 1, 2]
    mat = build_matrix(triangle_graph, node_ids)
    assert mat[0, 1] == pytest.approx(100.0)
    assert mat[0, 2] == pytest.approx(250.0)   # 100+150
    assert mat[1, 0] == pytest.approx(350.0)   # 150+200
    assert mat[2, 0] == pytest.approx(200.0)


def test_matrix_single_node(simple_graph):
    mat = build_matrix(simple_graph, [2])
    assert mat.shape == (1, 1)
    assert mat[0, 0] == 0.0


def test_matrix_empty_raises():
    import networkx as nx
    G = nx.DiGraph()
    with pytest.raises(ValueError, match="rỗng"):
        build_matrix(G, [])


def test_matrix_dtype(simple_graph):
    node_ids = list(simple_graph.nodes)
    mat = build_matrix(simple_graph, node_ids)
    assert mat.dtype == np.float64


def test_matrix_unreachable_node():
    """Node cô lập không kết nối với phần còn lại → row và col đều inf (trừ diagonal)."""
    import networkx as nx
    G = nx.DiGraph()
    G.add_node(0, y=10.0, x=106.0)
    G.add_node(1, y=10.001, x=106.001)
    G.add_node(99, y=11.0, x=107.0)      # node cô lập
    G.add_edge(0, 1, weight=100.0)
    G.add_edge(1, 0, weight=100.0)

    mat = build_matrix(G, [0, 1, 99])
    assert np.isinf(mat[0, 2]), "0→99 phải inf"
    assert np.isinf(mat[2, 0]), "99→0 phải inf"
    assert mat[2, 2] == 0.0, "diagonal 99→99 phải 0"
