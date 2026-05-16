# Mô phỏng Chuỗi số Thời gian

Module giảng dạy về chuỗi số thời gian và cách phân tích các thành phần của nó.

## Mô tả

Module minh họa 4 thành phần chính của một chuỗi số thời gian:

| Tab | Thành phần | Công thức | Trục thời gian |
|-----|------------|-----------|----------------|
| Xu hướng | Trend T_t | `T_t = a × t^k` | 120 tháng (10 năm) |
| Mùa vụ | Seasonal S_t | `S_t = A × sin(2πt/P)` | 36 tháng (3 năm) |
| Chu kỳ | Cyclical C_t | `C_t = A × sin(2πt/Pc)` | 240 tháng (20 năm) |
| Tổng hợp | Y_t | Cộng tính hoặc Nhân tính | 120 tháng (10 năm) |

## Tính năng

### Tab 1: Xu hướng (Trend)
- Chọn hướng xu hướng: Tăng dần hoặc Giảm dần
- Chọn dạng: Tuyến tính (k=1) hoặc Phi tuyến (k≠1)
- Điều chỉnh độ dốc `a` và lũy thừa `k`
- Hiển thị công thức và giá trị tại các mốc thời gian

### Tab 2: Mùa vụ (Seasonal)
- Chọn chu kỳ lặp: Tháng (P=1), Quý (P=3), Năm (P=12)
- Điều chỉnh biên độ dao động `A`
- Đường chu kỳ ranh giới được vẽ tự động

### Tab 3: Chu kỳ (Cyclical)
- Điều chỉnh khoảng thời gian chu kỳ P_c (24–120 tháng)
- Điều chỉnh biên độ `A`
- Hiển thị 20 năm để thấy rõ các đợt sóng dài

### Tab 4: Tổng hợp
- Chọn giữa mô hình Cộng tính và Nhân tính
- Bật/tắt từng thành phần T, S, C, I riêng lẻ
- Điều chỉnh độ nhiễu trắng σ
- Thêm đột biến ngẫu nhiên (outlier) bằng nút "Thêm đột biến"
- Đổi mẫu nhiễu để xem các kịch bản khác nhau
- Hiển thị từng thành phần dưới dạng đường kẻ mờ

## Mô hình toán học

### Mô hình Cộng tính (Additive):
```
Y_t = T_t + S_t + C_t + I_t
```

### Mô hình Nhân tính (Multiplicative):
```
Y_t = T_t × (1 + S_t/T̄) × (1 + C_t/T̄) + I_t
```
Trong đó T̄ = mean(|T_t|) là giá trị tham chiếu để chuẩn hóa biên độ mùa vụ và chu kỳ.

## Yêu cầu

- PySide6 >= 6.6
- matplotlib >= 3.8
- numpy >= 1.26

## Giới hạn phiên bản 1.0.0

- Không hỗ trợ import/export dữ liệu thực
- Không hỗ trợ phân tích chuỗi (decomposition) tự động
- Mô hình nhân tính yêu cầu xu hướng T_t > 0

## CHANGELOG

### v1.0.0
- Phát hành ban đầu
- 4 tab: Xu hướng, Mùa vụ, Chu kỳ, Tổng hợp
- Mô hình cộng tính và nhân tính
- Cơ chế thêm đột biến và đổi mẫu nhiễu
- Phục hồi trạng thái tab Tổng hợp
