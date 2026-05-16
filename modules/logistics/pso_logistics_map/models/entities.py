"""entities.py — Data entities cho pso_logistics_map.

Tương tự pso_logistics/models/entities.py nhưng dùng lat/lon thay vì x/y
(vì đây là bản đồ thật) và thêm node_id để liên kết với NetworkX graph.

Phiên bản:
    TSP v1.0  : Depot + Customer (lat, lon, node_id)
    VRP v1.1  : thêm Customer.demand + Vehicle.capacity
    VRPTW v1.2: thêm time window fields + Route time fields
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Depot:
    """Kho xuất phát — điểm bắt đầu và kết thúc của tất cả xe."""
    id: int
    lat: float
    lon: float
    node_id: int | None = None   # node_id trên NetworkX graph sau khi snap


@dataclass
class Customer:
    """Điểm giao hàng — khách hàng cần phục vụ."""
    id: int             # 1-based display ID
    lat: float
    lon: float
    node_id: int | None = None   # node_id trên NetworkX graph sau khi snap
    demand: float = 0.0                   # VRP v1.1+: nhu cầu hàng hóa
    service_time: float = 0.0            # VRPTW v1.2+: thời gian phục vụ tại node
    ready_time: float = 0.0              # VRPTW v1.2+: mở cửa sổ thời gian
    due_time: float = float("inf")       # VRPTW v1.2+: đóng cửa sổ thời gian


@dataclass
class Vehicle:
    """Phương tiện vận chuyển."""
    id: int
    capacity: float = float("inf")   # VRP v1.1+: tải trọng tối đa
    speed_kmph: float = 30.0         # VRPTW v1.2+: tốc độ km/h (để đổi sang giây)
    fixed_cost: float = 0.0          # chi phí cố định mỗi xe dùng


@dataclass
class Route:
    """Tuyến đường của một xe."""
    vehicle_id: int
    customer_ids: list[int] = field(default_factory=list)   # danh sách ID, thứ tự thăm
    distance_m: float = 0.0          # tổng khoảng cách (metres)
    load: float = 0.0                # tổng tải trọng
    # VRPTW v1.2+: rỗng với TSP/VRP
    arrival_times: list[float] = field(default_factory=list)
    start_service_times: list[float] = field(default_factory=list)
    waiting_times: list[float] = field(default_factory=list)
    lateness_times: list[float] = field(default_factory=list)
