# Mô tả thiết kế mô phỏng PSO cho bài toán giao hàng và xe vận tải với bản đồ

Stack được chọn lọc để tuân thủ ràng buộc **offline first** của IIMP:

**pyosmium (.pbf cục bộ) → NetworkX → ma trận chi phí → PSO rời rạc → trực quan hóa tuyến tối ưu**

---

# 1. Mục tiêu triển khai

Xây một module IIMP Python có thể:

* đọc file OSM `.pbf` đã tải sẵn bằng **pyosmium** (`osmium`) — hoàn toàn offline, không fetch API
* xây dựng đồ thị lưới đường bằng **NetworkX** từ nodes/edges Pyrosm trả về
* ánh xạ depot và điểm giao vào node gần nhất trên đồ thị bằng `scipy.spatial.KDTree`
* tính ma trận khoảng cách shortest-path bằng NetworkX
* dùng PSO rời rạc để tối ưu tuyến giao hàng — tái sử dụng engine từ `pso_logistics`
* hiển thị kết quả trên bản đồ tọa độ lat/lon thật bằng matplotlib

Ứng dụng nên hỗ trợ theo lộ trình:

* giai đoạn 1: TSP
* giai đoạn 2: VRP
* giai đoạn 3: VRPTW

---

# 2. Cấu trúc thư mục chuẩn IIMP

Module đặt trong `modules/logistics/pso_logistics_map/` theo chuẩn Module SDK v1.0.

```text
modules/logistics/pso_logistics_map/
│
├── module.json              # IIMP manifest: id, permissions, entry_point
├── entry.py                 # Export PSOLogisticsMapModule(BaseModule)
├── __init__.py
├── README.md
├── CHANGELOG.md
├── icon.png
│
├── core/
│   ├── pbf_loader.py        # Pyrosm: đọc .pbf → nodes/edges DataFrame
│   ├── graph_builder.py     # NetworkX: build DiGraph + pickle cache
│   ├── nearest_node.py      # scipy.KDTree: tọa độ → node_id gần nhất
│   ├── distance_matrix.py   # NetworkX shortest path → ma trận N×N
│   └── route_evaluator.py   # Tính chi phí tuyến từ matrix
│
├── models/
│   ├── config.py            # MapLogisticsPSOConfig (Pydantic)
│   ├── entities.py          # Depot, Customer, Vehicle, Route
│   └── state.py             # STATE_VERSION + default_state()
│
├── problems/
│   ├── tsp_problem.py       # TSPProblem: generate, evaluate, decode
│   ├── vrp_problem.py       # VRPProblem — v1.1
│   └── vrptw_problem.py     # VRPTWProblem — v1.2
│
├── pso/
│   ├── discrete_particle.py # Tái sử dụng từ pso_logistics
│   ├── discrete_swarm.py    # Tái sử dụng từ pso_logistics
│   └── operators.py         # Tái sử dụng từ pso_logistics
│
├── ui/
│   ├── main_view.py         # QWidget chính: 3 tab + trạng thái load
│   ├── map_canvas.py        # FigureCanvasQTAgg (matplotlib)
│   ├── controls_panel.py    # Tham số PSO, scenario, đường dẫn .pbf
│   └── convergence_panel.py # Đồ thị hội tụ
│
├── workers/
│   ├── graph_load_worker.py # QThread: đọc .pbf + build graph
│   ├── matrix_worker.py     # QThread: tính distance matrix
│   └── simulation_worker.py # QThread: chạy PSO iterations
│
├── assets/
│   └── pbf/                 # File .pbf đã tải sẵn (ví dụ: hcm_q1.pbf)
│
└── tests/
    ├── test_manifest.py
    ├── test_pbf_loader.py
    ├── test_graph_builder.py
    ├── test_nearest_node.py
    ├── test_distance_matrix.py
    ├── test_tsp_problem.py
    └── test_smoke_ui.py
```

---

# 3. Vai trò từng nhóm module

## 3.1. `core/`

Đây là lớp nền tảng dùng chung.

### `pbf_loader.py`

Phụ trách:

* đọc file `.pbf` cục bộ bằng **pyosmium** (`osmium.SimpleHandler`) — không gọi API internet
* trả về `(nodes_df, edges_df)` dạng pandas DataFrame
* hỗ trợ `network_type`: `driving`, `walking`, `cycling`
* raise lỗi rõ ràng nếu file không tồn tại hoặc hỏng

