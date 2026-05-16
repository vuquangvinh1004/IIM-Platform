# Mô tả thiết kế mô phỏng PSO cho bài toán giao hàng và xe vận tải

## 1. Mục tiêu hệ thống

Xây dựng một ứng dụng mô phỏng tối ưu hóa bầy đàn PSO cho các bài toán định tuyến vận tải và giao hàng trong logistics. Hệ thống phải cho phép người dùng quan sát trực quan cách các phương án tuyến đường được cải thiện qua từng vòng lặp, đồng thời hỗ trợ ba mức độ bài toán khác nhau trong ba tab độc lập:

* Tab 1: TSP, một xe, một tuyến đi qua toàn bộ điểm giao
* Tab 2: VRP, nhiều xe, có ràng buộc tải trọng
* Tab 3: VRPTW, nhiều xe, có tải trọng và khung thời gian giao hàng

Mục đích của hệ thống không chỉ là tìm nghiệm tốt mà còn phải giúp người dùng hiểu rõ:

* hạt trong PSO được biểu diễn như thế nào trong bài toán định tuyến
* nghiệm tốt nhất cá nhân và toàn cục tác động ra sao đến quá trình tối ưu
* sự khác nhau giữa ba mô hình TSP, VRP và VRPTW
* ảnh hưởng của tham số PSO tới tốc độ hội tụ và chất lượng tuyến đường

---

## 2. Kiến trúc tổng thể của ứng dụng

Hệ thống được thiết kế theo hướng mô-đun và OOP, gồm ba lớp chức năng chính:

### 2.1. Lớp giao diện mô phỏng

Phụ trách:

* hiển thị ba tab bài toán
* nhận tham số đầu vào từ người dùng
* hiển thị bản đồ điểm giao, tuyến đường, xe và trạng thái mô phỏng
* hiển thị đồ thị hội tụ
* hiển thị thông tin nghiệm tốt nhất

### 2.2. Lớp mô hình dữ liệu logistics

Phụ trách biểu diễn các thực thể nghiệp vụ:

* depot hoặc kho trung tâm
* khách hàng hoặc điểm giao nhận
* xe vận tải
* tuyến đường
* trạng thái giao hàng
* cửa sổ thời gian trong VRPTW

### 2.3. Lớp thuật toán PSO rời rạc

Phụ trách:

* khởi tạo quần thể nghiệm
* đánh giá fitness
* cập nhật pBest và gBest
* áp dụng các toán tử rời rạc thay cho cộng trừ vector liên tục
* lưu lịch sử quỹ đạo nghiệm để trực quan hóa

---

## 3. Thiết kế giao diện 3 tab

Ứng dụng phải có 3 tab chính, mỗi tab là một môi trường mô phỏng riêng, dùng chung phong cách giao diện nhưng khác nhau về logic nghiệp vụ và hàm mục tiêu.

---

# TAB 1. TSP – Mô phỏng một xe giao hàng

## 3.1. Mục tiêu tab TSP

Tab này mô phỏng bài toán người du lịch với một xe duy nhất xuất phát từ kho, đi qua toàn bộ điểm giao hàng đúng một lần, rồi quay về kho. Đây là tab đơn giản nhất, dùng để giúp người dùng hiểu nền tảng của PSO rời rạc trong định tuyến.

## 3.2. Cấu trúc dữ liệu

Dữ liệu đầu vào gồm:

* 1 kho trung tâm
* danh sách n điểm giao hàng
* tọa độ 2D của từng điểm

Một nghiệm, tức một hạt, được biểu diễn dưới dạng:

* một hoán vị thứ tự ghé thăm các điểm giao

Ví dụ:

* Depot → 4 → 2 → 1 → 5 → 3 → Depot

## 3.3. Ý nghĩa của hạt trong tab TSP

Mỗi hạt đại diện cho:

* một phương án sắp xếp thứ tự giao hàng của một xe

pBest là:

* thứ tự tuyến tốt nhất mà hạt đó từng tìm được

gBest là:

* thứ tự tuyến tốt nhất của toàn bộ bầy đàn

## 3.4. Hàm mục tiêu

Fitness trong TSP là:

* tổng chiều dài tuyến đường đi từ kho qua tất cả điểm và quay về kho

Công thức tổng quát:

* fitness = tổng khoảng cách giữa các điểm liên tiếp trên tuyến

Mục tiêu tối ưu:

* cực tiểu hóa tổng quãng đường

## 3.5. Cập nhật PSO trong không gian rời rạc

Do nghiệm là hoán vị, không dùng cộng trừ vector truyền thống. Thay vào đó, cần dùng các toán tử rời rạc như:

* swap: đổi chỗ hai điểm giao
* insert: lấy một điểm chèn sang vị trí khác
* reverse: đảo chiều một đoạn tuyến

“Vận tốc” của hạt được hiểu như:

* tập các thao tác biến đổi để làm nghiệm hiện tại tiến gần hơn tới pBest và gBest

## 3.6. Giao diện trong tab TSP

Tab cần gồm:

* khu vực cấu hình bên trái
* khu vực bản đồ tuyến đường ở giữa
* khu vực thống kê và hội tụ bên phải hoặc phía dưới

Người dùng có thể cấu hình:

* số điểm giao hàng
* seed dữ liệu
* số hạt
* số vòng lặp
* trọng số quán tính
* c1, c2
* số lần swap hoặc insert tối đa mỗi bước
* topology Star hoặc Ring nếu hỗ trợ

Phần trực quan cần hiển thị:

* kho trung tâm
* các điểm giao hàng
* tuyến đường tốt nhất hiện tại
* màu xe, dù chỉ có một xe vẫn nên hiển thị rõ ràng
* số vòng lặp hiện tại
* tổng quãng đường tốt nhất

## 3.7. Kết quả đầu ra tab TSP

Cần hiển thị:

* tuyến đường tốt nhất
* tổng khoảng cách tối ưu tìm được
* biểu đồ hội tụ fitness theo iteration
* animation thay đổi tuyến tốt nhất qua thời gian

---

# TAB 2. VRP – Mô phỏng nhiều xe có tải trọng

## 4.1. Mục tiêu tab VRP

Tab này mở rộng từ TSP sang tình huống thực tế hơn với nhiều xe cùng xuất phát từ kho, giao hàng cho các điểm khách khác nhau, và quay về kho. Mỗi xe có tải trọng tối đa, nên nghiệm không chỉ cần ngắn mà còn phải hợp lệ về mặt năng lực vận chuyển.

## 4.2. Cấu trúc dữ liệu

Dữ liệu đầu vào gồm:

* 1 kho trung tâm
* danh sách điểm giao hàng
* tọa độ từng điểm
* nhu cầu hàng hóa tại từng điểm
* số lượng xe
* tải trọng tối đa của mỗi xe

Một nghiệm, tức một hạt, được biểu diễn bằng:

* tập hợp nhiều tuyến đường, mỗi tuyến thuộc về một xe

Ví dụ:

* Xe 1: Depot → 1 → 4 → 7 → Depot
* Xe 2: Depot → 2 → 5 → Depot
* Xe 3: Depot → 3 → 6 → 8 → Depot

## 4.3. Ý nghĩa của hạt trong tab VRP

Mỗi hạt đại diện cho:

* một phương án phân công khách hàng cho từng xe
* đồng thời một phương án sắp xếp thứ tự ghé thăm trên từng tuyến

pBest là:

* kế hoạch phân tuyến tốt nhất mà hạt đó từng có

gBest là:

* kế hoạch phân tuyến tốt nhất toàn cục

## 4.4. Hàm mục tiêu

Fitness trong VRP không chỉ là tổng quãng đường mà còn phải xét tính hợp lệ.

Fitness tổng quát:

* fitness = tổng quãng đường + hệ số phạt quá tải + hệ số phạt vi phạm ràng buộc khác nếu có

Trong đó:

* tổng quãng đường là tổng độ dài của tất cả tuyến xe
* phạt quá tải được áp dụng nếu tổng nhu cầu khách hàng trên một xe vượt tải trọng tối đa

Mục tiêu tối ưu:

* giảm tổng quãng đường
* tránh hoặc cực tiểu hóa vi phạm tải trọng

## 4.5. Toán tử PSO rời rạc cho VRP

Do mỗi nghiệm gồm nhiều tuyến, cần thêm các thao tác:

* intra-route swap: đổi vị trí hai khách trong cùng tuyến
* inter-route swap: đổi khách giữa hai tuyến
* relocate: chuyển một khách từ xe này sang xe khác
* route split/merge nhẹ nếu thiết kế cho phép

Ý nghĩa học từ pBest và gBest:

* học cách nhóm khách hàng hợp lý hơn
* học thứ tự giao tốt hơn trong từng xe
* học cấu trúc tuyến ít tốn chi phí hơn

## 4.6. Giao diện trong tab VRP

Người dùng cần cấu hình được:

* số khách hàng
* số xe
* tải trọng xe
* phân bố nhu cầu hàng hóa
* số hạt
* số vòng lặp
* hệ số phạt quá tải
* tham số PSO

Vùng trực quan cần hiển thị:

* bản đồ 2D với kho và khách hàng
* mỗi xe có một màu riêng
* tuyến của từng xe vẽ bằng polyline khác màu
* bảng phụ liệt kê:

  * tải đã dùng của từng xe
  * số điểm giao trên tuyến
  * chiều dài tuyến
  * trạng thái hợp lệ hay vi phạm tải

## 4.7. Kết quả đầu ra tab VRP

Cần hiển thị:

* tuyến đường tốt nhất của từng xe
* tổng quãng đường toàn đội xe
* số lượng xe sử dụng
* tổng vi phạm tải nếu có
* fitness tốt nhất
* biểu đồ hội tụ
* animation cho thấy các tuyến dần được tái cấu trúc tốt hơn

---

# TAB 3. VRPTW – Mô phỏng nhiều xe với cửa sổ thời gian

## 5.1. Mục tiêu tab VRPTW

Đây là tab thực tế nhất. Ngoài tải trọng, mỗi điểm giao còn có cửa sổ thời gian phục vụ. Xe phải đến trong khoảng thời gian cho phép, hoặc nếu đến sớm thì phải chờ, nếu đến muộn thì bị phạt. Tab này mô phỏng gần với hoạt động giao hàng thực tế trong thương mại điện tử, phân phối bán lẻ hoặc giao nhận đô thị.

## 5.2. Cấu trúc dữ liệu

Dữ liệu đầu vào gồm:

* 1 kho trung tâm
* các điểm giao có tọa độ
* nhu cầu hàng hóa của từng điểm
* thời gian phục vụ tại từng điểm
* thời gian mở đầu và đóng cuối của cửa sổ giao hàng
* số xe
* tải trọng xe
* vận tốc trung bình xe hoặc ma trận thời gian di chuyển

Một hạt được biểu diễn bằng:

* tập hợp tuyến đường cho nhiều xe
* kèm trình tự ghé thăm từng khách hàng

## 5.3. Ý nghĩa của hạt trong tab VRPTW

Mỗi hạt là:

* một kế hoạch giao hàng hoàn chỉnh, bao gồm phân xe, thứ tự tuyến, và ngầm định thời gian đến từng điểm

pBest là:

* lịch giao tốt nhất mà hạt từng có xét theo fitness tổng hợp

gBest là:

* lịch giao tốt nhất toàn bầy đàn

## 5.4. Hàm mục tiêu

Fitness trong VRPTW cần là một hàm tổng hợp nhiều mục tiêu. Dạng tổng quát:

fitness =

* tổng quãng đường
* cộng phạt quá tải
* cộng phạt đến muộn
* cộng phạt chờ đợi quá nhiều nếu muốn
* cộng phạt số xe sử dụng nếu muốn tối ưu thêm

Ví dụ logic:

* đến sớm: được chờ, không nhất thiết phạt nặng
* đến muộn: phạt mạnh
* vượt tải: phạt rất mạnh
* mở quá nhiều xe: có thể phạt để khuyến khích gom tuyến hợp lý

## 5.5. Tính toán thời gian trong tuyến

Đối với mỗi tuyến xe cần tính:

* thời điểm rời kho
* thời gian di chuyển giữa các điểm
* thời gian đến từng điểm
* thời gian chờ nếu đến sớm
* thời gian bắt đầu phục vụ
* thời gian hoàn thành phục vụ
* thời gian quay về kho

Các đại lượng này phải được lưu để:

* đánh giá fitness
* hiển thị trong giao diện
* phân tích vi phạm thời gian

## 5.6. Toán tử PSO rời rạc cho VRPTW

