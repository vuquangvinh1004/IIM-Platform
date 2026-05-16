# Một số phương pháp dự báo thông dụng

Dưới đây là mô tả một số phương pháp dự báo thông dụng theo cấu trúc: **Mô hình + chú thích**, **Mẫu hình dữ liệu phù hợp**, và **Lưu ý khi sử dụng**.

| Phương pháp | Mô hình + chú thích | Mẫu hình dữ liệu phù hợp | Lưu ý khi sử dụng |
|---|---|---|---|
| **Naive (Naive Approach)** | **Mô hình:** `Ŷ(t+1) = Y(t)`  
**Chú thích:** Dự báo kỳ sau bằng đúng giá trị thực tế của kỳ hiện tại. Đây là mô hình rất đơn giản, thường được dùng làm mức chuẩn để so sánh với các mô hình khác. | Phù hợp nhất với dữ liệu **ổn định**, ít biến động có cấu trúc rõ ràng. Cũng có thể dùng như mô hình tham chiếu ban đầu cho chuỗi có **xu hướng yếu** hoặc biến động ngẫu nhiên. | Rất dễ áp dụng, không cần ước lượng nhiều tham số. Tuy nhiên, mô hình phản ứng hoàn toàn theo giá trị gần nhất nên dễ bị nhiễu nếu dữ liệu biến động bất thường. Không phù hợp khi dữ liệu có **xu hướng rõ**, **mùa vụ**, hoặc **chu kỳ**. |
| **Bình quân di động k thời kỳ (Moving Average-k)** | **Mô hình:** `Ŷ(t+1) = [Y(t) + Y(t-1) + ... + Y(t-k+1)] / k`  
**Chú thích:** Dự báo được tính bằng trung bình cộng của `k` quan sát gần nhất. Mục đích chính là làm trơn chuỗi số liệu ngắn hạn. | Phù hợp với dữ liệu **ổn định** hoặc dao động ngẫu nhiên quanh một mức trung bình tương đối cố định. Có thể dùng khi chuỗi không có **xu hướng** và không có **mùa vụ** rõ rệt. | Chọn `k` rất quan trọng: `k` nhỏ thì mô hình nhạy hơn với thay đổi mới, `k` lớn thì chuỗi được làm trơn hơn nhưng phản ứng chậm. Không phù hợp với dữ liệu có **xu hướng**, **mùa vụ**, hoặc các thay đổi cấu trúc nhanh. |
| **San bằng số mũ đơn giản (Simple Exponential Smoothing)** | **Mô hình:** `Ŷ(t+1) = αY(t) + (1-α)Ŷ(t)` với `0 < α < 1`  
**Chú thích:** Dự báo mới là sự kết hợp giữa giá trị thực tế gần nhất và dự báo của kỳ trước. Trọng số lớn hơn được đặt cho thông tin mới hơn thông qua tham số `α`. | Phù hợp với dữ liệu **ổn định**, không có **xu hướng** và không có **mùa vụ**. | Nếu `α` lớn, mô hình phản ứng nhanh với thay đổi mới; nếu `α` nhỏ, mô hình trơn hơn. Cần chọn giá trị `α` hợp lý. Không phù hợp cho chuỗi có **xu hướng**, **mùa vụ**, hoặc **chu kỳ** rõ rệt. |
| **Hồi quy tuyến tính (Linear Regression)** | **Mô hình:** `Y(t) = a + bt + ε(t)`  
**Chú thích:** Giá trị dự báo được mô tả như một hàm tuyến tính theo thời gian, trong đó `a` là hệ số chặn, `b` là độ dốc xu hướng, `ε(t)` là sai số ngẫu nhiên. Có thể mở rộng bằng cách thêm biến giải thích khác nếu cần. | Phù hợp với dữ liệu có **xu hướng tuyến tính**. Cũng có thể dùng cho dữ liệu kết hợp nếu mô hình được mở rộng thêm biến giả mùa vụ hoặc biến kinh tế giải thích. | Hiệu quả khi mối quan hệ với thời gian là tương đối tuyến tính. Nếu xu hướng thay đổi theo thời gian hoặc dữ liệu có **mùa vụ**, **chu kỳ** phức tạp mà không được mô hình hóa thêm, sai số sẽ tăng. Cần kiểm tra giả định phần dư và độ phù hợp của mô hình. |
| **Mô hình Holt (Holt's Model)** | **Mô hình:**  
Mức: `L(t) = αY(t) + (1-α)[L(t-1) + T(t-1)]`  
Xu hướng: `T(t) = β[L(t) - L(t-1)] + (1-β)T(t-1)`  
Dự báo: `Ŷ(t+h) = L(t) + hT(t)`  
**Chú thích:** Holt mở rộng san bằng số mũ đơn giản bằng cách bổ sung thành phần **xu hướng**. `L(t)` là mức, `T(t)` là xu hướng, `h` là số kỳ dự báo trước. | Phù hợp với dữ liệu có **xu hướng** nhưng **không có mùa vụ**. Thường dùng cho chuỗi tăng hoặc giảm khá đều theo thời gian. | Thích hợp hơn SES khi chuỗi có xu hướng rõ. Cần ước lượng hai tham số `α` và `β`. Nếu dữ liệu có **mùa vụ**, nên chuyển sang Holt-Winters thay vì Holt. Khi xu hướng thay đổi mạnh hoặc không ổn định, mô hình có thể dự báo lệch ở kỳ xa. |

## Tóm tắt ngắn

- **Naive**: dùng khi cần mô hình rất đơn giản hoặc làm chuẩn so sánh.
- **Bình quân di động**: dùng để làm trơn dữ liệu ổn định.
- **San bằng số mũ đơn giản**: phù hợp với dữ liệu ổn định, ưu tiên dữ liệu mới hơn.
- **Hồi quy tuyến tính**: phù hợp khi có xu hướng tuyến tính rõ.
- **Holt**: phù hợp khi có xu hướng nhưng chưa có mùa vụ.
