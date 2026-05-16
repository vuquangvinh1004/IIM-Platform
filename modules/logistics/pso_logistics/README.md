# PSO Logistics — Tối ưu hóa Giao hàng

Module mô phỏng thuật toán **Particle Swarm Optimization (PSO) rời rạc** cho bài toán giao hàng,
tích hợp vào IIMP theo chuẩn Module SDK v1.0.

---

## Phạm vi phiên bản

| Phiên bản | Bài toán | Trạng thái |
|-----------|----------|------------|
| **v1.0**  | TSP — Travelling Salesman Problem (1 xe, thăm tất cả điểm) | ✅ Hiện tại |
| v1.1      | VRP — Vehicle Routing Problem (nhiều xe, ràng buộc tải trọng) | 🔜 Kế hoạch |
| v1.2      | VRPTW — VRP with Time Windows | 🔜 Kế hoạch |

---

## Cấu trúc thư mục

```
pso_logistics/
├── module.json          # IIMP manifest
├── entry.py             # entry point → PSOLogisticsModule
├── module.py            # UI + BaseModule (view, lifecycle, state)
│
├── core/
│   ├── discrete_particle.py   # DiscreteParticle (permutation-based)
│   ├── discrete_swarm.py      # DiscreteSwarm (PSO engine)
│   ├── operators.py           # swap, insert, reverse_segment, move_toward
│   └── route_evaluator.py     # distance matrix + tour distance
│
├── models/
│   ├── config.py        # LogisticsPSOConfig
│   ├── entities.py      # Depot, Customer, Vehicle, Route (dataclasses)
│   └── state.py         # STATE_VERSION + default_state()
│
├── problems/
│   └── tsp_problem.py   # TSPProblem (generate, evaluate, decode)
│
├── workers/
│   └── simulation_worker.py  # SimulationWorker(QThread)
│
└── tests/
    ├── test_manifest.py
    ├── test_operators.py
    ├── test_tsp_problem.py
    ├── test_discrete_swarm.py
    └── test_smoke_ui.py
```

---

## Thuật toán PSO rời rạc (Discrete PSO — Permutation Space)

Không gian tìm kiếm là **không gian hoán vị** (không phải không gian vector liên tục như PSO gốc).
Mỗi hạt (particle) là một hoán vị `[p₀, p₁, …, pₙ₋₁]` biểu diễn thứ tự thăm các điểm giao.

**Quy tắc cập nhật vị trí tại mỗi bước:**

```
n_inertia = max(1, round(w × n_ops_max))
n_cog     = max(0, round(c₁ × r₁ × n_ops_max / 2))    r₁ ~ U[0,1]
n_soc     = max(0, round(c₂ × r₂ × n_ops_max / 2))    r₂ ~ U[0,1]

new_pos = apply_random_ops(pos, n_inertia, rng)          # thành phần quán tính
new_pos = move_toward(new_pos, pbest, rng, n_cog)        # thành phần cá nhân
new_pos = move_toward(new_pos, social_best, rng, n_soc)  # thành phần xã hội
```

**Các operator được sử dụng:**

| Operator | Mô tả |
|----------|-------|
| `swap` | Hoán đổi 2 vị trí ngẫu nhiên |
| `insert` | Tách 1 phần tử và chèn lại tại vị trí ngẫu nhiên |
| `reverse_segment` | Đảo ngược một đoạn con liên tiếp (bước 2-opt) |
| `move_toward` | Thực hiện k bước hoán đổi có chủ đích để tiếp cận target |

---

## Kiến trúc Threading

```
UI Thread                          Worker Thread (QThread)
──────────────────────────────     ─────────────────────────────────────
TSPProblem.generate(seed)  ──[1]─→  TSPProblem.generate(seed)  [cùng seed]
_map_canvas.setup(...)              DiscreteSwarm.run()
                                      ↓ iteration k
        ←── iteration_done(k, fitness, gbest_perm, all_perms) ──
_on_iteration(...)                  (plain Python types, no numpy)
  update_route(...)
  convergence_canvas.append(...)
        ←── simulation_done({...}) ──
_on_done(...)
```

**[1]** Problem được tạo trong cả 2 thread từ cùng `data_seed` → kết quả đồng nhất,
không có object mutable nào đi qua ranh giới thread.

**Animation Replay** (D3 — không trộn với simulation animation):
- Sau khi simulation kết thúc, nút `⏯ Phát lại` kích hoạt `QTimer`
- `QTimer.timeout` → đọc `_best_route_history[i]` và gọi `update_route()`
- Hoàn toàn tách biệt với QThread worker

---

## Hướng dẫn sử dụng nhanh

1. Chọn **Số điểm giao** (3–80) và **Seed dữ liệu**.
2. Điều chỉnh **Tham số PSO** theo nhu cầu (defaults là điểm khởi đầu tốt).
3. Nhấn **▶ Chạy** → quan sát tuyến đường tốt nhất cập nhật theo từng vòng lặp.
4. Nhấn **⏯ Phát lại** sau khi simulation xong để xem lại toàn bộ quá trình.
5. Xuất bản đồ hoặc đồ thị hội tụ bằng nút **📷 Xuất**.

---

## Ghi chú kỹ thuật

- Khoảng cách sử dụng **Euclidean distance** (không dùng haversine cho v1.0).
- Ma trận khoảng cách `dist_matrix[(n+1)×(n+1)]`: index 0 = depot, index i+1 = customers[i].
- `STATE_VERSION = "1.0.0"` — trạng thái module được lưu/khôi phục khi shell restart.
- `on_unload()`: dừng worker an toàn với `request_stop() + wait(3000 ms)`.
