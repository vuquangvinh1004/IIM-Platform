# INTEGRATED INTERACTIVE MODULE PLATFORM ARCHITECTURE

> QUAN TRỌNG CHO AI AGENT
>
> File này là nguồn chân lý cho toàn bộ dự án Integrated Interactive Module Platform.
>
> AI Agent bắt buộc phải đọc và tuân thủ file này trước khi:
>
> 1. Bắt đầu xây dựng bất kỳ phần nào của shell app
> 2. Tạo mới, sửa, xóa hoặc refactor bất kỳ module nào
> 3. Thay đổi chuẩn module contract, manifest, event bus hoặc state format
> 4. Thay đổi database schema, cách lưu cấu hình hoặc cách quản lý module
> 5. Tích hợp thư viện mới ảnh hưởng đến runtime, UI hoặc packaging
> 6. Thay đổi hành vi cài đặt, kích hoạt, vô hiệu hóa hoặc gỡ module
>
> Mọi thay đổi về kiến trúc, hành vi nghiệp vụ, database schema, tech stack, cấu trúc thư mục, chuẩn coding hoặc chuẩn module phải được ghi ngay vào phần CHANGELOG ở cuối file này.
>
> Lệnh khởi đầu bắt buộc cho AI Agent:
>
> Trước khi bắt đầu xây dựng, hãy đọc file IIMP_ARCHITECTURE.md và IIMP_ROADMAP.md để hiểu kiến trúc, nguyên tắc phát triển, chuẩn module, ranh giới kỹ thuật và lộ trình thực hiện của dự án Integrated Interactive Module Platform.

---

## 1. Tổng quan dự án

### 1.1. Mô tả

Integrated Interactive Module Platform là một ứng dụng desktop dạng nền tảng tích hợp module tương tác. Ứng dụng gồm hai phần cốt lõi:

1. Shell App, tức ứng dụng lõi, đóng vai trò là môi trường vận hành thống nhất
2. Module, tức các tính năng độc lập có thể được nạp vào hệ thống để sử dụng như các “băng chức năng”

Ý tưởng vận hành của hệ thống tương tự như một máy chơi game kết nối với màn hình hiển thị. Shell App là “máy”, còn mỗi module là một “băng”. Khi module được cài và kích hoạt, người dùng có thể chạy ngay tính năng đó trong cùng một giao diện chung mà không cần mở một phần mềm riêng.

Mỗi module có thể là:

1. Mô phỏng học thuật hoặc khoa học
2. Công cụ trực quan hóa dữ liệu
3. Hình vẽ 2D hoặc 3D có thể xoay hoặc chuyển động
4. Bảng tra, bảng tính nhỏ hoặc tiện ích tương tác
5. Công cụ trình diễn, giảng dạy hoặc khám phá khái niệm
6. Mini feature có logic hẹp nhưng tương tác rõ ràng

Ví dụ: module mô phỏng phân phối chuẩn có thể cho phép nhập diện tích đuôi hoặc giá trị tới hạn Z, tính phần xác suất tương ứng, tô màu vùng dưới đường cong chuẩn và xuất hình minh họa. Đây là ví dụ điển hình cho loại module mà nền tảng này cần hỗ trợ tốt.

### 1.2. Mục tiêu sản phẩm

| Mục tiêu | Diễn giải |
|---|---|
| Tích hợp nhiều công cụ nhỏ vào một nơi | Tránh việc mỗi tính năng phải chạy như một ứng dụng riêng lẻ |
| Chuẩn hóa trải nghiệm sử dụng | Mọi module đều hiển thị và vận hành trong cùng một giao diện chuyên nghiệp |
| Mở rộng lâu dài | Có thể thêm mới module mà không phá cấu trúc tổng thể |
| Tách rõ shell và module | Giảm coupling, tăng khả năng bảo trì và tái sử dụng |
| Hỗ trợ nội dung trực quan và tương tác | Phù hợp cho giảng dạy, trình bày, mô phỏng và thao tác khám phá |
| Vận hành cục bộ ổn định | Các chức năng cốt lõi chạy được offline, local first |
| Tạo hệ sinh thái module | Cho phép về sau phát triển bộ SDK, template module và quy trình đóng gói module |

### 1.3. Phạm vi phiên bản v1.0

Phiên bản v1.0 bắt buộc phải có:

1. Shell App với giao diện desktop thống nhất
2. Module registry để phát hiện và quản lý các module đã cài
3. Module loader để nạp và khởi chạy module
4. Chuẩn module manifest thống nhất
5. Chuẩn BaseModule contract thống nhất
6. Khu vực hiển thị nội dung module trong shell
7. Sidebar hoặc library để chọn module
8. Cơ chế enable, disable và uninstall module
9. Lưu cấu hình ứng dụng cục bộ
10. Lưu cấu hình và trạng thái cục bộ của từng module
11. Tối thiểu 2 module mẫu first-party
12. Đóng gói thành ứng dụng desktop cài đặt được trên Windows

Phiên bản v1.0 chưa bắt buộc phải có:

1. Marketplace online
2. Cloud sync
3. Nhiều tài khoản người dùng
4. Cập nhật module từ internet
5. Sandbox thực thi cấp hệ điều hành
6. Scripting engine cho module do người dùng tự viết trong UI
7. Hệ permission nâng cao theo từng thao tác runtime
8. Hỗ trợ web module hoặc mobile module

### 1.4. Đối tượng sử dụng

1. Giảng viên, giáo viên hoặc người biên soạn nội dung minh họa
2. Người học cần các công cụ mô phỏng hoặc tương tác trực quan
3. Nhà nghiên cứu muốn gom các tiện ích nhỏ vào cùng một nền tảng
4. Nhà phát triển nội bộ muốn phát triển nhiều module dưới một khung chung
5. Tổ chức nhỏ cần một ứng dụng desktop mở rộng dần bằng module

---

## 2. Nguyên tắc sản phẩm và ranh giới kiến trúc

### 2.1. Nguyên tắc bắt buộc

| Nguyên tắc | Nội dung |
|---|---|
| Desktop first | Mọi luồng chính phải tối ưu cho desktop trước |
| Offline first | Các chức năng lõi phải chạy được không cần internet |
| Local first | Dữ liệu và cấu hình mặc định lưu trên máy người dùng |
| Module first | Mọi tính năng mở rộng phải đi qua chuẩn module |
| Shell module separation | Shell quản lý vòng đời và UI khung; module chịu trách nhiệm năng lực chuyên biệt |
| Unified UX | Module khác nhau nhưng phải có cảm giác cùng một sản phẩm |
| Safe extensibility | Mở rộng phải có kiểm soát qua manifest, version và contract |
| Maintainability | Code phải testable, dễ refactor, dễ thêm module mới |
| Backward compatibility by contract | Không được phá module cũ nếu chưa version hóa rõ ràng |

### 2.2. Những điều AI Agent không được tự ý làm

1. Không tự ý chuyển dự án sang Electron, Tauri, web app, mobile app hoặc framework khác khi chưa có cập nhật chính thức trong file này.
2. Không nhúng logic module trực tiếp vào main window hoặc widget của shell.
3. Không hardcode danh sách module ngay trong UI.
4. Không bỏ qua module manifest để nạp module “tự phát”.
5. Không cho module ghi trực tiếp vào database lõi ngoài các service hoặc repository được phép.
6. Không để module ghi file bừa bãi ngoài thư mục dữ liệu hoặc thư mục export đã định nghĩa.
7. Không thay đổi chuẩn BaseModule contract mà không cập nhật tài liệu này và changelog.
8. Không đánh dấu task là hoàn thành nếu chỉ có mock UI hoặc placeholder module.
9. Không phá tính nhất quán giao diện bằng cách để mỗi module tự dựng một main window độc lập trong luồng mặc định.
10. Không thêm phụ thuộc nặng cho toàn hệ thống chỉ để phục vụ một module hẹp nếu chưa đánh giá tác động.
11. Không gắn internet hoặc API online vào luồng cốt lõi của v1.0 khi chưa có quyết định kiến trúc chính thức.
12. Không để module import chéo logic nội bộ của nhau trừ khi đi qua contract hoặc shared service đã được phê duyệt.

