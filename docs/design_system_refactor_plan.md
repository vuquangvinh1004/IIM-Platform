# Kế hoạch Refactor Design System cho IIMP

## Mục tiêu

Đưa toàn bộ shell và các module về cùng một design system mà không phá kiến trúc hiện tại, không làm rò rỉ logic nghiệp vụ lên UI, và không buộc mọi module phải refactor lớn trong một lần.

Nguyên tắc áp dụng:

- Shell sở hữu token, primitive hiển thị và semantic style roles.
- Module tiếp tục sở hữu nội dung chuyên môn, biểu đồ và tương tác đặc thù.
- Refactor theo chiều dọc từng lát cắt, không làm big bang redesign.
- Mọi thay đổi hiển thị phải tương thích với `IIMP_ARCHITECTURE.md` và `IIMP_MODULE_SDK.md`.

## Giai đoạn 0: Nguồn chân lý

Mục tiêu: tạo nền tảng thiết kế thống nhất trước khi mở rộng.

Việc cần làm:

1. Duy trì `DESIGN.md` ở root repo như nguồn chân lý thị giác.
2. Map token cần thiết vào code qua một owner duy nhất trong `ui/styles/` hoặc `ui/design_system/`.
3. Chốt semantic roles cho shell: background, surface, panel, badge, CTA, nav state, empty state, error state.
4. Thiết lập lệnh lint `DESIGN.md` như một bước validate lặp lại.

Điểm dừng:

- Token đã đủ để shell không phải hardcode màu, radius và typography ở các view chính.

## Giai đoạn 1: Shell chrome

Mục tiêu: thống nhất ngôn ngữ của shell trước khi động vào module.

Phạm vi:

1. Sidebar và navigation states.
2. Page header pattern.
3. Status badge, action button, empty state, error state.
4. Workspace host chrome.

Ưu tiên kỹ thuật:

- Dùng object names hoặc widget properties để style qua QSS tập trung.
- Không rải `setStyleSheet(...)` nếu style thuộc về shell design system.

Điểm dừng:

- Dashboard, Library, Workspace, Module Manager và Settings cùng nói một ngôn ngữ thị giác.

## Giai đoạn 2: Library-first experience

Mục tiêu: biến Library thành điểm vào chính có khả năng khám phá tốt.

Phạm vi:

1. Module card chuẩn hóa metadata, badge và action hierarchy.
2. Search, filter, folder panel, selected state và empty results state.
3. Recently used, featured hoặc grouped sections nếu dữ liệu sẵn sàng.

Điểm dừng:

- Người dùng có thể quét, nhận diện và mở module nhanh hơn mà không phải đọc chi tiết kỹ thuật dài.

## Giai đoạn 3: Shared UI primitives cho module

Mục tiêu: giảm phân mảnh giữa shell và module mà không khóa module vào một framework nặng.

Phạm vi:

1. Tạo các primitive nhẹ: panel, section title, info banner, semantic badge, empty state.
2. Công bố guideline hiển thị trong SDK.
3. Cung cấp helper palette cho chart, tab, button và form states.

Chiến lược tương thích:

- Không buộc module cũ phải đổi ngay.
- Primitive mới là opt-in, nhưng module mới và module được sửa nên dùng mặc định.

Điểm dừng:

- Module mới có thể đạt cảm giác cùng sản phẩm mà không phải tự dựng QSS từ đầu.

## Giai đoạn 4: Module migration theo cụm

Mục tiêu: refactor dần các module có ảnh hưởng lớn nhất.

Thứ tự ưu tiên đề xuất:

1. `statistics/normal_distribution`
2. `economics/supply_demand`
3. `statistics/time_series`
4. Các module first-party còn lại

Tiêu chí chọn:

- module có lượng người dùng cao
- module có nhiều hardcoded styles
- module đại diện cho pattern UI có thể tái dùng

Điểm dừng:

- Các module chủ lực dùng chung semantic palette, typography hierarchy và panel structure.

## Giai đoạn 5: Chất lượng và cưỡng chế nhẹ

Mục tiêu: giữ thiết kế không bị trôi theo thời gian.

Việc cần làm:

1. Thêm checklist review cho thay đổi UI.
2. Thêm rule nội bộ: style shell không được hardcode ở view nếu có token tương ứng.
3. Theo dõi các widget hoặc module còn dùng inline QSS nhiều.
4. Cân nhắc snapshot hoặc smoke test nhiều hơn cho shell views quan trọng.

## Rủi ro chính

1. Thêm một lớp design system quá nông, chỉ đổi tên cho các style cũ mà không gom ownership thật sự.
2. Refactor đồng loạt quá nhiều module gây change amplification và khó xác định regressions.
3. Lẫn lộn giữa token của shell và palette chuyên môn của chart trong module.
4. Dùng QSS quá mức cho logic trạng thái thay vì semantic widget properties.

## Cách triển khai an toàn

1. Mỗi vòng chỉ refactor một lát cắt có test smoke hoặc validation hẹp.
2. Ưu tiên thêm primitive và object names trước, rồi mới loại bỏ inline styles cũ.
3. Với module phức tạp, giữ nguyên logic và chỉ thay lớp trình bày bên ngoài trước.
4. Ghi rõ trong SDK đâu là shell-owned style, đâu là module-owned visualization.

## Kết quả mong muốn

Khi hoàn tất, IIMP sẽ có:

1. Một `DESIGN.md` làm nguồn chân lý thị giác.
2. Một shell có hierarchy rõ, thống nhất và giàu cảm giác workspace học thuật.
3. Một lộ trình migration module thực tế, không phá hợp đồng hiện tại của runtime và SDK.
