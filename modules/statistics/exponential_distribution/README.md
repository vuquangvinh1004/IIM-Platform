# Exponential Distribution Explorer

Phiên bản: **1.0.0** | Category: `statistics` | SDK: `1.0.0`

---

## Mô tả

Module mô phỏng khám phá **phân phối mũ (Exponential Distribution)** — một phân phối liên tục dùng để mô hình hóa thời gian chờ giữa các sự kiện xảy ra ngẫu nhiên độc lập (quá trình Poisson).

Phân phối mũ **Exp(μ)** hoàn toàn được xác định bởi một tham số:

| Ký hiệu | Tên | Ý nghĩa |
|---|---|---|
| **μ** | Trung bình (mean) | Thời gian trung bình giữa hai sự kiện liên tiếp |
| **λ = 1/μ** | Tốc độ (rate) | Số sự kiện trung bình xảy ra trong 1 đơn vị thời gian |

### Công thức

```
PDF : f(x) = λ · exp(−λx)       x ≥ 0
CDF : F(x) = 1 − exp(−λx)       x ≥ 0

Trung bình  : E[X] = μ = 1/λ
Phương sai  : Var[X] = μ² = 1/λ²
Độ lệch chuẩn: σ = μ = 1/λ
Trung vị    : m = μ · ln 2 ≈ 0,6931 · μ
Mode        : 0
```

### Tính chất không nhớ (Memoryless Property)

```
P(X > s + t | X > s) = P(X > t)
```

---

## Chức năng

### Tab 1 — Phân phối Exp(μ)

- Vẽ đường cong PDF của Exp(μ) với tham số μ nhập vào
- Đánh dấu trung bình μ (đường đỏ đứt) và trung vị m (đường xanh lá chấm)
- Tô màu vùng P(0 ≤ X ≤ μ) ≈ 63,21%
- Hiển thị kết quả: μ, λ, σ², σ, trung vị, P(0≤X≤μ), P(0≤X≤2μ)

### Tab 2 — x → Xác suất

Ba loại xác suất có thể tính:

| Loại | Công thức | Diễn giải |
|---|---|---|
| **P(X ≤ x)** | CDF(x) | Xác suất sự kiện xảy ra trước hoặc tại x |
| **P(X > x)** | 1 − CDF(x) = SF(x) | Xác suất sự kiện xảy ra sau x (survival) |
| **P(a ≤ X ≤ b)** | CDF(b) − CDF(a) | Xác suất sự kiện rơi trong khoảng [a, b] |

Biểu đồ tô màu vùng diện tích tương ứng dưới đường cong. Kết quả hiển thị đầy đủ các xác suất liên quan.

---

## Cách sử dụng

1. Nhập **μ (trung bình)** — giá trị phải > 0
2. Chọn tab và hành động:
   - **"▶ Vẽ đồ thị"** → Tab 1, vẽ phân phối
   - **"🔍 Tính xác suất"** → Tab 2, tính P từ x
3. Nếu ở Tab 2, chọn loại xác suất và nhập x (hoặc a, b)
4. Nhấn nút tương ứng để cập nhật biểu đồ
5. **"💾 Xuất PNG"** để lưu biểu đồ hiện tại

---

## Ví dụ

**Ví dụ 1**: Thời gian giữa các cuộc gọi đến trung tâm hỗ trợ trung bình là **3 phút** (μ=3).  
- P(cuộc gọi đến trong 2 phút đầu) = P(X ≤ 2) = 1 − e^{−2/3} ≈ **0,4866**  
- P(chờ hơn 5 phút) = P(X > 5) = e^{−5/3} ≈ **0,1889**

**Ví dụ 2**: Tuổi thọ linh kiện điện tử là Exp(μ=100 giờ).  
- P(hỏng trước 50 giờ) = 1 − e^{−0,5} ≈ **0,3935**  
- P(hoạt động được từ 80 đến 120 giờ) = e^{−0,8} − e^{−1,2} ≈ **0,1484**

---

## Giới hạn v1.0

- Phân phối một chiều (univariate) với một tham số duy nhất μ
- Chỉ hỗ trợ Exponential; chưa hỗ trợ Weibull hay Gamma tổng quát
- Export chỉ theo định dạng PNG

---

## Cấu trúc thư mục

```
exponential_distribution/
├── module.json      Manifest
├── entry.py         Entry point
├── module.py        Logic chính + UI
├── __init__.py
├── README.md        File này
├── CHANGELOG.md
└── tests/
    ├── __init__.py
    ├── test_manifest.py
    ├── test_calculator.py
    └── test_smoke_ui.py
```

---

## Permissions

| Permission | Lý do |
|---|---|
| `storage.read` / `storage.write` | Lưu và phục hồi trạng thái phiên |
| `settings.read` / `settings.write` | Đọc ghi cấu hình module (precision) |
| `export.file` | Xuất biểu đồ PNG |