Ngoài các thao tác của VRP, thuật toán cần ưu tiên những thay đổi làm tốt hơn về mặt thời gian:

* đổi chỗ các điểm gần nhau về vị trí và khung giờ
* chèn khách hàng vào tuyến có thời gian phù hợp hơn
* chuyển khách từ tuyến bị trễ sang tuyến khác
* đảo đoạn tuyến nếu giảm trễ giờ

Ở tab này, PSO rời rạc nên kết hợp với cơ chế sửa nghiệm nhẹ sau cập nhật, ví dụ:

* tự động điều chỉnh nếu một tuyến vượt quá nhiều ràng buộc
* ưu tiên đưa nghiệm về gần vùng khả thi

## 5.7. Giao diện trong tab VRPTW

Người dùng cần cấu hình:

* số khách hàng
* số xe
* tải trọng xe
* thời gian phục vụ trung bình
* khung giờ giao hàng cho từng khách
* tốc độ xe hoặc ma trận thời gian
* trọng số phạt trễ giờ
* trọng số phạt quá tải
* tham số PSO

Phần trực quan cần hiển thị hai lớp thông tin:

Lớp bản đồ:

* kho và khách hàng trên mặt phẳng 2D
* mỗi xe một màu
* tuyến đường tốt nhất hiện tại

Lớp lịch vận hành:

* bảng thời gian đến từng điểm
* trạng thái đúng giờ, chờ, hay muộn
* tải còn lại của xe
* tổng thời gian tuyến

Có thể dùng thêm:

* thanh timeline cho từng xe
* màu đỏ cho điểm giao trễ
* màu vàng cho điểm đến sớm phải chờ
* màu xanh cho điểm đúng giờ

## 5.8. Kết quả đầu ra tab VRPTW

Cần hiển thị:

* tuyến tốt nhất của từng xe
* tổng quãng đường
* tổng thời gian vận hành
* tổng số phút trễ
* tổng số phút chờ
* số điểm giao vi phạm time window
* fitness tốt nhất
* biểu đồ hội tụ
* animation mô phỏng xe chạy theo tuyến và thời điểm phục vụ

---

## 6. Thiết kế dữ liệu dùng chung cho cả 3 tab

## 6.1. Thực thể Depot

Lưu:

* id
* tọa độ x, y

## 6.2. Thực thể Customer

Lưu:

* id
* tọa độ x, y
* demand
* service_time
* ready_time
* due_time

Trong đó:

* TSP chỉ cần tọa độ
* VRP dùng tọa độ và demand
* VRPTW dùng toàn bộ

## 6.3. Thực thể Vehicle

Lưu:

* id
* capacity
* speed
* fixed_cost nếu muốn mở rộng

## 6.4. Thực thể Route

Lưu:

* vehicle_id
* danh sách customer_id theo thứ tự
* distance
* load
* arrival_times
* start_service_times
* waiting_times
* lateness_times

## 6.5. Thực thể Particle

Tùy tab mà `position` mang ý nghĩa khác:

* TSP: một hoán vị
* VRP: danh sách nhiều tuyến
* VRPTW: danh sách nhiều tuyến kèm khả năng tính lịch thời gian

Ngoài ra mọi particle đều cần:

* fitness hiện tại
* pbest_position
* pbest_fitness

---

## 7. Cách tổ chức PSO dùng chung cho ba bài toán

## 7.1. Thành phần dùng chung

Cả ba tab đều cần một bộ khung PSO chung gồm:

* Swarm
* Particle
* evaluator
* topology manager
* history recorder

## 7.2. Thành phần chuyên biệt theo tab

Mỗi tab nên có:

* bộ biểu diễn nghiệm riêng
* bộ toán tử cập nhật riêng
* hàm fitness riêng
* visualizer riêng

Tức là nên thiết kế theo mô hình:

* một engine PSO chung
* ba strategy riêng cho TSP, VRP, VRPTW

## 7.3. Gợi ý kiến trúc phần mềm

Có thể tổ chức thành:

* `core/` cho PSO chung
* `problems/tsp/`
* `problems/vrp/`
* `problems/vrptw/`
* `ui/` cho giao diện 3 tab
* `visualization/` cho bản đồ, timeline, hội tụ

---

