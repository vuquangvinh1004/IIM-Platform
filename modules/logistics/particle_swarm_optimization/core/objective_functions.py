"""Objective functions for PSO benchmarking.

Each function is registered via @register and can be retrieved by key.
Adding a new function: subclass ObjectiveFunction, decorate with @register,
set class attributes key and label.

Currently supported:
  sphere  — simple convex bowl (f_min = 0 at origin)
  ackley  — multimodal benchmark (f_min ≈ 0 at origin)
"""
from __future__ import annotations

import math
from abc import ABC, abstractmethod

import numpy as np

# ─── Registry ─────────────────────────────────────────────────────────────────

REGISTRY: dict[str, type[ObjectiveFunction]] = {}


def register(cls: type) -> type:
    """Class decorator: register an ObjectiveFunction subclass by its key."""
    REGISTRY[cls.key] = cls  # type: ignore[attr-defined]
    return cls


# ─── Base class ───────────────────────────────────────────────────────────────


class ObjectiveFunction(ABC):
    """Abstract base for PSO objective functions (minimization)."""

    key: str    # stable identifier, e.g. "sphere"
    label: str  # human-readable display name

    @abstractmethod
    def evaluate(self, x: np.ndarray) -> float:
        """Return scalar fitness value for position vector x.

        Lower is better (minimization problem).
        """

    @property
    def global_optimum(self) -> tuple[float, np.ndarray | None]:
        """Return (optimal_fitness, optional_position) if analytically known."""
        return float("nan"), None

    @property
    def suggested_bounds(self) -> tuple[float, float]:
        """Return (lower, upper) search bounds commonly used for this function."""
        return -5.0, 5.0


# ─── Sphere ───────────────────────────────────────────────────────────────────


@register
class Sphere(ObjectiveFunction):
    """f(x) = sum(x_i^2)

    Simple convex bowl — ideal for verifying algorithm correctness.
    Global minimum: 0 at the origin.
    """

    key = "sphere"
    label = "Sphere"

    def evaluate(self, x: np.ndarray) -> float:
        return float(np.sum(x ** 2))

    @property
    def global_optimum(self) -> tuple[float, np.ndarray | None]:
        return 0.0, None

    @property
    def suggested_bounds(self) -> tuple[float, float]:
        return -5.12, 5.12


# ─── Ackley ───────────────────────────────────────────────────────────────────


@register
class Ackley(ObjectiveFunction):
    """Ackley function — multimodal benchmark with many local minima.

    Global minimum: 0 at the origin.
    Challenging because particles can easily get trapped in local minima.
    """

    key = "ackley"
    label = "Ackley"

    # Standard Ackley parameters
    _A: float = 20.0
    _B: float = 0.2
    _C: float = 2.0 * math.pi

    def evaluate(self, x: np.ndarray) -> float:
        n = len(x)
        sum_sq = float(np.sum(x ** 2))
        sum_cos = float(np.sum(np.cos(self._C * x)))
        return float(
            -self._A * math.exp(-self._B * math.sqrt(sum_sq / n))
            - math.exp(sum_cos / n)
            + self._A
            + math.e
        )

    @property
    def global_optimum(self) -> tuple[float, np.ndarray | None]:
        return 0.0, None

    @property
    def suggested_bounds(self) -> tuple[float, float]:
        return -32.768, 32.768


# ─── Public helpers ───────────────────────────────────────────────────────────


def get_function(key: str) -> ObjectiveFunction:
    """Return a new instance of the function identified by key.

    Raises KeyError if key is not registered.
    """
    if key not in REGISTRY:
        raise KeyError(
            f"Unknown objective function: {key!r}. "
            f"Available: {sorted(REGISTRY.keys())}"
        )
    return REGISTRY[key]()


def list_functions() -> list[tuple[str, str]]:
    """Return [(key, label)] for all registered functions, in insertion order."""
    return [(k, cls.label) for k, cls in REGISTRY.items()]
