# MÔ TẢ MODULE MÔ PHỎNG CUNG - CẦU (PYTHON)

## 1. Cấu trúc chung

Giao diện gồm **3 Thẻ (Tabs)** chính:

* **Thẻ 1: Mô hình Cung - Cầu (Tổng quát)**
* **Thẻ 2: Đường Cung (Phân tích sâu)**
* **Thẻ 3: Đường Cầu (Phân tích sâu)**

---

## 2. Chi tiết các Thẻ (Tabs)

### Thẻ 1: Mô hình Cung - Cầu

**Mục tiêu:** Giúp học sinh hiểu về điểm cân bằng và trạng thái thị trường.

* **Phía trên bên phải:** Nút **[Giả định mô hình]** (Popup hiển thị các quy tắc: thị trường cạnh tranh, thông tin hoàn hảo...).
* **Khu vực đồ thị:** Trục tung ($P$ - Giá), Trục hoành ($Q$ - Lượng).
  * Đường Cung (S) dốc lên, đường Cầu (D) dốc xuống.
* **Hệ thống tương tác:**
    1. **Thanh trượt Giá (Dọc):** Nằm song song trục tung.
        * Khi kéo: Xuất hiện 2 điểm trên đường S và D tương ứng với mức giá đó.
        * Tại điểm cắt: Hiện chữ **"Điểm cân bằng"** kèm mũi tên.
        * Giá > Cân bằng: Tô màu **Đỏ** phần diện tích **Thặng dư**.
        * Giá < Cân bằng: Tô màu **Xanh dương** phần diện tích **Thiếu hụt**.
    2. **Khung lựa chọn & 3 Thanh trượt Yếu tố (Ngang):**
        * Người dùng chọn tối đa 3 yếu tố ảnh hưởng (từ danh sách cho trước).
        * Mỗi yếu tố được gán vào 1 thanh trượt (Ký hiệu: Vuông, Tam giác, Thoi).
        * Khi trượt: Đường S hoặc D tương ứng sẽ **dịch chuyển trái/phải** trên đồ thị.

### Thẻ 2 & 3: Đường Cung / Đường Cầu (Riêng biệt)

**Mục tiêu:** Phân biệt "Luật Cung/Cầu" và "Các yếu tố làm dịch chuyển đường".

* **Đồ thị:** Chỉ hiển thị 1 đường duy nhất (Cung hoặc Cầu).
* **Hệ thống tương tác:**
    1. **1 Thanh trượt Giá (Dọc):** Thay đổi giá để điểm chạy trên đường (Luật Cung/Cầu).
    2. **6 Thanh trượt Yếu tố (Ngang):** Tương ứng với 5 yếu tố ngoại sinh (ví dụ: Thu nhập, Công nghệ, Thuế...).
* **Hộp chú giải động (Dynamic Tooltip):** * Mỗi khi người dùng tương tác, hộp này sẽ hiển thị lý thuyết tương ứng.
  * *Ví dụ:* Khi kéo thanh trượt Giá ở Thẻ Cầu, hộp hiện: "Luật Cầu: Giá tăng thì lượng cầu giảm và ngược lại."

---

## 3. Góp ý bổ sung để module "xịn" hơn

1. **Phân biệt màu sắc nhất quán:** * Nên quy định màu cố định cho Cung (ví dụ: Cam) và Cầu (ví dụ: Xanh lá) xuyên suốt cả 3 thẻ để học sinh không bị nhầm lẫn.
2. **Chế độ "Reset":** * Thêm một nút "Thiết lập lại" để đưa tất cả các đường và thanh trượt về trạng thái cân bằng ban đầu.
3. **Sử dụng thư viện Python:**
    * Bạn nên dùng **Streamlit** hoặc **Dash (Plotly)**. Đây là những thư viện cực kỳ mạnh mẽ để tạo dashboard tương tác bằng Python mà không cần biết quá nhiều về HTML/CSS. Đặc biệt, Plotly cho phép di chuột vào điểm trên đồ thị để hiện thông số chính xác ($P, Q$).
4. **Minh họa bằng số:** * Bên cạnh đồ thị, hãy để một bảng nhỏ hiển thị con số cụ thể (Giá: 10, Lượng cung: 50, Lượng cầu: 30 -> Dư thừa: 20). Điều này giúp các bạn học sinh giỏi tính toán dễ theo dõi hơn.

---

## 4. Nội dung lý thuyết được dùng để xây dựng = mô hình cung - cầu

Lý thuyết cung - cầu là "xương sống" của kinh tế học vi mô, giải thích cách thị trường vận hành để xác định giá cả và số lượng hàng hóa được trao đổi. Dưới đây là phân tích chi tiết về các thành phần và cơ chế của mô hình này.

---

### 4.1\. Lý thuyết Cung - Cầu là gì?

Lý thuyết này mô tả mối quan hệ giữa lượng hàng hóa mà người bán sẵn sàng cung cấp (**Cung - Supply**) và lượng hàng hóa mà người mua sẵn sàng tiêu thụ (**Cầu - Demand**) tại các mức giá khác nhau.

