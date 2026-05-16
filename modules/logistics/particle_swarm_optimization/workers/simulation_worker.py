"""QThread-based worker that runs PSO simulation without blocking the UI.

Thread safety notes:
  - All data sent via signals must be plain Python types (list, float, int)
    so Qt's cross-thread signal mechanism can safely copy them.
  - numpy arrays are converted to list before emitting.
  - _stop_requested is a plain bool; it is only read by the background thread
    and written by the UI thread. In CPython this is safe due to the GIL, but
    calling request_stop() between iterations is the intended usage.

Flow:
  1. UI creates SimulationWorker(config), connects signals, calls start().
  2. Worker initialises Swarm and steps through iterations.
  3. After each step, iteration_done is emitted with per-step data.
  4. When all iterations complete (or stop was requested), simulation_done is
     emitted with final summary.
  5. UI connects worker.finished to a cleanup slot.
"""
from __future__ import annotations

from typing import Any

try:
    from PySide6.QtCore import QThread, Signal
    _QT = True
except ImportError:  # pragma: no cover — headless test environments
    _QT = False

from modules.logistics.particle_swarm_optimization.core.objective_functions import (
    get_function,
)
from modules.logistics.particle_swarm_optimization.core.swarm import Swarm
from modules.logistics.particle_swarm_optimization.models.config import PSOConfig

_ThreadBase = QThread if _QT else object  # type: ignore[misc,assignment]


class SimulationWorker(_ThreadBase):  # type: ignore[valid-type]
    """Run PSO in a background thread, emitting signals for each iteration.

    Signals (available only when PySide6 is installed):
        iteration_done(int, float, list, list):
            Emitted after every iteration.
            Args: (iteration_number, gbest_fitness,
                   gbest_position_as_list, all_positions_as_list_of_lists)

        simulation_done(dict):
            Emitted once when the simulation finishes (normally or early stop).
            Dict keys: gbest_position, gbest_fitness, convergence_history,
                       iterations_done, stopped_early, final_positions.

        error_occurred(str):
            Emitted if an unhandled exception is raised inside run().
    """

    if _QT:
        iteration_done = Signal(int, float, list, list)
        simulation_done = Signal(dict)
        error_occurred = Signal(str)

    def __init__(self, config: PSOConfig, parent: Any = None) -> None:
        super().__init__(parent)
        self._config = config
        self._stop_requested: bool = False

    def request_stop(self) -> None:
        """Request the simulation to stop after the current iteration.

        Thread-safe: only flips a flag; the worker checks it between steps.
        """
        self._stop_requested = True

    def run(self) -> None:  # noqa: C901
        """Body of the background thread — do not call directly."""
        try:
            self._stop_requested = False
            obj_func = get_function(self._config.objective)
            swarm = Swarm(self._config, obj_func)
            final_positions: list[list[float]] = []

            for _ in range(self._config.n_iterations):
                if self._stop_requested:
                    break

                result = swarm.step()

                # Convert numpy arrays to plain lists before crossing threads
                iter_no: int = result["iteration"]
                gbest_f: float = float(result["gbest_fitness"])
                gbest_p: list[float] = result["gbest_position"].tolist()
                positions: list[list[float]] = result["positions"].tolist()
                final_positions = positions  # keep reference to last frame

                self.iteration_done.emit(iter_no, gbest_f, gbest_p, positions)
                if self._config.step_delay_ms > 0 and not self._stop_requested:
                    self.msleep(self._config.step_delay_ms)

            self.simulation_done.emit(
                {
                    "gbest_position": swarm.gbest_position.tolist(),
                    "gbest_fitness": swarm.gbest_fitness,
                    "convergence_history": swarm.convergence_history,
                    "iterations_done": swarm.iteration,
                    "stopped_early": self._stop_requested,
                    "final_positions": final_positions,
                }
            )

        except Exception as exc:  # noqa: BLE001
            self.error_occurred.emit(str(exc))
