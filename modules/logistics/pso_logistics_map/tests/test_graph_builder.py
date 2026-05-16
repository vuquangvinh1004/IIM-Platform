"""test_graph_builder.py — Unit tests cho core/graph_builder.py."""
from __future__ import annotations

import pickle
import tempfile
from pathlib import Path

import networkx as nx
import pytest

from modules.logistics.pso_logistics_map.core.graph_builder import (
    build_graph,
    load_or_build,
)


# --------------------------------------------------------------------------- #
#  build_graph                                                                 #
# --------------------------------------------------------------------------- #

@pytest.fixture()
def sample_nodes_edges():
    nodes = {
        10: (10.0, 106.0),
        20: (10.001, 106.001),
        30: (10.002, 106.002),
    }
    edges = [
        (10, 20, 100.0),
        (20, 10, 100.0),
        (20, 30, 150.0),
        (30, 20, 150.0),
    ]
    return nodes, edges


def test_build_graph_node_count(sample_nodes_edges):
    nodes, edges = sample_nodes_edges
    G = build_graph(nodes, edges)
    assert len(G.nodes) == 3


def test_build_graph_edge_count(sample_nodes_edges):
    nodes, edges = sample_nodes_edges
    G = build_graph(nodes, edges)
    assert len(G.edges) == 4


def test_build_graph_node_attrs(sample_nodes_edges):
    nodes, edges = sample_nodes_edges
    G = build_graph(nodes, edges)
    assert G.nodes[10]["y"] == pytest.approx(10.0)
    assert G.nodes[10]["x"] == pytest.approx(106.0)
    assert G.nodes[20]["y"] == pytest.approx(10.001)


def test_build_graph_edge_weight(sample_nodes_edges):
    nodes, edges = sample_nodes_edges
    G = build_graph(nodes, edges)
    assert G[10][20]["weight"] == pytest.approx(100.0)
    assert G[20][30]["weight"] == pytest.approx(150.0)


def test_build_graph_is_digraph(sample_nodes_edges):
    nodes, edges = sample_nodes_edges
    G = build_graph(nodes, edges)
    assert isinstance(G, nx.DiGraph)


def test_build_graph_keeps_minimum_weight():
    """Nếu có hai edge (u,v) thì giữ edge có weight nhỏ hơn."""
    nodes = {1: (10.0, 106.0), 2: (10.001, 106.001)}
    edges = [(1, 2, 300.0), (1, 2, 100.0)]
    G = build_graph(nodes, edges)
    assert G[1][2]["weight"] == pytest.approx(100.0)


def test_build_graph_empty():
    G = build_graph({}, [])
    assert len(G.nodes) == 0
    assert len(G.edges) == 0


# --------------------------------------------------------------------------- #
#  load_or_build — cache                                                        #
# --------------------------------------------------------------------------- #

def test_load_or_build_creates_cache(sample_nodes_edges, tmp_path, monkeypatch):
    nodes, edges = sample_nodes_edges
    cache_path = tmp_path / "test_cache.pkl"

    # Patch pbf_loader.load_network để không cần file thật
    monkeypatch.setattr(
        "modules.logistics.pso_logistics_map.core.graph_builder.load_network",
        lambda pbf, nt, bbox=None: (nodes, edges),
    )

    G = load_or_build("fake.pbf", str(cache_path))
    assert cache_path.exists(), "Cache file phải được tạo"
    assert len(G.nodes) == 3


def test_load_or_build_reads_from_cache(sample_nodes_edges, tmp_path, monkeypatch):
    nodes, edges = sample_nodes_edges
    cache_path = tmp_path / "cache.pkl"

    # Tạo cache trước
    G_original = build_graph(nodes, edges)
    with cache_path.open("wb") as fh:
        pickle.dump(G_original, fh)

    call_count = {"n": 0}

    def fake_load(pbf, nt, bbox=None):
        call_count["n"] += 1
        return nodes, edges

    monkeypatch.setattr(
        "modules.logistics.pso_logistics_map.core.graph_builder.load_network",
        fake_load,
    )

    G = load_or_build("fake.pbf", str(cache_path))
    assert call_count["n"] == 0, "Phải dùng cache, không gọi load_network"
    assert len(G.nodes) == 3


def test_load_or_build_cache_roundtrip(sample_nodes_edges, tmp_path, monkeypatch):
    nodes, edges = sample_nodes_edges
    cache_path = tmp_path / "roundtrip.pkl"

    monkeypatch.setattr(
        "modules.logistics.pso_logistics_map.core.graph_builder.load_network",
        lambda pbf, nt, bbox=None: (nodes, edges),
    )

    G1 = load_or_build("fake.pbf", str(cache_path))
    G2 = load_or_build("fake.pbf", str(cache_path))

    assert set(G1.nodes) == set(G2.nodes)
    assert set(G1.edges) == set(G2.edges)
