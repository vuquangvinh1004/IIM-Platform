"""Numerical computation tests for multiple_linear_regression_3d."""
from __future__ import annotations

import numpy as np
import pytest

from modules.statistics.multiple_linear_regression_3d.module import (
    _regression_metrics,
    _solve_ols_two_predictors,
)


def test_solve_ols_exact_recovery() -> None:
    x1 = np.array([1.0, 2.0, 4.0, 5.0, 7.0, 9.0], dtype=float)
    x2 = np.array([2.0, 1.0, 3.0, 0.0, 4.0, 6.0], dtype=float)

    b0_true = 3.5
    b1_true = 1.2
    b2_true = -0.8
    y = b0_true + b1_true * x1 + b2_true * x2

    beta = _solve_ols_two_predictors(x1, x2, y)

    assert beta[0] == pytest.approx(b0_true, abs=1e-10)
    assert beta[1] == pytest.approx(b1_true, abs=1e-10)
    assert beta[2] == pytest.approx(b2_true, abs=1e-10)


def test_solve_ols_rank_deficient_raises() -> None:
    x1 = np.array([1.0, 2.0, 3.0, 4.0], dtype=float)
    x2 = 2.0 * x1  # collinear -> singular design for 2 predictors
    y = np.array([5.0, 7.0, 9.0, 11.0], dtype=float)

    with pytest.raises(ValueError):
        _solve_ols_two_predictors(x1, x2, y)


def test_regression_metrics_perfect_fit() -> None:
    y = np.array([2.0, 4.0, 6.0, 8.0, 10.0], dtype=float)
    y_hat = y.copy()

    sse, sst, r2, adj_r2 = _regression_metrics(y, y_hat, predictor_count=2)

    assert sse == pytest.approx(0.0)
    assert sst > 0.0
    assert r2 == pytest.approx(1.0)
    assert adj_r2 == pytest.approx(1.0)


def test_regression_metrics_non_perfect_fit() -> None:
    y = np.array([2.0, 3.5, 5.0, 6.5, 8.0, 10.5], dtype=float)
    y_hat = np.array([2.1, 3.2, 5.2, 6.8, 7.6, 10.0], dtype=float)

    sse, sst, r2, adj_r2 = _regression_metrics(y, y_hat, predictor_count=2)

    expected_sse = float(np.sum((y - y_hat) ** 2))
    expected_sst = float(np.sum((y - np.mean(y)) ** 2))
    expected_r2 = 1.0 - (expected_sse / expected_sst)
    expected_adj = 1.0 - ((1.0 - expected_r2) * (len(y) - 1) / (len(y) - 2 - 1))

    assert sse == pytest.approx(expected_sse)
    assert sst == pytest.approx(expected_sst)
    assert r2 == pytest.approx(expected_r2)
    assert adj_r2 == pytest.approx(expected_adj)
