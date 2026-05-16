# PSO — Tối ưu hóa Bầy đàn

**Module ID:** `particle_swarm_optimization`  
**Version:** 1.0.0  
**Category:** `quantitative_methods / optimization`  
**SDK:** 1.0.0

---

## Mô tả

Mô phỏng thuật toán **Particle Swarm Optimization (PSO)** — một metaheuristic lấy cảm hứng từ hành vi bầy đàn trong tự nhiên. Module cho phép quan sát trực tiếp quá trình hội tụ của bầy đàn và so sánh ảnh hưởng của các siêu tham số.

---

## Tính năng

| Tính năng | Mô tả |
|---|---|
| Hàm mục tiêu | Sphere (đơn giản, lồi) và Ackley (đa cực trị) |
| Topology | Star (gBest toàn cục) và Ring (lBest láng giềng) |
| Xử lý biên | Clipping (cắt biên) và Reflection (phản xạ) |
| Inertia weight | Giảm tuyến tính từ w_start → w_end |
| Giới hạn vận tốc | Vmax = tỷ lệ × (cận trên − cận dưới) |
| Trực quan 2D | Contour nền + scatter các hạt + đánh dấu gBest |
| Đồ thị hội tụ | gBest fitness theo vòng lặp |
| Export | PNG scatter 2D và PNG đồ thị hội tụ |
| State restore | Tham số và kết quả lần chạy cuối được lưu lại |

---

## Tham số cấu hình

| Tham số | Giá trị mặc định | Mô tả |
|---|---|---|
| Hàm mục tiêu | Sphere | `sphere` hoặc `ackley` |
| Số chiều | 2 | Chiều không gian tìm kiếm |
| Cận dưới | -5.12 | Giới hạn dưới đồng đều cho mọi chiều |
| Cận trên | 5.12 | Giới hạn trên đồng đều cho mọi chiều |
| Số hạt | 30 | Kích thước bầy đàn |
| Số vòng lặp | 100 | Số bước tiến hóa tối đa |
| w_start | 0.9 | Trọng số quán tính ban đầu |
| w_end | 0.4 | Trọng số quán tính cuối |
| c₁ | 1.5 | Hệ số nhận thức cá nhân |
| c₂ | 1.5 | Hệ số xã hội (gBest/lBest) |
| Vmax (tỷ lệ) | 0.20 | Tốc độ tối đa = 0.20 × (ub − lb) |
| Topology | Star | `star` = gBest; `ring` = lBest láng giềng |
| Xử lý biên | Clipping | `clip` hoặc `reflect` |
| Seed | 42 | 0 = sinh ngẫu nhiên mỗi lần chạy |

---

## Mô hình toán học

**Cập nhật vận tốc:**

```
v(t+1) = w · v(t) + c₁·r₁·(pBest - x(t)) + c₂·r₂·(gBest - x(t))
```

**Cập nhật vị trí:**

```
x(t+1) = x(t) + v(t+1)
```

- `w` giảm tuyến tính từ `w_start` → `w_end` qua `n_iterations` bước.
- `r₁`, `r₂` là số ngẫu nhiên đều trong [0, 1].

---

## Cấu trúc thư mục

```text
particle_swarm_optimization/
├── module.json          # Manifest
├── entry.py             # Loader entry point
├── module.py            # BaseModule + toàn bộ UI
├── README.md
├── core/
│   ├── objective_functions.py  # Sphere, Ackley + registry
│   ├── particle.py             # Lớp Particle
│   └── swarm.py                # Lớp Swarm + step() + run()
├── models/
│   ├── config.py               # PSOConfig dataclass
│   └── state.py                # State schema + STATE_VERSION
├── workers/
│   └── simulation_worker.py    # QThread wrapper
└── tests/
    ├── test_manifest.py
    ├── test_objective_functions.py
    ├── test_particle.py
    ├── test_swarm.py
    └── test_smoke_ui.py
```

---

## Chạy thử (kịch bản mẫu)

### Kịch bản 1 — Sphere, 2D, Star, Clip
Dùng để xác nhận thuật toán hội tụ đúng:
- Hàm: Sphere → cực tiểu toàn cục tại gốc tọa độ
- Topology: Star
- Boundary: Clipping
- Kết quả kỳ vọng: gBest fitness → 0

### Kịch bản 2 — Ackley, 2D, Star, w giảm tuyến tính
Quan sát khả năng thoát cực trị cục bộ:
- Hàm: Ackley → nhiều cực trị cục bộ
- w: 0.9 → 0.4 (giảm tuyến tính)
- Kết quả kỳ vọng: gBest fitness → 0 (khởi đầu từ vùng ngẫu nhiên)

### Kịch bản 3 — Ackley, so sánh Star vs Ring
So sánh tốc độ hội tụ vs đa dạng quần thể:
- Cùng seed để so sánh công bằng
- Star hội tụ nhanh hơn nhưng dễ kẹt cực trị cục bộ hơn Ring

---

## Giới hạn v1.0

- Chỉ hỗ trợ biên đồng đều cho mọi chiều (không hỗ trợ biên khác nhau theo từng chiều).
- Trực quan hóa không gian 2D chỉ hoạt động khi `n_dimensions = 2`.
- Chưa hỗ trợ PSO rời rạc (TSP).
- Chưa hỗ trợ adaptive PSO hoặc hybrid PSO.

---

## Changelog

### v1.0.0 — 2026-04-13
- Module khởi tạo: Sphere + Ackley, Star + Ring topology, Clip + Reflect boundary
- QThread-based simulation để không block UI
- 2D particle scatter với contour nền
- Convergence chart theo vòng lặp
- Export PNG cho scatter và convergence
- State persistence qua StateManager
