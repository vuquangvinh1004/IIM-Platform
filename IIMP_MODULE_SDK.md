# INTEGRATED INTERACTIVE MODULE PLATFORM MODULE SDK

> QUAN TRỌNG CHO AI AGENT
>
> File này là bộ chuẩn chính thức để thiết kế, phát triển, kiểm thử, đóng gói và bảo trì module cho dự án Integrated Interactive Module Platform.
>
> AI Agent bắt buộc phải đọc và tuân thủ file này trước khi:
>
> 1. Tạo module mới
> 2. Sửa, refactor hoặc mở rộng module hiện có
> 3. Thay đổi `module.json`, `entry.py`, `BaseModule` hoặc contract lifecycle
> 4. Thêm service mới vào module context
> 5. Thêm quyền truy cập mới cho module
> 6. Thay đổi chuẩn state, settings, export hoặc event payload
>
> File này phải được dùng cùng với:
>
> 1. `IIMP_ARCHITECTURE.md`
> 2. `IIMP_ROADMAP.md`
>
> Nếu có xung đột giữa các file, thứ tự ưu tiên là:
>
> 1. `IIMP_ARCHITECTURE.md`
> 2. `IIMP_MODULE_SDK.md`
> 3. `IIMP_ROADMAP.md`
>
> Mọi thay đổi về chuẩn module phải được cập nhật ngay vào phần CHANGELOG ở cuối file này.

---

## 1. Mục đích của Module SDK

### 1.1. Mục đích

Module SDK định nghĩa bộ quy chuẩn tối thiểu và chính thức để mọi module trong Integrated Interactive Module Platform có thể:

1. Được shell phát hiện và nạp đúng cách
2. Hiển thị trong giao diện thống nhất của ứng dụng
3. Tương tác an toàn với host app thông qua context và service được cấp phép
4. Lưu trạng thái, cấu hình và dữ liệu tạm nhất quán
5. Có thể kiểm thử, đóng gói, bảo trì và nâng cấp lâu dài

### 1.2. Mục tiêu của SDK

| Mục tiêu | Diễn giải |
|---|---|
| Chuẩn hóa module | Mọi module phải theo cùng một contract kỹ thuật |
| Tăng khả năng mở rộng | Có thể thêm module mới mà không làm rối kiến trúc shell |
| Giảm coupling | Module không phụ thuộc trực tiếp vào nội bộ của shell hoặc module khác |
| Tăng khả năng tái sử dụng | Có thể dùng lại template, test pattern và service pattern |
| Bảo đảm chất lượng | Mỗi module đều có chuẩn tối thiểu về UI, state, error handling và testing |
| Hỗ trợ AI Agent | AI Agent có thể tạo module mới một cách nhất quán, không lệch chuẩn |

### 1.3. Module là gì

Trong dự án này, module là một đơn vị chức năng độc lập, được đóng gói theo một cấu trúc tiêu chuẩn, có manifest mô tả metadata, có entry point rõ ràng, có lớp runtime chính kế thừa từ `BaseModule`, và có thể được Shell App phát hiện, xác thực, load, activate, render, deactivate và unload.

Module có thể là:

1. Mô phỏng xác suất, thống kê, vật lý hoặc logic
2. Công cụ trực quan hóa dữ liệu hoặc hình học
3. Bảng tra cứu có thao tác kéo thả, tô sáng hoặc lọc
4. Công cụ 2D hoặc 3D có tương tác cơ bản
5. Mini tool học thuật, kỹ thuật hoặc chuyên môn
6. Công cụ export hình, bảng hoặc dữ liệu cục bộ

Ví dụ điển hình: module mô phỏng phân phối chuẩn cho phép người dùng nhập diện tích đuôi hoặc giá trị Z, vẽ đường cong chuẩn, tô vùng xác suất và xuất hình minh họa.

---

## 2. Các nguyên tắc bắt buộc khi phát triển module

### 2.1. Nguyên tắc chung

| Nguyên tắc | Nội dung |
|---|---|
| Contract first | Mọi module phải tuân thủ `module.json` và `BaseModule` trước khi viết logic UI |
| Hosted, not standalone | Module mặc định chạy bên trong shell, không tự tạo main window độc lập |
| Local first | Module phải hoạt động với dữ liệu cục bộ nếu thuộc phạm vi v1.0 |
| Safe by default | Module chỉ dùng service được cấp qua context, không truy cập bừa bãi tài nguyên hệ thống |
| Unified UX | Giao diện module phải có cảm giác cùng một sản phẩm |
| Graceful failure | Lỗi module không được làm sập shell toàn cục |
| Observable | Module phải có logging và error reporting tối thiểu |
| Serializable state | State quan trọng phải có khả năng lưu và phục hồi nếu module công bố hỗ trợ session restore |
| Testable | Module phải đủ tách biệt để test logic và UI ở mức tối thiểu |

### 2.2. Những điều AI Agent không được làm khi viết module

1. Không bypass `module.json` để hardcode metadata trong shell
2. Không import trực tiếp code nội bộ của shell ngoài các API công bố trong SDK
3. Không ghi thẳng vào database lõi bằng truy vấn tự phát nếu chưa có repository hoặc service được phép
4. Không tự ghi file ra thư mục bất kỳ ngoài các đường dẫn do host cấp
5. Không mở nhiều cửa sổ riêng làm phá vỡ trải nghiệm shell, trừ khi kiến trúc file này cập nhật cho phép
6. Không tự tạo thread hoặc process dài hạn mà không có cleanup rõ ràng
7. Không chèn dependency nặng vào toàn app chỉ để phục vụ một module hẹp mà chưa được phê duyệt
8. Không định nghĩa event payload tùy tiện mà không ghi rõ schema hoặc contract
9. Không lưu state theo định dạng không version hóa nếu state đó cần phục hồi lâu dài
10. Không dùng network call trong luồng cốt lõi của module v1.0 trừ khi được phê duyệt chính thức
11. Không để module import chéo lẫn nhau để gọi trực tiếp logic nội bộ
12. Không đánh dấu module là “production ready” nếu chưa có manifest hợp lệ, error handling và smoke test

---
### 2.3. Triết lý thiết kế module

