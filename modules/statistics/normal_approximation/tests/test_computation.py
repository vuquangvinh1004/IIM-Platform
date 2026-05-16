"""Unit tests for the pure computation functions in normal_approximation."""
from __future__ import annotations

import math

import pytest

from modules.statistics.normal_approximation.module import (
    _binom_pmf,
    _normal_pdf,
    _poisson_pmf,
)

import numpy as np


# ── Binomial PMF ──────────────────────────────────────────────────────────────

class TestBinomPmf:

    def test_basic_known_value(self):
        # B(10, 0.5): P(X=5) = C(10,5) * 0.5^10 = 252/1024
        result = _binom_pmf(5, 10, 0.5)
        expected = 252 / 1024
        assert abs(result - expected) < 1e-12

    def test_k_zero(self):
        # P(X=0) = (1-p)^n
        result = _binom_pmf(0, 10, 0.3)
        expected = 0.7 ** 10
        assert abs(result - expected) < 1e-12

    def test_k_equals_n(self):
        # P(X=n) = p^n
        result = _binom_pmf(5, 5, 0.4)
        expected = 0.4 ** 5
        assert abs(result - expected) < 1e-12

    def test_k_out_of_range_negative(self):
        assert _binom_pmf(-1, 10, 0.5) == 0.0

    def test_k_out_of_range_above_n(self):
        assert _binom_pmf(11, 10, 0.5) == 0.0

    def test_p_zero(self):
        assert _binom_pmf(0, 10, 0.0) == 1.0
        assert _binom_pmf(1, 10, 0.0) == 0.0

    def test_p_one(self):
        assert _binom_pmf(10, 10, 1.0) == 1.0
        assert _binom_pmf(9, 10, 1.0) == 0.0

    def test_probabilities_sum_to_one(self):
        n, p = 30, 0.4
        total = sum(_binom_pmf(k, n, p) for k in range(n + 1))
        assert abs(total - 1.0) < 1e-10

    def test_large_n_does_not_overflow(self):
        # n=300 with p=0.5 — log-space evaluation must not raise
        total = sum(_binom_pmf(k, 300, 0.5) for k in range(301))
        assert abs(total - 1.0) < 1e-8


# ── Poisson PMF ───────────────────────────────────────────────────────────────

class TestPoissonPmf:

    def test_known_value_lam1(self):
        # P(μ=1): P(X=0) = e^-1
        result = _poisson_pmf(0, 1.0)
        assert abs(result - math.exp(-1.0)) < 1e-12

    def test_known_value_lam5(self):
        # P(μ=5): P(X=3) = e^-5 * 5^3 / 6
        result = _poisson_pmf(3, 5.0)
        expected = math.exp(-5.0) * (5.0 ** 3) / math.factorial(3)
        assert abs(result - expected) < 1e-12

    def test_k_negative(self):
        assert _poisson_pmf(-1, 5.0) == 0.0

    def test_lam_zero(self):
        assert _poisson_pmf(0, 0.0) == 0.0

    def test_probabilities_sum_to_one(self):
        lam = 8.0
        k_max = int(lam + 10 * math.sqrt(lam)) + 1
        total = sum(_poisson_pmf(k, lam) for k in range(k_max))
        assert abs(total - 1.0) < 1e-6

    def test_large_lambda_does_not_overflow(self):
        # μ=80 — high rate, log-space must stay stable
        lam = 80.0
        k_max = int(lam + 6 * math.sqrt(lam)) + 1
        total = sum(_poisson_pmf(k, lam) for k in range(k_max))
        assert abs(total - 1.0) < 1e-5


# ── Normal PDF ────────────────────────────────────────────────────────────────

class TestNormalPdf:

    def test_peak_at_mean(self):
        # PDF maximum at x=μ equals 1/(σ√2π)
        mu, sigma = 5.0, 2.0
        x = np.array([mu])
        result = _normal_pdf(x, mu, sigma)[0]
        expected = 1.0 / (sigma * math.sqrt(2.0 * math.pi))
        assert abs(result - expected) < 1e-12

    def test_symmetry(self):
        mu, sigma = 0.0, 1.0
        x_pos = np.array([1.5])
        x_neg = np.array([-1.5])
        assert abs(_normal_pdf(x_pos, mu, sigma)[0] - _normal_pdf(x_neg, mu, sigma)[0]) < 1e-15

    def test_integral_approximates_one(self):
        # Numerical integration via trapezoidal rule over ±6σ should be ≈ 1
        mu, sigma = 3.0, 1.5
        x = np.linspace(mu - 6 * sigma, mu + 6 * sigma, 10_000)
        y = _normal_pdf(x, mu, sigma)
        area = np.trapezoid(y, x)
        assert abs(area - 1.0) < 1e-5
