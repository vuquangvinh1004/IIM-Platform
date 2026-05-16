---
version: alpha
name: IIMP Academic Canvas
description: Design system for the Integrated Interactive Module Platform, optimized for a scholarly, visual, desktop-first workspace.
colors:
  background: "#F3F0E8"
  on-background: "#1E2B36"
  surface: "#FBF9F4"
  on-surface: "#22313D"
  surface-container-low: "#F6F2EA"
  surface-container: "#ECE6DB"
  surface-container-high: "#E2DBCF"
  surface-container-highest: "#D7CDBF"
  surface-variant: "#E9E2D6"
  outline: "#A79A8B"
  outline-variant: "#D8D0C4"
  primary: "#173A5E"
  on-primary: "#FFFFFF"
  primary-container: "#2C618D"
  on-primary-container: "#F4F9FF"
  secondary: "#1F6B5D"
  on-secondary: "#FFFFFF"
  secondary-container: "#D9EEE8"
  on-secondary-container: "#123F36"
  tertiary: "#8D571C"
  on-tertiary: "#FFFFFF"
  tertiary-container: "#F4DCBE"
  on-tertiary-container: "#5E3811"
  error: "#B0413E"
  on-error: "#FFFFFF"
  error-container: "#F6DBDA"
  on-error-container: "#5D1F1D"
  success: "#2F7A55"
  on-success: "#FFFFFF"
  success-container: "#DCEEDB"
  warning: "#B36A1F"
  on-warning: "#FFFFFF"
typography:
  display:
    fontFamily: Aptos Display
    fontSize: 34px
    fontWeight: 700
    lineHeight: 40px
    letterSpacing: -0.02em
  headline-lg:
    fontFamily: Aptos Display
    fontSize: 26px
    fontWeight: 700
    lineHeight: 32px
    letterSpacing: -0.01em
  headline-md:
    fontFamily: Aptos Display
    fontSize: 22px
    fontWeight: 600
    lineHeight: 28px
  title-md:
    fontFamily: Aptos
    fontSize: 18px
    fontWeight: 600
    lineHeight: 24px
  title-sm:
    fontFamily: Aptos
    fontSize: 15px
    fontWeight: 600
    lineHeight: 20px
  body-lg:
    fontFamily: Aptos
    fontSize: 15px
    fontWeight: 400
    lineHeight: 22px
  body-md:
    fontFamily: Aptos
    fontSize: 14px
    fontWeight: 400
    lineHeight: 20px
  label-md:
    fontFamily: Bahnschrift
    fontSize: 12px
    fontWeight: 600
    lineHeight: 16px
    letterSpacing: 0.04em
  label-sm:
    fontFamily: Bahnschrift
    fontSize: 11px
    fontWeight: 500
    lineHeight: 14px
    letterSpacing: 0.05em
  caption:
    fontFamily: Aptos
    fontSize: 12px
    fontWeight: 400
    lineHeight: 16px
rounded:
  sm: 6px
  md: 10px
  lg: 16px
  xl: 24px
  full: 9999px
spacing:
  base: 8px
  xs: 4px
  sm: 8px
  md: 12px
  lg: 20px
  xl: 32px
  xxl: 48px
  gutter: 20px
  margin: 24px
