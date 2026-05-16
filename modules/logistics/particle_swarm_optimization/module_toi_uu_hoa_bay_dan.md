# Mô tả thiết kế mô phỏng thuật toán Tối ưu hóa bầy đàn (PSO) bằng Python

## 1. Mục tiêu hệ thống

Xây dựng một mô phỏng thuật toán Particle Swarm Optimization (PSO) trên Python nhằm quan sát trực quan quá trình hội tụ của bầy đàn trong không gian tìm kiếm và đánh giá ảnh hưởng của các siêu tham số đến hiệu quả tối ưu.

Hệ thống cần hỗ trợ:

* mô phỏng PSO chuẩn trong không gian liên tục
* kiểm thử trên các hàm mục tiêu kinh điển
* trực quan hóa chuyển động và hội tụ của các hạt
* mở rộng để nghiên cứu topology, xử lý biên và điều khiển tham số

## 2. Kiến trúc tổng thể

Hệ thống được thiết kế theo hướng lập trình hướng đối tượng để phản ánh đúng cấu trúc của PSO và dễ mở rộng.

### 2.1. Thành phần chính

Hệ thống gồm các thành phần sau:

#### a. Lớp `Particle`

Đại diện cho một hạt trong bầy đàn.

Mỗi hạt cần lưu trữ:

* vị trí hiện tại `position`
* vận tốc hiện tại `velocity`
* giá trị hàm mục tiêu tại vị trí hiện tại `fitness`
* vị trí tốt nhất cá nhân `pbest_position`
* giá trị tốt nhất cá nhân `pbest_fitness`

Lớp này cần hỗ trợ các hành vi:

* khởi tạo ngẫu nhiên trong miền tìm kiếm
* đánh giá fitness
* cập nhật vận tốc
* cập nhật vị trí
* cập nhật bộ nhớ cá nhân `pBest`

#### b. Lớp `Swarm`

Đại diện cho toàn bộ bầy đàn.

Lớp này cần quản lý:

* danh sách các hạt
* nghiệm tốt nhất toàn cục `gbest_position`
* giá trị tốt nhất toàn cục `gbest_fitness`
* lịch sử hội tụ qua từng vòng lặp
* tham số toàn cục của mô hình

Lớp này cần hỗ trợ:

* khởi tạo bầy đàn
* lặp tiến hóa qua nhiều thế hệ
* cập nhật `gBest`
* điều phối cập nhật các hạt
* lưu dữ liệu phục vụ trực quan hóa và phân tích

#### c. Lớp hoặc module `ObjectiveFunction`

Quản lý các hàm mục tiêu để thử nghiệm.

Ít nhất cần hỗ trợ:

* `Sphere`
* `Ackley`

Thiết kế nên đủ linh hoạt để sau này bổ sung:

* Rastrigin
* Rosenbrock
* Griewank
* TSP dạng rời rạc

#### d. Module `Visualizer`

Phụ trách trực quan hóa quá trình tối ưu.

Cần hỗ trợ:

* biểu đồ scatter của các hạt trong không gian 2D
* biểu đồ đường thể hiện quá trình giảm của `gBest fitness`
* animation hoặc cập nhật theo từng iteration nếu có thể

## 3. Phạm vi chức năng

## 3.1. Chức năng mô phỏng cơ bản

Hệ thống cần cho phép:

* chọn hàm mục tiêu
* đặt số chiều không gian tìm kiếm
* đặt số lượng hạt
* đặt số vòng lặp tối đa
* thiết lập miền tìm kiếm cho từng chiều
* chạy mô phỏng PSO và trả về nghiệm tốt nhất tìm được

## 3.2. Chức năng điều khiển tham số

Hệ thống cần cho phép cấu hình:

* trọng số quán tính `w`
* hệ số nhận thức cá nhân `c1`
* hệ số xã hội `c2`
* giới hạn vận tốc `Vmax`
* chiến lược thay đổi `w` theo thời gian

Yêu cầu mặc định:

* `w` giảm tuyến tính từ 0.9 xuống 0.4
* `c1` và `c2` nằm trong khoảng 1.5 đến 2.0
* `Vmax` được đặt theo tỷ lệ của miền tìm kiếm

## 3.3. Chức năng theo dõi và ghi nhận dữ liệu

Trong mỗi vòng lặp, hệ thống cần ghi nhận:

* giá trị `gbest_fitness`
* vị trí `gbest_position`
* vị trí của toàn bộ hạt
* vận tốc trung bình hoặc độ phân tán của bầy đàn nếu có