Ví dụ nhiệm vụ:

* đọc `assets/pbf/hcm_q1.pbf`
* trả về nodes (id, geometry.x/y) và edges (u, v, length)

### `graph_builder.py`

Phụ trách:

* nhận nodes/edges DataFrame từ `pbf_loader.py`
* build `networkx.DiGraph` với node attributes `x` (lon), `y` (lat)
* lưu cache graph dạng pickle để tránh parse lại .pbf mỗi lần
* trả về graph đã index theo `node_id`

### `nearest_node.py`

Phụ trách:

* nhận danh sách điểm (lat, lon) — depot + customers
* dùng `scipy.spatial.KDTree` trên mảng tọa độ nodes của graph
* trả về `node_id` gần nhất cho từng điểm
* **không cần GeoPandas trực tiếp** — scipy.KDTree thay thế hoàn toàn

### `distance_matrix.py`

Phụ trách:

* tính ma trận chi phí giữa depot và các khách hàng
* hỗ trợ:

  * ma trận khoảng cách
  * ma trận thời gian
* dùng shortest path từ `networkx`

Đây là module cực quan trọng vì output của nó sẽ là đầu vào cho PSO.

### `entities.py` (trong models/)

Chứa các dataclass dữ liệu:

* `Depot`
* `Customer`
* `Vehicle`
* `Route`

### `route_evaluator.py`

Chứa các hàm phụ:

* tính tổng khoảng cách tuyến từ distance matrix
* chuẩn hóa dữ liệu
* format route

---

## 3.2. `pso/`

Đây là engine PSO rời rạc — **tái sử dụng từ `pso_logistics`**, không viết lại.

### `discrete_particle.py`

Khai báo khung cơ bản cho một hạt:

* `position` là hoán vị thứ tự thăm
* `fitness`
* `pbest_position`
* `pbest_fitness`

### `discrete_swarm.py`

Quản lý toàn swarm:

* danh sách particle
* `gbest_position`
* `gbest_fitness`
* `convergence_history`

### `operators.py`

Chứa các toán tử rời rạc:

* swap
* insert
* reverse
* relocate
* inter-route swap

Đây là phần thay cho "vận tốc" kiểu liên tục. Hỗ trợ Star và Ring topology.

---

## 3.3. `problems/`

Mỗi bài toán có implementation riêng.

### `tsp_problem.py`

Biểu diễn:

* một hạt là một hoán vị khách hàng

Fitness:

* tổng chi phí tuyến đi qua tất cả điểm rồi quay về kho

### `vrp_problem.py`

Biểu diễn:

* một hạt là tập nhiều tuyến, mỗi tuyến thuộc một xe

Fitness:

* tổng quãng đường
* cộng phạt quá tải

### `vrptw_problem.py`

Biểu diễn:

* giống VRP nhưng thêm logic thời gian

Fitness:

* tổng quãng đường
* cộng phạt quá tải
* cộng phạt trễ giờ
* có thể cộng thêm phạt chờ lâu hoặc dùng quá nhiều xe

---

## 3.4. `ui/`

Lớp giao diện — IIMP-hosted, không tự tạo main window.

### `main_view.py`

Phụ trách:

* là QWidget chính được host bởi shell IIMP
* đặt 3 tab: TSP / VRP / VRPTW
* hiển thị trạng thái load graph và tiến trình PSO

### `map_canvas.py`

Phụ trách:

* `FigureCanvasQTAgg` nhúng matplotlib vào Qt
* vẽ tọa độ lat/lon, depot, khách hàng, tuyến gBest
* cập nhật realtime qua signal từ `SimulationWorker`

### `controls_panel.py`

Phụ trách:

* nhập tham số PSO (w, c1, c2, iterations, particles)
* chọn đường dẫn file .pbf
* sinh hoặc nhập danh sách điểm giao từ CSV

### `convergence_panel.py`

Phụ trách:

* vẽ đồ thị fitness theo iteration sử dụng matplotlib
* cập nhật realtime qua signal từ worker

---

## 3.5. `workers/`

Lớp thực thi tác vụ nặng — bắt buộc dùng QThread, không được chạy trên main thread.

### `graph_load_worker.py`

