"""test_discrete_swarm.py — Unit tests for DiscreteSwarm (PSO engine)."""
from __future__ import annotations

import random
import threading
from typing import Any

import pytest

from modules.logistics.pso_logistics.core.discrete_swarm import DiscreteSwarm
from modules.logistics.pso_logistics.models.config import LogisticsPSOConfig
from modules.logistics.pso_logistics.problems.tsp_problem import TSPProblem

# ── fixtures ──────────────────────────────────────────────────────────────────


def _make_problem(n: int = 8, seed: int = 1) -> TSPProblem:
    return TSPProblem.generate(n_customers=n, coord_range=50.0, data_seed=seed)


def _make_config(**kwargs: Any) -> LogisticsPSOConfig:
    defaults = dict(
        n_customers=8,
        coord_range=50.0,
        data_seed=1,
        n_particles=15,
        n_iterations=30,
        w=0.5,
        c1=1.5,
        c2=1.5,
        n_ops_max=3,
        topology="star",
        pso_seed=42,
        step_delay_ms=0,
    )
    defaults.update(kwargs)
    return LogisticsPSOConfig(**defaults)


def _make_swarm(n: int = 8, **kwargs: Any) -> DiscreteSwarm:
    config = _make_config(n_customers=n, **kwargs)
    problem = _make_problem(n, seed=config.data_seed)
    rng = random.Random(config.pso_seed)
    return DiscreteSwarm(config, problem, rng)


# ── initialisation ────────────────────────────────────────────────────────────


def test_init_particle_count():
    swarm = _make_swarm(n_particles=20)
    assert len(swarm.particles) == 20


def test_init_gbest_finite():
    swarm = _make_swarm()
    assert swarm.gbest_fitness < float("inf")


def test_init_convergence_history_length():
    swarm = _make_swarm()
    # Initial gbest is recorded as iteration 0
    assert len(swarm.convergence_history) == 1


def test_init_gbest_in_convergence():
    swarm = _make_swarm()
    assert swarm.convergence_history[0] == swarm.gbest_fitness


def test_init_all_particles_valid_permutation():
    n = 10
    swarm = _make_swarm(n=n)
    for p in swarm.particles:
        assert sorted(p.position) == list(range(n))


# ── step() ────────────────────────────────────────────────────────────────────


def test_step_increments_iteration():
    swarm = _make_swarm()
    assert swarm.iteration == 0
    swarm.step()
    assert swarm.iteration == 1
    swarm.step()
    assert swarm.iteration == 2


def test_step_appends_convergence():
    swarm = _make_swarm()
    before = len(swarm.convergence_history)
    swarm.step()
    assert len(swarm.convergence_history) == before + 1


def test_step_returns_required_keys():
    swarm = _make_swarm()
    result = swarm.step()
    for key in ("iteration", "gbest_fitness", "gbest_position", "positions"):
        assert key in result


def test_step_gbest_nondecreasing():
    """gbest_fitness must be non-increasing across iterations."""
    swarm = _make_swarm(n_iterations=40)
    prev = swarm.gbest_fitness
    for _ in range(40):
        result = swarm.step()
        assert result["gbest_fitness"] <= prev + 1e-9
        prev = result["gbest_fitness"]


def test_step_positions_are_valid_permutations():
    n = 8
    swarm = _make_swarm(n=n)
    result = swarm.step()
    for pos in result["positions"]:
        assert sorted(pos) == list(range(n))


def test_step_gbest_position_valid_permutation():
    n = 8
    swarm = _make_swarm(n=n)
    result = swarm.step()
    assert sorted(result["gbest_position"]) == list(range(n))


# ── run() ─────────────────────────────────────────────────────────────────────


def test_run_returns_required_keys():
    swarm = _make_swarm(n_iterations=10)
    summary = swarm.run()
    for key in ("gbest_position", "gbest_fitness", "convergence_history", "iterations_done"):
        assert key in summary


def test_run_convergence_history_length():
    n_iter = 25
    swarm = _make_swarm(n_iterations=n_iter)
    summary = swarm.run()
    # init entry + n_iter steps = n_iter + 1
    assert len(summary["convergence_history"]) == n_iter + 1


def test_run_iterations_done():
    n_iter = 20
    swarm = _make_swarm(n_iterations=n_iter)
    summary = swarm.run()
    assert summary["iterations_done"] == n_iter


def test_run_gbest_valid_permutation():
    n = 8
    swarm = _make_swarm(n=n)
    summary = swarm.run()
    assert sorted(summary["gbest_position"]) == list(range(n))


# ── topology ──────────────────────────────────────────────────────────────────


def test_ring_topology_produces_valid_result():
    swarm = _make_swarm(topology="ring", n_iterations=15)
    summary = swarm.run()
    assert sorted(summary["gbest_position"]) == list(range(8))


def test_star_topology_produces_valid_result():
    swarm = _make_swarm(topology="star", n_iterations=15)
    summary = swarm.run()
    assert sorted(summary["gbest_position"]) == list(range(8))


# ── reproducibility ───────────────────────────────────────────────────────────


def test_reproducible_same_seed():
    config = _make_config(pso_seed=99)
    problem = _make_problem(8, seed=config.data_seed)

    rng1 = random.Random(config.pso_seed)
    s1 = DiscreteSwarm(config, problem, rng1)
    res1 = s1.run()

    rng2 = random.Random(config.pso_seed)
    s2 = DiscreteSwarm(config, problem, rng2)
    res2 = s2.run()

    assert res1["gbest_fitness"] == pytest.approx(res2["gbest_fitness"])
    assert res1["gbest_position"] == res2["gbest_position"]


def test_different_seeds_may_differ():
    """Not guaranteed to differ due to chance, but statistically very likely."""
    config_a = _make_config(pso_seed=1)
    config_b = _make_config(pso_seed=9999)
    problem = _make_problem()

    rng_a = random.Random(config_a.pso_seed)
    s_a = DiscreteSwarm(config_a, problem, rng_a)
    h_a = s_a.run()["convergence_history"]

    rng_b = random.Random(config_b.pso_seed)
    s_b = DiscreteSwarm(config_b, problem, rng_b)
    h_b = s_b.run()["convergence_history"]

    # At least one intermediate value should differ
    assert h_a != h_b


# ── stop_flag ─────────────────────────────────────────────────────────────────


def test_run_stop_flag():
    """run() should exit early when stop_flag returns True."""
    stop_after = 5
    call_count: list[int] = [0]

    def _stop() -> bool:
        call_count[0] += 1
        return call_count[0] >= stop_after

    swarm = _make_swarm(n_iterations=100)
    summary = swarm.run(stop_flag=_stop)
    assert summary["iterations_done"] < 100


# ── on_iteration callback ─────────────────────────────────────────────────────


def test_run_on_iteration_callback():
    n_iter = 15
    results: list[dict] = []
    swarm = _make_swarm(n_iterations=n_iter)
    swarm.run(on_iteration=results.append)
    assert len(results) == n_iter
    for r in results:
        assert "iteration" in r
        assert "gbest_fitness" in r
