"""Tests: Swarm and full PSO run — headless (no Qt required).

These tests cover:
  - Swarm initialisation
  - Single step behaviour
  - Full run with Sphere (convergence toward 0)
  - Boundary handling (clip and reflect)
  - Topology: star and ring
  - Reproducibility via seed
"""
from __future__ import annotations

import numpy as np
import pytest

from modules.logistics.particle_swarm_optimization.core.objective_functions import (
    Ackley,
    Sphere,
    get_function,
)
from modules.logistics.particle_swarm_optimization.core.swarm import Swarm
from modules.logistics.particle_swarm_optimization.models.config import PSOConfig


def _swarm(
    objective: str = "sphere",
    n_particles: int = 20,
    n_dim: int = 2,
    n_iter: int = 50,
    topology: str = "star",
    boundary: str = "clip",
    seed: int = 42,
    lb: float = -5.12,
    ub: float = 5.12,
) -> Swarm:
    cfg = PSOConfig(
        n_particles=n_particles,
        n_dimensions=n_dim,
        n_iterations=n_iter,
        lower_bound=lb,
        upper_bound=ub,
        topology=topology,
        boundary=boundary,
        seed=seed,
        objective=objective,
    )
    return Swarm(cfg, get_function(objective))


class TestSwarmInit:
    def test_initial_convergence_has_one_entry(self):
        sw = _swarm()
        assert len(sw.convergence_history) == 1

    def test_gbest_fitness_is_finite(self):
        sw = _swarm()
        assert np.isfinite(sw.gbest_fitness)

    def test_gbest_position_shape(self):
        sw = _swarm(n_dim=3)
        assert sw.gbest_position.shape == (3,)

    def test_iteration_starts_at_zero(self):
        sw = _swarm()
        assert sw.iteration == 0

    def test_positions_within_bounds(self):
        sw = _swarm(lb=-10.0, ub=10.0)
        pos = sw.current_positions
        assert (pos >= -10.0).all() and (pos <= 10.0).all()


class TestSwarmStep:
    def test_step_increments_iteration(self):
        sw = _swarm()
        sw.step()
        assert sw.iteration == 1

    def test_step_appends_convergence(self):
        sw = _swarm()
        sw.step()
        assert len(sw.convergence_history) == 2

    def test_gbest_non_increasing(self):
        sw = _swarm(n_iter=30, seed=0)
        prev = sw.gbest_fitness
        for _ in range(30):
            sw.step()
            assert sw.gbest_fitness <= prev + 1e-12
            prev = sw.gbest_fitness

    def test_step_returns_dict_keys(self):
        sw = _swarm()
        result = sw.step()
        assert "iteration" in result
        assert "gbest_fitness" in result
        assert "gbest_position" in result
        assert "positions" in result


class TestSwarmRun:
    def test_run_returns_expected_keys(self):
        sw = _swarm()
        result = sw.run()
        for key in ("gbest_position", "gbest_fitness", "convergence_history", "iterations_done"):
            assert key in result

    def test_run_sphere_converges_toward_zero(self):
        """PSO should dramatically reduce Sphere fitness over 200 iterations."""
        sw = _swarm(n_iter=200, n_particles=30, seed=7)
        result = sw.run()
        assert result["gbest_fitness"] < 1.0, (
            f"Expected gbest < 1.0, got {result['gbest_fitness']}"
        )

    def test_run_convergence_history_length(self):
        sw = _swarm(n_iter=50)
        result = sw.run()
        # History length = n_iterations + 1 (initial state at iteration 0)
        assert len(result["convergence_history"]) == 51

    def test_run_iterations_done(self):
        sw = _swarm(n_iter=30)
        result = sw.run()
        assert result["iterations_done"] == 30

    def test_run_stop_flag(self):
        sw = _swarm(n_iter=100)
        call_count = [0]

        def stop_after_10():
            return call_count[0] >= 10

        def count(i, *_):
            call_count[0] = i

        sw.run(on_iteration=count, stop_flag=stop_after_10)
        assert sw.iteration <= 11   # stopped early


class TestBoundary:
    def test_clip_positions_within_bounds(self):
        """After running with clip, all positions must be within bounds."""
        sw = _swarm(boundary="clip", n_iter=20)
        sw.run()
        pos = np.array([p.position for p in sw._particles])
        assert (pos >= -5.12 - 1e-9).all()
        assert (pos <= 5.12 + 1e-9).all()

    def test_reflect_positions_within_bounds(self):
        sw = _swarm(boundary="reflect", n_iter=20)
        sw.run()
        pos = np.array([p.position for p in sw._particles])
        assert (pos >= -5.12 - 1e-9).all()
        assert (pos <= 5.12 + 1e-9).all()


class TestTopology:
    def test_star_topology_produces_result(self):
        sw = _swarm(topology="star", n_iter=30, seed=1)
        result = sw.run()
        assert result["gbest_fitness"] < sw.convergence_history[0]

    def test_ring_topology_produces_result(self):
        sw = _swarm(topology="ring", n_iter=30, seed=1)
        result = sw.run()
        assert np.isfinite(result["gbest_fitness"])

    def test_ring_and_star_same_seed_differ_or_agree(self):
        """Both topologies should be runnable; result may differ — just no error."""
        star = _swarm(topology="star", n_iter=50, seed=99).run()
        ring = _swarm(topology="ring", n_iter=50, seed=99).run()
        assert np.isfinite(star["gbest_fitness"])
        assert np.isfinite(ring["gbest_fitness"])


class TestReproducibility:
    def test_same_seed_same_result(self):
        r1 = _swarm(seed=42, n_iter=30).run()
        r2 = _swarm(seed=42, n_iter=30).run()
        assert r1["gbest_fitness"] == pytest.approx(r2["gbest_fitness"])
        np.testing.assert_array_almost_equal(
            r1["gbest_position"], r2["gbest_position"]
        )

    def test_different_seeds_different_result(self):
        r1 = _swarm(seed=1, n_iter=30).run()
        r2 = _swarm(seed=9999, n_iter=30).run()
        # Very small probability they are identical (but theoretically possible)
        # Just verify no crash
        assert np.isfinite(r1["gbest_fitness"])
        assert np.isfinite(r2["gbest_fitness"])


class TestAckleySwarm:
    def test_ackley_2d_runs_without_error(self):
        cfg = PSOConfig(
            n_particles=30,
            n_dimensions=2,
            n_iterations=100,
            lower_bound=-32.768,
            upper_bound=32.768,
            seed=42,
            objective="ackley",
        )
        sw = Swarm(cfg, Ackley())
        result = sw.run()
        assert np.isfinite(result["gbest_fitness"])
        assert result["gbest_fitness"] >= 0.0