Phụ trách:

* đọc .pbf qua `pbf_loader.py` (3–15 giây)
* build graph qua `graph_builder.py`
* emit `graph_ready(G)` khi xong
* emit `error(msg)` nếu file không tồn tại

### `matrix_worker.py`

Phụ trách:

* nhận graph + danh sách điểm
* tính distance matrix qua `distance_matrix.py`
* emit `matrix_ready(matrix)` khi xong

### `simulation_worker.py`

Phụ trách:

* chạy PSO rời rạc từng iteration
* emit `progress_updated(iteration, gbest_fitness, best_route)` mỗi vòng
* emit `finished(result)` khi hết iteration

---

# 4. Luồng chạy tổng thể

Pipeline nên đi theo thứ tự này:

## Bước 1. Đọc đồ thị đường phố từ file .pbf

Từ Pyrosm (offline):

* đọc file `.pbf` đã tải sẵn trong `assets/pbf/`
* dùng `network_type="driving"` để lấy nodes và edges
* build `networkx.DiGraph` qua `graph_builder.py`
* lưu pickle cache để load nhanh từ lần sau

Output:

* `G` là `networkx.DiGraph` với tọa độ lat/lon trên mỗi node

## Bước 2. Tạo depot và khách hàng

Nguồn điểm có thể là:

* nhập tay theo tọa độ
* chọn ngẫu nhiên trên graph
* lấy từ file CSV

Output:

* danh sách điểm giao và kho

## Bước 3. Ánh xạ các điểm vào graph

Mỗi depot và customer cần map vào node gần nhất trên graph bằng `scipy.spatial.KDTree`.

Output:

* `node_id` tương ứng cho mỗi điểm

## Bước 4. Tính ma trận chi phí

Dùng `nx.shortest_path_length` trên graph để tính:

* distance matrix
  hoặc
* travel time matrix

Output:

* ma trận numpy `(N+1) × (N+1)`

## Bước 5. Khởi tạo bài toán tối ưu

Tùy mode:

* TSP
* VRP
* VRPTW

## Bước 6. Chạy PSO

PSO dùng:

* ma trận chi phí
* dữ liệu demand
* dữ liệu vehicle
* dữ liệu time window nếu có

Output:

* nghiệm tốt nhất
* fitness tốt nhất
* lịch sử hội tụ

## Bước 7. Hiển thị

Vẽ:

* tuyến tốt nhất trên bản đồ tọa độ lat/lon thật
* biểu đồ hội tụ
* animation nếu có

---

# 5. Thiết kế dữ liệu cốt lõi

Bạn nên có các model như sau.

## `Depot`

```python
from dataclasses import dataclass

@dataclass
class Depot:
    id: str
    lat: float
    lon: float
    node_id: int | None = None
```

## `Customer`

```python
from dataclasses import dataclass

@dataclass
class Customer:
    id: str
    lat: float
    lon: float
    demand: float = 0.0
    service_time: float = 0.0
    ready_time: float = 0.0
    due_time: float = float("inf")
    node_id: int | None = None
```

## `Vehicle`

```python
from dataclasses import dataclass

@dataclass
class Vehicle:
    id: str
    capacity: float
    speed_kmph: float = 20.0
    fixed_cost: float = 0.0
```

## `Route`

```python
from dataclasses import dataclass, field

@dataclass
class Route:
    vehicle_id: str
    customer_ids: list[str] = field(default_factory=list)
    distance: float = 0.0
    load: float = 0.0
    arrival_times: list[float] = field(default_factory=list)
    waiting_times: list[float] = field(default_factory=list)
    lateness_times: list[float] = field(default_factory=list)
```

---

# 6. Cách tổ chức solver

Nên dùng mô hình:

* một abstract solver chung
* ba solver riêng

Ví dụ:

```python
class BaseSolver:
    def solve(self):
        raise NotImplementedError
```

Sau đó:

* `TSPSolver(BaseSolver)`
* `VRPSolver(BaseSolver)`
* `VRPTWSolver(BaseSolver)`

Mỗi solver sẽ:

* build particle
* đánh giá fitness
* chạy optimize
* trả về best solution

---

# 7. Biểu diễn nghiệm cho từng bài toán

## TSP

`position` là một danh sách thứ tự khách hàng:

