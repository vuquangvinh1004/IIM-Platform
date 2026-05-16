"""SimulationWorker — QThread chạy PSO trên bài toán TSP/VRP/VRPTW theo bản đồ thật.

Chạy trên background thread, phát signals vào main thread:
    progress_updated(iteration, gbest_fitness, gbest_position)
    finished(result_dict)
    error_occurred(message)

Sử dụng:
    worker = SimulationWorker(config, dist_matrix)                         # TSP
    worker = SimulationWorker(config, dist_matrix, demands=d)              # VRP
    worker = SimulationWorker(config, dist_matrix, demands=d,              # VRPTW
                              time_windows=tw, service_times=st)
    worker.progress_updated.connect(on_progress)
    worker.finished.connect(on_done)
    worker.start()
    # ... để dừng sớm:
    worker.stop()
"""
from __future__ import annotations

import random

import numpy as np
from PySide6.QtCore import QThread, Signal

from modules.logistics.pso_logistics_map.models.config import MapLogisticsPSOConfig
from modules.logistics.pso_logistics_map.problems.tsp_problem import TSPProblem
from modules.logistics.pso_logistics_map.pso.discrete_swarm import DiscreteSwarm


class SimulationWorker(QThread):
    """Worker thread chạy PSO simulation không chặn main thread."""

    # iteration: int, gbest_fitness: float, gbest_position: list[int]
    progress_updated = Signal(int, float, list)

    # {"gbest_position": list, "gbest_fitness": float,
    #  "convergence_history": list[float], "iterations_done": int}
    result_ready = Signal(dict)

    # thông báo lỗi dạng chuỗi
    error_occurred = Signal(str)

    def __init__(
        self,
        config: MapLogisticsPSOConfig,
        dist_matrix: np.ndarray,
        demands: np.ndarray | None = None,
        time_windows: np.ndarray | None = None,
        service_times: np.ndarray | None = None,
        parent=None,
    ) -> None:
        """
        Args:
            config        : cấu hình PSO (n_particles, n_iterations, …).
            dist_matrix   : ma trận khoảng cách shape (n_customers+1, n_customers+1).
                            index 0 = depot; dùng numpy inf cho cung không đi được.
            demands       : shape (n_customers,); bắt buộc khi problem_type='vrp'/'vrptw'.
            time_windows  : shape (n_customers, 2) = (ready_s, due_s);
                            bắt buộc khi problem_type='vrptw'.
            service_times : shape (n_customers,) in seconds;
                            bắt buộc khi problem_type='vrptw'.
            parent        : Qt parent object (thường là None).
        """
        super().__init__(parent)
        self._config = config
        self._dist_matrix = dist_matrix
        self._demands = demands
        self._time_windows = time_windows
        self._service_times = service_times
        self._stop_requested = False

    # ── Public control ────────────────────────────────────────────────────────

    def stop(self) -> None:
        """Yêu cầu dừng sau iteration hiện tại."""
        self._stop_requested = True

    # ── QThread.run ───────────────────────────────────────────────────────────

    # ── QThread.run ───────────────────────────────────────────────────────────

    def run(self) -> None:  # noqa: C901
        """Entry point của background thread (gọi bởi QThread.start())."""
        self._stop_requested = False
        try:
            pt = self._config.problem_type
            if pt == "vrptw":
                from modules.logistics.pso_logistics_map.problems.vrptw_problem import (  # noqa: PLC0415
                    VRPTWProblem,
                )
                speed_mps = self._config.vehicle_speed_kmph / 3.6
                if self._demands is None or self._time_windows is None or self._service_times is None:
                    raise ValueError("demands, time_windows, service_times bắt buộc cho VRPTW")
                problem = VRPTWProblem(
                    self._dist_matrix,
                    self._config.n_customers,
                    self._config.n_vehicles,
                    self._demands,
                    self._config.vehicle_capacity,
                    speed_mps,
                    self._time_windows,
                    self._service_times,
                    self._config.tw_penalty,
                    self._config.overload_penalty,
                )
            elif pt == "vrp":
                from modules.logistics.pso_logistics_map.problems.vrp_problem import (  # noqa: PLC0415
                    VRPProblem,
                )
                if self._demands is None:
                    raise ValueError("demands bắt buộc cho VRP")
                problem = VRPProblem(
                    self._dist_matrix,
                    self._config.n_customers,
                    self._config.n_vehicles,
                    self._demands,
                    self._config.vehicle_capacity,
                    self._config.overload_penalty,
                )
            else:
                problem = TSPProblem(self._dist_matrix, self._config.n_customers)
            rng = random.Random(self._config.pso_seed)
            swarm = DiscreteSwarm(self._config, problem, rng)

            for _ in range(self._config.n_iterations):
                if self._stop_requested:
                    break

                result = swarm.step()
                self.progress_updated.emit(
                    result["iteration"],
                    result["gbest_fitness"],
                    list(result["gbest_position"]),
                )

                if self._config.step_delay_ms > 0:
                    self.msleep(self._config.step_delay_ms)

            self.result_ready.emit(
                {
                    "gbest_position": list(swarm.gbest_position),
                    "gbest_fitness": swarm.gbest_fitness,
                    "convergence_history": list(swarm.convergence_history),
                    "iterations_done": swarm.iteration,
                }
            )
        except Exception as exc:  # noqa: BLE001
            self.error_occurred.emit(str(exc))