> Tài liệu tham khảo: `philosophy_of_software_design.md` và §2.3 trong `IIMP_ARCHITECTURE.md`.
>
> Các nguyên tắc dưới đây áp dụng trực tiếp cho việc thiết kế và phát triển module. Chúng bổ sung cho các nguyên tắc tổng thể đã nêu trong ARCHITECTURE.

#### 2.3.1. Module phải "sâu" (Deep Module Design) — Ch. 4

Module tốt có **interface đơn giản** và **implementation phức tạp ẩn bên trong**. Người dùng module (và shell) không cần biết module tính toán thế nào — chỉ cần biết cách gọi.

**Hướng dẫn cụ thể:**

| Nguyên tắc | Ví dụ đúng | Ví dụ sai |
|---|---|---|
| Ẩn logic tính toán sau service nội bộ | `calculator.py` tách khỏi widget | Widget tự tính toán trực tiếp trong `clicked()` handler |
| Ẩn định dạng state sau `get_state()` / `restore_state()` | Module tự serialize/deserialize | Shell phải biết cấu trúc dict của từng module |
| Interface `build_view()` luôn trả về một `QWidget` sạch | Một root widget chứa tất cả | Nhiều phương thức để shell lắp ghép từng phần |
| Không để caller phải chuẩn bị nhiều bước trước khi dùng module | `on_load()` tự khởi tạo mọi thứ | Caller phải gọi `init_a()`, `init_b()`, rồi `load()` |

#### 2.3.2. Ẩn thông tin trong module (Information Hiding) — Ch. 5

Các lớp bên trong module không được leak chi tiết lên view hoặc ra ngoài qua `ModuleContext`.

**Hướng dẫn cụ thể:**

| Nguyên tắc | Áp dụng |
|---|---|
| `services/calculator.py` không được import từ `ui/` | Tách hoàn toàn logic và UI trong module |
| `models/state.py` không được biết về định dạng DB của shell | State chỉ là dataclass thuần Python, không phụ thuộc ORM |
| View không được biết thuật toán tính toán | View gọi `calculator.compute(inputs)` → nhận kết quả, không biết bên trong làm gì |
| Nếu hai widget cùng cần một dữ liệu, đặt dữ liệu đó vào model/service — không truyền qua tham số widget | Tránh temporal decomposition |

#### 2.3.3. Xử lý lỗi trong module (Error Handling) — Ch. 10

Module không được để exception bay ra ngoài ranh giới `BaseModule`. Shell không biết (và không cần biết) cách xử lý lỗi nội bộ của từng module.

**Hướng dẫn cụ thể:**

| Nguyên tắc | Áp dụng |
|---|---|
| `on_load()`, `on_activate()`, `on_deactivate()`, `on_unload()` phải catch mọi exception nội bộ | Log và degrade gracefully |
| Khi tính toán thất bại, hiển thị thông báo lỗi trong view của module, không raise lên shell | View có trạng thái "error state" riêng |
| Không định nghĩa exception tùy tiện chỉ để throw ngay lập tức rồi catch ở chính nơi throw | Xử lý trực tiếp thay vì dùng exception như flow control |
| `restore_state()` phải tolerate dữ liệu cũ hoặc thiếu key — không crash khi gặp state schema cũ | Backward-compatible state restore |

#### 2.3.4. Viết docstring trước khi viết code (Comment-First) — Ch. 15

Docstring của `on_load()`, `build_view()`, `get_state()`, `get_settings_schema()` và `export()` phải được viết **trước khi** implement. Nếu không thể viết docstring rõ ràng, design chưa đủ chín.

**Các comment bắt buộc:**

| Thành phần | Nội dung comment bắt buộc |
|---|---|
| Class kế thừa `BaseModule` | Mô tả module làm gì, audience là ai, dependency nào cần inject |
| `on_load()` | Các resource nào được khởi tạo; exception nào có thể xảy ra và cách handle |
| `get_state()` | Danh sách key trả về, ý nghĩa từng key, giá trị `_state_version` |
| `restore_state()` | Cách handle missing key, version cũ, invalid value |
| `get_settings_schema()` | Cấu trúc settings, kiểu dữ liệu, giá trị mặc định và ý nghĩa |
| Method tính toán phức tạp | Tham chiếu công thức hoặc thuật toán; không giải thích lại code |

#### 2.3.5. Đặt tên nhất quán trong module (Naming Consistency) — Ch. 14 & 17

Tên trong module phải nhất quán với convention của toàn nền tảng và nhất quán nội bộ trong chính module.

**Quy tắc:**

| Quy tắc | Ví dụ đúng | Ví dụ sai |
|---|---|---|
| Input model dùng `inputs.py` / `InputData` | `class InputData` | `class FormData`, `class Params`, `class Config` (lẫn lộn) |
| Output model dùng `outputs.py` / `OutputData` hoặc `Result` | `class ComputeResult` | Trả về dict vô danh |
| View class kết thúc bằng `View` | `DistributionView` | `DistPanel`, `DistWidget` (không nhất quán) |
| Service class kết thúc bằng `Service` hoặc rõ ràng là noun | `Calculator`, `Exporter` | `do_compute`, `helper` |
| Signal tên theo sự kiện đã xảy ra (past tense hoặc noun) | `result_ready`, `export_completed` | `calculate`, `doExport` |

---
## 3. Năng lực và giới hạn của Module SDK v1.0

### 3.1. SDK v1.0 bảo đảm

1. Module discovery từ thư mục module cục bộ
2. Manifest validation bằng schema chuẩn
3. Entry point loading an toàn có kiểm tra lỗi
4. Lifecycle cơ bản: discover, validate, load, activate, render, deactivate, unload
5. Context được truyền từ host cho module
6. State và settings persistence cơ bản
7. Đăng ký menu action và toolbar action ở mức giới hạn nếu shell hỗ trợ
8. Export file cục bộ qua host file service
9. Logging và activity event cơ bản
10. Compatibility check theo `sdk_version` và `min_platform_version`

### 3.2. SDK v1.0 chưa bảo đảm