```python
[3, 1, 5, 2, 4]
```

## VRP

`position` là danh sách nhiều route:

```python
[
    ["C1", "C4", "C7"],
    ["C2", "C5"],
    ["C3", "C6", "C8"]
]
```

## VRPTW

Cũng có thể giữ biểu diễn như VRP, nhưng evaluation sẽ tính thêm:

* arrival time
* waiting
* lateness

---

# 8. Hàm fitness đề xuất

## TSP

```python
fitness = total_distance
```

## VRP

```python
fitness = total_distance + alpha * overload_penalty
```

## VRPTW

```python
fitness = (
    total_distance
    + alpha * overload_penalty
    + beta * lateness_penalty
    + gamma * vehicle_usage_penalty
)
```

Trong đó:

* `alpha` nên lớn
* `beta` rất lớn nếu muốn ưu tiên đúng giờ
* `gamma` dùng khi muốn hạn chế số xe

---

# 9. Cách dùng pyosmium + scipy.KDTree + NetworkX

## `pbf_loader.py`

Nhiệm vụ chính:

* đọc `.pbf` bằng **pyosmium** (`osmium`) — hoạt động hoàn toàn offline
* stream qua `osmium.SimpleHandler` với `locations=True`
* trả về `(nodes: dict[int, (lat, lon)], edges: list[(u, v, metres)])`
* tính khoảng cách cạnh bằng Haversine — không cần GeoPandas

Ví dụ luồng:

```python
import osmium
import math

class _NetworkHandler(osmium.SimpleHandler):
    def __init__(self, allowed_tags):
        super().__init__()
        self._allowed = allowed_tags
        self.nodes = {}   # {node_id: (lat, lon)}
        self.edges = []   # [(u, v, metres)]

    def way(self, w):
        if w.tags.get("highway") not in self._allowed:
            return
        is_oneway = w.tags.get("oneway", "no") in ("yes", "1", "true")
        for i in range(len(w.nodes) - 1):
            u, v = w.nodes[i], w.nodes[i + 1]
            if not u.location.valid() or not v.location.valid():
                continue
            self.nodes[u.ref] = (u.location.lat, u.location.lon)
            self.nodes[v.ref] = (v.location.lat, v.location.lon)
            dist = haversine_m(u.location.lat, u.location.lon,
                               v.location.lat, v.location.lon)
            self.edges.append((u.ref, v.ref, dist))
            if not is_oneway:
                self.edges.append((v.ref, u.ref, dist))

handler = _NetworkHandler(allowed_tags)
handler.apply_file("assets/pbf/hcm_q1.pbf", locations=True)
# handler.nodes: dict, handler.edges: list
```

## `graph_builder.py`

Nhiệm vụ chính:

* nhận nodes/edges DataFrame, tạo `networkx.DiGraph`
* cache graph dưới dạng pickle để load nhanh từ lần sau

Ví dụ luồng:

```python
import networkx as nx

G = nx.DiGraph()
for _, row in nodes.iterrows():
    G.add_node(int(row["id"]), x=float(row.geometry.x), y=float(row.geometry.y))
for _, row in edges.iterrows():
    G.add_edge(int(row["u"]), int(row["v"]), weight=float(row["length"]))
```

## `nearest_node.py`

Nhiệm vụ chính:

* dùng `scipy.spatial.KDTree` trên mảng node coordinates
* ánh xạ (lat, lon) → node_id gần nhất — **không cần GeoPandas**

Ví dụ luồng:

```python
from scipy.spatial import KDTree
import numpy as np

node_ids = list(G.nodes)
coords = np.array([[G.nodes[n]["y"], G.nodes[n]["x"]] for n in node_ids])
tree = KDTree(coords)

def find_nearest(lat: float, lon: float) -> int:
    _, idx = tree.query([lat, lon])
    return node_ids[idx]
```

## `distance_matrix.py`

Nhiệm vụ chính:

* với danh sách `node_id` của depot + customers
* chạy `nx.shortest_path_length` từng cặp theo `weight="length"`
* trả về ma trận numpy `(N+1) × (N+1)`

Đây là lớp kết nối giữa dữ liệu bản đồ thật và engine PSO.

---

# 10. `entry.py` và `module.py` nên làm gì

`entry.py` là entry point chuẩn IIMP, chỉ có một nhiệm vụ: export class kế thừa `BaseModule`.