---

### 2.3. Triết lý thiết kế phần mềm

> Tài liệu tham khảo: `philosophy_of_software_design.md` (A Philosophy of Software Design — John Ousterhout)
>
> Đây là bộ nguyên tắc thiết kế **bắt buộc** áp dụng xuyên suốt toàn bộ quá trình phát triển — không chỉ cho lần viết đầu tiên mà cho cả mọi lần sửa đổi, refactor và mở rộng về sau. Mục tiêu duy nhất: **giảm complexity tích lũy**.

#### 2.3.1. Lập trình chiến lược (Strategic Programming) — Ch. 3

Tactical programming — viết nhanh cho xong — tích lũy complexity theo từng thay đổi nhỏ. Sau đủ nhiều thay đổi nhỏ, toàn bộ codebase trở nên khó đọc và khó sửa.

**Quy tắc bắt buộc:**

| Quy tắc | Áp dụng |
|---|---|
| Dành 10–20% effort mỗi sprint để cleanup, refactor và cải thiện thiết kế hiện có | Mọi sprint, mọi contributor |
| Khi sửa một file, tìm cách cải thiện thiết kế ở vùng lân cận — không chỉ sửa đúng điểm được yêu cầu | Mọi PR |
| Nếu thiết kế hiện tại cản trở thay đổi, ưu tiên refactor thiết kế trước — đừng workaround bằng flag hoặc exception đặc biệt | Mọi contributor |
| Với mỗi quyết định thiết kế quan trọng, thử ít nhất 2 phương án trước khi chọn (Design It Twice — Ch. 11) | Architecture decision |

#### 2.3.2. Module sâu (Deep Modules) — Ch. 4

Một module tốt có **interface đơn giản** che khuất **implementation phức tạp**. Module nông — ít logic nhưng nhiều method/tham số — tích lũy complexity vào caller.

**Quy tắc bắt buộc:**

| Quy tắc | Áp dụng |
|---|---|
| `ModuleService` phải che khuất toàn bộ complexity của lifecycle — caller chỉ gọi `load()`, `activate()`, `deactivate()`, `unload()` | `core/services/module_service.py` |
| Các service layer phải xử lý nội bộ, không để caller phải biết chi tiết persistence, rollback hay sync | Tất cả `core/services/` |
| Không tạo class chỉ để bọc một phương thức khác với signature giống hệt (pass-through methods/classes) | Mọi layer |
| Nếu một class chỉ có 1–2 method thực chất và không có logic riêng, hãy gộp vào class liên quan | Mọi layer |
| Mỗi tầng trong kiến trúc phải cung cấp abstraction **khác biệt** so với tầng trên và tầng dưới | App Shell → Module Runtime → Storage |

#### 2.3.3. Ẩn thông tin (Information Hiding) — Ch. 5

Mỗi module chỉ lộ ra những gì caller **thực sự cần**. Mọi chi tiết về cách implement, định dạng lưu trữ, cấu trúc DB, schema nội bộ phải được ẩn hoàn toàn.

**Quy tắc bắt buộc:**

| Quy tắc | Áp dụng |
|---|---|
| Widget và view không được import hoặc biết về ORM models (`DBModuleRegistry`, `DBSetting`...) | `ui/` |
| Module không được biết shell dùng SQLite hay storage engine gì — chỉ giao tiếp qua service interface | `modules/` |
| Service không được trả về raw ORM object ra ngoài — phải map sang dataclass hoặc primitive | `core/services/` |
| Nếu hai class đều cần biết cùng một detail (ví dụ format file, schema DB), rút detail đó vào một class duy nhất | Mọi layer |
| Khi phát hiện thông tin bị lặp lại ở nhiều module, đó là dấu hiệu cần tạo một abstraction mới để che khuất | Mọi layer |

#### 2.3.4. Kéo complexity xuống tầng dưới (Pull Complexity Down) — Ch. 8

Tầng dưới gánh complexity để tầng trên có interface đơn giản. Đừng "punt" complexity lên caller.

**Quy tắc bắt buộc:**

| Quy tắc | Áp dụng |
|---|---|
| Service phải tự suy ra giá trị mặc định hợp lý thay vì bắt caller cấu hình mọi thứ | `core/services/` |
| `ModuleService` phải tự xử lý synchronization DB + in-memory sau mỗi thao tác — caller không cần biết có hai nơi cần update | `core/services/module_service.py` |
| Khi một thao tác cần nhiều bước phối hợp, đóng gói tất cả vào một method duy nhất trong tầng dưới | Mọi service |
| Shell (UI layer) chỉ được biết kết quả (thành công / thất bại + thông điệp lỗi), không được tự xử lý rollback hay retry | `ui/` |

#### 2.3.5. Xử lý lỗi (Define Errors Out of Existence) — Ch. 10

Exception là nguồn complexity lớn nhất. Mục tiêu là giảm số nơi exception phải được xử lý — không phải thêm `try/except` ở khắp nơi.

**Quy tắc bắt buộc:**

| Quy tắc | Áp dụng |
|---|---|
| Service phải xử lý exception ở mức thấp nhất có thể — không để exception bay lên caller nếu caller không có cách handle tốt hơn | `core/services/` |
| Module load thất bại không được raise exception lên `MainWindow` — `ModuleService.load()` phải catch, log và trả về `None` | `core/services/module_service.py` |
| Không để exception bị nuốt im lặng (silent swallow) — phải log ở mức `error` hoặc `warning` trước khi suppress | Mọi layer |
| Khi thiết kế API, ưu tiên định nghĩa sao cho trường hợp "không hợp lệ" không thể xảy ra, thay vì xử lý nó ở caller | Mọi public interface |
| Tập hợp nhiều loại lỗi cùng tầng vào một handler duy nhất ở điểm gần nhất có thể xử lý được, không catch lẻ tẻ | Mọi layer |

#### 2.3.6. Đặt tên (Naming) — Ch. 14

Tên là tài liệu trực tiếp trong code. Tên mơ hồ tạo unknown unknowns — người đọc không biết mình đang hiểu sai.

**Quy tắc bắt buộc:**

| Quy tắc | Áp dụng |
|---|---|
| Tên phải mô tả chính xác hành vi hoặc dữ liệu, không chỉ "đủ gần" | Mọi file |
| Dùng nhất quán một tên cho một khái niệm — không đổi giữa `module_id` / `mod_id` / `id` trong cùng một luồng | Mọi layer |
| Tên method phải mô tả **hiệu ứng (side effect) hoặc giá trị trả về**, không phải cách implement | `core/` |
| Nếu không tìm được tên ngắn và chính xác, đó thường là dấu hiệu khái niệm chưa được định nghĩa rõ — dừng lại và thiết kế lại | Mọi file |
| Enum và constant phải tự giải thích ngữ nghĩa — không dùng số nguyên hoặc chuỗi kỳ lạ cho trạng thái | `core/utils/constants.py` |

#### 2.3.7. Code rõ ràng (Code Should Be Obvious) — Ch. 18

Code được thiết kế để **đọc**, không phải để viết. Developer mới (hoặc AI Agent) phải hiểu ý định từ code mà không cần hỏi tác giả.

**Quy tắc bắt buộc:**