1. Sandbox an ninh cấp hệ điều hành
2. Tải module động từ marketplace online
3. Cấp quyền cực chi tiết theo runtime từng lệnh hệ thống
4. Hot reload hoàn chỉnh cho production
5. Multi-user isolation
6. Cloud sync cho module state
7. Cross-module dependency graph phức tạp
8. Hệ visual builder cho module ngay trong UI

---

## 4. Cấu trúc thư mục chuẩn của một module

```text
modules/
└── normal_distribution/
    ├── module.json
    ├── README.md
    ├── CHANGELOG.md
    ├── icon.png
    ├── entry.py
    ├── assets/
    │   ├── screenshots/
    │   └── styles/
    ├── ui/
    │   ├── main_view.py
    │   ├── controls_panel.py
    │   └── result_panel.py
    ├── services/
    │   ├── calculator.py
    │   └── exporter.py
    ├── models/
    │   ├── inputs.py
    │   ├── outputs.py
    │   └── state.py
    ├── tests/
    │   ├── test_manifest.py
    │   ├── test_calculator.py
    │   └── test_smoke_ui.py
    └── __init__.py
```

### 4.1. File bắt buộc

| File | Bắt buộc | Vai trò |
|---|---|---|
| `module.json` | Có | Metadata, compatibility, permissions, entry point |
| `entry.py` | Có | Nơi export module class hoặc factory |
| `README.md` | Có | Mô tả module, cách dùng, giới hạn |
| `__init__.py` | Có | Đánh dấu package Python |

### 4.2. File khuyến nghị mạnh

| File | Mục đích |
|---|---|
| `CHANGELOG.md` | Theo dõi thay đổi theo version |
| `icon.png` | Hiển thị trong module library |
| `models/state.py` | Chuẩn hóa state lưu và restore |
| `tests/` | Bảo đảm chất lượng tối thiểu |
| `assets/` | Chứa tài nguyên cục bộ của module |

---

## 5. Manifest chuẩn: `module.json`

### 5.1. Vai trò

`module.json` là nguồn chân lý cho metadata và compatibility của module. Shell không được giả định metadata từ tên thư mục hay class name nếu manifest không xác nhận điều đó.

### 5.2. Thuộc tính bắt buộc

| Thuộc tính | Kiểu | Bắt buộc | Mô tả |
|---|---|---|---|
| `id` | string | Có | Định danh duy nhất toàn nền tảng, dạng snake_case hoặc kebab-case ổn định |
| `name` | string | Có | Tên hiển thị của module |
| `version` | string | Có | Phiên bản module theo semantic versioning |
| `sdk_version` | string | Có | Phiên bản SDK mà module tuân theo |
| `min_platform_version` | string | Có | Phiên bản nền tảng tối thiểu để module chạy |
| `entry_point` | string | Có | Đường dẫn import tới class hoặc factory |
| `description` | string | Có | Mô tả ngắn cho người dùng |
| `category` | string | Có | Nhóm chức năng của module |
| `author` | string | Có | Tác giả hoặc nhóm phát triển |
| `permissions` | list[string] | Có | Danh sách quyền mà module yêu cầu |
| `tags` | list[string] | Có | Từ khóa tìm kiếm |
| `supports_state_restore` | boolean | Có | Có hỗ trợ phục hồi phiên làm việc hay không |
| `supports_export` | boolean | Có | Có chức năng export cục bộ hay không |

### 5.3. Thuộc tính tùy chọn có kiểm soát

| Thuộc tính | Kiểu | Mô tả |
|---|---|---|
| `icon` | string | Đường dẫn tương đối tới icon |
| `homepage` | string | URL tài liệu hoặc repo nội bộ nếu có |
| `license` | string | Kiểu giấy phép nội bộ hoặc open-source |
| `ui` | object | Gợi ý về kích thước tối thiểu, layout mode |
| `data_contract_version` | string | Version cho state hoặc persisted data |
| `default_settings` | object | Cấu hình mặc định của module |
| `capabilities` | list[string] | Năng lực công bố của module |
| `compatibility_notes` | string | Ghi chú compatibility nếu cần |

### 5.4. Quy tắc đặt `id`

1. Phải ổn định theo thời gian
2. Không dùng ký tự đặc biệt ngoài chữ, số, `_` hoặc `-`
3. Không đổi `id` chỉ vì đổi tên hiển thị
4. Không trùng với module khác, kể cả module đã gỡ nhưng vẫn có record lịch sử

### 5.5. Ví dụ manifest chuẩn

```json
{
  "id": "normal_distribution",
  "name": "Normal Distribution Explorer",
  "version": "1.0.0",
  "sdk_version": "1.0.0",
  "min_platform_version": "1.0.0",
  "entry_point": "modules.normal_distribution.entry:NormalDistributionModule",
  "description": "Mô phỏng phân phối chuẩn, tính diện tích xác suất và giá trị Z, đồng thời trực quan hóa vùng dưới đường cong.",
  "category": "statistics",
  "author": "Internal Team",
  "permissions": [
    "storage.read",
    "storage.write",
    "export.file"
  ],
  "tags": [
    "statistics",
    "normal distribution",
    "z score",
    "probability"
  ],
  "supports_state_restore": true,
  "supports_export": true,
  "icon": "icon.png",
  "data_contract_version": "1.0.0",
  "default_settings": {
    "precision": 3,
    "theme_variant": "default"
  },
  "capabilities": [
    "plot.2d",
    "compute.statistics",
    "export.image"
  ]
}
```

### 5.6. Validation rule tối thiểu

1. Nếu thiếu trường bắt buộc, module không được load
2. Nếu `entry_point` sai, module không được activate
3. Nếu `sdk_version` không tương thích, module phải bị chặn với thông báo rõ ràng
4. Nếu quyền yêu cầu không nằm trong danh sách shell hỗ trợ, module phải bị đánh dấu incompatible hoặc unsupported
5. Nếu `version` hoặc `min_platform_version` không parse được, manifest bị xem là invalid

---

## 6. Entry point và BaseModule contract

### 6.1. Quy ước entry point

`entry_point` phải trỏ tới một class kế thừa `BaseModule` hoặc một factory trả về instance hợp lệ của `BaseModule`.

Ví dụ:

```python
# entry.py
from .module import NormalDistributionModule

__all__ = ["NormalDistributionModule"]
```