```python
# entry.py
from .module import PSOLogisticsMapModule

__all__ = ["PSOLogisticsMapModule"]
```

`module.py` là class chính của module, kế thừa `BaseModule`:

```python
from core.module_runtime.base_module import BaseModule
from .ui.main_view import MainView

class PSOLogisticsMapModule(BaseModule):
    def on_activate(self) -> None:
        self._view = MainView(self._context)

    def get_widget(self):
        return self._view

    def on_deactivate(self) -> None:
        self._view.stop_simulation()

    def save_state(self) -> dict:
        return self._view.get_state()

    def restore_state(self, state: dict) -> None:
        self._view.set_state(state)
```

---

# 11. Cấu hình nên tách ra `models/config.py`

Ví dụ:

```python
# Đường dẫn file .pbf cục bộ (đặt trong assets/pbf/ của module)
PBF_FILE = "assets/pbf/hcm_q1.pbf"
NETWORK_TYPE = "driving"   # driving | walking | cycling

# Cache graph (pickle) để tránh parse lại .pbf mỗi lần load
GRAPH_CACHE_FILE = "assets/pbf/cache/hcm_q1_graph.pkl"

N_CUSTOMERS = 15
N_VEHICLES = 3

PSO_PARTICLES = 30
PSO_ITERATIONS = 100
W = 0.7
C1 = 1.7
C2 = 1.7

OVERLOAD_PENALTY = 1000
LATENESS_PENALTY = 2000
RANDOM_SEED = 42
```

---

# 12. Lộ trình triển khai thực tế

Tôi khuyên bạn làm theo đúng thứ tự này.

## Giai đoạn 1

Làm `TSP` trên bản đồ thật:

* 1 depot
* 10 khách hàng
* 1 xe
* tối ưu theo distance

## Giai đoạn 2

Nâng lên `VRP`:

* 2 đến 4 xe
* thêm demand
* thêm capacity

## Giai đoạn 3

Nâng lên `VRPTW`:

* thêm ready time
* due time
* service time
* travel time

---

# 13. Kiến trúc tối thiểu IIMP — bắt đầu bằng TSP

Tập file tối thiểu để có module chạy được trong IIMP với TSP:

```text
modules/logistics/pso_logistics_map/
├── module.json
├── entry.py
├── __init__.py
├── README.md
│
├── core/
│   ├── pbf_loader.py          # Pyrosm → nodes/edges
│   ├── graph_builder.py       # NetworkX DiGraph + pickle cache
│   ├── nearest_node.py        # scipy.KDTree → node_id
│   └── distance_matrix.py     # shortest path → N×N matrix
│
├── models/
│   ├── entities.py            # Depot, Customer, Vehicle, Route
│   └── config.py              # MapLogisticsPSOConfig
│
├── problems/
│   └── tsp_problem.py
│
├── pso/
│   ├── discrete_particle.py   # copy từ pso_logistics
│   ├── discrete_swarm.py      # copy từ pso_logistics
│   └── operators.py           # copy từ pso_logistics
│
├── ui/
│   ├── main_view.py           # BaseModule container
│   └── map_canvas.py          # matplotlib FigureCanvas
│
├── workers/
│   ├── graph_load_worker.py   # QThread: .pbf → graph
│   └── simulation_worker.py   # QThread: PSO iterations
│
└── assets/
    └── pbf/
        └── hcm_q1.pbf         # File .pbf cục bộ (~5-30 MB)
```

Khi TSP chạy ổn thêm `vrp_problem.py`, `vrptw_problem.py` và `matrix_worker.py`.

---

# 14. Kết luận

Stack điều chỉnh tuân thủ đầy đủ ràng buộc IIMP:

* `pyosmium` (`osmium`) đọc file `.pbf` đã tải sẵn qua `osmium.SimpleHandler` — hoàn toàn offline, không vi phạm nguyên tắc IIMP
* `scipy.spatial.KDTree` ánh xạ tọa độ điểm giao vào node gần nhất — không cần GeoPandas trực tiếp
* `NetworkX` xây đồ thị đường phố và tính ma trận chi phí shortest-path
* `models/entities.py` giữ dữ liệu `Depot`, `Customer`, `Vehicle`, `Route`
* `problems/` chứa logic riêng cho TSP, VRP, VRPTW
* `pso/` là engine PSO rời rạc — **tái sử dụng từ `pso_logistics`**, không viết lại
* `ui/map_canvas.py` + matplotlib vẽ tuyến trên bản đồ tọa độ lat/lon thật
* Tất cả tác vụ nặng chạy trong `QThread` workers — shell không bị freeze