components:
  button-primary:
    backgroundColor: "{colors.tertiary}"
    textColor: "{colors.on-tertiary}"
    typography: "{typography.label-md}"
    rounded: "{rounded.md}"
    padding: 12px
  button-primary-hover:
    backgroundColor: "{colors.tertiary-container}"
    textColor: "{colors.on-tertiary-container}"
  button-secondary:
    backgroundColor: "{colors.primary}"
    textColor: "{colors.on-primary}"
    typography: "{typography.label-md}"
    rounded: "{rounded.md}"
    padding: 12px
  button-secondary-hover:
    backgroundColor: "{colors.primary-container}"
    textColor: "{colors.on-primary-container}"
  nav-item:
    backgroundColor: transparent
    textColor: "{colors.on-primary}"
    typography: "{typography.title-sm}"
    rounded: "{rounded.md}"
    padding: 12px
  nav-item-active:
    backgroundColor: "{colors.tertiary}"
    textColor: "{colors.on-tertiary}"
  module-card:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.on-surface}"
    rounded: "{rounded.lg}"
    padding: 20px
  status-badge:
    backgroundColor: "{colors.secondary-container}"
    textColor: "{colors.on-secondary-container}"
    typography: "{typography.label-sm}"
    rounded: "{rounded.full}"
    padding: 8px
  empty-state-panel:
    backgroundColor: "{colors.surface-container-low}"
    textColor: "{colors.on-surface}"
    rounded: "{rounded.xl}"
    padding: 32px
  input-field:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.on-surface}"
    typography: "{typography.body-md}"
    rounded: "{rounded.md}"
    padding: 12px
---

# IIMP Design System

## Overview

IIMP phải mang cảm giác của một academic studio trên desktop: tập trung, sáng sủa, đáng tin cậy, và có chiều sâu vừa đủ để người dùng cảm thấy mình đang làm việc trong một workspace chuyên môn chứ không phải một bảng điều khiển quản trị chung chung.

Đối tượng sử dụng chính là giảng viên, người học, nhà nghiên cứu, và người phát triển module nội bộ. Vì vậy giao diện cần truyền được ba tín hiệu cùng lúc:

- có cấu trúc rõ ràng để giảm cognitive load trong các tác vụ chuyên môn
- có ngôn ngữ thị giác đủ ấm và giàu nhịp điệu để khuyến khích khám phá module
- có độ nhất quán đủ cao để nhiều module khác nhau vẫn có cảm giác cùng một sản phẩm

Phong cách tổng thể là Scholarly Visual Workspace: nền giấy sáng, khối nội dung phân lớp bằng tonal surfaces, headline nghiêm túc, metadata kỹ thuật gọn và sắc, và một màu nhấn duy nhất cho lời gọi hành động quan trọng.

## Colors

Hệ màu của IIMP dựa trên ba vai trò chính:

- Primary là xanh atlas đậm, dùng cho cấu trúc shell, navigation và các vùng mang tính nền tảng.
- Secondary là xanh lục trầm, dùng cho trạng thái lành mạnh, hoạt động bình thường và các chỉ dấu tích cực.
- Tertiary là màu amber đất, là động cơ tương tác chính cho CTA, điểm nhấn và các quyết định người dùng cần chú ý.

Các surface phải tạo cảm giác như nhiều lớp giấy và bảng trình bày nằm trên cùng một mặt bàn học thuật. Không dùng nền trắng tinh và viền đậm ở khắp nơi. Độ phân cấp phải đến từ tonal layers trước, border sau.

Màu lỗi phải rõ nhưng không gây gắt. Màu thành công và cảnh báo phải được dùng như semantic roles, không thay thế cho màu chủ đạo của sản phẩm.

## Typography

Typography cần phân biệt rõ giữa nội dung kể chuyện và metadata kỹ thuật.

- Aptos Display dùng cho display và headline vì vừa nghiêm túc vừa mềm hơn phong cách enterprise cứng.
- Aptos dùng cho body để giữ độ đọc cao ở desktop density trung bình.
- Bahnschrift dùng cho label và metadata nhỏ để tạo cảm giác chính xác, mô-đun và có tính công cụ.

Tiêu đề phải đủ mạnh để tạo cấu trúc cho từng màn. Label phải cô đọng, nhất quán, và không cạnh tranh với body text. Không dùng quá nhiều biến thể trọng lượng trên cùng một màn hình; ưu tiên hai trọng lượng chính là regular và semibold.

## Layout

Layout của IIMP theo mô hình desktop-first workspace:

- Một thanh điều hướng cố định ở cạnh trái cho các vùng chính của shell.
- Một vùng nội dung chính rộng, ưu tiên khả năng xem biểu đồ, mô phỏng và bảng điều khiển module.
- Mỗi màn có page header riêng để người dùng luôn biết mình đang ở đâu và hành động quan trọng nhất là gì.