### 6.2. Contract tối thiểu của BaseModule

Mỗi module phải cung cấp một lớp chính kế thừa `BaseModule`. Tên lớp không bắt buộc cố định, nhưng hành vi contract là bắt buộc.

```python
from abc import ABC, abstractmethod
from typing import Any
from PySide6.QtWidgets import QWidget

class BaseModule(ABC):
    manifest: dict
    context: Any

    def __init__(self, manifest: dict, context: Any) -> None:
        self.manifest = manifest
        self.context = context

    @abstractmethod
    def on_load(self) -> None:
        ...

    @abstractmethod
    def build_view(self) -> QWidget:
        ...

    @abstractmethod
    def on_activate(self) -> None:
        ...

    @abstractmethod
    def on_deactivate(self) -> None:
        ...

    @abstractmethod
    def on_unload(self) -> None:
        ...

    def get_state(self) -> dict:
        return {}

    def restore_state(self, state: dict) -> None:
        pass

    def get_settings_schema(self) -> dict:
        return {}

    def export(self, target_path: str, export_type: str = "default") -> None:
        raise NotImplementedError
```

### 6.3. Ý nghĩa các phương thức

| Phương thức | Vai trò | Bắt buộc |
|---|---|---|
| `on_load()` | Khởi tạo tài nguyên nhẹ, đăng ký signal nội bộ, chuẩn bị service | Có |
| `build_view()` | Tạo QWidget gốc cho host frame | Có |
| `on_activate()` | Gọi khi module được đưa vào workspace | Có |
| `on_deactivate()` | Gọi khi module rời focus hoặc bị thay module khác | Có |
| `on_unload()` | Cleanup, ngắt signal, dừng worker, giải phóng resource | Có |
| `get_state()` | Trả về state có thể serialize | Không nhưng khuyến nghị mạnh |
| `restore_state()` | Phục hồi state từ dữ liệu đã lưu | Không nhưng khuyến nghị mạnh |
| `get_settings_schema()` | Công bố cấu trúc settings riêng | Không |
| `export()` | Export file nếu module hỗ trợ | Không |

### 6.4. Quy tắc với `build_view()`

1. Phải trả về đúng một `QWidget` root
2. Không được trả về `None`
3. Không được tự mở `show()` như một main window độc lập trong luồng mặc định
4. Không được gắn trực tiếp module view vào shell bằng cách bypass host frame
5. Root view phải chịu được resize và khởi tạo lại nếu shell yêu cầu rebuild

---

## 7. Lifecycle chuẩn của module

### 7.1. Sơ đồ vòng đời

```text
discovered
→ validated
→ loaded
→ view_built
→ activated
→ deactivated
→ reactivated (optional)
→ unloaded
```

### 7.2. Mô tả lifecycle

| Giai đoạn | Mô tả |
|---|---|
| `discovered` | Shell phát hiện thư mục module |
| `validated` | Manifest hợp lệ, compatibility chấp nhận được |
| `loaded` | Entry point import thành công, instance được tạo |
| `view_built` | `build_view()` trả QWidget hợp lệ |
| `activated` | Module được gắn vào workspace và bắt đầu tương tác |
| `deactivated` | Module rời focus nhưng chưa bị hủy hoàn toàn |
| `unloaded` | Module được dọn dẹp và giải phóng khỏi runtime |

### 7.3. Những gì được phép và không được phép theo lifecycle

| Giai đoạn | Được phép | Không được phép |
|---|---|---|
| `on_load()` | Tạo model, bind service, chuẩn bị cache nhẹ | Render widget phức tạp kiểu side effect khó kiểm soát |
| `build_view()` | Tạo UI tree | Chạy tính toán nặng chặn UI quá lâu |
| `on_activate()` | Kết nối signal, refresh dữ liệu, resume worker | Reset state của người dùng nếu không có lý do |
| `on_deactivate()` | Pause timer, save draft state | Hủy toàn bộ resource khi shell chỉ tạm chuyển module |
| `on_unload()` | Cleanup triệt để | Gọi shell internals không qua context |

### 7.4. Cleanup bắt buộc

Trước khi module unload, phải đảm bảo:

1. Timer được dừng
2. Worker thread được stop hoặc join an toàn
3. File handle được đóng
4. Signal được disconnect nếu cần
5. Temporary cache nội bộ được giải phóng hợp lý
6. Không còn callback treo gây reference cycle nghiêm trọng

---

## 8. ModuleContext và Host Services

### 8.1. Nguyên tắc

Module chỉ được tương tác với shell thông qua `ModuleContext` hoặc các interface/service mà shell công bố. Module không được import chéo vào cấu trúc nội bộ của shell để lấy singleton hoặc state toàn cục một cách tự phát.

### 8.2. Cấu trúc khái niệm của `ModuleContext`

```python
class ModuleContext:
    logger: Any
    event_bus: Any
    storage_service: Any
    export_service: Any
    settings_service: Any
    activity_service: Any
    dialog_service: Any
    theme_service: Any
    workspace_service: Any
    path_service: Any
    platform_info: Any
```

### 8.3. Service tối thiểu nên có trong v1.0

| Service | Vai trò |
|---|---|
| `logger` | Ghi log theo module id |
| `event_bus` | Pub-sub event mức app hoặc module |
| `storage_service` | Lưu state và dữ liệu cục bộ của module |
| `settings_service` | Đọc ghi settings của module |
| `export_service` | Mở dialog export hoặc ghi file an toàn |
| `activity_service` | Ghi nhận các hành động quan trọng |
| `dialog_service` | Hiển thị message box, confirm dialog thống nhất |
| `theme_service` | Cấp palette hoặc token UI |
| `path_service` | Cung cấp đường dẫn chuẩn cho data, cache, export |
| `platform_info` | Thông tin phiên bản shell, SDK, OS |

### 8.4. Quy tắc với host services

1. Không giả định service nào tồn tại ngoài danh sách công bố chính thức
2. Không tự monkey patch service của host
3. Không lưu reference sâu vào đối tượng private của shell
4. Không gọi service theo kiểu side effect không kiểm soát trong constructor
5. Nếu service lỗi, module phải degrade gracefully và báo lỗi rõ ràng