| Quy tắc | Áp dụng |
|---|---|
| Không để giá trị "magic" (số nguyên, chuỗi thô) xuất hiện trực tiếp trong logic — đặt thành constant hoặc enum có tên | Mọi file |
| Chỉ số navigation, state enum, permission string phải là typed constant hoặc enum | `ui/`, `core/utils/constants.py` |
| Event handler phức tạp (signal-slot chain) phải có comment mô tả luồng trigger | `ui/`, `core/module_runtime/event_bus.py` |
| Nếu một đoạn code cần comment dài để giải thích **cách hoạt động**, đó là dấu hiệu cần refactor thành method riêng với tên rõ hơn | Mọi file |

#### 2.3.8. Tài liệu hóa (Comments Should Describe Non-Obvious Things) — Ch. 13 & 15

Comment giải thích **tại sao**, **điều kiện biên**, **invariant** và **contract** — không phải giải thích lại code đã rõ.

**Quy tắc bắt buộc:**

| Loại | Yêu cầu |
|---|---|
| Public method/class trong `core/` | Bắt buộc có docstring: mô tả **mục đích**, **precondition**, **side effect** và **giá trị trả về** |
| `BaseModule` và các abstract method trong SDK | Bắt buộc có docstring với **ví dụ**, **required keys** và **cảnh báo khi override** |
| Cross-layer decision (vd: tại sao DB update phải trước in-memory update) | Bắt buộc có inline comment giải thích thứ tự và lý do |
| Magic constant hoặc formula không hiển nhiên | Bắt buộc có comment nguồn gốc hoặc giải thích toán học |
| Deprecated code hoặc shim backward-compat | Bắt buộc có comment ghi rõ lý do tồn tại và khi nào sẽ xóa |
| Comment lặp lại code (đọc code là hiểu ngay) | **Bị cấm** — xóa đi |

---

## 3. Tech stack chính thức

### 3.1. Công nghệ cốt lõi

| Thành phần | Công nghệ | Version đề xuất | Lý do lựa chọn |
|---|---|---:|---|
| Desktop framework | PySide6 | >= 6.6 | Ổn định, widget phong phú, phù hợp cho desktop app Python |
| Python | Python | >= 3.11 | Type hints tốt, hệ sinh thái mạnh, phù hợp plugin runtime |
| Database | SQLite | >= 3.40 | Serverless, local first, đủ cho registry và settings của v1.0 |
| ORM | SQLAlchemy | >= 2.0 | Tách persistence rõ ràng, dễ test, dễ migrate |
| Migration | Alembic | >= 1.13 | Kiểm soát schema theo version |
| Module loading | importlib + pathlib | builtin | Phù hợp cho local module discovery và entry point loading |
| Validation | pydantic | >= 2.0 | Kiểm tra manifest, settings, payload |
| Logging | loguru | >= 0.7 | Logging dễ đọc, dễ xoay vòng file |
| Event signaling | Qt Signals + internal event bus | n/a | Phù hợp UI app và module lifecycle |
| Visualization 2D mặc định | matplotlib | >= 3.8 | Hợp với mô phỏng học thuật, đồ thị thống kê |
| Data helpers | numpy, pandas | >= 1.26, >= 2.1 | Hỗ trợ module tính toán và dữ liệu |
| Testing | pytest, pytest-qt, pytest-cov | >= 7.4 | Unit test, UI test, coverage |
| Packaging | PyInstaller | >= 6.0 | Đóng gói desktop app cho Windows trước |

### 3.2. Công nghệ tùy chọn có kiểm soát

Các công nghệ sau chỉ được thêm khi có lý do rõ ràng và cập nhật changelog:

| Công nghệ | Trạng thái | Ghi chú |
|---|---|---|
| pyqtgraph | Tùy chọn | Dùng cho biểu đồ realtime hoặc hiệu năng cao |
| VisPy | Tùy chọn | Dùng cho module đồ họa tăng tốc GPU |
| OpenGL hoặc Qt3D | Tùy chọn | Chỉ khi v1.0 hoặc v1.1 cần module 3D thực sự |
| scipy | Tùy chọn có ưu tiên | Hợp lý cho module mô phỏng thống kê, tối ưu hóa, khoa học |
| Plotly offline | Tùy chọn | Chỉ khi thật sự cần tương tác kiểu web nhúng |

### 3.3. Lựa chọn bị loại khỏi v1.0

| Công nghệ | Trạng thái | Lý do |
|---|---|---|
| Electron | Không dùng | Nặng, lệch khỏi định hướng Python desktop |
| FastAPI hoặc Django | Không dùng | Không phải web app ở v1.0 |
| PostgreSQL | Không dùng | Dư thừa cho local platform v1.0 |
| Redis | Không dùng | Không cần cho workload hiện tại |
| Marketplace online bắt buộc | Không dùng | Trái với offline first |
| Dynamic remote code download | Không dùng | Tăng rủi ro an toàn và phức tạp release |

### 3.4. Package tối thiểu đề xuất

```python
PySide6>=6.6.0
SQLAlchemy>=2.0.0
alembic>=1.13.0
pydantic>=2.0.0
loguru>=0.7.2
matplotlib>=3.8.0
numpy>=1.26.0
pandas>=2.1.0
pytest>=7.4.0
pytest-qt>=4.2.0
pytest-cov>=4.1.0
PyInstaller>=6.0.0
```

---

## 4. Cấu trúc thư mục chuẩn

```text
integrated_interactive_module_platform/
│
├── main.py
├── IIMP_ARCHITECTURE.md
├── IIMP_ROADMAP.md
├── README.md
├── requirements.txt
├── requirements-dev.txt
├── .env.example
├── .gitignore
│
├── config/
│   ├── __init__.py
│   ├── settings.py
│   ├── database.py
│   └── paths.py
│
├── core/
│   ├── __init__.py
│   ├── app_kernel/
│   │   ├── __init__.py
│   │   ├── bootstrap.py
│   │   ├── lifecycle.py
│   │   ├── startup_checks.py
│   │   └── shutdown_manager.py
│   ├── module_runtime/
│   │   ├── __init__.py
│   │   ├── base_module.py
│   │   ├── manifest_schema.py
│   │   ├── loader.py
│   │   ├── registry.py
│   │   ├── sandbox_policy.py
│   │   ├── state_manager.py
│   │   └── event_bus.py
│   ├── services/
│   │   ├── __init__.py
│   │   ├── module_service.py
│   │   ├── settings_service.py
│   │   ├── workspace_service.py
│   │   ├── export_service.py
│   │   └── permission_service.py
│   ├── storage/
│   │   ├── __init__.py
│   │   ├── models.py
│   │   ├── connection.py
│   │   ├── session.py
│   │   └── migrations/
│   │       └── versions/
│   └── utils/
│       ├── __init__.py
│       ├── constants.py
│       ├── validators.py
│       ├── exceptions.py
│       ├── helpers.py
│       └── logger.py
│
├── modules/
│   ├── __init__.py
│   ├── statistics/
│   │   └── normal_distribution/
│   │       ├── manifest.json
│   │       ├── module.py
│   │       ├── widgets/
│   │       ├── assets/
│   │       ├── tests/
│   │       └── README.md
│   ├── visualization/
│   │   └── interactive_geometry/
│   │       ├── manifest.json
│   │       ├── module.py
│   │       ├── widgets/
│   │       ├── assets/
│   │       └── tests/
│   └── templates/
│       └── starter_module/
│           ├── manifest.json
│           ├── module.py
│           └── README.md
│
├── ui/
│   ├── __init__.py
│   ├── main_window.py
│   ├── styles/
│   │   ├── __init__.py
│   │   ├── themes.py
│   │   └── qss_styles.py
│   ├── widgets/
│   │   ├── __init__.py
│   │   ├── module_card.py
│   │   ├── module_toolbar.py
│   │   ├── module_host_frame.py
│   │   ├── status_strip.py
│   │   ├── activity_panel.py
│   │   └── permission_badge.py
│   ├── dialogs/
│   │   ├── __init__.py
│   │   ├── install_module_dialog.py
│   │   ├── module_details_dialog.py
│   │   ├── permission_dialog.py
│   │   └── app_settings_dialog.py
│   └── views/
│       ├── __init__.py
│       ├── dashboard_view.py
│       ├── module_library_view.py
│       ├── workspace_view.py
│       ├── module_manager_view.py
│       ├── activity_history_view.py
│       └── settings_view.py
│
├── data/
│   ├── database/
│   │   └── iimp.db
│   ├── module_data/
│   ├── workspace/
│   ├── exports/
│   ├── temp/
│   └── logs/
│
├── assets/
│   ├── icons/
│   ├── images/
│   └── templates/
│
├── docs/
│   ├── module_sdk.md
│   ├── module_manifest_reference.md
│   ├── release_notes.md
│   └── migration_notes.md
│
├── tests/
│   ├── __init__.py
│   ├── conftest.py
│   ├── unit/
│   ├── integration/
│   ├── ui/
│   └── fixtures/
│
└── scripts/
    ├── dev/
    └── release/
```

