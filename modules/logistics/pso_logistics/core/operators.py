"""Discrete PSO operators for permutation-based routing problems.

All operators take a permutation (list[int]) and a seeded random.Random
instance, then return a new permutation.  No global state — thread-safe.

Operators:
    swap               — exchange positions of two random elements
    insert             — remove one element, re-insert at a random position
    reverse_segment    — reverse a random contiguous sub-sequence
    move_toward        — n targeted swaps that align source closer to target
    apply_random_ops   — apply n randomly-chosen operators in sequence
"""
from __future__ import annotations

import random


def swap(perm: list[int], rng: random.Random) -> list[int]:
    """Swap two randomly chosen positions.  Preserves all elements."""
    n = len(perm)
    if n < 2:
        return list(perm)
    result = list(perm)
    i, j = rng.sample(range(n), 2)
    result[i], result[j] = result[j], result[i]
    return result


def insert(perm: list[int], rng: random.Random) -> list[int]:
    """Remove element at random position i, re-insert at random position j≠i."""
    n = len(perm)
    if n < 2:
        return list(perm)
    result = list(perm)
    i = rng.randrange(n)
    elem = result.pop(i)
    j = rng.randrange(len(result) + 1)
    result.insert(j, elem)
    return result


def reverse_segment(perm: list[int], rng: random.Random) -> list[int]:
    """Reverse a randomly chosen contiguous sub-sequence (2-Or move)."""
    n = len(perm)
    if n < 2:
        return list(perm)
    result = list(perm)
    i, j = sorted(rng.sample(range(n), 2))
    result[i : j + 1] = result[i : j + 1][::-1]
    return result


def move_toward(
    source: list[int],
    target: list[int],
    rng: random.Random,
    n_steps: int,
) -> list[int]:
    """Apply up to n_steps targeted swaps to make *source* more similar to *target*.

    Each step:
    1. Find all positions where source[i] != target[i].
    2. Pick one such position i at random.
    3. Find j such that source[j] == target[i].
    4. Swap source[i] and source[j].

    Returns a new list (source unchanged).
    Stops early if source already equals target.
    """
    result = list(source)
    for _ in range(n_steps):
        diff = [i for i in range(len(result)) if result[i] != target[i]]
        if not diff:
            break
        i = rng.choice(diff)
        j = result.index(target[i])
        result[i], result[j] = result[j], result[i]
    return result


def apply_random_ops(
    perm: list[int],
    n_ops: int,
    rng: random.Random,
) -> list[int]:
    """Apply n_ops randomly-chosen operators to perm sequentially."""
    if n_ops <= 0:
        return list(perm)
    ops = [swap, insert, reverse_segment]
    result = list(perm)
    for _ in range(n_ops):
        op = rng.choice(ops)
        result = op(result, rng)
    return result
