# Mô phỏng Cung - Cầu

Module tương tác mô phỏng mô hình Cung - Cầu trong kinh tế vi mô.

## Tính năng

- **Tab 1 — Mô hình Cung - Cầu**: Đồ thị tổng quát với điểm cân bằng, vùng thặng dư (đỏ) và thiếu hụt (xanh). Thanh trượt giá dọc + 3 thanh trượt yếu tố ngang dịch chuyển đường cung/cầu.
- **Tab 2 — Đường Cung**: Phân tích sâu luật cung với 5 yếu tố ngoại sinh.  
- **Tab 3 — Đường Cầu**: Phân tích sâu luật cầu với 5 yếu tố ngoại sinh.

## Mô hình kinh tế

- Đường cung: `Qs = -10 + 3P` (dốc lên)
- Đường cầu: `Qd = 70 - 2P` (dốc xuống)
- Điểm cân bằng: `P* = 16`, `Q* = 38`

## Yêu cầu

- PySide6 >= 6.6
- matplotlib >= 3.8
- numpy >= 1.26
