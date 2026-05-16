"""TSPProblem — Travelling Salesman Problem trên ma trận khoảng cách thật.

Ma trận đầu vào có kích thước (n_customers + 1) × (n_customers + 1):
    hàng/cột 0         = depot
    hàng/cột 1..n      = customer 0..n-1

Particle position là một hoán vị của [0, 1, ..., n_customers - 1].
Tuyến đường:  depot → customer[perm[0]] → ... → customer[perm[-1]] → depot
"""
from __future__ import annotations

import random

import numpy as np


class TSPProblem:
    """TSP trên ma trận khoảng cách đường bộ.

    Tương thích với giao diện DiscreteSwarm:
        initial_position(rng) -> list[int]
        evaluate(perm)        -> float  (tổng khoảng cách, metres)
    """

    def __init__(self, dist_matrix: np.ndarray, n_customers: int) -> None:
        """
        Args:
            dist_matrix : mảng 2D shape (n_customers+1, n_customers+1).
                          index 0 = depot; index k+1 = customer k.
                          Giá trị float, inf = không thể đi được.
            n_customers : số điểm giao (= n_customers, không tính depot).
        """
        if dist_matrix.ndim != 2:
            raise ValueError("dist_matrix phải là mảng 2D")
        expected = n_customers + 1
        if dist_matrix.shape != (expected, expected):
            raise ValueError(
                f"dist_matrix phải có shape ({expected}, {expected}), "
                f"nhận được {dist_matrix.shape}"
            )
        if n_customers < 1:
            raise ValueError("n_customers phải >= 1")
        self._mat = dist_matrix
        self.n_customers = n_customers

    # ── Giao diện yêu cầu bởi DiscreteSwarm ──────────────────────────────────

    def initial_position(self, rng: random.Random) -> list[int]:
        """Trả về hoán vị ngẫu nhiên của [0, ..., n_customers - 1]."""
        perm = list(range(self.n_customers))
        rng.shuffle(perm)
        return perm

    def evaluate(self, perm: list[int]) -> float:
        """Tính tổng khoảng cách tuyến đường khép kín depot → ... → depot.

        Args:
            perm : hoán vị của [0, ..., n_customers - 1].

        Returns:
            Tổng khoảng cách (metres), hoặc inf nếu có cung không đi được.
        """
        mat = self._mat
        # depot = matrix index 0 ; customer k = matrix index k+1
        depot = 0
        indices = [depot] + [c + 1 for c in perm] + [depot]
        total = 0.0
        for i in range(len(indices) - 1):
            d = mat[indices[i], indices[i + 1]]
            if d == np.inf or d != d:  # inf hoặc NaN
                return float("inf")
            total += d
        return total