## 8. Cách trực quan hóa trong mô phỏng

## 8.1. Bản đồ 2D

Mỗi tab đều phải có:

* một lưới tọa độ 2D
* kho hiển thị bằng biểu tượng nổi bật
* khách hàng hiển thị bằng các điểm tròn có nhãn
* tuyến đường hiển thị bằng đường nối

## 8.2. Đường đi của “bầy đàn”

Trong ngữ cảnh logistics, thay vì xem hạt như chấm bay, có thể trực quan hóa theo hai cách:

Cách 1:

* hiển thị sự thay đổi của nghiệm tốt nhất qua từng vòng lặp
* tức là tuyến đường tốt nhất được vẽ lại theo từng iteration

Cách 2:

* hiển thị nhiều nghiệm của nhiều hạt dưới dạng các tuyến mờ
* hạt nào tốt hơn có màu đậm hơn
* qua thời gian các tuyến xấu biến mất và tuyến tốt dần ổn định

## 8.3. Đồ thị hội tụ

Phải có biểu đồ:

* trục x là số vòng lặp
* trục y là fitness tốt nhất toàn cục

Có thể thêm:

* fitness trung bình của swarm
* độ đa dạng quần thể qua thời gian

## 8.4. Animation vận hành xe

Đối với nghiệm gBest cuối cùng:

* xe di chuyển dọc theo tuyến
* hiển thị trạng thái phục vụ từng điểm
* cập nhật tải xe sau mỗi điểm
* trong VRPTW hiển thị thời gian thực tế đến và rời điểm giao

---

## 9. Cấu hình đầu vào chung cho người dùng

Ứng dụng cần cho phép người dùng điều chỉnh:

* số lượng khách hàng
* số xe
* seed ngẫu nhiên
* số hạt
* số vòng lặp
* trọng số quán tính
* c1, c2
* topology
* số thao tác cập nhật tối đa mỗi bước
* chế độ hiển thị animation
* tốc độ phát mô phỏng

Riêng từng tab cần thêm:

* TSP: chỉ cần số điểm và khoảng tọa độ
* VRP: thêm nhu cầu hàng hóa và tải trọng xe
* VRPTW: thêm service time, ready time, due time, tốc độ xe

---

## 10. Yêu cầu đầu ra của hệ thống

Mỗi tab cần trả về:

* nghiệm tốt nhất cuối cùng
* fitness tốt nhất
* lịch sử hội tụ
* dữ liệu phục vụ animation
* bảng chi tiết tuyến đường

Cụ thể:

* Tab TSP: chuỗi thứ tự ghé thăm và tổng quãng đường
* Tab VRP: danh sách tuyến xe, tải sử dụng, khoảng cách từng tuyến
* Tab VRPTW: danh sách tuyến xe, thời gian đến, thời gian chờ, thời gian trễ, tải sử dụng

---

## 11. Yêu cầu về chất lượng mô phỏng

Hệ thống cần đảm bảo:

* người dùng có thể thấy rõ sự khác biệt giữa TSP, VRP và VRPTW
* quá trình tối ưu được trực quan hóa rõ chứ không chỉ in số liệu
* dữ liệu được sinh ngẫu nhiên nhưng có seed để tái lập
* nghiệm có thể chưa tối ưu tuyệt đối nhưng phải hợp lý và dễ giải thích
* kiến trúc đủ mở để sau này thay PSO bằng GA, ACO hoặc DE

---

## 12. Kịch bản sử dụng đề xuất

### Kịch bản 1: Học cơ bản với TSP

Người dùng tạo 10 điểm giao hàng và chạy PSO để xem một xe dần tìm ra vòng giao ngắn hơn.

### Kịch bản 2: So sánh nhiều xe với VRP

Người dùng tạo 20 điểm giao và 3 xe với tải trọng khác nhau để xem PSO phân chia khách hàng ra sao.

### Kịch bản 3: Mô phỏng giao hàng thực tế với VRPTW

Người dùng tạo 15 điểm giao, 3 xe, và các khung giờ khác nhau để xem xe nào giao đúng giờ, xe nào bị trễ và PSO điều chỉnh tuyến thế nào để giảm vi phạm.

---

## 13. Yêu cầu triển khai dành cho AI Agent

