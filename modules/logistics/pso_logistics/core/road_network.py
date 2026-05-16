"""Grid-based road network for PSO Logistics simulations.

Models a city street grid where vehicles must follow roads (not straight lines).
Blocked road segments simulate buildings, rivers, bridges, etc.

Coordinate system:
    Node (r, c): world position (c * cell_size,  r * cell_size)
    Index      : r * cols + c
    Row 0 = bottom (y=0), row (rows-1) = top (y=coord_range)
"""
from __future__ import annotations

import math
import random
from collections import deque
from typing import Any

import numpy as np


class RoadNetwork:
    """City-grid road network with randomly blocked road segments."""

    def __init__(
        self,
        rows: int,
        cols: int,
        cell_size: float,
        blocked: frozenset[tuple[int, int]],
    ) -> None:
        self.rows = rows
        self.cols = cols
        self.cell_size = cell_size
        self.n_nodes = rows * cols
        self._blocked = blocked
        self._adj: list[list[int]] = self._build_adj()
        # BFS cache (populated on demand; keyed by (src, dst))
        self._dist_cache: dict[tuple[int, int], float] = {}
        self._path_cache: dict[tuple[int, int], list[int]] = {}

    # ── Factory ───────────────────────────────────────────────────────────────

    @classmethod
    def generate(
        cls,
        coord_range: float,
        grid_steps: int,
        block_fraction: float,
        data_seed: int,
    ) -> "RoadNetwork":
        """Deterministically generate a city road grid.

        Args:
            coord_range   : world extents [0, coord_range]²
            grid_steps    : grid resolution (grid_steps+1 intersections per side)
            block_fraction: fraction of edges to block (0.0 = full grid, 0.3 = spare)
            data_seed     : reproducibility seed
        """
        rng = random.Random(data_seed)
        rows = cols = grid_steps + 1
        cell = coord_range / grid_steps

        # Collect all undirected edges
        all_edges: list[tuple[int, int]] = []
        for r in range(rows):
            for c in range(cols):
                idx = r * cols + c
                if c + 1 < cols:
                    all_edges.append((idx, idx + 1))        # horizontal
                if r + 1 < rows:
                    all_edges.append((idx, idx + cols))     # vertical

        # Shuffle + remove edges while keeping every node connected (degree ≥ 1)
        rng.shuffle(all_edges)
        degree = [0] * (rows * cols)
        for a, b in all_edges:
            degree[a] += 1
            degree[b] += 1

        n_block = int(len(all_edges) * block_fraction)
        blocked: set[tuple[int, int]] = set()
        removed = 0
        for a, b in all_edges:
            if removed >= n_block:
                break
            if degree[a] > 1 and degree[b] > 1:
                blocked.add((a, b))
                blocked.add((b, a))
                degree[a] -= 1
                degree[b] -= 1
                removed += 1

        return cls(rows, cols, cell, frozenset(blocked))

    # ── Graph construction ────────────────────────────────────────────────────

    def _build_adj(self) -> list[list[int]]:
        adj: list[list[int]] = [[] for _ in range(self.n_nodes)]
        rows, cols = self.rows, self.cols
        for r in range(rows):
            for c in range(cols):
                idx = r * cols + c
                for dr, dc in ((0, 1), (0, -1), (1, 0), (-1, 0)):
                    nr, nc = r + dr, c + dc
                    if 0 <= nr < rows and 0 <= nc < cols:
                        nidx = nr * cols + nc
                        if (idx, nidx) not in self._blocked:
                            adj[idx].append(nidx)
        return adj

    # ── Geometry ──────────────────────────────────────────────────────────────

    def node_xy(self, idx: int) -> tuple[float, float]:
        """World coordinates (x, y) for node index."""
        r, c = divmod(idx, self.cols)
        return c * self.cell_size, r * self.cell_size

    def nearest_node(self, x: float, y: float) -> int:
        """Closest grid intersection to world point (x, y)."""
        c = round(x / self.cell_size)
        r = round(y / self.cell_size)
        c = max(0, min(self.cols - 1, c))
        r = max(0, min(self.rows - 1, r))
        return r * self.cols + c

    # ── BFS shortest path (cached) ────────────────────────────────────────────

    def bfs(self, src: int, dst: int) -> tuple[float, list[int]]:
        """BFS on unweighted grid; returns (road_distance, path_node_list)."""
        key = (src, dst)
        if key in self._dist_cache:
            return self._dist_cache[key], self._path_cache[key]

        if src == dst:
            self._dist_cache[key] = 0.0
            self._path_cache[key] = [src]
            return 0.0, [src]

        parent: dict[int, int] = {src: -1}
        q: deque[int] = deque([src])
        found = False
        while q:
            node = q.popleft()
            if node == dst:
                found = True
                break
            for nb in self._adj[node]:
                if nb not in parent:
                    parent[nb] = node
                    q.append(nb)

        if not found:
            # Isolated node (should not occur on properly generated grid)
            sx, sy = self.node_xy(src)
            tx, ty = self.node_xy(dst)
            d = math.hypot(tx - sx, ty - sy)
            self._store(key, (dst, src), d, [src, dst])
            return d, [src, dst]

        path: list[int] = []
        cur = dst
        while cur != -1:
            path.append(cur)
            cur = parent[cur]
        path.reverse()
        d = (len(path) - 1) * self.cell_size
        self._store(key, (dst, src), d, path)
        return d, path

    def _store(
        self,
        key_fwd: tuple[int, int],
        key_rev: tuple[int, int],
        d: float,
        path: list[int],
    ) -> None:
        self._dist_cache[key_fwd] = d
        self._path_cache[key_fwd] = path
        self._dist_cache[key_rev] = d
        self._path_cache[key_rev] = list(reversed(path))

    def road_distance(self, src: int, dst: int) -> float:
        return self.bfs(src, dst)[0]

    def get_path_xy(self, src: int, dst: int) -> list[tuple[float, float]]:
        """World-coordinate waypoints for a road segment between two nodes."""
        _, path = self.bfs(src, dst)
        return [self.node_xy(n) for n in path]

    # ── Distance matrix ───────────────────────────────────────────────────────

    def build_dist_matrix(self, node_indices: list[int]) -> np.ndarray:
        """Symmetric road-distance matrix for a list of node indices.

        Also pre-populates the BFS cache for all pairs (used during route drawing).
        """
        n = len(node_indices)
        dm = np.zeros((n, n), dtype=np.float64)
        for i in range(n):
            for j in range(i + 1, n):
                d = self.road_distance(node_indices[i], node_indices[j])
                dm[i, j] = dm[j, i] = d
        return dm

    # ── Tour visualization ────────────────────────────────────────────────────

    def tour_coords(
        self,
        node_indices: list[int],
        perm: list[int],
    ) -> list[tuple[float, float]]:
        """Flat (x, y) coordinate list for a complete TSP tour along roads.

        node_indices : [depot_node_idx, cust0_idx, cust1_idx, …]
        perm         : 0-based customer visit order
        Returns      : continuous road-following path for drawing
        """
        order = (
            [node_indices[0]]
            + [node_indices[p + 1] for p in perm]
            + [node_indices[0]]
        )
        coords: list[tuple[float, float]] = []
        for i in range(len(order) - 1):
            seg = self.get_path_xy(order[i], order[i + 1])
            if coords and seg:
                seg = list(seg[1:])   # drop duplicate junction point
            coords.extend(seg)
        return coords

    # ── Drawing ───────────────────────────────────────────────────────────────

    def draw_background(self, ax: Any) -> None:
        """Draw road grid on a matplotlib Axes (zorder=1–2).

        Connected edges → light grey road lines.
        Intersection dots → subtle grey circles.
        Gaps where edges were removed visually represent buildings / obstacles.
        """
        drawn: set[tuple[int, int]] = set()
        for r in range(self.rows):
            for c in range(self.cols):
                idx = r * self.cols + c
                x1, y1 = self.node_xy(idx)
                for nb in self._adj[idx]:
                    key = (min(idx, nb), max(idx, nb))
                    if key not in drawn:
                        x2, y2 = self.node_xy(nb)
                        ax.plot(
                            [x1, x2], [y1, y2],
                            color="#CACFD2", lw=3.5, zorder=1,
                            solid_capstyle="round",
                        )
                        drawn.add(key)

        # Intersection dots
        for idx in range(self.n_nodes):
            x, y = self.node_xy(idx)
            ax.plot(x, y, "o", color="#AAB7B8", ms=3.0, zorder=2, markeredgewidth=0)
