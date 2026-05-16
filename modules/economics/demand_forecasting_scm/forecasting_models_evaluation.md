# Các tiêu chí đánh giá mô hình dự báo thông dụng

Dưới đây là phần trình bày một số tiêu chí đánh giá mô hình dự báo theo cấu trúc: **Mô hình + chú thích**, **Ý nghĩa/diễn giải**, **Lưu ý khi sử dụng**.

| Tiêu chí | Mô hình + chú thích | Ý nghĩa / diễn giải | Lưu ý khi sử dụng |
|---|---|---|---|
| **MAE (Mean Absolute Error)** | **Mô hình:** \[ MAE = \frac{\sum_{t=1}^{n} |e_t|}{n} \] với \(e_t = Y_t - \hat{Y}_t\).  
**Chú thích:** Là sai số tuyệt đối bình quân giữa giá trị thực tế và giá trị dự báo. | Đo lường mức sai lệch bình quân của dự báo so với thực tế theo **đơn vị gốc** của dữ liệu. Giá trị MAE càng nhỏ thì dự báo càng chính xác. | Dễ hiểu, dễ giải thích, ít bị ảnh hưởng cực đoan hơn RMSE. Tuy nhiên, vì dùng giá trị tuyệt đối nên không phản ánh hướng sai lệch âm hay dương. Phù hợp khi cần đánh giá độ lớn sai số trung bình một cách trực quan. |
| **RMSE (Root Mean Squared Error)** | **Mô hình:** \[ RMSE = \sqrt{\frac{\sum_{t=1}^{n} e_t^2}{n}} \] với \(e_t = Y_t - \hat{Y}_t\).  
**Chú thích:** Là căn bậc hai của bình quân sai số bình phương. | Đo lường mức sai số dự báo, nhưng **phạt nặng hơn** đối với các sai số lớn do sai số được bình phương trước khi lấy trung bình. Giá trị RMSE càng nhỏ thì mô hình càng tốt. | Hữu ích khi các sai số lớn là vấn đề nghiêm trọng trong thực tiễn. Nhạy cảm với ngoại lệ hơn MAE. Cũng có cùng đơn vị với dữ liệu gốc nên khá thuận tiện để diễn giải, nhưng có thể bị kéo lên mạnh khi xuất hiện vài dự báo sai lệch lớn. |
| **MAPE (Mean Absolute Percentage Error)** | **Mô hình:** \[ MAPE = \frac{100}{n} \sum_{t=1}^{n} \left| \frac{e_t}{Y_t} \right| \]  
**Chú thích:** Là phần trăm sai số tuyệt đối bình quân, thể hiện sai số dự báo dưới dạng tỷ lệ phần trăm. | Cho biết bình quân dự báo sai lệch bao nhiêu phần trăm so với giá trị thực tế. Đây là chỉ tiêu rất phổ biến vì dễ so sánh giữa các chuỗi dữ liệu khác đơn vị đo hoặc khác quy mô. | Không phù hợp khi dữ liệu thực tế có giá trị bằng 0 hoặc rất gần 0 vì có thể làm chỉ tiêu không xác định hoặc bị méo mạnh. MAPE thường dễ hiểu với nhà quản trị, nhưng có thể gây thiên lệch khi chuỗi có nhiều giá trị nhỏ. |
| **Cum. Bias (Bias tích lũy)** | **Mô hình:** \[ Cum.\ Bias = \sum_{t=1}^{n} e_t = \sum_{t=1}^{n} (Y_t - \hat{Y}_t) \]  
**Chú thích:** Là tổng đại số của các sai số dự báo qua nhiều kỳ. | Phản ánh **xu hướng lệch có hệ thống** của mô hình. Nếu Cum. Bias dương lớn, mô hình có xu hướng **dự báo thấp hơn thực tế**. Nếu Cum. Bias âm lớn, mô hình có xu hướng **dự báo cao hơn thực tế**. Nếu gần 0, về tổng thể mô hình ít thiên lệch hơn. | Không đo trực tiếp độ lớn sai số bình quân như MAE hay RMSE, mà chủ yếu cho biết mô hình có bị lệch một phía hay không. Có thể xảy ra trường hợp Cum. Bias gần 0 nhưng sai số từng kỳ vẫn lớn do sai số dương và âm bù trừ lẫn nhau. Vì vậy nên dùng kết hợp với các chỉ tiêu như MAE hoặc RMSE. |
| **FVA (Forecast Value Added)** | **Mô hình:** Một cách biểu diễn phổ biến: \[ FVA = Error_{baseline} - Error_{model} \] hoặc \[ FVA\% = \frac{Error_{baseline} - Error_{model}}{Error_{baseline}} \times 100\% \]  
**Chú thích:** So sánh sai số của mô hình hoặc bước dự báo đang xét với một mức chuẩn, thường là dự báo cơ sở như Naive. | Dùng để đánh giá xem mô hình, quy trình, hoặc một bước can thiệp trong hệ thống dự báo có thực sự **tạo thêm giá trị** hay không. Nếu FVA dương, mô hình đang cải thiện độ chính xác so với mức chuẩn. Nếu FVA âm, mô hình hoặc quy trình đang làm dự báo tệ hơn mức chuẩn. | Đây không phải là một thước đo sai số độc lập như MAE hay RMSE, mà là thước đo **giá trị gia tăng của hoạt động dự báo**. Kết quả FVA phụ thuộc mạnh vào mức chuẩn được chọn. Khi áp dụng, cần xác định rõ đang so sánh theo chỉ tiêu nào, chẳng hạn MAE, RMSE hoặc MAPE. Rất hữu ích trong quản trị quy trình dự báo để phát hiện bước nào đang cải thiện hoặc làm giảm chất lượng dự báo. |

## Gợi ý diễn giải ngắn gọn

- **MAE**: cho biết sai số tuyệt đối bình quân theo đơn vị gốc của dữ liệu.
- **RMSE**: tương tự MAE nhưng nhấn mạnh mạnh hơn vào các sai số lớn.
- **MAPE**: cho biết sai số bình quân theo tỷ lệ phần trăm.
- **Cum. Bias**: cho biết mô hình có thiên lệch dự báo thấp hoặc cao một cách có hệ thống hay không.
- **FVA**: cho biết mô hình hoặc quy trình dự báo có tạo thêm giá trị so với mức chuẩn hay không.

## Nhận xét tổng quát

Trong thực tiễn, không nên chỉ dựa vào một tiêu chí duy nhất để kết luận mô hình nào tốt hơn. **MAE**, **RMSE** và **MAPE** giúp đánh giá độ lớn sai số dưới các góc nhìn khác nhau; **Cum. Bias** giúp nhận diện xu hướng thiên lệch hệ thống; còn **FVA** giúp đánh giá hiệu quả thực sự của mô hình hoặc quy trình dự báo so với một mức chuẩn. Vì vậy, việc kết hợp nhiều tiêu chí thường cho cái nhìn toàn diện và đáng tin cậy hơn về chất lượng dự báo.