Hãy xây dựng một ứng dụng mô phỏng PSO cho logistics với 3 tab riêng biệt:

* Tab TSP
* Tab VRP
* Tab VRPTW

Ứng dụng phải:

* có giao diện trực quan
* có bản đồ 2D
* có biểu đồ hội tụ
* có animation tuyến đường
* có khả năng cấu hình tham số
* dùng chung một khung PSO nhưng cho phép thay đổi biểu diễn nghiệm và fitness theo từng bài toán

Ngoài ra cần:

* tách biệt rõ mô hình dữ liệu, thuật toán và giao diện
* lưu được lịch sử nghiệm tốt nhất
* hỗ trợ seed để chạy lặp lại
* dễ mở rộng sang bài toán giao nhận thực tế hơn trong tương lai

---

## 14. Kết luận thiết kế

Ba tab này phải thể hiện ba cấp độ tăng dần của độ phức tạp:

* TSP là mức nền tảng, tập trung vào tối ưu đường đi cho một xe
* VRP là mức trung gian, bổ sung ràng buộc tải trọng và phân xe
* VRPTW là mức nâng cao, mô phỏng gần thực tế logistics với cả tải trọng và thời gian

Thiết kế này giúp hệ thống vừa có giá trị học thuật, vừa có giá trị trực quan, vừa đủ linh hoạt để phát triển thành một công cụ mô phỏng vận tải thông minh.

---

## 15. Điều chỉnh thiết kế cho phù hợp với nền tảng IIMP

> Phần này ghi lại các điều chỉnh bắt buộc so với thiết kế gốc để đảm bảo module pso_logistics tuân thủ kiến trúc IIMP, SDK module và các tiêu chí kỹ thuật đã được xác lập của nền tảng.

---

### D1 — Phân giai đoạn triển khai (thay vì build 3 tab cùng lúc)

Thay vì xây dựng đồng thời cả 3 tab (TSP, VRP, VRPTW), module được chia thành 3 phiên bản riêng biệt:

**v1.0 — TSP only (phạm vi thực hiện ngay)**

* 1 tab TSP duy nhất trong QTabWidget, có cấu trúc và thiết kế sẵn sàng cho mở rộng
* PSO rời rạc: position là hoán vị, toán tử swap / insert / reverse_segment
* Bản đồ 2D: depot (hình vuông đỏ) + customers (chấm xanh có nhãn) + best route (polyline xanh lá)
* Convergence chart
* Animation tuyến gBest thay đổi từng iteration (không phải xe chạy theo tuyến)
* Replay animation sau khi simulation kết thúc (QTimer, không mix với simulation worker)
* State persistence và Export PNG
* Bộ tests đầy đủ

**v1.1 — VRP (sau khi TSP stable)**

* Thêm tab VRP: nhiều xe, penalty tải trọng
* Color-coded routes per vehicle
* Bảng tóm tắt trạng thái từng xe

**v1.2 — VRPTW (sau khi VRP stable)**

* Thêm tab VRPTW
* Time window evaluation và penalty đến muộn
* Bảng thời gian đến + trạng thái màu (đỏ/vàng/xanh)
* Timeline bar chart (không bắt buộc cho v1.2 MVP)

---

### D2 — Điều chỉnh kiến trúc thuật toán: không tái dùng core PSO hiện tại

Module `particle_swarm_optimization` hiện tại dùng vector thực (position + velocity ∈ ℝⁿ). Module logistics dùng không gian rời rạc (hoán vị / danh sách route). Hai module này **không được chia sẻ core**, mỗi module có engine riêng biệt.

Folder structure chính thức của `pso_logistics/`:

```
modules/quantitative_methods/pso_logistics/
  core/
    discrete_particle.py       # DiscreteParticle: position = permutation / route list
    discrete_swarm.py          # DiscreteSwarm: step() dùng operator thay vector
    operators.py               # swap, insert, reverse_segment, move_toward
    route_evaluator.py         # build_distance_matrix, tsp_tour_distance
  problems/
    tsp_problem.py             # TSP: generate(), evaluate(), initial_position()
  models/
    entities.py                # Depot, Customer, Vehicle, Route dataclasses
    config.py                  # LogisticsPSOConfig dataclass
    state.py                   # STATE_VERSION + default_state()
  workers/
    simulation_worker.py       # SimulationWorker(QThread): non-blocking
  module.py                    # Full UI + PSOLogisticsModule(BaseModule)
  module.json                  # Manifest
  entry.py                     # Entry point
  README.md
  tests/
    test_manifest.py
    test_operators.py
    test_tsp_problem.py
    test_discrete_swarm.py
    test_smoke_ui.py
```

