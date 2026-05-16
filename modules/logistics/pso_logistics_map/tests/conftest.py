"""conftest.py — Shared pytest fixtures cho pso_logistics_map tests."""
from __future__ import annotations

import networkx as nx
import pytest


@pytest.fixture()
def simple_graph() -> nx.DiGraph:
    """Graph 5 nodes dạng chuỗi thẳng:
        0 --(100m)--> 1 --(200m)--> 2 --(300m)--> 3 --(400m)--> 4
        (tất cả hai chiều)
    Tọa độ đặt theo kinh độ tăng dần, vĩ độ cố định 10.0
    """
    G: nx.DiGraph = nx.DiGraph()
    lons = [106.0, 106.001, 106.002, 106.003, 106.004]
    lat = 10.0
    weights = [100.0, 200.0, 300.0, 400.0]
    for i, lon in enumerate(lons):
        G.add_node(i, y=lat, x=lon)
    for i, w in enumerate(weights):
        G.add_edge(i, i + 1, weight=w)
        G.add_edge(i + 1, i, weight=w)
    return G


@pytest.fixture()
def triangle_graph() -> nx.DiGraph:
    """Graph tam giác 3 nodes không đều:
        0 --(100m)--> 1 --(150m)--> 2 --(200m)--> 0
        (một chiều — để test trường hợp đồ thị có hướng)
    """
    G: nx.DiGraph = nx.DiGraph()
    G.add_node(0, y=10.0, x=106.0)
    G.add_node(1, y=10.001, x=106.001)
    G.add_node(2, y=10.002, x=106.0)
    G.add_edge(0, 1, weight=100.0)
    G.add_edge(1, 2, weight=150.0)
    G.add_edge(2, 0, weight=200.0)
    return G
