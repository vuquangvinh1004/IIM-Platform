# Normal Distribution Explorer — IIMP Module v2.0.0

## Thông tin module

| Thuộc tính | Giá trị |
|---|---|
| ID | `normal_distribution` |
| Tên | Normal Distribution Explorer |
| Phiên bản | 2.0.0 |
| Danh mục | statistics |
| SDK version | 1.0.0 |

## Mô tả

Module mô phỏng phân phối chuẩn N(μ, σ) với ba chế độ hoạt động độc lập, hỗ trợ **tham số bất kỳ** (trung bình μ và độ lệch chuẩn σ):

### Chế độ 1 — Phân phối N(μ, σ)
- Hiển thị đường cong bell của N(μ, σ) với các dải xác suất
- Quy tắc **68–95–99,7%**: vùng [μ−σ, μ+σ], [μ−2σ, μ+2σ], [μ−3σ, μ+3σ]
- Đường tham chiếu tại μ (đỏ) và μ±kσ (xám chấm)
- Kết quả: μ, σ, σ², các khoảng xác suất

### Chế độ 2 — α → Z/X (Tìm ngưỡng tới hạn)
- Người dùng nhập diện tích đuôi trái (α_trái) và đuôi phải (α_phải)
- Module tính **z tới hạn** bằng `scipy.stats.norm.ppf(α)`
- Tính **X tới hạn** = μ + σ × z (dành cho phân phối tổng quát)
- Đồ thị tô màu vùng đuôi (đỏ) và vùng giữa (xanh)
- Kết quả: z_l, z_r, X_l, X_r (nếu μ≠0 hoặc σ≠1), α_l, α_r, 1−α

### Chế độ 3 — Z/X → α (Tìm xác suất)
- Người dùng nhập giá trị ngưỡng Z hoặc X (chọn được qua radio button)
- Module tính **diện tích đuôi trái, đuôi phải và vùng giữa** bằng `scipy.stats.norm.cdf`
- Tự động hoán đổi nếu giá trị trái > giá trị phải
- Kết quả: area_l, area_r, area_m, z_l, z_r, X_l, X_r

## Tham số phân phối

| Tham số | Ký hiệu | Phạm vi | Mặc định |
|---|---|---|---|
| Trung bình | μ | −1000 đến 1000 | 0,0 |
| Độ lệch chuẩn | σ | 0,001 đến 1000 | 1,0 |

## Permissions yêu cầu

| Permission | Mục đích |
|---|---|
| `storage.read` | Đọc state session từ DB |
| `storage.write` | Lưu state session vào DB |
| `export.file` | Xuất đồ thị PNG qua ExportService |
| `settings.read` | Đọc cài đặt precision |
| `settings.write` | Lưu cài đặt precision |

## State persistence

Module lưu và khôi phục toàn bộ trạng thái giao diện:

```json
{
  "mu": 0.0,
  "sigma": 1.0,
  "tab": 0,
  "alpha_l": 0.025,
  "alpha_r": 0.025,
  "z_l": -1.96,
  "z_r": 1.96,
  "z_input_mode": "z",
  "precision": 4
}
```

## Cấu trúc thư mục

```
modules/statistics/normal_distribution/
├── __init__.py
├── module.json          ← manifest v2.0.0
├── entry.py             ← exports NormalDistributionModule
├── module.py            ← NormalDistributionModule + _NormalCurveCanvas
├── README.md
└── tests/
    ├── __init__.py
    ├── test_manifest.py       ← kiểm tra manifest schema
    ├── test_calculator.py     ← unit test 2 static computation methods
    └── test_smoke_ui.py       ← smoke test dựng view, 3 tab, lifecycle
```

## Thay đổi từ v1.0.0

| Thay đổi | Ghi chú |
|---|---|
| Thêm tham số μ và σ tùy ý | Không còn giới hạn N(0,1) |
| Thêm Tab 1: Phân phối N(μ,σ) | Dải 68-95-99,7%, đường tham chiếu |
| Tái cấu trúc thành 3 tab | Mỗi chế độ độc lập rõ ràng |
| Chế độ Z/X toggle trong Tab 3 | Nhập Z hoặc X, tự chuyển đổi |
| Canvas class đổi tên | `_DistributionCanvas` → `_NormalCurveCanvas` |
| State schema version 2.0.0 | Thêm: mu, sigma, tab, z_l, z_r, z_input_mode |
| Default precision | 3 → 4 |


## Thông tin module

| Thuộc tính | Giá trị |
|---|---|
| ID | `normal_distribution` |
| Tên | Normal Distribution Explorer |
| Phiên bản | 1.0.0 |
| Danh mục | statistics |
| SDK version | 1.0.0 |

## Mô tả

Module mô phỏng phân phối chuẩn tắc, cho phép người dùng:
- Nhập diện tích đuôi (α) để tìm giá trị tới hạn z
- Nhập giá trị tới hạn z để tìm diện tích
- Quan sát vùng xác suất tô màu trực tiếp trên đường cong
- Xuất đồ thị ra file PNG độ phân giải cao

## Chế độ hoạt động

### Chế độ α (Nhập diện tích)
- Người dùng nhập diện tích đuôi trái và đuôi phải (0.00001 – 0.49999)
- Module tự động tính ngưỡng z tương ứng bằng `scipy.stats.norm.ppf`

### Chế độ z (Nhập giá trị tới hạn)
- Người dùng nhập giá trị z cho đuôi trái (âm) và đuôi phải (dương)
- Module tự động tính diện tích tương ứng bằng `scipy.stats.norm.cdf`

## Permissions yêu cầu

| Permission | Mục đích |
|---|---|
| `storage.read` | Đọc state session từ DB |
| `storage.write` | Lưu state session vào DB |
| `export.file` | Xuất đồ thị PNG qua ExportService |
| `settings.read` | Đọc cài đặt precision |
| `settings.write` | Lưu cài đặt precision |

## State persistence

Module lưu và khôi phục các trường sau:

```json
{
  "mode": "alpha",
  "left_val": 0.05,
  "right_val": 0.05,
  "precision": 3
}
```

## Cấu trúc thư mục

```
modules/statistics/normal_distribution/
├── __init__.py
├── module.json          ← manifest
├── entry.py             ← exports NormalDistributionModule
├── module.py            ← NormalDistributionModule + _DistributionCanvas
├── README.md
└── tests/
    ├── __init__.py
    ├── test_manifest.py
    ├── test_calculator.py
    └── test_smoke_ui.py
```

## Phụ thuộc

- `matplotlib >= 3.7`
- `numpy >= 1.24`
- `scipy >= 1.11`
- `PySide6 >= 6.6`

## Entry point

```
modules.statistics.normal_distribution.entry:NormalDistributionModule
```

## Tham chiếu gốc

Logic tính toán và visualization được port từ `C4_Mo_phong_phan_phoi_chuan.py`
(phiên bản standalone) sang kiến trúc IIMP module với Qt-embedded canvas.