Mối quan hệ này quyết định mức giá thị trường và sản lượng giao dịch thực tế.

* **Luật Cầu:** Khi giá tăng, lượng cầu giảm (và ngược lại), giả định các yếu tố khác không đổi.
* **Luật Cung:** Khi giá tăng, lượng cung tăng (và ngược lại), giả định các yếu tố khác không đổi.

---

### 4.2\. Các yếu tố ảnh hưởng đến Đường Cầu (Demand)

Đường cầu thường dốc xuống. Khi các yếu tố ngoài giá thay đổi, đường cầu sẽ **dịch chuyển** (sang phải là tăng, sang trái là giảm).

| Nhóm yếu tố | Cách thức ảnh hưởng |
| :--- | :--- |
| **Thu nhập** | Với **hàng hóa thông thường**, thu nhập tăng làm cầu tăng. Với **hàng hóa thứ cấp**, thu nhập tăng làm cầu giảm. |
| **Hàng thay thế:** | Giá hàng A tăng làm cầu hàng B tăng. |
| **Hàng bổ sung:** | Giá hàng A tăng làm cầu hàng B giảm. |
| **Sở thích & Thị hiếu** | Nếu người tiêu dùng thích sản phẩm hơn (do quảng cáo, xu hướng), cầu sẽ tăng. |
| **Kỳ vọng** | Nếu kỳ vọng giá sẽ tăng trong tương lai, người dân sẽ mua nhiều hơn ở hiện tại (cầu tăng). |
| **Số lượng người mua** | Thị trường càng đông dân cư hoặc mở rộng quy mô, cầu càng tăng. |

---

### 4.3\. Các yếu tố ảnh hưởng đến Đường Cung (Supply)

Đường cung thường dốc lên. Sự thay đổi của các yếu tố này làm đường cung **dịch chuyển**.

| Nhóm yếu tố | Cách thức ảnh hưởng |
| :--- | :--- |
| **Giá các yếu tố đầu vào** | Giá nguyên liệu, nhân công tăng làm chi phí sản xuất tăng -\> Cung giảm. |
| **Công nghệ** | Cải tiến công nghệ giúp sản xuất hiệu quả hơn, chi phí thấp hơn -\> Cung tăng. |
| **Kỳ vọng của nhà sản xuất** | Nếu kỳ vọng giá tăng trong tương lai, họ có thể tích trữ hàng (cung hiện tại giảm). |
| **Thuế:** | Tăng thuế làm cung giảm. |
| **Trợ cấp:** | Tăng trợ cấp làm cung tăng. |
| **Số lượng người bán** | Càng nhiều doanh nghiệp gia nhập ngành, cung thị trường càng tăng. |

---

### 4.4\. Cân bằng Cung - Cầu (Market Equilibrium)

Cân bằng thị trường xảy ra tại điểm mà đường cung và đường cầu cắt nhau. Tại đây:

* **Giá cân bằng ($P^*$):** Mức giá mà tại đó lượng cung bằng lượng cầu.
* **Lượng cân bằng ($Q^*$):** Số lượng hàng hóa được mua và bán tại mức giá cân bằng.

Trạng thái cân bằng được biểu diễn qua phương trình:
$$Q_s(P) = Q_d(P)$$

* **Dư thừa (Surplus):** Khi giá thị trường cao hơn giá cân bằng ($P > P^*$), lượng cung lớn hơn lượng cầu. Người bán phải hạ giá để giải phóng hàng tồn.
* **Thiếu hụt (Shortage):** Khi giá thị trường thấp hơn giá cân bằng ($P < P^*$), lượng cầu lớn hơn lượng cung. Người mua cạnh tranh đẩy giá lên cao.

---

### 4.5\. Các giả định khi xây dựng mô hình Cung - Cầu

Để mô hình cung - cầu hoạt động chính xác trong lý thuyết, các nhà kinh tế đưa ra các giả định quan trọng sau:

1. **Ceteris Paribus (Các yếu tố khác không đổi):** Khi xem xét tác động của giá lên lượng cung/cầu, ta giả định tất cả các yếu tố khác (thu nhập, công nghệ, thuế...) đều giữ nguyên.
2. **Thị trường cạnh tranh hoàn hảo:** Giả định có rất nhiều người mua và người bán, sản phẩm đồng nhất, và không ai có đủ quyền lực để tự ý điều khiển giá (người chấp nhận giá).
3. **Hành vi hợp lý (Rationality):** Người tiêu dùng luôn muốn tối đa hóa lợi ích, còn nhà sản xuất luôn muốn tối đa hóa lợi nhuận.
4. **Thông tin hoàn hảo:** Mọi người tham gia thị trường đều biết rõ về giá cả, chất lượng và các điều kiện giao dịch.
5. **Không có ngoại ứng:** Giả định các hành vi mua bán chỉ ảnh hưởng đến người trong cuộc, không gây tác động lên bên thứ ba (như ô nhiễm môi trường).