Dữ liệu này dùng để:

* vẽ đồ thị hội tụ
* dựng hoạt ảnh
* phân tích ảnh hưởng của tham số

## 4. Mô hình toán học cần cài đặt

Tại mỗi bước lặp `t`, mỗi hạt được cập nhật theo hai phương trình chuẩn của PSO:

### 4.1. Phương trình cập nhật vận tốc

$$
v_i(t+1) = w \cdot v_i(t) + c_1 r_1 (pBest_i - x_i(t)) + c_2 r_2 (gBest - x_i(t))
$$

Trong đó:

* `w` là trọng số quán tính
* `c1` là hệ số học từ kinh nghiệm cá nhân
* `c2` là hệ số học từ bầy đàn
* `r1`, `r2` là các số ngẫu nhiên phân bố đều trong đoạn [0, 1]

### 4.2. Phương trình cập nhật vị trí

$$
x_i(t+1) = x_i(t) + v_i(t+1)
$$

### 4.3. Điều kiện cập nhật bộ nhớ

Sau khi cập nhật vị trí:

* nếu fitness mới tốt hơn `pbest_fitness` thì cập nhật `pBest`
* nếu fitness mới tốt hơn `gbest_fitness` thì cập nhật `gBest`

## 5. Hàm mục tiêu cần hỗ trợ

## 5.1. Hàm Sphere

Mục đích:

* dùng để kiểm tra tính đúng đắn cơ bản của thuật toán
* phù hợp để quan sát hội tụ đơn giản

Công thức:
$$
f(x) = \sum_{i=1}^{n} x_i^2
$$

Đặc điểm:

* một cực tiểu toàn cục tại gốc tọa độ
* bề mặt mượt, lồi, dễ tối ưu

## 5.2. Hàm Ackley

Mục đích:

* kiểm tra khả năng thoát khỏi cực trị địa phương
* đánh giá hành vi hội tụ trong bề mặt phức tạp

Đặc điểm:

* nhiều cực trị cục bộ
* có một cực tiểu toàn cục rõ ràng
* thường dùng trong benchmark tối ưu hóa

## 5.3. Hướng mở rộng cho bài toán logistics

Sau khi mô hình PSO liên tục hoạt động ổn định, có thể phát triển phiên bản cho bài toán TSP.

Yêu cầu mở rộng:

* biểu diễn vị trí bằng hoán vị thành phố
* thay phép cộng trừ vector bằng các toán tử hoán đổi
* thiết kế lại khái niệm vận tốc theo hướng rời rạc

Phần này chưa cần triển khai ở phiên bản đầu tiên nhưng kiến trúc nên đủ linh hoạt để mở rộng.

## 6. Xử lý biên và giới hạn vận tốc

## 6.1. Giới hạn vận tốc

Cần chặn vận tốc trong khoảng:
[
[-V_{max}, V_{max}]
]

Mục đích:

* tránh hạt di chuyển quá xa trong một lần cập nhật
* giữ ổn định quá trình tìm kiếm

## 6.2. Xử lý khi hạt vượt biên

Hệ thống nên hỗ trợ ít nhất hai cơ chế:

### a. Clipping

Nếu vị trí vượt khỏi miền cho phép thì cắt về biên gần nhất.

### b. Reflection

Nếu vượt biên thì phản xạ lại và đổi chiều vận tốc tương ứng.

Thiết kế nên cho phép chọn phương pháp xử lý biên khi cấu hình mô phỏng.

## 7. Topology bầy đàn

Phiên bản đầu tiên cần hỗ trợ topology chuẩn kiểu Star:

* mọi hạt đều biết `gBest` toàn cục

Phiên bản mở rộng nên hỗ trợ Ring:

* mỗi hạt chỉ tham chiếu nghiệm tốt nhất trong nhóm láng giềng gần nó

Mục tiêu nghiên cứu:

* so sánh tốc độ hội tụ
* đánh giá khả năng duy trì đa dạng quần thể
* quan sát nguy cơ kẹt ở cực trị cục bộ

## 8. Trực quan hóa

## 8.1. Trực quan hóa trong không gian 2D

Khi số chiều bằng 2, cần vẽ:

* contour hoặc heatmap của hàm mục tiêu
* scatter plot vị trí các hạt
* đánh dấu `gBest`

Có thể cập nhật theo từng iteration để thấy bầy đàn dần co cụm.

## 8.2. Đồ thị hội tụ

Vẽ đường biểu diễn:

* trục hoành là số vòng lặp
* trục tung là `gbest_fitness`