Khoảng cách theo nhịp 8px, nhưng nên nhóm ở các mức `md`, `lg`, `xl` thay vì lạm dụng các khoảng cực nhỏ. Trang shell nên dùng `margin` cố định để tạo cảm giác rộng rãi và chủ động. Cards và panel cần padding lớn hơn mức admin dashboard thông thường để nội dung học thuật có không khí thở.

## Elevation & Depth

IIMP không nên dựa vào shadow dày. Độ sâu chủ yếu đến từ tonal layering:

- background là mặt nền giấy tổng
- surface là card hoặc panel nội dung chính
- surface-container và các biến thể cao hơn dùng để phân cấp trong cùng một màn

Shadow nếu dùng chỉ nên rất nhẹ, gần như một ambient lift. Hover state nên thể hiện qua thay đổi nền, viền và độ sáng trước khi tăng bóng đổ. Mục tiêu là cảm giác chính xác và có kiểm soát, không phải glossy hay decorative.

## Shapes

Ngôn ngữ hình dạng của IIMP là Soft Precision.

- Input và button dùng radius vừa phải để giữ cảm giác công cụ.
- Card và empty state dùng radius lớn hơn để tạo sự thân thiện và tách khối rõ hơn.
- Badge trạng thái phải bo tròn hoàn toàn để đọc nhanh như semantic markers.

Không trộn quá nhiều mức bo góc trên cùng một màn. Radius phải phản ánh vai trò, không phải sở thích ngẫu nhiên.

## Components

### Navigation

Navigation item phải có trạng thái active rõ ràng nhưng không được biến sidebar thành một cột màu chói. Active state nên dùng tertiary làm tín hiệu chính, còn hover state dùng tonal shift nhẹ.

### Page Header

Mỗi màn shell cần có page header gồm tiêu đề, mô tả ngắn và hành động chính. Đây là điểm tạo hierarchy đầu tiên cho người dùng khi chuyển ngữ cảnh.

### Module Card

Module card là đơn vị duyệt chính trong Library. Mỗi card phải giúp người dùng trả lời nhanh bốn câu hỏi:

- module này làm gì
- thuộc nhóm nào
- có sẵn sàng để mở không
- hành động tiếp theo là gì

Card phải đủ giàu metadata để quét nhanh, nhưng không được nặng như một bảng thông số kỹ thuật.

### Empty and Error States

Trạng thái rỗng và lỗi không được chỉ là một dòng text. Chúng phải giữ cùng ngôn ngữ thị giác với shell, có tiêu đề, thông điệp hỗ trợ và một hành động hồi phục rõ ràng.

### Workspace Chrome

Workspace là sân khấu chính của sản phẩm. Khi có module, shell chrome phải lùi xuống để nhường chỗ cho nội dung. Khi chưa có module hoặc có lỗi, shell phải dẫn dắt người dùng quay lại Library hoặc chọn một hành động tiếp theo rõ ràng.

## Do's and Don'ts

- Do dùng `tertiary` cho lời gọi hành động quan trọng nhất trên mỗi màn.
- Do dùng semantic containers và badge để phân loại module, trạng thái và nhóm thông tin.
- Do giữ nhiều khoảng thở xung quanh biểu đồ, mô phỏng và block giải thích.
- Do thiết kế shell như một workspace học thuật thống nhất, không như nhiều app nhỏ ghép lại.
- Do kéo quyết định màu, shape, spacing và typography xuống token hoặc primitive dùng chung.

- Don't hardcode màu và radius trực tiếp trong từng view nếu đó là quyết định của shell.
- Don't dùng một màu xanh cho mọi thứ tương tác, mọi trạng thái và mọi badge.
- Don't để trạng thái rỗng, lỗi hoặc loading trở thành fallback kỹ thuật vô hồn.
- Don't để module card giống row quản trị; nó phải là bề mặt khám phá.
- Don't phá hierarchy bằng quá nhiều border dày, icon ngẫu nhiên hoặc emoji trong luồng chính của shell.