---

## 9. Permissions chuẩn

### 9.1. Mục đích

Permissions trong v1.0 chưa phải hệ sandbox cứng, nhưng là cơ chế khai báo năng lực mà module cần để host có thể kiểm tra compatibility, audit và hiển thị minh bạch.

### 9.2. Danh sách quyền chuẩn gợi ý cho v1.0

| Permission | Ý nghĩa |
|---|---|
| `storage.read` | Đọc state hoặc file trong vùng dữ liệu được cấp |
| `storage.write` | Ghi state hoặc dữ liệu cục bộ trong vùng dữ liệu được cấp |
| `settings.read` | Đọc cấu hình module |
| `settings.write` | Ghi cấu hình module |
| `export.file` | Xuất file ra thư mục người dùng chọn |
| `dialogs.basic` | Hiển thị thông báo hoặc hộp xác nhận cơ bản |
| `activity.write` | Ghi nhật ký hoạt động |
| `workspace.control` | Yêu cầu hành vi workspace như refresh host hoặc focus view |
| `clipboard.write` | Ghi dữ liệu ra clipboard nếu shell hỗ trợ |

### 9.3. Quy tắc sử dụng permissions

1. Chỉ khai báo quyền thật sự cần
2. Không yêu cầu `storage.write` nếu module chỉ đọc và hiển thị
3. Nếu module gọi export nhưng manifest không có `export.file`, shell có thể chặn hoặc cảnh báo
4. Quyền không đồng nghĩa với được phép truy cập toàn hệ thống, chỉ là khai báo capability trong phạm vi SDK

---

## 10. Chuẩn UI và trải nghiệm người dùng cho module

### 10.1. Nguyên tắc UI

| Nguyên tắc | Nội dung |
|---|---|
| Embedded first | UI được thiết kế để chạy trong host frame |
| Responsive in desktop sense | Resize được trong phạm vi desktop window |
| Consistent | Dùng token giao diện, spacing, typography của shell nếu có |
| Observable | Trạng thái loading, success, error phải nhìn thấy được |
| Practical | Ưu tiên rõ ràng, dễ hiểu, dễ thao tác hơn là quá phô diễn |

### 10.2. Bố cục đề xuất cho module tương tác

Một module nên chia tối thiểu thành các vùng sau nếu phù hợp:

1. Header: tên module hoặc trạng thái hiện tại
2. Input area: khu nhập tham số, tùy chọn hoặc mode
3. Main canvas/view: vùng minh họa, biểu đồ, bảng hoặc hình tương tác
4. Result area: hiển thị kết quả tính toán, diễn giải hoặc highlight
5. Action area: reset, export, lưu, trợ giúp

### 10.3. Những điều không nên làm trong UI module

1. Không dùng quá nhiều popup chồng nhau
2. Không ẩn logic quan trọng phía sau thao tác khó khám phá
3. Không khóa cứng kích thước UI khiến host resize bị vỡ layout
4. Không để lỗi hiển thị bằng traceback thô cho người dùng cuối
5. Không dùng style quá khác shell nếu host đã có theme system

### 10.4. Hành vi lỗi và trạng thái rỗng

Module phải hiển thị rõ ít nhất ba trạng thái:

1. Ready
2. Error
3. Empty or initial state

Nếu module cần tính toán hoặc load dữ liệu, nên có thêm:

1. Loading
2. Completed

---

## 11. State, settings và persistence

### 11.1. Phân biệt

| Khái niệm | Mục đích | Ví dụ |
|---|---|---|
| State | Trạng thái phiên làm việc có thể phục hồi | Input gần nhất, tab đang mở, mode đang chọn |
| Settings | Cấu hình tương đối ổn định | Số chữ số thập phân, theme variant, default export format |
| Cache | Dữ liệu tạm có thể xóa | Dữ liệu tính toán trung gian, hình render tạm |

### 11.2. Quy tắc lưu state

1. State phải serialize được sang JSON-compatible dict nếu đi theo chuẩn mặc định
2. State nên có version nếu cấu trúc có thể thay đổi
3. Không nhét object Qt hoặc object không serialize được vào state
4. Không lưu dữ liệu quá lớn vào state nếu chỉ cần cache tạm
5. `get_state()` phải trả kết quả nhất quán và không gây side effect

### 11.3. Quy tắc restore state

1. `restore_state()` phải chịu được state thiếu khóa hoặc state cũ hơn
2. Không crash chỉ vì state cũ không tương thích hoàn toàn
3. Nếu state lỗi, module phải fallback về default state và ghi log rõ ràng
4. Nếu `supports_state_restore = false`, shell không được ép module restore

### 11.4. Ví dụ state cho module phân phối chuẩn

```json
{
  "state_version": "1.0.0",
  "mode": "alpha",
  "left_value": 0.05,
  "right_value": 0.025,
  "precision": 3,
  "last_export_format": "png"
}
```

---

## 12. Event bus và trao đổi dữ liệu

### 12.1. Nguyên tắc

Module không nên gọi trực tiếp module khác. Nếu cần phát thông tin ra ngoài hoặc phản ứng với sự kiện mức app, module phải đi qua event bus hoặc service được host công bố.

### 12.2. Quy ước event tối thiểu

| Thành phần | Quy ước |
|---|---|
| Tên event | dạng `module.<module_id>.<action>` hoặc `app.<domain>.<action>` |
| Payload | dict rõ ràng, có khóa ổn định |
| Metadata | nên có timestamp, source module id nếu phù hợp |

### 12.3. Ví dụ event

```python
self.context.event_bus.publish(
    "module.normal_distribution.calculated",
    {
        "mode": "alpha",
        "left_area": 0.05,
        "right_area": 0.025,
        "z_left": -1.645,
        "z_right": 1.96
    }
)
```

### 12.4. Quy tắc event payload

1. Không publish object Qt trực tiếp
2. Không publish payload quá lớn nếu chỉ dùng nội bộ module
3. Nếu payload có versioning riêng, phải ghi trong docs module
4. Không dùng event bus như nơi truyền toàn bộ state liên tục một cách lạm dụng

---

## 13. Logging, error handling và observability

