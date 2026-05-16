"""QThread-based worker that runs PSO Logistics simulation without blocking the UI.

Thread safety:
    - Problem is regenerated from config inside run() using the same data_seed,
      so result is identical to what the UI pre-rendered.  No mutable objects
      cross the thread boundary.
    - All signal payloads use plain Python types (int, float, list).
    - _stop_requested is a plain bool; safe to flip from UI thread via GIL.

Signals emitted:
    iteration_done(int, float, list[int], list[list[int]])
        iteration, gbest_fitness, gbest_perm, all_perms

    simulation_done(dict)
        gbest_perm, gbest_fitness, convergence_history,
        iterations_done, stopped_early

    error_occurred(str)
"""
from __future__ import annotations

import random
from typing import Any

try:
    from PySide6.QtCore import QThread, Signal
    _QT = True
except ImportError:  # pragma: no cover — headless CI
    _QT = False

from modules.logistics.pso_logistics.core.discrete_swarm import (
    DiscreteSwarm,
)
from modules.logistics.pso_logistics.models.config import LogisticsPSOConfig
from modules.logistics.pso_logistics.problems.tsp_problem import TSPProblem
from modules.logistics.pso_logistics.problems.vrp_problem import VRPProblem
from modules.logistics.pso_logistics.problems.vrptw_problem import VRPTWProblem

_ThreadBase = QThread if _QT else object  # type: ignore[misc,assignment]


class SimulationWorker(_ThreadBase):  # type: ignore[valid-type]
    """Run discrete PSO in a background thread."""

    if _QT:
        iteration_done = Signal(int, float, list, list)
        simulation_done = Signal(dict)
        error_occurred = Signal(str)

    def __init__(self, config: LogisticsPSOConfig, parent: Any = None) -> None:
        super().__init__(parent)
        self._config = config
        self._stop_requested: bool = False

    def request_stop(self) -> None:
        """Signal the worker to stop after the current iteration."""
        self._stop_requested = True

    def run(self) -> None:  # noqa: C901
        """Body of the background thread — do not call directly."""
        try:
            self._stop_requested = False

            # Re-generate problem from config (same seeds → same layout as UI)
            if self._config.problem_type == "vrptw":
                problem = VRPTWProblem.generate(
                    self._config.n_customers,
                    self._config.coord_range,
                    self._config.data_seed,
                    self._config.demand_seed,
                    self._config.n_vehicles,
                    self._config.vehicle_capacity,
                    self._config.max_demand,
                    self._config.vehicle_speed,
                    self._config.tw_seed,
                    self._config.tw_width,
                    self._config.service_time_max,
                    self._config.tw_penalty,
                )
            elif self._config.problem_type == "vrp":
                problem = VRPProblem.generate(
                    self._config.n_customers,
                    self._config.coord_range,
                    self._config.data_seed,
                    self._config.demand_seed,
                    self._config.n_vehicles,
                    self._config.vehicle_capacity,
                    self._config.max_demand,
                )
            else:
                problem = TSPProblem.generate(
                    self._config.n_customers,
                    self._config.coord_range,
                    self._config.data_seed,
                    road_mode=self._config.road_mode,
                )

            rng = random.Random(self._config.pso_seed)
            swarm = DiscreteSwarm(self._config, problem, rng)

            # Emit iteration 0 (initial swarm state)
            self.iteration_done.emit(
                0,
                float(swarm.gbest_fitness),
                list(swarm.gbest_position),
                [list(p.position) for p in swarm.particles],
            )

            for _ in range(self._config.n_iterations):
                if self._stop_requested:
                    break

                result = swarm.step()

                self.iteration_done.emit(
                    int(result["iteration"]),
                    float(result["gbest_fitness"]),
                    list(result["gbest_position"]),
                    [list(p) for p in result["positions"]],
                )

                if self._config.step_delay_ms > 0 and not self._stop_requested:
                    self.msleep(self._config.step_delay_ms)

            self.simulation_done.emit(
                {
                    "gbest_perm": list(swarm.gbest_position),
                    "gbest_fitness": float(swarm.gbest_fitness),
                    "convergence_history": list(swarm.convergence_history),
                    "iterations_done": swarm.iteration,
                    "stopped_early": self._stop_requested,
                }
            )

        except Exception as exc:  # noqa: BLE001
            self.error_occurred.emit(str(exc))