**Cập nhật PSO rời rạc — quy tắc cập nhật per-iteration:**

```
n_inertia = max(1, round(w × n_ops_max))
n_cog     = max(0, round(c1 × r1 × n_ops_max / 2))   # r1 ~ U[0,1]
n_soc     = max(0, round(c2 × r2 × n_ops_max / 2))   # r2 ~ U[0,1]
new_pos   = apply_random_ops(pos, n_inertia)
new_pos   = move_toward(new_pos, pbest, n_cog)
new_pos   = move_toward(new_pos, social_best, n_soc)
```

Trong đó `move_toward(source, target, n)` áp dụng n targeted swaps làm source tiến gần target hơn.

---

### D3 — Tách biệt hai loại animation

Thiết kế gốc (Section 8.4) mô tả "xe di chuyển dọc tuyến" — đây là animation **vận hành xe theo tuyến đường**, khác hoàn toàn với **animation PSO iteration** (tuyến gBest thay đổi từng vòng).

Quy tắc tách biệt bắt buộc:

* **Animation PSO** (trong lúc simulation chạy): signal từ `SimulationWorker` → slot `_on_iteration()` → `update_route()` → `draw_idle()`. Chạy trong suốt simulation.
* **Replay animation** (sau khi simulation xong): nút "Phát lại" kích hoạt `QTimer` → đọc frame-by-frame từ `_best_route_history` → `update_route()`. **Không chạy song song** với simulation worker.

Không bao giờ mix logic hai loại animation này vào cùng một luồng.

---

### D4 — Cụ thể hóa hàm mục tiêu VRP (dành cho v1.1)

Hàm mục tiêu VRP được cụ thể hóa:

```
fitness = total_distance + lambda_cap × Σ max(0, load_k − capacity)
```

Trong đó:
* `total_distance` = tổng quãng đường tất cả tuyến xe
* `lambda_cap` = 1000 (mặc định, người dùng có thể điều chỉnh)
* `load_k` = tổng nhu cầu khách hàng trên tuyến xe k
* `capacity` = tải trọng tối đa mỗi xe

Mức phạt lambda_cap = 1000 đủ mạnh để loại nghiệm vi phạm ra khỏi vùng tối ưu khi total_distance ~ 10²–10³.

---

### D5 — IIMP Compliance — Các yêu cầu bắt buộc khi triển khai

Những điểm **bắt buộc** ngoài thiết kế nghiệp vụ gốc, theo chuẩn IIMP_MODULE_SDK.md:

1. **Hosted, not standalone**: `build_view()` trả về `QWidget`, không mở cửa sổ mới; không có `plt.show()`
2. **BaseModule contract**: phải implement đủ `on_load`, `build_view`, `on_activate`, `on_deactivate`, `on_unload`, `get_state`, `restore_state`
3. **Thread safety**: `on_unload()` gọi `worker.request_stop()` + `worker.wait(3000)` trước khi module bị gỡ
4. **State versioning**: `get_state()` tự inject `_state_version = STATE_VERSION = "1.0.0"`; `restore_state()` compatible với BUG-03 fix
5. **Signal type safety**: worker chỉ emit plain Python types (`int`, `float`, `list`) — numpy arrays phải `.tolist()` trước khi emit
6. **manifest**: `id = "pso_logistics"`, `category = "quantitative_methods"`, `subcategory = "optimization"`, `supports_state_restore = true`, `supports_export = true`
7. **Problem generation thread-safe**: `TSPProblem.generate(n_customers, coord_range, data_seed)` được gọi ở **cả** UI thread (cho render) và worker thread (cho swarm) — kết quả giống nhau vì cùng seed, tránh pass object qua thread boundary
8. **Data sinh ngẫu nhiên feasible**: default `data_seed = 42`, `n_customers = 10`, `coord_range = 100.0` — bảo đảm bài toán TSP có nghiệm hội tụ có thể hiển thị trong thời gian hợp lý


