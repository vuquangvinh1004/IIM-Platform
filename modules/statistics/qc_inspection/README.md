# QC Kiểm tra Chất lượng

> Module IIMP — `qc_inspection` v1.0.0  
> Category: `statistics`

## Mô tả

Module mô phỏng quy trình kiểm tra chất lượng sản phẩm (QC) trên dây chuyền sản xuất. Người dùng đóng vai nhân viên QC, phân loại thành phẩm / phế phẩm qua nhiều lần kiểm tra, sau đó phân tích dữ liệu bằng phân phối nhị thức và Poisson.

## Tính năng

### Giao diện kiểm tra

- Nhập số sản phẩm mỗi lần (1 – 40) và số lần kiểm tra
- **QC Thủ công**: Xem khay sản phẩm (thành phẩm ✓ xanh / phế phẩm ✕ đỏ), click để đánh dấu phế phẩm → Ghi nhận
- **QC Tự động**: Tự sinh dữ liệu cho toàn bộ lần còn lại
- Bảng kết quả: Lần KT | Tổng SP | Số PP | Tỷ lệ PP

### Giao diện mô phỏng (sau khi hoàn đủ số lần)

- Thống kê tổng hợp: tổng SP kiểm, tổng PP, tỷ lệ p, n, μ
- Bảng tần số phế phẩm + Biểu đồ cột tần số
- Đối chiếu lý thuyết:
  - **Phân phối Nhị thức** Bin(n, p̂) vs. tần suất thực tế
  - **Phân phối Poisson** Po(μ = n·p̂) vs. tần suất thực tế

## Cách sử dụng

1. Nhập **số SP/lần** (khuyến nghị 10-20) và **số lần KT** (khuyến nghị ≥ 20 để phân phối rõ ràng)
2. Nhấn **QC Thủ công**:
   - Khay sản phẩm xuất hiện. Sản phẩm xanh ✓ = thành phẩm, đỏ ✕ = phế phẩm (nhìn bằng mắt)
   - Click vào sản phẩm phế phẩm để đánh dấu (border xanh dương = đã chọn)
   - Nhấn **Ghi nhận** để lưu kết quả lần này
   - Lặp lại cho đến khi đủ số lần
3. Hoặc nhấn **QC Tự động** để tự động hoàn tất toàn bộ
4. Sau khi đủ số lần, nhấn **Mô phỏng →** để chuyển sang phân tích thống kê
5. Nhấn **← Quay lại** để về giao diện kiểm tra (dữ liệu được giữ nguyên)

## Nền tảng thống kê

Mỗi sản phẩm có xác suất bị lỗi cố định p ≈ 0.25 (ẩn với người dùng để mô phỏng thực tế).

Số phế phẩm X trong một lần kiểm tra n sản phẩm theo lý thuyết:

- **X ~ Bin(n, p)**: P(X = k) = C(n,k) · pᵏ · (1-p)^(n-k)
- **X ≈ Po(μ = n·p)** khi n lớn, p nhỏ: P(X = k) = e^(-μ) · μᵏ / k!

Module tính p̂ thực tế = tổng phế phẩm / tổng sản phẩm kiểm tra, sau đó vẽ đồ thị lý thuyết với p = p̂ so với phân phối thực tế.

## Giới hạn v1.0

- Xác suất phế phẩm nền cố định (không cấu hình được từ UI)
- Không hỗ trợ export (sẽ bổ sung ở phiên bản sau)
- Không khôi phục khay sản phẩm thủ công đang dở khi restore session
- Phân phối Poisson phù hợp nhất khi n lớn và p nhỏ (n ≥ 20, p ≤ 0.1)

## Cấu trúc thư mục

```text
qc_inspection/
├── module.json      Manifest: metadata, permissions, entry point
├── entry.py         Export QCInspectionModule
├── module.py        Toàn bộ engine + UI
├── __init__.py
├── README.md        File này
├── CHANGELOG.md
└── tests/
    ├── test_manifest.py
    ├── test_calculator.py
    └── test_smoke_ui.py
```

## Thay đổi

Xem [CHANGELOG.md](CHANGELOG.md).
