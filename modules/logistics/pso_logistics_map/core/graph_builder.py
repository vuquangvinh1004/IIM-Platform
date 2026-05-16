"""graph_builder.py — Xây NetworkX DiGraph từ nodes/edges và quản lý pickle cache.

Public API:
    build_graph(nodes, edges) -> nx.DiGraph
    load_or_build(pbf_path, cache_path, network_type) -> nx.DiGraph

Node attributes : x (lon), y (lat)
Edge attribute  : weight (metres, shortest if duplicate edges)
"""
from __future__ import annotations

import pickle
from pathlib import Path

import networkx as nx

from .pbf_loader import BBox, load_network


def build_graph(
    nodes: dict[int, tuple[float, float]],
    edges: list[tuple[int, int, float]],
) -> nx.DiGraph:
    """Build a weighted directed graph from raw nodes/edges dicts.

    Args:
        nodes : ``{node_id: (lat, lon)}``
        edges : ``[(u_id, v_id, length_m), ...]``

    Returns:
        ``nx.DiGraph`` with node attrs ``y=lat, x=lon``
        and edge attr ``weight=length_metres``.
    """
    G: nx.DiGraph = nx.DiGraph()

    for node_id, (lat, lon) in nodes.items():
        G.add_node(node_id, y=lat, x=lon)

    for u, v, length in edges:
        # Keep minimum weight if multiple parallel edges exist
        if G.has_edge(u, v):
            if length < G[u][v]["weight"]:
                G[u][v]["weight"] = length
        else:
            G.add_edge(u, v, weight=length)

    return G


def load_or_build(
    pbf_path: str | Path,
    cache_path: str | Path,
    network_type: str = "driving",
    bbox: BBox | None = None,
) -> nx.DiGraph:
    """Return graph from pickle cache when available; otherwise parse .pbf.

    Args:
        pbf_path     : Path to the local .pbf file.
        cache_path   : Path for the pickle cache (created automatically).
        network_type : ``"driving"`` | ``"walking"`` | ``"cycling"``
        bbox         : Optional ``(min_lat, min_lon, max_lat, max_lon)`` to clip
                       the network to a region.  Use ``KNOWN_BBOXES`` from
                       ``pbf_loader`` for pre-defined areas.

    Returns:
        ``nx.DiGraph`` ready for shortest-path queries.
    """
    cache = Path(cache_path)

    if cache.exists():
        with cache.open("rb") as fh:
            return pickle.load(fh)  # noqa: S301 — trusted local file

    nodes, edges = load_network(pbf_path, network_type, bbox=bbox)
    G = build_graph(nodes, edges)

    cache.parent.mkdir(parents=True, exist_ok=True)
    with cache.open("wb") as fh:
        pickle.dump(G, fh, protocol=pickle.HIGHEST_PROTOCOL)

    return G
