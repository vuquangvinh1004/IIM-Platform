# Tìm hiểu PSO với Đa đồ thị

## Kịch bản mô phỏng: Giải toán Tối ưu hóa Lộ trình bằng PSO

### 1. Cấu trúc mô phỏng (Setup)

* **Không gian bài toán:** Một bản đồ phẳng với 5 điểm tọa độ cố định ($A, B, C, D, E$).
* **Đối tượng mô phỏng:** 10 "hạt" (hạt xe giao hàng).
* **Giao diện trực quan:** 10 biểu đồ con (subplots) sắp xếp cạnh nhau. Mỗi biểu đồ đại diện cho "tư duy" hiện tại của một hạt.
* **Mục tiêu (Fitness Function):** Tìm chuỗi thứ tự đi qua 5 điểm sao cho Tổng Quãng đường $L$ là nhỏ nhất.

---

## 2. Quy trình vận hành từng bước (Step-by-Step)

### Bước 1: Khởi tạo bầy đàn (Initialization - Sự hỗn loạn ban đầu)

* **Hành động:** 10 hạt chọn ngẫu nhiên thứ tự các điểm (Ví dụ: Hạt 1 đi `A-B-C-D-E`, Hạt 2 đi `C-E-A-B-D`).
* **Hiển thị:** Trên 10 biểu đồ, các đường nối giữa 5 điểm hiện lên chồng chéo, không giống nhau.
* **Ghi nhận:** Máy tính tính tổng quãng đường của từng hạt. Hạt nào có quãng đường ngắn nhất sẽ được gắn nhãn là **Gbest** (Cả bầy cùng biết hạt này đang dẫn đầu).

### Bước 2: Chu kỳ học hỏi và Cập nhật (The Update Cycle)

Ở mỗi vòng lặp tiếp theo, mỗi hạt sẽ không còn chạy ngẫu nhiên mà thực hiện "phép tính vận tốc" dựa trên 3 yếu tố:

1. **Quán tính ($w$):** Tiếp tục xu hướng của lộ trình cũ.
2. **Ký ức cá nhân ($c_1$):** Có xu hướng quay lại thứ tự tốt nhất mà *chính nó* từng tìm được ($Pbest$).
3. **Học hỏi xã hội ($c_2$):** Có xu hướng bắt chước thứ tự của hạt tốt nhất bầy ($Gbest$).

### Bước 3: Phép toán biến đổi (Swap Operators)

* **Cách thức:** Vì đây là các điểm rời rạc, "di chuyển" nghĩa là **tráo đổi**.
* *Ví dụ:* Nếu $Gbest$ đi `A-C` mà hạt hiện tại đi `A-B`, hạt sẽ thực hiện lệnh tráo đổi vị trí của `B` và `C` để giống với "kẻ giỏi nhất".

### Bước 4: Hội tụ (Convergence)

* **Kết quả:** Sau 20-50 vòng lặp, lực kéo từ $Gbest$ sẽ làm cho lộ trình của 10 hạt dần trở nên giống hệt nhau. 10 biểu đồ con lúc này sẽ hiển thị 10 hình vẽ giống nhau – đó chính là lộ trình tối ưu nhất mà bầy đàn tìm được.

---

## 3. Các đề xuất cải thiện để mô phỏng "thực" hơn

Để mô phỏng của bạn không chỉ dừng lại ở mức cơ bản mà thực sự mạnh mẽ, hãy thêm các yếu tố sau:

### A. Thêm "Yếu tố đột biến" (Mutation) [Đề xuất quan trọng]

Để tránh vấn đề "bẫy tối ưu cục bộ" mà bạn đã lo lắng, hãy quy định: *Ở mỗi vòng lặp, có 5% cơ hội một hạt sẽ tự tráo đổi ngẫu nhiên 2 điểm bất kỳ mà không cần học hỏi ai.* Điều này giúp bầy đàn luôn có cơ hội tìm thấy "lối đi mới" tốt hơn nghiệm hiện tại.

### B. Hiệu ứng trực quan hóa màu sắc

* Sử dụng màu **Đỏ** cho lộ trình của hạt đang là $Gbest$.
* Sử dụng màu **Xám** cho các hạt khác.
* Khi một hạt bất kỳ tìm được đường ngắn hơn $Gbest$ cũ, nó sẽ "đổi màu" thành Đỏ, tạo hiệu ứng bầy đàn đang tranh đua rất sinh động.

### C. Bổ sung biểu đồ đường cong hội tụ

Bên cạnh 10 biểu đồ bản đồ, bạn nên có thêm 1 biểu đồ thứ 11 vẽ đường thẳng thể hiện giá trị quãng đường ngắn nhất giảm dần theo thời gian. Khi đường này đi ngang (không giảm thêm được nữa), đó là lúc thuật toán đã hoàn thành nhiệm vụ.

---

## 4. Bảng tham số thiết kế cho mô phỏng của bạn

| Tham số | Giá trị gợi ý | Ý nghĩa thiết kế |
| :--- | :--- | :--- |
| **Số lượng hạt** | 10 | Đủ để quan sát mà không làm rối màn hình. |
| **Hệ số quán tính ($w$)** | 0.9 giảm dần về 0.4 | Đầu buổi "xông xáo", cuối buổi "cẩn trọng". |
| **Hệ số $c_1, c_2$** | 1.5 đến 2.0 | Cân bằng giữa cái tôi và tính cộng đồng. |
| **Số lần lặp (Iterations)** | 50 - 100 | Đủ thời gian để thấy sự hội tụ rõ nét. |
