"""distance_matrix.py — Tính ma trận chi phí shortest-path từ NetworkX DiGraph.

Public API:
    build_matrix(graph, node_ids) -> np.ndarray  shape (n, n)

Ma trận[i][j] = khoảng cách ngắn nhất (metres) từ node_ids[i] đến node_ids[j].
Cặp không kết nối được = np.inf.  Đường chéo = 0.
"""
from __future__ import annotations

import numpy as np
import networkx as nx


def build_matrix(
    graph: nx.DiGraph,
    node_ids: list[int],
) -> np.ndarray:
    """Compute all-pairs shortest-path distance matrix for the given nodes.

    Uses Dijkstra (single-source) once per source node for efficiency.

    Args:
        graph    : Directed graph with edge attribute ``"weight"`` (metres).
        node_ids : Ordered list of node IDs; index 0 is conventionally the depot.

    Returns:
        ``np.ndarray`` of shape ``(n, n)``, dtype ``float64``.
        Unreachable pairs are ``np.inf``.

    Raises:
        ValueError: if ``node_ids`` is empty.
    """
    n = len(node_ids)
    if n == 0:
        raise ValueError("node_ids không được rỗng.")

    matrix = np.full((n, n), np.inf, dtype=np.float64)
    np.fill_diagonal(matrix, 0.0)

    node_to_idx = {nid: i for i, nid in enumerate(node_ids)}

    for i, src in enumerate(node_ids):
        try:
            lengths: dict[int, float] = nx.single_source_dijkstra_path_length(
                graph, src, weight="weight"
            )
        except nx.NodeNotFound:
            continue  # leave row as inf

        for tgt, dist in lengths.items():
            j = node_to_idx.get(tgt)
            if j is not None:
                matrix[i, j] = dist

    return matrix