### 4.1. Quy tắc cấu trúc

1. Không đặt logic runtime lõi trong `ui/`.
2. Không đặt truy cập database trực tiếp vào widget hoặc view.
3. Không để mỗi module tự tạo main window riêng cho luồng sử dụng tiêu chuẩn.
4. Không để file tạm và script rời rạc ở root lâu dài.
5. Mọi dữ liệu cục bộ của app và module phải nằm dưới `data/`.
6. Mọi module first-party đều phải có `manifest.json` và `module.py`.
7. Mọi module tương lai đều nên có thư mục `tests/` riêng.

---

## 5. Kiến trúc hệ thống và module

### 5.1. Thành phần cốt lõi

Integrated Interactive Module Platform gồm 5 lớp chính:

1. App Shell  
   Chịu trách nhiệm khởi tạo ứng dụng, main window, điều hướng, layout chung, theme và status bar.

2. Module Runtime  
   Chịu trách nhiệm phát hiện module, đọc manifest, load class entry point, quản lý vòng đời, quản lý trạng thái và kết nối module vào host frame.

3. Storage and Settings Layer  
   Chịu trách nhiệm lưu registry, app settings, module settings, workspace state và activity history.

4. Shared Services  
   Cung cấp các năng lực chung như export file, permission check, logging, event dispatch và helpers.

5. Modules  
   Là các đơn vị chức năng độc lập, ví dụ mô phỏng phân phối chuẩn, hình học tương tác, bảng tra, hoặc tiện ích minh họa khác.

### 5.2. Kiến trúc logic tổng thể

```text
┌────────────────────────────────────────────────────────────┐
│                        App Shell                           │
│  Main Window | Navigation | Theme | Status | Host Frame   │
└────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌────────────────────────────────────────────────────────────┐
│                     Module Runtime                         │
│  Registry | Loader | BaseModule | Event Bus | State       │
└────────────────────────────────────────────────────────────┘
              │                     │
              ▼                     ▼
┌───────────────────────┐   ┌──────────────────────────────┐
│ Shared Services       │   │ Storage and Settings         │
│ Export | Permission   │   │ SQLite | Settings | Sessions │
│ Logging | Helpers     │   │ Registry State | Activity    │
└───────────────────────┘   └──────────────────────────────┘
              │
              ▼
┌────────────────────────────────────────────────────────────┐
│                         Modules                            │
│ Normal Distribution | 3D View | Lookup Tool | Simulation │
└────────────────────────────────────────────────────────────┘
```

### 5.3. Định nghĩa chuẩn của một module

Một module hợp lệ trong hệ thống phải có ít nhất các thành phần sau:

1. `manifest.json`
2. `module.py` chứa class entry point
3. Một class kế thừa `BaseModule`
4. Tối thiểu một widget hoặc view để host vào shell
5. Metadata và version rõ ràng

### 5.4. Chuẩn `manifest.json`

Manifest là nguồn chân lý về metadata của module. Tối thiểu phải có các trường sau:

```json
{
  "id": "statistics.normal_distribution",
  "name": "Normal Distribution Explorer",
  "version": "1.0.0",
  "description": "Mô phỏng phân phối chuẩn và vùng xác suất",
  "author": "Internal Team",
  "category": "statistics",
  "entry_point": "modules.statistics.normal_distribution.module:NormalDistributionModule",
  "min_platform_version": "1.0.0",
  "permissions": ["module_data_rw", "export_files"],
  "tags": ["statistics", "normal-distribution", "visualization"],
  "icon": "assets/icon.png"
}
```

### 5.5. Chuẩn `BaseModule`

Mọi module phải tuân thủ contract tối thiểu sau:

```python
from abc import ABC, abstractmethod
from PySide6.QtWidgets import QWidget

class BaseModule(ABC):
    module_id: str
    module_name: str
    module_version: str

    @abstractmethod
    def on_load(self, context) -> None:
        ...

    @abstractmethod
    def create_widget(self, parent=None) -> QWidget:
        ...

    def on_activate(self) -> None:
        pass

    def on_deactivate(self) -> None:
        pass

    def on_unload(self) -> None:
        pass

    def get_default_state(self) -> dict:
        return {}

    def save_state(self) -> dict:
        return {}

    def restore_state(self, state: dict) -> None:
        pass
```

### 5.6. Vòng đời chuẩn của module

1. Discovery  
   Runtime quét thư mục module và đọc manifest.

2. Validation  
   Runtime kiểm tra manifest, version compatibility, entry point và dependency cơ bản.

3. Load  
   Runtime import class module và gọi `on_load(context)`.

4. Host  
   Runtime gọi `create_widget()` và gắn widget của module vào `module_host_frame`.

5. Activate  
   Khi người dùng mở module, runtime gọi `on_activate()`.

6. Deactivate  
   Khi người dùng rời module hoặc đổi module, runtime gọi `on_deactivate()`.

7. Persist  
   Runtime gọi `save_state()` theo sự kiện hoặc khi app tắt.

8. Unload  
   Runtime gọi `on_unload()` khi app shutdown hoặc uninstall.

### 5.7. Module context chuẩn

Shell được phép truyền vào module một `ModuleContext` với các service đã chuẩn hóa, ví dụ:

1. `logger`
2. `event_bus`
3. `settings_service`
4. `export_service`
5. `module_data_path`
6. `workspace_path`
7. `permission_service`
8. `platform_version`

Không được để module truy cập tùy tiện toàn bộ đối tượng main window hoặc DB session thô, trừ khi contract sau này định nghĩa rõ.

### 5.8. Phân loại module trong v1.0

| Loại | Mô tả |
|---|---|
| Visualization Module | Hiển thị biểu đồ, hình 2D, hình 3D, bản đồ tương tác |
| Simulation Module | Mô phỏng một hiện tượng hoặc quy trình |
| Utility Module | Bảng tra, calculator, mini tool |
| Educational Module | Công cụ minh họa khái niệm, bài tập, thí nghiệm trực quan |
| Hybrid Module | Kết hợp tính toán, trực quan hóa và export |

### 5.9. Chính sách phụ thuộc module

1. Module không được phụ thuộc trực tiếp vào một module khác trong v1.0.
2. Mọi năng lực dùng chung phải đi qua `core/services/` hoặc utility shared.
3. Nếu một module cần thư viện nặng riêng, phải ghi rõ trong manifest và changelog.
4. Không cho phép dependency chain module-to-module chưa được chuẩn hóa.

---