---

# 15. Tuân thủ IIMP Module SDK

## 15.1. Manifest `module.json`

```json
{
  "id": "pso_logistics_map",
  "name": "PSO — Giao hàng trên Bản đồ Thật",
  "version": "1.0.0",
  "sdk_version": "1.0.0",
  "min_platform_version": "1.0.0",
  "entry_point": "modules.logistics.pso_logistics_map.entry:PSOLogisticsMapModule",
  "category": "logistics",
  "subcategory": "routing",
  "description": "Mô phỏng PSO rời rạc cho TSP/VRP/VRPTW trên mạng đường thật từ file OSM .pbf.",
  "tags": ["pso", "logistics", "routing", "tsp", "vrp", "osm", "map"],
  "author": "IIMP Team",
  "supports_state_restore": true,
  "supports_export": true,
  "ui": { "min_width": 1200, "min_height": 720, "layout_mode": "split" },
  "permissions": ["storage.read", "storage.write", "export.file", "settings.read", "settings.write"],
  "dependencies": {
    "python": ">=3.11",
    "packages": ["PySide6", "matplotlib", "numpy", "scipy", "networkx", "pyrosm"]
  }
}
```

## 15.2. Tác vụ nặng bắt buộc chạy trong QThread

| Tác vụ | Worker | Ghi chú |
|---|---|---|
| Đọc .pbf + build graph | `GraphLoadWorker` | 3–15 giây, tùy kích thước .pbf |
| Tính distance matrix | `MatrixWorker` | O(N²) × Dijkstra |
| Chạy PSO iterations | `SimulationWorker` | emit `progress_updated` mỗi iteration |

## 15.3. Nguyên tắc offline first

File `.pbf` **phải ship cùng module** trong `assets/pbf/`. Không fetch dữ liệu OSM tại runtime.
Nếu file không tồn tại: module hiển thị lỗi rõ ràng, không crash shell.

## 15.4. Dependencies cần phê duyệt

Trước khi triển khai cần thêm vào `requirements.txt` của IIMP:

```
networkx>=3.2
osmium>=4.0
```

> **Lý do chọn pyosmium thay pyrosm:** `pyrosm>=0.6.2` không build được trên Python 3.13
> (dependency `pyrobuf` legacy C extension build fail). `pyosmium` (package `osmium`) có
> pre-built wheel cho Python 3.13 Windows, không kéo theo GDAL/fiona/geopandas.
> Khoảng cách cạnh tính bằng Haversine thuần Python — không cần GeoPandas.

Created 2 todos

