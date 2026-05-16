# MODULE MÔ PHỎNG CHUỖI SỐ THỜI GIAN

## 1. Thiết kế cấu trúc các Tab (UI/UX)

Để thống nhất, chúng ta sẽ sử dụng **tháng** làm đơn vị thời gian cơ bản cho trục hoành ($t$).

### Tab 1: Xu hướng (Trend - $T_t$)

* **Mô tả:** Thể hiện hướng đi dài hạn của dữ liệu.
* **Điều khiển (Sidebar):**
  * *Hướng:* Chọn Tăng hoặc Giảm.
  * *Dạng:* Chọn Tuyến tính ($y = ax$) hoặc Phi tuyến ($y = ax^k$).
  * *Độ dốc ($a$):* Thanh trượt từ 0 đến 10.
  * *Tốc độ thay đổi ($k$):* Thanh trượt (nếu chọn Phi tuyến), giúp đường cong uốn lượn nhiều hay ít.
* **Đồ thị:** Trục hoành 120 tháng (10 năm).

### Tab 2: Mùa vụ (Seasonality - $S_t$)

* **Mô tả:** Những biến động lặp lại trong một khoảng thời gian cố định.
* **Điều khiển (Sidebar):**
  * *Chu kỳ lặp:* Chọn Tháng ($P=1$), Quý ($P=3$), hoặc Năm ($P=12$).
  * *Mức độ biến động ($A$):* Thanh trượt điều chỉnh biên độ cao/thấp.
* **Đồ thị:** Trục hoành 36 tháng (3 năm) để thấy rõ sự lặp lại.

### Tab 3: Chu kỳ (Cyclical - $C_t$)

* **Mô tả:** Những biến động lên xuống dài hạn, không cố định như mùa vụ.
* **Điều khiển (Sidebar):**
  * *Khoảng thời gian ($P_{cycle}$):* Thanh trượt từ 24 đến 120 tháng (2-10 năm).
  * *Mức độ biến động:* Biên độ của các đợt sóng dài.
* **Đồ thị:** Trục hoành 240 tháng (20 năm).

### Tab 4: Tổng hợp (Main Time Series - $Y_t$)

* **Mô tả:** "Bản nhạc hoàn chỉnh" kết hợp từ các thành phần trên.
* **Điều khiển (Sidebar):**
  * *Loại mô hình:* Chọn **Cộng tính** hoặc **Nhân tính**.
  * *Thành phần:* Các checkbox để bật/tắt $T, S, C, I$.
  * *Nhiễu (Noise):* Thanh trượt điều chỉnh độ "răng cưa" của đường đồ thị.
  * *Biến động đột biến (Irregular):* Nút bấm "Add Shock" để tạo các điểm bùng phát ngẫu nhiên.

---

## 2. Đề xuất công thức toán học (Backend)

Để mô phỏng tự nhiên nhất, bạn nên sử dụng các hàm số sau:

### A. Hàm xu hướng ($T_t$)

Sử dụng hàm lũy thừa để bao quát cả tuyến tính và phi tuyến:
$$T_t = direction \times (a \times t^k)$$

* Nếu $k=1$: Đường thẳng (Tuyến tính).
* Nếu $k>1$: Đường cong tăng tốc.
* Nếu $k<1$: Đường cong tăng chậm dần.

### B. Hàm mùa vụ và chu kỳ ($S_t$ và $C_t$)

Sử dụng **hàm Sin** là cách đơn giản và hiệu quả nhất để minh họa tính tuần hoàn:
$$f(t) = A \times \sin\left(\frac{2\pi t}{P}\right)$$

* **Mùa vụ:** $P$ sẽ nhận các giá trị 1, 3, hoặc 12.
* **Chu kỳ:** $P$ sẽ nhận giá trị từ thanh trượt (24 đến 120).
* *Gợi ý nâng cao:* Nếu muốn mùa vụ trông "thực" hơn (không quá mượt như sóng sin), bạn có thể dùng **Hàm sóng vuông** hoặc cộng 2-3 sóng Sin lại với nhau.

### C. Biến động ngẫu nhiên ($I_t$) và Nhiễu (Noise)

* **Nhiễu trắng (White Noise):** Sử dụng hàm số ngẫu nhiên theo phân phối chuẩn: $Noise \sim N(0, \sigma^2)$.
* **Đột biến (Outliers):** Khi nhấn nút, cộng thêm một giá trị lớn $V$ vào một vị trí $t$ ngẫu nhiên:
  * Cộng tính: $Y_{t} = Y_{t} + V$
  * Nhân tính: $Y_{t} = Y_{t} \times (1 + V\%)$

---

## 3. Cách thức xây dựng module

Tôi đề xuất bạn sử dụng **Streamlit (Python)**. Đây là công cụ mạnh mẽ nhất hiện nay để tạo các ứng dụng mô phỏng dữ liệu chỉ với vài dòng code:

1. **Ngôn ngữ:** Python.
2. **Thư viện đồ thị:** **Plotly** (để người dùng có thể rê chuột xem giá trị cụ thể, phóng to/thu nhỏ đồ thị).
3. **Thư viện tính toán:** **Numpy** (để tạo mảng thời gian và tính toán hàm Sin nhanh chóng).
4. **Triển khai:** Có thể chạy trực tiếp trên trình duyệt qua Streamlit Cloud (miễn phí).

**Luồng xử lý dữ liệu sẽ như sau:**

1. Khởi tạo mảng `t = [0, 1, 2, ..., 240]`.
2. Tính toán các mảng thành phần riêng biệt dựa trên slider: `trend_array`, `seasonal_array`, `cycle_array`.
3. Nếu chọn **Cộng tính**: `total = trend + seasonal + cycle + noise`.
4. Nếu chọn **Nhân tính**: `total = trend * (1 + seasonal_idx) * (1 + cycle_idx) + noise`.
   * *Lưu ý:* Trong mô hình nhân tính, các thành phần mùa vụ nên dao động quanh mức 1 (ví dụ: 0.9 đến 1.1) để không làm biến dạng hoàn toàn xu hướng.