## 6. Quy trình nghiệp vụ chuẩn

### 6.1. Luồng khởi động ứng dụng

1. App Shell khởi tạo config, paths, logger, DB connection.
2. Hệ thống thực hiện startup checks.
3. Runtime quét thư mục module.
4. Runtime validate manifest và tạo registry in-memory.
5. Hệ thống đồng bộ registry với DB local.
6. Main window mở với module library và dashboard.

### 6.2. Luồng cài module local

1. Người dùng chọn thư mục module hoặc gói module được hỗ trợ.
2. Hệ thống đọc manifest.
3. Hệ thống kiểm tra version, entry point và tính hợp lệ.
4. Hệ thống ghi metadata vào registry.
5. Hệ thống đánh dấu module là installed và enabled nếu hợp lệ.
6. Module xuất hiện trong library.

### 6.3. Luồng mở module

1. Người dùng chọn module từ library.
2. Runtime kiểm tra trạng thái enable.
3. Runtime load module nếu chưa load.
4. Runtime tạo widget của module.
5. Host frame hiển thị widget.
6. Status bar và toolbar cập nhật theo module hiện tại.
7. Hệ thống ghi activity log.

### 6.4. Luồng lưu trạng thái module

1. Module phát sinh thay đổi trạng thái.
2. Runtime hoặc state manager gọi `save_state()`.
3. State được serialize thành JSON.
4. Hệ thống lưu vào `module_sessions` hoặc `module_settings`.
5. Khi mở lại module, runtime gọi `restore_state()`.

### 6.5. Luồng disable hoặc uninstall module

1. Người dùng chọn disable hoặc uninstall.
2. Hệ thống kiểm tra module đang chạy hay không.
3. Nếu đang chạy, runtime deactivate và unload trước.
4. Hệ thống cập nhật registry state.
5. Nếu uninstall, hệ thống xóa tham chiếu cài đặt và tùy chọn dọn dữ liệu module.
6. Activity log được ghi lại.

---

## 7. Quy tắc nghiệp vụ lõi của nền tảng

### 7.1. Shell và module là hai tầng riêng biệt

1. Shell chịu trách nhiệm điều hướng, layout, thống nhất UX và vòng đời.
2. Module chịu trách nhiệm năng lực chuyên môn và UI nội bộ của module.
3. Shell không được chứa logic đặc thù của từng module, trừ metadata hiển thị chuẩn hóa.
4. Module không được tự biến mình thành một app độc lập phá vỡ luồng nền tảng.

### 7.2. Manifest là điểm vào chính thức

1. Một module không có manifest hợp lệ thì không được load.
2. Manifest là nguồn chân lý của metadata module.
3. Mọi thay đổi id, version hoặc entry point phải được cập nhật trong manifest trước.

### 7.3. Module state phải có thể lưu và phục hồi

1. Module cần định nghĩa state có thể serialize được.
2. State phải có khả năng phục hồi tối thiểu cho phiên làm việc gần nhất.
3. Không lưu object Python không serialize trực tiếp vào DB.
4. Dữ liệu lớn của module phải lưu vào thư mục module data riêng nếu cần.

### 7.4. Giao diện phải thống nhất

1. Main window, sidebar, toolbar, status bar, host frame, dialog phải theo cùng một hệ design.
2. Module được tự do trong vùng nội dung của mình, nhưng không được phá theme chung.
3. Module phải hỗ trợ co giãn theo layout của shell.
4. Không dùng cửa sổ popup tràn lan nếu không cần thiết.

### 7.5. Chính sách permissions v1.0

Trong v1.0, permissions được khai báo trong manifest và chủ yếu phục vụ minh bạch nội bộ. Chưa bắt buộc sandbox mức hệ điều hành.

Các permission chuẩn v1.0:

| Permission | Ý nghĩa |
|---|---|
| module_data_rw | Đọc và ghi dữ liệu trong thư mục module riêng |
| workspace_rw | Đọc và ghi trạng thái workspace |
| export_files | Ghi file export do người dùng yêu cầu |
| read_local_files | Đọc file local do người dùng chọn |
| network_optional | Có thể dùng internet nếu module tương lai cần và được bật |
| gpu_render | Dùng backend tăng tốc đồ họa nếu có |

Quy tắc:

1. Không cấp `network_optional` cho module v1.0 nếu không thật cần.
2. Module không được giả định rằng permission luôn được cấp.
3. Nếu về sau thêm prompt cấp quyền, contract phải mở rộng chính thức.

### 7.6. Phiên bản và tương thích

1. Platform phải có version chính thức.
2. Module phải khai báo `min_platform_version`.
3. Nếu module không tương thích version hiện tại, hệ thống phải cảnh báo và không load mù.
4. Không được phá backward compatibility của BaseModule trong phạm vi major version nếu chưa có migration plan.

---

## 8. Database schema chính thức

### 8.1. Tổng quan bảng dữ liệu

Phiên bản v1.0 sử dụng 7 bảng chính:

1. module_registry
2. module_settings
3. module_sessions
4. workspace_items
5. app_settings
6. activity_logs
7. installed_artifacts

### 8.2. Schema chi tiết