Replacing 187 lines with 330 lines in [](file:///d%3A/Nen_tang_tich_hop_moduler/modules/logistics/module_PSO_voi_ban_do.md)

## Lộ trình phát triển `pso_logistics_map`

### Phase 0 — Kiểm tra môi trường (1–2 ngày)

**Mục tiêu:** Xác nhận stack có thể cài và chạy được trên Windows trước khi viết bất kỳ code module nào.

* Cài thử `pyrosm>=0.6.1` trong virtualenv của IIMP, kiểm tra không conflict
* Tải thử file `.pbf` nhỏ (Quận 1 HCM ~5 MB từ Geofabrik)
* Chạy script probe: `OSM(pbf).get_network(network_type="driving", nodes=True)` → xác nhận nodes/edges DataFrame hợp lệ
* Kiểm tra `geopandas` được kéo theo không bị lỗi do thiếu GDAL; nếu lỗi, chuyển sang `pyogrio` backend
* Kết quả mong đợi: file `.pbf` parse thành công, thấy node có `geometry.x/y`

---

### Phase 1 — Core data pipeline (3–5 ngày)

**Mục tiêu:** Xây bộ đọc bản đồ + tính ma trận chi phí — **hoàn toàn không có UI**.

| File | Nhiệm vụ |
|---|---|
| `core/pbf_loader.py` | Pyrosm → `(nodes_df, edges_df)` |
| `core/graph_builder.py` | `networkx.DiGraph` + pickle cache |
| `core/nearest_node.py` | `scipy.KDTree` → `node_id` |
| `core/distance_matrix.py` | `nx.shortest_path_length` → `np.ndarray` |
| `models/entities.py` | `Depot`, `Customer`, `Vehicle`, `Route` |

**Tiêu chí hoàn thành:**
* `test_pbf_loader.py`: parse file .pbf, assert `len(nodes) > 0`
* `test_graph_builder.py`: graph có nodes với attribute `x`, `y`; pickle cache load lại đúng
* `test_nearest_node.py`: 3 tọa độ mẫu → 3 `node_id` hợp lệ
* `test_distance_matrix.py`: ma trận 5×5 không có `inf` giữa các node kết nối

---

### Phase 2 — TSP integration (4–6 ngày)

**Mục tiêu:** PSO chạy được trên ma trận distance matrix thật, hội tụ đúng hướng.

* Copy `pso/discrete_particle.py`, `discrete_swarm.py`, `operators.py` từ `pso_logistics` (không sửa)
* Viết `problems/tsp_problem.py` dùng distance matrix thật (không phải tọa độ 2D abstract)
* Viết `workers/simulation_worker.py` (QThread, emit `progress_updated` + `finished`)
* Script headless test chạy PSO 100 iterations trên 10 điểm mẫu lấy từ đồ thị HCM Q1
* Kiểm tra fitness giảm qua các iteration

**Tiêu chí hoàn thành:**
* `test_tsp_problem.py`: generate 10 particles, evaluate đều trả về fitness > 0
* Script headless xác nhận `gbest_fitness` iteration 100 < iteration 1

---

### Phase 3 — IIMP shell integration (3–4 ngày)

**Mục tiêu:** Module load được trong IIMP, không crash shell.

* Viết module.json (manifest đầy đủ)
* Viết `entry.py` + `module.py` (`PSOLogisticsMapModule(BaseModule)`)
* Viết `ui/main_view.py` (QWidget với 1 tab TSP tối giản)
* Viết `workers/graph_load_worker.py` (QThread: `.pbf` → graph, emit `graph_ready` / `error`)
* Kết nối `GraphLoadWorker` → `MainView`: nút Load → progress indicator → map_canvas hiển thị nodes

**Tiêu chí hoàn thành:**
* `test_manifest.py`: manifest hợp lệ theo `ManifestSchema`
* `test_smoke_ui.py`: `PSOLogisticsMapModule` instantiate không raise exception
* Chạy IIMP thật: module xuất hiện trong danh sách, click → view mở, nút Load Graph hoạt động

---

### Phase 4 — VRP + VRPTW tabs (4–6 ngày)

**Mục tiêu:** Hỗ trợ đủ 3 mode trong UI.

* Viết `problems/vrp_problem.py` + `problems/vrptw_problem.py`
* Viết `workers/matrix_worker.py` (QThread: tính matrix riêng biệt với graph_load)
* Thêm Tab 2 (VRP) và Tab 3 (VRPTW) vào `main_view.py`
* `controls_panel.py`: nhập số xe, capacity, time windows theo tab

**Tiêu chí hoàn thành:**
* `test_vrp_problem.py`, `test_vrptw_problem.py`: evaluate + decode không raise
* Ba tab hoạt động độc lập trong IIMP

---

### Phase 5 — Polish & release (3–5 ngày)

**Mục tiêu:** Đủ điều kiện merge vào main platform.

* `save_state` / `restore_state` lưu lại scenario đang dở (pydantic + JSON)
* Export kết quả: ảnh PNG bản đồ + CSV danh sách tuyến
* Tối ưu cache: kiểm tra pickle cache theo hash của .pbf (tránh dùng cache cũ khi đổi file)
* Bổ sung tests đạt tổng ≥ 50 cases
* Thêm `networkx>=3.2` và `pyrosm>=0.6.1` vào requirements.txt sau khi có phê duyệt
* Cập nhật IIMP_ROADMAP.md đánh dấu `pso_logistics_map v1.0.0`

---

**Thứ tự ưu tiên tuyệt đối:** Phase 0 và Phase 1 phải ổn trước — nếu Pyrosm không parse được `.pbf` trên Windows, mọi phase sau đều không có giá trị.
