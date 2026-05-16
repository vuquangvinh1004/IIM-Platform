"""nearest_node.py — Ánh xạ tọa độ (lat, lon) sang node_id gần nhất trên graph.

Dùng scipy.spatial.KDTree — không phụ thuộc GeoPandas.

Public API:
    NearestNodeIndex(graph) — xây KDTree từ graph
        .find(lat, lon)                   -> int
        .find_batch([(lat, lon), ...])    -> list[int]
"""
from __future__ import annotations

import numpy as np
from scipy.spatial import KDTree
import networkx as nx


class NearestNodeIndex:
    """O(log n) nearest-node lookup using KDTree on graph node coordinates.

    Args:
        graph: ``nx.DiGraph`` with node attributes ``y`` (lat) and ``x`` (lon).

    Raises:
        ValueError: if graph has no nodes.
    """

    def __init__(self, graph: nx.DiGraph) -> None:
        nodes = list(graph.nodes)
        if not nodes:
            raise ValueError("Graph không có node nào để build KDTree.")

        self._node_ids: list[int] = nodes
        coords = np.array(
            [[graph.nodes[n]["y"], graph.nodes[n]["x"]] for n in nodes],
            dtype=np.float64,
        )
        self._tree = KDTree(coords)

    def find(self, lat: float, lon: float) -> int:
        """Return node_id of the graph node nearest to (lat, lon).

        Args:
            lat: Latitude in decimal degrees.
            lon: Longitude in decimal degrees.

        Returns:
            Node ID (int) of the nearest graph node.
        """
        _, idx = self._tree.query([lat, lon])
        return self._node_ids[int(idx)]

    def find_batch(self, points: list[tuple[float, float]]) -> list[int]:
        """Return a list of nearest node_ids for a list of (lat, lon) points.

        Args:
            points: List of (lat, lon) tuples.

        Returns:
            List of node IDs, same length and order as *points*.
        """
        if not points:
            return []
        pts = np.array(points, dtype=np.float64)
        _, idxs = self._tree.query(pts)
        return [self._node_ids[int(i)] for i in idxs]
