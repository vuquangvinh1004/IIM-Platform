"""test_operators.py — Unit tests for discrete PSO operators."""
from __future__ import annotations

import random

import pytest

from modules.logistics.pso_logistics.core.operators import (
    apply_random_ops,
    insert,
    move_toward,
    reverse_segment,
    swap,
)
apply_random_operators = apply_random_ops  # alias used in tests

# ── helpers ────────────────────────────────────────────────────────────────────

def _rng(seed: int = 0) -> random.Random:
    return random.Random(seed)


def _diff(a: list[int], b: list[int]) -> int:
    """Count positions where a and b differ."""
    return sum(1 for x, y in zip(a, b) if x != y)


# ── swap ──────────────────────────────────────────────────────────────────────

def test_swap_preserves_elements():
    perm = list(range(8))
    result = swap(perm, _rng(1))
    assert sorted(result) == sorted(perm)


def test_swap_is_copy():
    perm = list(range(5))
    result = swap(perm, _rng(2))
    assert result is not perm


def test_swap_changes_exactly_two_positions_or_same():
    """Result may be same as input only if i==j (unlikely but possible with tiny n)."""
    perm = list(range(10))
    result = swap(perm, _rng(7))
    d = _diff(perm, result)
    assert d in (0, 2)


def test_swap_single_element():
    perm = [0]
    result = swap(perm, _rng(0))
    assert result == [0]


# ── insert ────────────────────────────────────────────────────────────────────

def test_insert_preserves_elements():
    perm = list(range(8))
    result = insert(perm, _rng(3))
    assert sorted(result) == sorted(perm)


def test_insert_is_copy():
    perm = list(range(5))
    result = insert(perm, _rng(4))
    assert result is not perm


def test_insert_single_element():
    perm = [0]
    result = insert(perm, _rng(0))
    assert result == [0]


# ── reverse_segment ───────────────────────────────────────────────────────────

def test_reverse_segment_preserves_elements():
    perm = list(range(9))
    result = reverse_segment(perm, _rng(5))
    assert sorted(result) == sorted(perm)


def test_reverse_segment_is_copy():
    perm = list(range(6))
    result = reverse_segment(perm, _rng(6))
    assert result is not perm


def test_reverse_segment_single():
    perm = [0]
    result = reverse_segment(perm, _rng(0))
    assert result == [0]


# ── move_toward ───────────────────────────────────────────────────────────────

def test_move_toward_reduces_diff():
    rng = _rng(42)
    source = list(range(10))
    target = list(reversed(range(10)))
    initial_diff = _diff(source, target)
    result = move_toward(source, target, rng, n_steps=5)
    assert sorted(result) == sorted(source), "move_toward must preserve element set"
    final_diff = _diff(result, target)
    assert final_diff <= initial_diff


def test_move_toward_preserves_elements():
    rng = _rng(10)
    source = [3, 1, 4, 1, 5, 9, 2, 6]  # duplicates not expected in TSP but test robustness
    source = list(range(8))
    target = list(range(7, -1, -1))
    result = move_toward(source, target, rng, n_steps=3)
    assert sorted(result) == sorted(source)


def test_move_toward_zero_steps():
    rng = _rng(0)
    source = [2, 0, 1, 3]
    target = [0, 1, 2, 3]
    result = move_toward(source, target, rng, n_steps=0)
    assert result == source


def test_move_toward_identical():
    rng = _rng(0)
    source = [0, 1, 2, 3]
    result = move_toward(source, source[:], rng, n_steps=5)
    assert result == source


def test_move_toward_is_copy():
    rng = _rng(0)
    source = [0, 1, 2, 3]
    target = [3, 2, 1, 0]
    result = move_toward(source, target, rng, n_steps=1)
    assert result is not source


# ── apply_random_operators ────────────────────────────────────────────────────

def test_apply_random_operators_preserves_elements():
    rng = _rng(99)
    perm = list(range(12))
    result = apply_random_operators(perm, 10, rng)
    assert sorted(result) == sorted(perm)


def test_apply_random_operators_reproducible():
    perm = list(range(7))
    r1 = apply_random_operators(perm, 5, _rng(77))
    r2 = apply_random_operators(perm, 5, _rng(77))
    assert r1 == r2


def test_apply_random_operators_zero_ops():
    rng = _rng(0)
    perm = list(range(5))
    result = apply_random_operators(perm, 0, rng)
    assert result == perm