```sql
CREATE TABLE module_registry (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    module_id TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    category TEXT,
    version TEXT NOT NULL,
    description TEXT,
    entry_point TEXT NOT NULL,
    install_path TEXT NOT NULL,
    icon_path TEXT,
    is_enabled BOOLEAN DEFAULT 1,
    is_builtin BOOLEAN DEFAULT 0,
    permissions TEXT,
    tags TEXT,
    min_platform_version TEXT,
    installed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE module_settings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    module_id TEXT NOT NULL,
    setting_key TEXT NOT NULL,
    setting_value TEXT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(module_id, setting_key),
    FOREIGN KEY (module_id) REFERENCES module_registry(module_id) ON DELETE CASCADE
);

CREATE TABLE module_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    module_id TEXT NOT NULL,
    session_name TEXT,
    session_state TEXT,
    is_last_active BOOLEAN DEFAULT 0,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (module_id) REFERENCES module_registry(module_id) ON DELETE CASCADE
);

CREATE TABLE workspace_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    module_id TEXT NOT NULL,
    title TEXT,
    pinned BOOLEAN DEFAULT 0,
    sort_order INTEGER DEFAULT 0,
    metadata_json TEXT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (module_id) REFERENCES module_registry(module_id) ON DELETE CASCADE
);

CREATE TABLE app_settings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    setting_key TEXT NOT NULL UNIQUE,
    setting_value TEXT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE activity_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    module_id TEXT,
    activity_type TEXT NOT NULL,
    message TEXT,
    metadata_json TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE installed_artifacts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    artifact_type TEXT NOT NULL CHECK(artifact_type IN ('MODULE', 'TEMPLATE', 'ASSET')),
    artifact_name TEXT NOT NULL,
    artifact_version TEXT,
    artifact_path TEXT NOT NULL,
    checksum TEXT,
    installed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 8.3. Giải thích dữ liệu cốt lõi

| Trường | Ý nghĩa |
|---|---|
| module_registry.permissions | JSON string chứa danh sách permission |
| module_settings.setting_value | Giá trị cấu hình từng module dưới dạng text hoặc JSON |
| module_sessions.session_state | JSON state của phiên gần nhất |
| workspace_items.metadata_json | Metadata cho pin, quick launch, layout hoặc grouping |
| activity_logs.metadata_json | Metadata JSON phục vụ audit nhẹ hoặc debug |

### 8.4. Migration policy

1. Mọi thay đổi schema phải có migration file.
2. Không sửa schema trực tiếp trong DB production local mà không có migration plan.
3. Mọi breaking change phải có “Migration Notes” trong changelog và docs.
4. Nếu thay đổi state format mà ảnh hưởng module cũ, phải ghi rõ compatibility strategy.

---

## 9. UI và UX pattern chính thức

### 9.1. Cấu trúc main window

```text
┌──────────────────────────────────────────────────────────────────────┐
│ Integrated Interactive Module Platform          [ _ ][ □ ][ X ]     │
├────────────────┬─────────────────────────────────────────────────────┤
│ Dashboard      │ Toolbar theo module hiện tại                       │
│ Module Library │─────────────────────────────────────────────────────│
│ Workspace      │                                                     │
│ Manager        │      Module Host Frame                              │
│ Activity       │      Vùng hiển thị module                           │
│ Settings       │                                                     │
│                │                                                     │
├────────────────┴─────────────────────────────────────────────────────┤
│ Status: Ready | Modules: 2 loaded | DB: OK | Theme: Light           │
└──────────────────────────────────────────────────────────────────────┘
```

### 9.2. Màn hình thư viện module bắt buộc có

1. Danh sách module dạng card hoặc list
2. Tên, icon, category, version, mô tả ngắn
3. Trạng thái enabled hoặc disabled
4. Nút mở module
5. Nút xem chi tiết
6. Bộ lọc theo category
7. Tìm kiếm theo tên hoặc tag

### 9.3. Màn hình quản lý module bắt buộc có

1. Danh sách module cài sẵn và module cài thêm
2. Bật và tắt module
3. Gỡ module
4. Xem path cài đặt
5. Xem permissions
6. Xem version và compatibility status

### 9.4. Quy tắc UX bắt buộc

1. Thao tác dài như cài module, import module, backup, export phải có progress indicator nếu đủ dài.
2. Không block UI thread bằng xử lý nặng.
3. Mọi lỗi phải có thông báo dễ hiểu.
4. Module khi load thất bại phải hiển thị fallback view rõ ràng.
5. Chuyển module phải mượt và không làm shell bị chớp hoặc reset không cần thiết.
6. Module phải có khoảng trắng, padding và layout nhất quán với shell.
7. Theme switch phải ảnh hưởng cả shell và module nếu module dùng shared style hooks.

---

## 10. Quy tắc phát triển cho AI Agent

### 10.1. Coding standards

1. Tuân thủ PEP 8.
2. Bắt buộc dùng type hints.
3. Bắt buộc có docstring cho class và function public.
4. Mỗi file chỉ nên có một trách nhiệm chính.
5. Max line length đề xuất là 100.
6. Bắt buộc tách interface, service, persistence và UI rõ ràng.

### 10.2. Architecture standards

1. UI shell chỉ gọi service layer hoặc runtime layer, không gọi thẳng DB trong view.
2. `BaseModule` là contract chung, không được tạo nhiều biến thể tùy hứng trong v1.0.
3. Mọi enum và constants phải đặt trong `core/utils/constants.py`.
4. Không copy logic load hoặc validate module ở nhiều nơi; phải tập trung tại runtime.
5. Không để module phụ thuộc trực tiếp vào nhau.
6. Không để shell biết chi tiết đặc thù nghiệp vụ của từng module.
7. Mọi thay đổi contract module phải cập nhật file này.

### 10.3. Testing requirements

| Loại test | Bắt buộc cho v1.0 |
|---|---|
| Unit tests cho manifest validation | Có |
| Unit tests cho module loader | Có |
| Unit tests cho state serialization | Có |
| Integration tests cho discovery đến activation | Có |
| UI tests cho main shell và module host | Có |
| Coverage target | Tối thiểu 80% cho phần core và module runtime |

### 10.4. Error handling

1. Không được `except Exception` rồi bỏ qua im lặng.
2. Mọi lỗi manifest phải chỉ rõ file và trường sai.
3. Mọi lỗi DB phải rollback transaction.
4. Mọi lỗi khi load module phải được log rõ ràng và không làm app crash toàn cục nếu có thể tránh.
5. Mọi lỗi serialize state phải có fallback rõ ràng.

### 10.5. Logging policy

Bắt buộc log các nhóm sự kiện sau:

1. App start và shutdown
2. Module discovery start và finish
3. Module install, enable, disable, uninstall
4. Module activation và deactivation
5. State save và restore lỗi nghiêm trọng
6. Migration DB
7. Warning và error

### 10.6. Definition of Done bắt buộc

Một task chỉ được xem là hoàn thành khi thỏa tất cả điều kiện sau:

1. Code chạy được
2. Không phá hành vi hiện có
3. Có test phù hợp
4. Test pass
5. Có cập nhật ROADMAP
6. Có cập nhật CHANGELOG trong file này
7. Nếu thay đổi hiển thị hoặc hành vi người dùng thì phải cập nhật README hoặc docs liên quan

---

## 11. Kế hoạch đóng gói và phát hành

### 11.1. Mục tiêu phát hành v1.0

1. Windows là nền tảng ưu tiên đầu tiên.
2. Có file `.exe` hoặc installer hoàn chỉnh.
3. Có thư mục dữ liệu local được khởi tạo tự động.
4. Có sẵn tối thiểu 2 module first-party.
5. Có tài liệu hướng dẫn tạo module cơ bản.

### 11.2. Công cụ đóng gói

1. PyInstaller cho build standalone
2. Inno Setup cho installer Windows

### 11.3. Ràng buộc phát hành

1. Không phát hành nếu module loader còn gây crash toàn app khi manifest lỗi.
2. Không phát hành nếu registry hoặc state migration chưa được kiểm tra.
3. Không phát hành nếu shell không hiển thị được fallback khi module load thất bại.
4. Không phát hành nếu module mẫu đầu tiên chưa đạt chuẩn contract và UX tối thiểu.

---

## 12. Checklist bắt buộc trước khi AI Agent code

- [ ] Đã đọc file này từ đầu đến cuối
- [ ] Đã đọc IIMP_ROADMAP.md
- [ ] Hiểu rõ ranh giới giữa shell, runtime, services và modules
- [ ] Hiểu rõ chuẩn manifest và BaseModule
- [ ] Không thay đổi contract khi chưa cập nhật tài liệu
- [ ] Có kế hoạch test cho task sắp làm
- [ ] Biết file nào sẽ bị tác động
- [ ] Biết có cần migration hay không
- [ ] Nếu module mới thuộc dạng phức tạp (§20.2 trong IIMP_MODULE_SDK.md): đã đọc Module Design Document `module_<id>.md` và xác nhận compliance trước khi bắt đầu code

### Checklist thiết kế (Design Philosophy — §2.3)

Trước khi gửi PR hoặc đánh dấu task hoàn thành, kiểm tra:

- [ ] **Deep module**: Class/method mới có interface đơn giản hơn implementation không? Nếu interface phức tạp hơn cần thiết, hãy gộp hoặc ẩn bớt.
- [ ] **Information hiding**: Caller có cần biết chi tiết implementation không? Nếu có, hãy che khuất vào service layer.
- [ ] **No pass-through**: Không có method nào chỉ forward sang method khác với signature giống hệt.
- [ ] **Pull complexity down**: Logic phức tạp đã được đẩy xuống tầng dưới, caller không phải tự xử lý rollback hay sync.
- [ ] **Error handling**: Exception không bị nuốt im lặng; lỗi được xử lý ở tầng phù hợp nhất, không float lên quá cao.
- [ ] **Naming**: Tên mới có chính xác và nhất quán với convention hiện tại không?
- [ ] **Obvious code**: Không có magic string/int; không có luồng điều khiển khó theo dõi mà không có comment.
- [ ] **Comments**: Public interface có docstring mô tả contract? Cross-layer decision có inline comment giải thích lý do?
- [ ] **Strategic**: Có cơ hội cải thiện design ở vùng lân cận không? Nếu có, đã làm hoặc ghi nhận để làm sau?

---

## 13. CHANGELOG

Quy tắc ghi chú:

1. Format: `YYYY-MM-DD | [Agent] | [Category] | Description`
2. Categories: ADDED, CHANGED, FIXED, REMOVED, DEPRECATED
3. Nếu có thay đổi schema, phải ghi thêm dòng “Migration Notes”

### 2026-03-24

ADDED | OpenAI GPT-5.4 Thinking | INITIAL | Khởi tạo tài liệu kiến trúc chuẩn cho Integrated Interactive Module Platform. Xác lập mô hình shell app và module, chuẩn manifest, BaseModule contract, module lifecycle, tech stack, database schema, UX pattern, coding standards, testing requirements và quy tắc bắt buộc cho AI Agent.

ADDED | OpenAI GPT-5.4 Thinking | REFERENCE_MODULE | Xác lập module mô phỏng phân phối chuẩn là một reference module first-party cho định hướng v1.0, dùng để định nghĩa cách nền tảng host một mô-đun tính toán và trực quan hóa trong cùng một giao diện thống nhất.

### 2026-07-14

ADDED | GitHub Copilot (Claude Sonnet 4.6) | FOUNDATION | Triển khai toàn bộ Phase 1 Foundation và Phase 2 Module Runtime trong một sprint. Các file đã tạo:

- `config/`: paths.py, settings.py, database.py
- `core/utils/`: constants.py (ModuleState, ArtifactType, PermissionType, ActivityType enums), exceptions.py, logger.py, helpers.py, validators.py
- `core/storage/`: models.py (7 ORM tables: module_registry, module_settings, module_sessions, workspace_items, app_settings, activity_logs, installed_artifacts), connection.py, session.py, migrations/env.py
- `core/app_kernel/`: bootstrap.py, startup_checks.py, lifecycle.py, shutdown_manager.py
- `core/module_runtime/`: base_module.py, manifest_schema.py, loader.py, module_context.py, registry.py, discovery.py, event_bus.py, state_manager.py, sandbox_policy.py
- `core/services/`: module_service.py, settings_service.py, activity_service.py, export_service.py, path_service.py, ui_services.py, permission_service.py, workspace_service.py
- `ui/`: main_window.py, 6 views (dashboard, module_library, workspace, module_manager, activity_history, settings), widgets (module_host_frame, status_strip, module_card), styles (qss_styles.py, themes.py)
- `tests/`: conftest.py, unit/ (test_manifest_validation, test_helpers_validators, test_registry), integration/ (test_discovery)
- `main.py`: application entry point

ADDED | GitHub Copilot (Claude Sonnet 4.6) | MODULE_TEMPLATE | Tạo `modules/templates/starter_module/` — template chuẩn cho developer module mới. Bao gồm: module.json, entry.py, module.py (StarterModule), README.md.

ADDED | GitHub Copilot (Claude Sonnet 4.6) | REFERENCE_MODULE_IMPL | Triển khai `modules/statistics/normal_distribution/` — reference module đầu tiên, port từ C4_Mo_phong_phan_phoi_chuan.py. Bao gồm: module.json, entry.py, module.py (NormalDistributionModule +_DistributionCanvas), README.md, tests/ (test_manifest.py, test_calculator.py, test_smoke_ui.py). Module hỗ trợ: 2 chế độ nhập (α/z), Qt-embedded matplotlib canvas, export PNG, state persistence.

DECISION | GitHub Copilot (Claude Sonnet 4.6) | MANIFEST_FILENAME | Dùng `module.json` (không phải `manifest.json`) theo SDK §4. SDK lấy precedence khi có mâu thuẫn với phần mô tả architecture §5.4.

DECISION | GitHub Copilot (Claude Sonnet 4.6) | BUILD_VIEW | Dùng `build_view()` (không phải `create_widget()`) theo chuẩn trong SDK §6.2 — chi tiết và rõ ràng hơn phần mô tả quy trình trong architecture.

### 2026-07-15

ADDED | GitHub Copilot (Claude Sonnet 4.6) | PHASE3_FULL_UI | Hoàn thành Phase 3 Unified UI and Workspace — 100%. Toàn bộ views đã được implement đầy đủ:

- `ui/views/dashboard_view.py`: Real DB stats (total / enabled / disabled module counts từ `module_registry`) + activity feed (20 bản ghi gần nhất từ `activity_logs`). Stat cards color-coded, dot indicators cho từng loại sự kiện.
- `ui/views/module_manager_view.py`: `_ModuleRow` widget per module (info block, state badge, Bật/Tắt, Gỡ). `ModuleManagerView` với scrollable list + install-local + refresh buttons. DI qua `set_services(registry, module_service)`. Confirmation dialogs cho disable/uninstall.
- `ui/views/activity_history_view.py`: `QTableWidget` 4 cột, `QComboBox` filter 15 loại event, query 200 records, color-coded event types. QColor imported properly.
- `ui/views/settings_view.py`: 5 sections (Giao diện, Logging, Hành vi module, Đường dẫn, Thông tin). DI qua `set_settings_service(svc)`. Keys: `app.theme`, `app.log_level`, `app.max_recent_items`, `app.restore_module_state`.
- `ui/main_window.py`: `_navigate()` gọi `view.refresh()` nếu view có method đó — Dashboard và ActivityHistory tự refresh khi navigate tới.

ADDED | GitHub Copilot (Claude Sonnet 4.6) | PHASE5_PERSISTENCE | Hoàn thành Phase 5 Persistence and Module Manager — 90%. Các thành phần đã implement:

- `core/services/module_service.py`: Thêm `enable_module()`, `disable_module()`, `uninstall_module()`, `install_local_module()`. Mỗi method đều log activity event tương ứng. Uninstall cascade xoá settings + sessions trong DB.
- `core/module_runtime/registry.py`: Thêm `unregister(module_id)` để xoá record khỏi in-memory registry.
- `main.py`: `settings_service` đã được pass vào `MainWindow` constructor. `APP_START` và `APP_SHUTDOWN` activity logs đã được ghi.
- Còn open: `workspace_items` support (pin/quick-launch), backup/restore DB.

### 2026-07-15 (cont.)

ADDED | GitHub Copilot (Claude Sonnet 4.6) | MODULE_V2 | Nâng cấp `modules/statistics/normal_distribution/` lên v2.0.0:

- `module.py`: Rewrite toàn bộ. `_DistributionCanvas` → `_NormalCurveCanvas` với 3 rendering methods. 3 tab độc lập trong QTabWidget.
- Tab 1 "Phân phối N(μ,σ)": Bell curve với dải 68-95-99,7%, đường tham chiếu μ±kσ. Hỗ trợ μ và σ tùy ý.
- Tab 2 "α → Z/X": Static method `_compute_alpha_to_z(mu, sigma, alpha_l, alpha_r)`. Tính z tới hạn và X tới hạn = μ + σ×z.
- Tab 3 "Z/X → α": Static method `_compute_z_to_alpha(mu, sigma, val_l, val_r, input_mode)`. Radio button chuyển giữa Z và X, tự chuyển đổi giá trị spinbox.
- `module.json`: version 1.0.0 → 2.0.0, data_contract_version 2.0.0, default precision 3 → 4.
- `tests/test_calculator.py`: Rewrite hoàn toàn, 9 test cases cho 2 static methods.
- `tests/test_smoke_ui.py`: Thêm 3 test: tab count, state round-trip, lifecycle.

---

### 2026-07-16

FIXED | GitHub Copilot (Claude Sonnet 4.6) | PARSE_VERSION_BUG | `core/utils/helpers.py` — `parse_version()` silently returned empty tuple for non-version strings like `"abc"` (filter `p.isdigit()` removed non-digit parts without raising). Fixed: use `int(p)` for all non-empty parts; raise `ValueError` if result is empty. All existing parse tests now pass. Fixes 2 previously failing unit tests: `TestParseVersion::test_invalid_raises` and `test_manifest_validation::test_invalid_version_raises`.

ADDED | GitHub Copilot (Claude Sonnet 4.6) | PHASE4_DOCS | Phase 4 — `docs/module_sdk.md` tạo mới:

- Hướng dẫn step-by-step cho developer (và AI Agent) tạo module mới từ starter template
- Bao gồm: folder structure, module.json spec, BaseModule contract, test patterns (manifest/calculator/smoke), state persistence, export, host services, headless test guard, checklist trước tích hợp, lỗi thường gặp
- Phase 4 nâng lên 70%

ADDED | GitHub Copilot (Claude Sonnet 4.6) | PHASE5_WORKSPACE_ITEMS | Phase 5 — `core/services/workspace_service.py` triển khai đầy đủ WorkspaceItem CRUD:

- Giữ lại `active_module_id` / `set_active()` từ stub cũ
- Thêm `WorkspaceItemData` dataclass (không leak ORM object ra ngoài service)
- Thêm: `get_all_items()`, `get_pinned_items()`, `add_item()`, `remove_item()`, `set_pinned()`, `reorder()`, `is_pinned()`
- `add_item()` idempotent (không tạo duplicate), `set_pinned()` tự tạo item nếu chưa có
- `tests/unit/test_workspace_service.py`: 15 unit tests, in-memory SQLite fixture với monkeypatch SessionFactory, FK enforcement bật
- Phase 5 nâng lên 100%; backup/restore DB chuyển sang Deferred

---

### 2026-07-17 — Phase 6: Testing, Packaging, Release

ADDED | GitHub Copilot (Claude Sonnet 4.6) | PHASE6_TESTING | Phase 6 — Test infrastructure hoàn thành. Chi tiết:

- **Coverage**: core/ đạt 91% (189 tests, 0 failures) — vượt target ≥ 80%.
- **New test files — unit**: `test_event_bus.py` (9), `test_sandbox_policy.py` (6), `test_permission_service.py` (5), `test_module_context.py` (5), `test_shutdown_manager.py` (5), `test_startup_checks.py` (6), `test_exceptions.py` (12), `test_path_service.py` (5), `test_logger.py` (3). `test_helpers_validators.py` mở rộng thêm coverage cho `truncate()`, `validate_permissions()`, error paths.
- **New test files — integration**: `conftest.py` (db_factory fixture với StaticPool + FK ON), `test_settings_service.py` (11), `test_activity_service.py` (5), `test_state_manager.py` (8), `test_loader.py` (9), `test_runtime_regression.py` (10), `test_connection.py` (2), `test_session.py` (2), `test_export_service.py` (3), `test_module_service.py` (20+).
- **Test patterns confirmed**: in-memory SQLite với `StaticPool`; FK seed helpers với explicit `session.commit()`; post-class-creation attribute assignment cho mock class bodies.

ADDED | GitHub Copilot (Claude Sonnet 4.6) | PHASE6_HEADLESS_MODULE | Tạo `modules/templates/headless_test_module/` — module không có dependency PySide6. Dùng trong loader integration tests để kiểm tra pipeline load/instantiate trong môi trường headless (CI, test không có display).

FIXED | GitHub Copilot (Claude Sonnet 4.6) | EXPORT_SERVICE_IMPORT | `core/services/export_service.py` — guard PySide6 import với try/except (tương tự pattern trong `base_module.py`). Cho phép import ExportService trong môi trường headless; `ask_save_path()` vẫn chỉ hoạt động khi có Qt.

FIXED | GitHub Copilot (Claude Sonnet 4.6) | MODULE_SERVICE_DEAD_IMPORT | `core/services/module_service.py::install_local_module()` — xoá dòng `from core.module_runtime.discovery import _try_load_manifest` (dead import, hàm không tồn tại). Không ảnh hưởng behaviour.

ADDED | GitHub Copilot (Claude Sonnet 4.6) | PHASE6_PACKAGING | Tạo `iimp.spec` — PyInstaller one-directory build config cho Windows:

- Entry point: `main.py`
- Data includes: `modules/`, `config/`, `alembic.ini`, `.env.example`, `ui/styles/`
- Hidden imports: SQLAlchemy SQLite dialect, PySide6 sub-packages, matplotlib Qt backends, numpy/pandas/scipy, loguru, pydantic, alembic runtime
- `console=False` cho production build (không mở terminal)
- `upx=True` cho binary compression

ADDED | GitHub Copilot (Claude Sonnet 4.6) | PHASE6_DOCS | Tạo tài liệu người dùng:

- `docs/quickstart.md`: Hướng dẫn cài đặt, first run, tổng quan UI, mở module, install module, export, settings, phím tắt, troubleshooting.
- `docs/release_checklist.md`: Release checklist v1.0 với 7 sections (Code Quality, Documentation, Module Integrity, Platform Behaviour, Build & Packaging, Security, Final Sign-off).

---

END OF ARCHITECTURE DOCUMENT

Last Updated: 2026-04-12
Version: 1.0.0-rc2

### 2026-04-12

ADDED | GitHub Copilot (Claude Sonnet 4.6) | MODULE_DESIGN_DOC_STANDARD | Bổ sung quy chuẩn Module Design Document vào hệ sinh thái tài liệu IIMP:
- IIMP_MODULE_SDK.md §20.2: định nghĩa bắt buộc tạo `module_<id>.md` cho module phức tạp (nhiều tab, nhiều phương pháp tính toán, animation, import dữ liệu)
- IIMP_MODULE_SDK.md §21: bổ sung DoD #11 — module phức tạp phải có Design Document trước khi code
- IIMP_MODULE_SDK.md §22: cập nhật prompt khởi đầu — bắt buộc đọc `module_<id>.md` như nguồn chân lý thứ hai
- IIMP_ARCHITECTURE.md §12: bổ sung mục checklist — AI Agent phải xác nhận compliance Design Document trước khi bắt đầu code
- Tài liệu mẫu: `module_supply_chain_forecasting.md` v2.0.0 là instance đầu tiên tuân thủ chuẩn này

### 2026-05-05

ADDED | GitHub Copilot (Claude Sonnet 4.6) | DESIGN_PHILOSOPHY | Tích hợp triết lý thiết kế phần mềm (A Philosophy of Software Design — Ousterhout) vào tài liệu nền tảng:
- IIMP_ARCHITECTURE.md §2.3: Bổ sung 8 nguyên tắc bắt buộc với quy tắc cụ thể cho từng layer (Strategic Programming, Deep Modules, Information Hiding, Pull Complexity Down, Define Errors Out, Naming, Obvious Code, Comments).
- IIMP_ARCHITECTURE.md §12: Bổ sung Design Philosophy Checklist — 9 mục kiểm tra thiết kế bắt buộc trước mỗi PR.
- IIMP_MODULE_SDK.md §2.3: Bổ sung hướng dẫn triết lý thiết kế cho module developer — deep interface, information hiding, comment-first, error handling, naming consistency.
- IIMP_MODULE_SDK.md §16: Bổ sung chuẩn tài liệu hóa module (interface docstring, state contract, error contract).
- IIMP_ROADMAP.md: Bổ sung nguyên tắc quản lý technical debt và quy trình design review.
- README.md: Bổ sung tham chiếu đến triết lý thiết kế.
- Áp dụng thực tế các nguyên tắc này: AppServices dataclass (Ch.7), _persist_enabled_flag (Ch.5), ShutdownManager.connect_to_app (Ch.4), required services (Ch.8), _NavIndex enum (Ch.14/18), interface docstrings (Ch.13).