### 13.1. Logging tối thiểu

Module phải log được tối thiểu các mốc sau:

1. on_load thành công hoặc thất bại
2. activate và deactivate
3. export bắt đầu và kết thúc
4. restore state thành công hoặc fallback
5. lỗi tính toán hoặc lỗi dữ liệu đầu vào quan trọng

### 13.2. Mức log khuyến nghị

| Level | Dùng khi |
|---|---|
| `DEBUG` | Thông tin dev, payload gọn, flow nội bộ |
| `INFO` | Mốc hoạt động chính |
| `WARNING` | Dữ liệu chưa hợp lệ nhưng có thể fallback |
| `ERROR` | Thao tác thất bại hoặc module không hoàn thành hành vi chính |

### 13.3. Error handling bắt buộc

1. Lỗi input người dùng phải được diễn giải ngắn gọn, không phơi raw traceback
2. Lỗi runtime phải được log đủ để debug
3. `on_unload()` phải cố cleanup ngay cả khi có lỗi ở bước trước
4. Export lỗi phải thông báo rõ vì sao thất bại nếu host cung cấp được thông tin đó
5. Không dùng `except: pass` để nuốt lỗi im lặng

---

## 14. Hiệu năng và concurrency

### 14.1. Nguyên tắc hiệu năng

1. Module không được block UI thread quá lâu với tính toán nặng
2. Tính toán nhỏ có thể chạy trực tiếp nếu phản hồi tức thì
3. Tính toán nặng phải dùng worker hoặc chiến lược bất đồng bộ phù hợp với Qt
4. Worker phải có cơ chế hủy hoặc cleanup rõ ràng

### 14.2. Khi nào cần worker

Nên cân nhắc worker nếu:

1. Tính toán kéo dài hơn cảm nhận tức thì của người dùng
2. Có render đồ họa phức tạp lặp lại nhiều lần
3. Có thao tác export khối lượng lớn
4. Có pipeline tiền xử lý dữ liệu đáng kể

### 14.3. Không được làm

1. Không tạo thread vô tội vạ
2. Không truy cập widget trực tiếp từ thread nền
3. Không để thread chạy tiếp sau khi module unload
4. Không dùng global mutable state để đồng bộ worker thiếu kiểm soát

---

## 15. Quy chuẩn export

### 15.1. Khi module công bố `supports_export = true`

Module phải làm rõ:

1. Loại export hỗ trợ
2. Định dạng file hỗ trợ
3. Nội dung export là gì
4. Điều kiện dữ liệu cần có để export thành công

### 15.2. Quy tắc export

1. Ưu tiên đi qua `export_service` của host
2. Không ghi đè file người dùng mà không xác nhận nếu host có hỗ trợ confirm
3. Tên file mặc định nên có ý nghĩa và an toàn
4. Export lỗi phải trả thông báo rõ ràng

### 15.3. Ví dụ cho module phân phối chuẩn

Loại export phù hợp:

1. Ảnh biểu đồ PNG
2. Dữ liệu kết quả JSON hoặc CSV nhỏ
3. Snapshot cấu hình hiện tại

---

## 15.5. Chuẩn tài liệu hóa module (Documentation Standard)

> Dựa trên Ch. 13 & 15 — A Philosophy of Software Design.
>
> Tài liệu hóa không phải việc làm sau khi code xong. Nó là công cụ thiết kế: nếu không thể viết docstring rõ ràng cho một API, đó là dấu hiệu API chưa được thiết kế đúng.

### 15.5.1. Docstring bắt buộc

**Class-level docstring** — bắt buộc cho mọi class public trong module:

```python
class NormalDistributionModule(BaseModule):
    """
    Module mô phỏng và trực quan hóa phân phối chuẩn.

    Cho phép người dùng điều chỉnh μ (mean) và σ (std dev) để quan sát
    hình dạng phân phối thay đổi theo thời gian thực.

    Dependency: không có external service nào ngoài AppServices từ shell.
    State: lưu μ, σ và tab đang chọn — tham khảo get_state() để biết schema.
    """
```

**Method-level docstring** — bắt buộc cho các override của BaseModule:

```python
def get_state(self) -> dict:
    """
    Trả về state hiện tại của module để persist vào storage.

    Returns:
        dict với các key:
            _state_version (int): phiên bản schema, hiện tại là 1.
            mu (float): giá trị mean hiện tại, default 0.0.
            sigma (float): giá trị std dev hiện tại, default 1.0.
            active_tab (int): index tab đang hiển thị, default 0.

    Note:
        restore_state() phải backward-compatible với version thấp hơn.
    """
```

### 15.5.2. Những gì không cần comment

| Không cần comment | Lý do |
|---|---|
| `self._mu = mu` | Self-explanatory — tên đã rõ |
| `return self._result` | Trả về field có tên rõ ràng |
| `if value < 0: raise ValueError(...)` | Validation hiển nhiên |
| Import statements | Không có context ẩn |

### 15.5.3. Những gì bắt buộc có comment

| Bắt buộc comment | Lý do |
|---|---|
| Cross-layer side effect (vd: gọi service từ slot) | Không hiển nhiên với người đọc |
| Magic constant hoặc công thức toán học | Cần tham chiếu để review |
| Workaround hoặc TODO có lý do kỹ thuật | Bảo tồn context cho người tiếp theo |
| State version migration logic | Cần giải thích tại sao schema thay đổi |

---

## 16. Kiểm thử module

### 16.1. Mức test tối thiểu cho mọi module

| Loại test | Bắt buộc | Nội dung |
|---|---|---|
| Manifest validation test | Có | Manifest parse được và đúng schema |
| Logic unit test | Có | Kiểm tra logic tính toán chính |
| UI smoke test | Có | View build được, không crash khi render cơ bản |
| State test | Khuyến nghị mạnh | get/restore state hoạt động |
| Export test | Khuyến nghị mạnh | Nếu module hỗ trợ export |

### 16.2. Tiêu chí chấp nhận tối thiểu trước khi merge

1. Manifest hợp lệ
2. Module load được trong shell test environment
3. `build_view()` trả root widget hợp lệ
4. Không crash khi activate rồi deactivate
5. Logic cốt lõi có ít nhất một test case đúng và một test case biên hoặc lỗi

