# Xấp xỉ Chuẩn của Phân phối Rời rạc

Module mô phỏng và minh hoạ xấp xỉ chuẩn (Central Limit Theorem) của hai phân phối rời rạc phổ biến.

## Tính năng

### Panel 1 — Phân phối Nhị thức B(n, p)

- Biểu đồ cột thể hiện PMF của B(n, p)
- Đường cong chuẩn xấp xỉ N(np, npq) chồng lên
- Điều chỉnh **n** (5 ÷ 300) và **p** (0.01 ÷ 0.99) bằng spin-box
- Kiểm tra điều kiện xấp xỉ: np ≥ 5 và nq ≥ 5

### Panel 2 — Phân phối Poisson P(μ)

- Biểu đồ cột thể hiện PMF của P(μ)
- Đường cong chuẩn xấp xỉ N(μ, μ) chồng lên
- Điều chỉnh **μ** (1.0 ÷ 100.0) bằng spin-box
- Kiểm tra điều kiện xấp xỉ: μ ≥ 10

## Cơ sở lý thuyết

| Phân phối | Xấp xỉ bởi | μ | σ² |
|---|---|---|---|
| B(n, p) | N(np, npq) | np | npq |
| P(μ) | N(μ, μ) | μ | μ |

Xấp xỉ chuẩn hợp lệ khi phân phối rời rạc đủ "cân xứng" và có phương sai đủ lớn.

## Thông số kỹ thuật

| Thuộc tính | Giá trị |
|---|---|
| ID | `normal_approximation` |
| Phiên bản | 1.0.0 |
| SDK | 1.0.0 |
| Danh mục | statistics |
| Lưu trạng thái | Có |
| Export | Không |

## Phụ thuộc

- `numpy` (đã có trong platform)
- `matplotlib` (đã có trong platform)

## Giới hạn

- Không hỗ trợ export ảnh trong v1.0
- Phạm vi n tối đa 300 để đảm bảo hiệu suất render
