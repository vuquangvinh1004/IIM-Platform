# Interactive Geometry Explorer

**Module ID:** `interactive_geometry`  
**Version:** 1.0.0  
**Category:** visualization  
**SDK Version:** 1.0.0  

## Mô tả

Module khám phá hình học 3D tương tác, minh chứng khả năng hiển thị mặt không gian ba chiều ngay trong shell IIMP. Toàn bộ tính toán hình học được thực hiện bằng thuần numpy — không phụ thuộc Qt ở lớp logic.

## Các hình dạng hỗ trợ

| Hình dạng | Định nghĩa |
|---|---|
| **Sine 2D (Sinc)** | Z = sin(r) / r, r = √(X²+Y²) |
| **Paraboloid** | Z = X² + Y² |
| **Yên ngựa (Saddle)** | Z = X² − Y² |
| **Hình cầu** | Tham số (θ, φ): x=sin(θ)cos(φ), y=sin(θ)sin(φ), z=cos(θ) |
| **Hình xuyến (Torus)** | R=3, r=1; tham số (θ, φ) |

## Điều khiển

- **Chọn hình dạng** — radio buttons
- **Elevation / Azimuth** — góc nhìn 3D (spinbox)
- **Độ phân giải** — Low (30×30) / Medium (60×60) / High (100×100)
- **Bảng màu** — 7 colormaps matplotlib
- **Xuất ảnh PNG** — gọi ExportService

## Thống kê tự động

Sau mỗi lần render, panel hiển thị:
- Z min / Z max / Z mean / Z std

## State persistence

State gồm: `shape`, `colormap`, `elevation`, `azimuth`, `resolution`.  
Tất cả JSON-serializable, tương thích `StateManager`.

## Export

Xuất canvas hiện tại dưới dạng PNG 150 DPI qua `ExportService.export_bytes`.

## Quyền

```json
["storage.read", "storage.write", "export.file", "settings.read", "settings.write"]
```

## Tests

```
modules/visualization/interactive_geometry/tests/
  test_manifest.py        — Kiểm tra manifest hợp lệ qua ModuleManifest
  test_geometry_core.py   — Unit tests cho compute_surface() và surface_stats()
  test_smoke_ui.py        — Smoke test build_view() (bỏ qua nếu không có PySide6)
```

## Yêu cầu

- Python ≥ 3.11
- numpy (đã có trong requirements.txt)
- matplotlib ≥ 3.8 với `mpl_toolkits.mplot3d` (đã có)
- PySide6 (chỉ cần để render UI, không cần để test logic)
