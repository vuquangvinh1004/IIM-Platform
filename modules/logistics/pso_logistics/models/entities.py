"""Shared data entities for PSO logistics problems.

TSP v1.0  : uses Depot + Customer (id, x, y only)
VRP v1.1  : adds Customer.demand + Vehicle.capacity
VRPTW v1.2: adds Customer.service_time, ready_time, due_time + Route time fields
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Depot:
    """Central warehouse / starting point for all vehicles."""
    id: int
    x: float
    y: float


@dataclass
class Customer:
    """Delivery stop / customer node."""
    id: int        # 1-based display ID
    x: float
    y: float
    demand: float = 0.0           # VRP v1.1+: cargo demand
    service_time: float = 0.0    # VRPTW v1.2+: time to serve at this node
    ready_time: float = 0.0      # VRPTW v1.2+: earliest service start
    due_time: float = float("inf")  # VRPTW v1.2+: latest allowed arrival


@dataclass
class Vehicle:
    """Transport vehicle."""
    id: int
    capacity: float = float("inf")  # VRP v1.1+: max cargo
    speed: float = 1.0              # VRPTW v1.2+: distance per time unit
    fixed_cost: float = 0.0         # optional cost per vehicle used


@dataclass
class Route:
    """One vehicle's planned tour."""
    vehicle_id: int
    customer_ids: list[int] = field(default_factory=list)  # ordered visit list
    distance: float = 0.0
    load: float = 0.0
    # VRPTW v1.2+ fields (empty lists for TSP/VRP)
    arrival_times: list[float] = field(default_factory=list)
    start_service_times: list[float] = field(default_factory=list)
    waiting_times: list[float] = field(default_factory=list)
    lateness_times: list[float] = field(default_factory=list)