### 16.3. Ví dụ test cases cho module phân phối chuẩn

1. Nhập `mode = alpha` với đuôi trái và đuôi phải hợp lệ, tính ra `z` đúng gần đúng
2. Nhập `mode = z`, tính ra diện tích đuôi đúng gần đúng
3. Giá trị đầu vào ngoài miền hợp lệ bị chặn và báo đúng
4. View render được kể cả khi chưa có dữ liệu tính toán
5. Export PNG thành công vào thư mục tạm

---

## 17. Versioning và compatibility

### 17.1. Semantic versioning

Module phải dùng semantic versioning:

`MAJOR.MINOR.PATCH`

| Thành phần | Ý nghĩa |
|---|---|
| `MAJOR` | Thay đổi phá vỡ compatibility |
| `MINOR` | Thêm tính năng tương thích ngược |
| `PATCH` | Sửa lỗi, tối ưu nhỏ, không đổi contract |

### 17.2. Quy tắc compatibility

1. `sdk_version` thể hiện chuẩn SDK mà module tuân theo
2. `min_platform_version` là phiên bản shell tối thiểu cần có
3. Nếu thay đổi state schema theo cách không tương thích ngược, phải tăng `data_contract_version`
4. Nếu thay đổi hành vi export hoặc event payload quan trọng, phải ghi rõ trong changelog

### 17.3. Khi nào phải tăng major version

1. Đổi manifest theo cách cũ không parse được
2. Đổi event payload khiến consumer cũ hỏng
3. Đổi state schema mà không thể tự migrate
4. Đổi permission hoặc capability theo hướng phá API nội bộ công bố

---

## 18. Template module chuẩn cho AI Agent

### 18.1. Skeleton tối giản đề xuất

```python
# entry.py
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel
from core.module_runtime.base_module import BaseModule

class ExampleModule(BaseModule):
    def __init__(self, manifest, context):
        super().__init__(manifest, context)
        self._view = None

    def on_load(self) -> None:
        self.context.logger.info(f"Loading module: {self.manifest['id']}")

    def build_view(self) -> QWidget:
        if self._view is None:
            root = QWidget()
            layout = QVBoxLayout(root)
            layout.addWidget(QLabel(self.manifest["name"]))
            self._view = root
        return self._view

    def on_activate(self) -> None:
        self.context.logger.info(f"Activated: {self.manifest['id']}")

    def on_deactivate(self) -> None:
        self.context.logger.info(f"Deactivated: {self.manifest['id']}")

    def on_unload(self) -> None:
        self.context.logger.info(f"Unloaded: {self.manifest['id']}")

    def get_state(self) -> dict:
        return {"state_version": "1.0.0"}

    def restore_state(self, state: dict) -> None:
        pass
```

### 18.2. Checklist mà AI Agent phải tự kiểm trước khi kết thúc task module

1. Đã có `module.json` hợp lệ chưa
2. `entry_point` có import được không
3. Class chính có kế thừa `BaseModule` không
4. `build_view()` có trả `QWidget` root không
5. Module có cleanup ở `on_unload()` không
6. State có serialize được không nếu module hỗ trợ restore
7. README của module đã mô tả mục đích, input, output và giới hạn chưa
8. Có ít nhất test manifest, test logic và test smoke UI chưa
9. Module có dùng service đúng qua context thay vì import nội bộ shell không
10. Module có tuân thủ permissions đã khai báo không

---

## 19. Module phân phối chuẩn như reference module

### 19.1. Vai trò của reference module

Module phân phối chuẩn là module first-party dùng để chứng minh rằng SDK và runtime thực sự vận hành được trong tình huống thật. Nó không chỉ là ví dụ minh họa, mà còn là chuẩn tham chiếu để kiểm tra các năng lực sau:

1. Input form nhiều mode
2. Tính toán logic học thuật
3. Vẽ biểu đồ 2D trong host frame
4. Tô vùng highlight theo dữ liệu người dùng
5. Export hình ảnh
6. Lưu và restore state
7. Xử lý lỗi input thân thiện

### 19.2. Chuyển từ script sang module đúng chuẩn

Script hiện tại cần được tái cấu trúc thành module theo hướng:

1. Tách logic tính toán khỏi mã vẽ và khỏi lệnh chạy trực tiếp
2. Bỏ lệnh thực thi tự động ở cuối file
3. Đóng gói logic vào service nội bộ của module
4. Tạo view Qt để người dùng nhập `alpha` hoặc `z`
5. Dùng canvas hoặc backend phù hợp để nhúng biểu đồ vào shell
6. Dùng `export_service` thay vì ghi file tự do trong luồng chính
7. Lưu mode, input gần nhất, precision và đường dẫn export gần nhất vào state/settings

### 19.3. Acceptance criteria cho reference module này

1. Người dùng có thể chọn mode `alpha` hoặc `z`
2. Người dùng có thể nhập giá trị hợp lệ và nhận kết quả đúng gần đúng
3. Đồ thị phân phối chuẩn hiển thị được trong shell
4. Vùng tô màu phản ánh đúng dữ liệu đầu vào
5. Có thể export ảnh PNG
6. Reload module không làm mất state nếu bật restore
7. Input lỗi được báo rõ ràng, không crash app

---

## 20. Quy chuẩn tài liệu đi kèm mỗi module

Mỗi module production-ready phải có tối thiểu các tài liệu sau:

| Tài liệu | Bắt buộc | Nội dung |
|---|---|---|
| `README.md` | Có | Mục đích, cách dùng, input, output, giới hạn, dependencies |
| `CHANGELOG.md` | Khuyến nghị mạnh | Lịch sử thay đổi |
| `tests/` | Có | Bộ test tối thiểu |
| Screenshot hoặc GIF demo | Khuyến nghị | Phục vụ review nội bộ |

### 20.1. Cấu trúc README đề xuất

1. Tên module
2. Mục đích
3. Chức năng chính
4. Input và output
5. Permissions yêu cầu
6. State hỗ trợ lưu/phục hồi gì
7. Cách export
8. Giới hạn hiện tại
9. Cách chạy test