Mục đích:

* đánh giá tốc độ hội tụ
* so sánh giữa các bộ tham số hoặc topology khác nhau

## 8.3. Animation

Nếu có thể, hệ thống nên hỗ trợ tạo animation quá trình di chuyển của các hạt để phục vụ giảng dạy hoặc nghiên cứu trực quan.

## 9. Công nghệ đề xuất

Ngôn ngữ và thư viện:

* Python 3.x
* NumPy để tính toán vector và sinh số ngẫu nhiên
* Matplotlib để vẽ đồ thị và animation
* Có thể dùng `dataclasses` nếu phù hợp
* Có thể dùng `abc` hoặc pattern interface nếu muốn chuẩn hóa hàm mục tiêu

## 10. Cấu hình đầu vào

AI Agent cần xây dựng hệ thống sao cho người dùng có thể thay đổi các tham số sau:

* số lượng hạt
* số chiều
* số vòng lặp
* cận dưới và cận trên của không gian tìm kiếm
* `w_start`, `w_end`
* `c1`, `c2`
* `Vmax`
* loại hàm mục tiêu
* topology
* phương pháp xử lý biên
* seed ngẫu nhiên để tái lập kết quả

## 11. Kết quả đầu ra mong muốn

Hệ thống cần trả về:

* nghiệm tốt nhất tìm được `gbest_position`
* giá trị tối ưu tốt nhất `gbest_fitness`
* lịch sử hội tụ
* biểu đồ hội tụ
* biểu đồ hoặc animation vị trí hạt nếu chạy ở 2D

## 12. Yêu cầu chất lượng mã nguồn

AI Agent cần triển khai theo các nguyên tắc sau:

* tách biệt rõ phần mô hình, phần thuật toán và phần trực quan hóa
* mã nguồn dễ đọc, có chú thích
* dễ mở rộng thêm hàm mục tiêu mới
* dễ thay đổi topology và boundary handling
* có thể chạy độc lập bằng một file `main.py`
* nên có cấu trúc thư mục rõ ràng

Ví dụ cấu trúc gợi ý:

```text
pso_simulation/
│
├── main.py
├── config.py
├── particle.py
├── swarm.py
├── objective_functions.py
├── visualizer.py
├── experiments.py
└── utils.py
```

## 13. Kịch bản thử nghiệm tối thiểu

AI Agent cần xây dựng ít nhất ba kịch bản chạy thử:

### Kịch bản 1

* hàm Sphere
* không gian 2D
* topology Star
* boundary handling kiểu clipping

Mục tiêu:

* xác nhận thuật toán hội tụ đúng

### Kịch bản 2

* hàm Ackley
* không gian 2D
* topology Star
* `w` giảm tuyến tính

Mục tiêu:

* quan sát khả năng thoát cực trị cục bộ

### Kịch bản 3

* hàm Ackley
* so sánh Star và Ring
* cùng một bộ seed

Mục tiêu:

* so sánh tốc độ hội tụ và độ ổn định

## 14. Định hướng mở rộng nghiên cứu

Sau khi bản cơ bản hoàn thiện, có thể tiếp tục mở rộng theo các hướng:

* PSO rời rạc cho TSP
* hybrid PSO với local search
* adaptive PSO
* so sánh PSO với GA hoặc DE
* dashboard tương tác thay đổi tham số theo thời gian thực

## 15. Yêu cầu triển khai dành cho AI Agent

Hãy xây dựng một mô phỏng PSO bằng Python theo kiến trúc OOP với các yêu cầu sau:

* có lớp `Particle` và `Swarm`
* hỗ trợ ít nhất hai hàm mục tiêu là Sphere và Ackley
* triển khai đầy đủ cập nhật vận tốc, vị trí, `pBest`, `gBest`
* hỗ trợ trọng số quán tính giảm tuyến tính
* hỗ trợ giới hạn vận tốc và xử lý biên
* hỗ trợ topology Star, và nếu có thể thì thêm Ring
* trực quan hóa chuyển động của hạt trong không gian 2D bằng Matplotlib
* vẽ đồ thị hội tụ của `gBest fitness`
* tổ chức mã nguồn rõ ràng, dễ mở rộng, dễ chạy thử

Ngoài ra:

* cần có ví dụ chạy mẫu
* cần có chú thích giải thích từng thành phần chính
* ưu tiên thiết kế sạch, tách mô-đun rõ ràng
* ưu tiên khả năng mở rộng để phục vụ nghiên cứu sau này
