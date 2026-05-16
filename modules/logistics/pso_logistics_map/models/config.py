"""config.py — MapLogisticsPSOConfig: tham số cấu hình cho pso_logistics_map."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class MapLogisticsPSOConfig:
    """Tham số cấu hình cho module PSO logistics trên bản đồ thật.

    Map / Đồ thị
    ------------
    pbf_file         : đường dẫn đến file .pbf cục bộ (liên quan đến thư mục module)
    network_type     : "driving" | "walking" | "cycling"
    graph_cache_file : đường dẫn lưu cache pickle của graph

    Bài toán
    --------
    n_customers  : số điểm giao (không tính depot)
    n_vehicles   : số xe (VRP/VRPTW)
    data_seed    : seed cho việc chọn ngẫu nhiên tọa độ điểm giao

    PSO
    ---
    n_particles  : kích thước bầy
    n_iterations : số vòng lặp tối đa
    w            : trọng số quán tính
    c1           : hệ số gia tốc nhận thức (pbest)
    c2           : hệ số gia tốc xã hội (gbest/lbest)
    n_ops_max    : số toán tử tối đa mỗi thành phần mỗi bước
    topology     : "star" (gbest toàn cục) | "ring" (lbest vòng)
    pso_seed     : seed PSO; None = không xác định

    VRP v1.1
    --------
    vehicle_capacity : tải trọng tối đa mỗi xe
    demand_seed      : seed cho nhu cầu khách hàng

    VRPTW v1.2
    ----------
    vehicle_speed_kmph : tốc độ xe (km/h)
    tw_seed            : seed cho time window
    tw_width_s         : độ rộng cửa sổ thời gian (giây)
    service_time_max_s : thời gian phục vụ tối đa (giây)
    tw_penalty         : phạt mỗi giây trễ giờ
    overload_penalty   : phạt mỗi đơn vị quá tải

    Hiển thị
    --------
    step_delay_ms : milliseconds nghỉ giữa các iteration (0 = max speed)
    """

    # ── Map ───────────────────────────────────────────────────────────────────
    pbf_file: str = "assets/pbf/hcm_q1.pbf"
    network_type: str = "driving"
    graph_cache_file: str = "assets/pbf/cache/hcm_q1_graph.pkl"

    # ── Bài toán ──────────────────────────────────────────────────────────────
    problem_type: str = "tsp"   # "tsp" | "vrp" | "vrptw"
    n_customers: int = 10
    n_vehicles: int = 3
    data_seed: int = 42

    # ── PSO ───────────────────────────────────────────────────────────────────
    n_particles: int = 30
    n_iterations: int = 100
    w: float = 0.5
    c1: float = 1.5
    c2: float = 1.5
    n_ops_max: int = 3
    topology: str = "star"       # "star" | "ring"
    pso_seed: int | None = 42

    # ── VRP v1.1 ──────────────────────────────────────────────────────────────
    vehicle_capacity: float = 50.0
    demand_seed: int = 7
    max_demand: float = 15.0

    # ── VRPTW v1.2 ────────────────────────────────────────────────────────────
    vehicle_speed_kmph: float = 30.0
    tw_seed: int = 13
    tw_width_s: float = 1800.0       # 30 phút
    service_time_max_s: float = 300.0  # 5 phút
    tw_penalty: float = 10.0
    overload_penalty: float = 1000.0

    # ── Hiển thị ──────────────────────────────────────────────────────────────
    step_delay_ms: int = 50