### 20.2. Module Design Document (bắt buộc cho module phức tạp)

Ngoài `README.md` thông thường, các module thuộc dạng **mô phỏng, phân tích, tính toán nhiều bước hoặc có nhiều tab/phương pháp** phải được thiết kế trước bằng một file `module_<tên>.md` đặt tại thư mục gốc workspace (không trong thư mục module). File này phải được AI Agent đọc và tuân thủ như nguồn chân lý trong suốt quá trình triển khai.

**Khi nào bắt buộc có Module Design Document:**

| Điều kiện | Ví dụ |
|---|---|
| Module có từ 2 tab chính trở lên | demand_forecasting_scm, time_series |
| Module có nhiều phương pháp tính toán hoặc mô hình | demand_forecasting_scm |
| Module có dialog chức năng đặc biệt (animation, hold-out, control chart) | demand_forecasting_scm |
| Module có logic nhập dữ liệu phức tạp (import file, làm sạch, phân tích) | demand_forecasting_scm |
| Module có state phức tạp hơn một vài số đơn giản | bất kỳ module nào có dataset |

**Cấu trúc bắt buộc của một Module Design Document:**

| Section | Bắt buộc | Nội dung |
|---|---|---|
| §0 Ghi chú kiến trúc | Có | Giải thích quyết định tech stack, điều chỉnh so với thiết kế gốc |
| §1 Thông tin module | Có | ID, tên, category, thư mục, permissions, supports_state_restore/export |
| §2 Mục tiêu & phạm vi | Có | Mục tiêu nghiệp vụ, đối tượng sử dụng |
| §3 Lộ trình (nếu có phase) | Có nếu chia phase | Bảng tab/tính năng theo phase |
| §4 Tech stack | Có | Liệt kê cụ thể theo chuẩn IIMP |
| §5 Cấu trúc thư mục | Có | Đầy đủ file và mô tả vai trò từng file |
| §6 Thiết kế UI | Có | Widget tree chi tiết cho từng màn hình/dialog |
| §7 Danh sách phương pháp | Có nếu áp dụng | Tham số, thư viện sử dụng |
| §8 Công thức | Có nếu áp dụng | Công thức tính toán chính xác |
| §9 Logic nghiệp vụ đặc biệt | Có nếu áp dụng | Smart Suggestion, animation, hold-out logic |
| §10 State model | Có | Cấu trúc class state, version hóa |
| §11 Host Services sử dụng | Có | Liệt kê service + mục đích |
| §12 Definition of Done | Có | Checklist cụ thể cho module/phase |
| §13 Hướng dẫn cho AI Agent | Có | Ràng buộc triển khai, điều không được làm |

**Quy trình:**

1. Trước khi code bất kỳ file nào của module phức tạp: tạo Module Design Document
2. Sau khi tài liệu được xác nhận (hoặc tự rà soát compliance): mới bắt đầu triển khai
3. Khi Phase 1 hoàn thành: cập nhật trạng thái trong tài liệu; bổ sung §Phase 2 nếu cần
4. Tài liệu phải được giữ đồng bộ với code — nếu có thay đổi thiết kế, cập nhật tài liệu trước

**Tên file quy ước:** `module_<module_id>.md` — ví dụ: `module_demand_forecasting_scm.md`

---

## 21. Definition of Done cho một module

Một module chỉ được xem là hoàn thành khi thỏa tất cả các điều kiện sau:

1. Có `module.json` hợp lệ theo schema hiện hành
2. Có entry point import được
3. Kế thừa `BaseModule` và đủ lifecycle bắt buộc
4. View render được trong host frame
5. Không crash khi activate, deactivate và unload
6. Có README mô tả rõ hành vi
7. Có test tối thiểu theo chuẩn SDK
8. Có error handling cơ bản cho luồng chính
9. Có logging tối thiểu
10. Không vi phạm các nguyên tắc trong `IIMP_ARCHITECTURE.md`
11. Nếu module thuộc dạng phức tạp (§20.2): phải có Module Design Document đầy đủ, đã được rà soát compliance trước khi bắt đầu code

---

## 22. Prompt khởi đầu bắt buộc cho AI Agent khi phát triển module

Trước khi tạo hoặc sửa bất kỳ module nào, AI Agent phải tự áp dụng chỉ dẫn khởi đầu sau:

> Hãy đọc `IIMP_ARCHITECTURE.md`, `IIMP_ROADMAP.md` và `IIMP_MODULE_SDK.md` trước khi thực hiện task. Mọi thay đổi phải giữ đúng định hướng shell app + module runtime, tuân thủ `module.json`, `BaseModule`, lifecycle, permissions, state persistence và unified UX. Không được viết module như một app độc lập. Không bypass host services hoặc import trực tiếp internals ngoài các API công bố. Nếu cần thay đổi contract module, phải cập nhật tài liệu và changelog trước. **Nếu module thuộc dạng phức tạp (§20.2), phải đọc và tuân thủ Module Design Document `module_<id>.md` tương ứng như nguồn chân lý thứ hai sau bộ ba tài liệu kiến trúc.**

---

## 23. CHANGELOG

### 2026-03-24

1. Khởi tạo file `IIMP_MODULE_SDK.md`
2. Định nghĩa chuẩn manifest `module.json`
3. Định nghĩa `BaseModule` contract và lifecycle chuẩn
4. Định nghĩa `ModuleContext`, host services và permissions cơ bản
5. Bổ sung quy chuẩn UI, state, export, testing, versioning và Definition of Done cho module
6. Định vị module mô phỏng phân phối chuẩn là reference module first-party của SDK

### 2026-04-12

1. Bổ sung §20.2 — Module Design Document: quy chuẩn bắt buộc cho module phức tạp (nhiều tab, nhiều phương pháp, animation, import dữ liệu). Định nghĩa cấu trúc 13 section, điều kiện áp dụng, quy trình tạo và đồng bộ với code
2. Cập nhật §21 DoD: bổ sung điều kiện 11 — phải có Design Document cho module phức tạp
3. Cập nhật §22 Prompt khởi đầu: bắt buộc đọc `module_<id>.md` như nguồn chân lý thứ hai khi module thuộc dạng phức tạp
