"""Tests: Particle class behaviour."""
from __future__ import annotations

import numpy as np
import pytest

from modules.logistics.particle_swarm_optimization.core.particle import Particle


def _make_particle(pos=(1.0, 2.0), vel=(0.1, -0.1), fitness=5.0) -> Particle:
    return Particle(
        position=np.array(pos),
        velocity=np.array(vel),
        fitness=fitness,
    )


class TestParticle:
    def test_initial_pbest_equals_initial_position(self):
        p = _make_particle(pos=(3.0, 4.0), fitness=25.0)
        np.testing.assert_array_equal(p.pbest_position, p.position)
        assert p.pbest_fitness == 25.0

    def test_position_is_copy(self):
        arr = np.array([1.0, 2.0])
        p = Particle(position=arr, velocity=arr, fitness=0.0)
        arr[0] = 99.0
        assert p.position[0] == pytest.approx(1.0)  # not affected

    def test_velocity_is_copy(self):
        arr = np.array([0.5, 0.5])
        p = Particle(position=np.zeros(2), velocity=arr, fitness=0.0)
        arr[0] = 99.0
        assert p.velocity[0] == pytest.approx(0.5)

    def test_update_pbest_improves(self):
        p = _make_particle(fitness=10.0)
        p.position = np.array([0.1, 0.1])
        p.fitness = 0.02
        p.update_pbest()
        assert p.pbest_fitness == pytest.approx(0.02)
        np.testing.assert_array_almost_equal(p.pbest_position, [0.1, 0.1])

    def test_update_pbest_no_improvement(self):
        p = _make_particle(pos=(1.0, 1.0), fitness=2.0)
        p.position = np.array([5.0, 5.0])
        p.fitness = 50.0   # worse
        p.update_pbest()
        assert p.pbest_fitness == pytest.approx(2.0)
        np.testing.assert_array_almost_equal(p.pbest_position, [1.0, 1.0])

    def test_update_pbest_equal_no_change(self):
        p = _make_particle(fitness=5.0)
        p.fitness = 5.0   # same — no strict improvement
        original_pbest = p.pbest_position.copy()
        p.update_pbest()
        np.testing.assert_array_equal(p.pbest_position, original_pbest)
