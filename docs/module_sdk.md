# IIMP Module Developer Guide

> Version: 1.0.0  
> Áp dụng cho: SDK v1.0.0, Platform v0.0.1+  
> Tài liệu căn bản: [IIMP_MODULE_SDK.md](../IIMP_MODULE_SDK.md)

Hướng dẫn này dành cho developer muốn tạo, kiểm thử và tích hợp module mới vào **Integrated Interactive Module Platform (IIMP)**. Tất cả code mẫu trong tài liệu này đều lấy từ module hiện có trong repo.

---

## Mục lục

1. [Tổng quan nhanh](#1-tổng-quan-nhanh)
2. [Cấu trúc thư mục](#2-cấu-trúc-thư-mục)
3. [Bước 1 — Sao chép starter template](#3-bước-1--sao-chép-starter-template)
4. [Bước 2 — Viết module.json](#4-bước-2--viết-modulejson)
5. [Bước 3 — Implement module.py](#5-bước-3--implement-modulepy)
6. [Bước 4 — Viết entry.py](#6-bước-4--viết-entrypy)
7. [Bước 5 — Viết tests](#7-bước-5--viết-tests)
8. [State persistence](#8-state-persistence)
9. [Export capability](#9-export-capability)
10. [Dùng host services](#10-dùng-host-services)
11. [Headless test guard](#11-headless-test-guard)
12. [Checklist trước khi tích hợp](#12-checklist-trước-khi-tích-hợp)
13. [Lỗi thường gặp](#13-lỗi-thường-gặp)

---

## 1. Tổng quan nhanh

Module trong IIMP là một Python package nằm trong thư mục `modules/`. Shell tự động phát hiện module khi:

1. Thư mục `modules/<category>/<module_id>/` tồn tại
2. File `module.json` hợp lệ
3. Entry point trỏ đến một class kế thừa `BaseModule`

Sau khi shell load module, nó có thể được mở từ Module Library, state có thể được lưu/phục hồi, và module có thể export file nếu khai báo hỗ trợ.

**Luồng tối giản:**

```
Tạo thư mục → module.json → module.py → entry.py → tests → chạy app
```

---

## 2. Cấu trúc thư mục

```text
modules/
└── <category>/
    └── <module_id>/
        ├── module.json          # metadata, compatibility, permissions
        ├── entry.py             # export class hoặc factory
        ├── module.py            # logic chính, kế thừa BaseModule
        ├── README.md            # mô tả module
        ├── __init__.py          # đánh dấu Python package
        └── tests/
            ├── __init__.py
            ├── test_manifest.py # kiểm tra module.json
            ├── test_calculator.py # kiểm tra logic thuần (không cần Qt)
            └── test_smoke_ui.py   # kiểm tra UI cơ bản (cần PySide6)
```

Ví dụ thực tế:

```text
modules/statistics/normal_distribution/
modules/templates/starter_module/
```

---

## 3. Bước 1 — Sao chép starter template

```
Sao chép toàn bộ thư mục:
  modules/templates/starter_module/
→ modules/<category>/<your_module_id>/
```

Sau đó đổi tên mọi chỗ tham chiếu đến `starter_module` thành `<your_module_id>`.

Starter template đã có sẵn impl tối thiểu của tất cả các method bắt buộc, giúp bạn không bỏ sót contract.

---

## 4. Bước 2 — Viết module.json

### Cấu trúc đầy đủ

```json
{
  "id": "my_module",
  "name": "My Module",
  "version": "1.0.0",
  "sdk_version": "1.0.0",
  "min_platform_version": "1.0.0",
  "entry_point": "modules.<category>.my_module.entry:MyModule",
  "description": "Mô tả ngắn gọn, hiển thị trong Module Library.",
  "category": "<category>",
  "author": "IIMP Team",
  "permissions": [
    "storage.read",
    "storage.write",
    "export.file"
  ],
  "tags": ["keyword1", "keyword2"],
  "supports_state_restore": true,
  "supports_export": true,
  "icon": "icon.png",
  "data_contract_version": "1.0.0",
  "default_settings": {
    "precision": 4
  },
  "capabilities": [
    "plot.2d",
    "compute.statistics",
    "export.image"
  ],
  "ui": {
    "min_width": 800,
    "min_height": 560
  }
}
```

### Quy tắc quan trọng

| Trường | Quy tắc |
|---|---|
| `id` | snake_case, ổn định — **không đổi sau khi đã deploy** |
| `entry_point` | phải ở dạng `module.path:ClassName`, không dùng thư mục tuyệt đối |
| `version` | tuân theo semantic versioning: `MAJOR.MINOR.PATCH` |
| `permissions` | chỉ khai báo quyền thật sự dùng |
| `supports_state_restore` | `true` nếu module implement `get_state()` / `restore_state()` |
| `supports_export` | `true` nếu module implement `export()` |

### Danh sách permissions hợp lệ

| Permission | Khi nào dùng |
|---|---|
| `storage.read` | Đọc state, file |
| `storage.write` | Ghi state, dữ liệu cục bộ |
| `settings.read` | Đọc cấu hình module |
| `settings.write` | Ghi cấu hình module |
| `export.file` | Xuất file ra ngoài |
| `dialogs.basic` | Hiển thị message box, confirm dialog |
| `activity.write` | Ghi log hoạt động |

---

## 5. Bước 3 — Implement module.py

### Skeleton cơ bản

```python
"""MyModule — mô tả ngắn gọn."""
from __future__ import annotations

from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget
from core.module_runtime.base_module import BaseModule


class MyModule(BaseModule):

    def __init__(self, manifest: dict, context) -> None:
        super().__init__(manifest, context)
        self._view: QWidget | None = None

    # ── Lifecycle bắt buộc ────────────────────────────────────────────────────

    def on_load(self) -> None:
        """Khởi tạo tài nguyên nhẹ. Chưa tạo widget."""
        self.context.logger.info(f"[{self.module_id}] on_load()")

    def build_view(self) -> QWidget:
        """Tạo và trả về root QWidget. Idempotent."""
        if self._view is None:
            root = QWidget()
            layout = QVBoxLayout(root)
            layout.addWidget(QLabel(f"Module: {self.module_name}"))
            self._view = root
        return self._view

    def on_activate(self) -> None:
        """Kết nối signal, refresh data nếu cần."""
        self.context.logger.info(f"[{self.module_id}] on_activate()")

    def on_deactivate(self) -> None:
        """Tạm dừng timer, lưu draft state nếu cần."""
        self.context.logger.info(f"[{self.module_id}] on_deactivate()")

    def on_unload(self) -> None:
        """Cleanup triệt để: dừng timer, đóng file handle, giải phóng resource."""
        self.context.logger.info(f"[{self.module_id}] on_unload()")
        self._view = None
```

### Các method lifecycle quan trọng

| Method | Được phép | Không được phép |
|---|---|---|
| `on_load()` | Tạo model, bind service, chuẩn bị cache nhẹ | Tạo widget phức tạp, gọi tính toán nặng |
| `build_view()` | Tạo toàn bộ UI tree, trả QWidget | Trả `None`, gọi `show()`, mở main window độc lập |
| `on_activate()` | Kết nối signal, refresh dữ liệu | Reset state người dùng không có lý do |
| `on_deactivate()` | Ngắt signal tạm, lưu draft | Hủy toàn bộ resource |
| `on_unload()` | Cleanup mọi thứ | Gọi shell internals không qua context |

> **Lưu ý**: `build_view()` nên là idempotent — nếu gọi lại thì trả cùng widget, không tạo mới từ đầu.

### Tách logic thuần ra khỏi UI

Để dễ test và bảo trì, hãy tách logic tính toán thành `@staticmethod` hoặc function thuần:

```python
class MyModule(BaseModule):

    @staticmethod
    def _compute_result(param_a: float, param_b: float) -> float:
        """Logic tính toán thuần — không cần Qt, dễ test riêng."""
        return param_a * param_b  # ví dụ đơn giản

    def _on_calculate(self) -> None:
        """Slot UI: đọc input, gọi logic, cập nhật kết quả."""
        a = self._spin_a.value()
        b = self._spin_b.value()
        result = self._compute_result(a, b)
        self._result_label.setText(f"Kết quả: {result:.4f}")
```

Xem ví dụ thực tế: `_compute_alpha_to_z()` và `_compute_z_to_alpha()` trong `modules/statistics/normal_distribution/module.py`.

---

## 6. Bước 4 — Viết entry.py

```python
"""Entry point — export class chính của module."""
from modules.<category>.<module_id>.module import MyModule

__all__ = ["MyModule"]
```

> Giữ `entry.py` ngắn gọn. Đây chỉ là nơi shell tìm entry point.

---

## 7. Bước 5 — Viết tests

### test_manifest.py — Luôn bắt buộc

Kiểm tra `module.json` hợp lệ, không cần Qt:

```python
"""Tests for module.json manifest."""
from __future__ import annotations

import json
from pathlib import Path

import pytest
from core.module_runtime.manifest_schema import ModuleManifest

MODULE_DIR = Path(__file__).parent.parent
MANIFEST_PATH = MODULE_DIR / "module.json"


def test_manifest_file_exists():
    assert MANIFEST_PATH.exists(), "module.json không tồn tại"


def test_manifest_parses_successfully():
    data = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    manifest = ModuleManifest(**data)
    assert manifest.id == "my_module"
    assert manifest.version.startswith("1.")


def test_manifest_has_required_permissions():
    data = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    assert "storage.read" in data["permissions"]


def test_manifest_supports_state_and_export():
    data = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    assert data.get("supports_state_restore") is True
    assert data.get("supports_export") is True


def test_manifest_sdk_version_field():
    data = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    assert "sdk_version" in data
    assert "min_platform_version" in data
```

### test_calculator.py — Cho logic thuần

Không cần PySide6, chạy được trong mọi môi trường:

```python
"""Tests for pure computation logic."""
from __future__ import annotations

import pytest
from modules.<category>.<module_id>.module import MyModule


class TestMyComputation:

    def test_basic_result(self):
        result = MyModule._compute_result(2.0, 3.0)
        assert result == pytest.approx(6.0)

    def test_edge_case(self):
        result = MyModule._compute_result(0.0, 5.0)
        assert result == pytest.approx(0.0)


class TestState:

    def setup_method(self):
        manifest = {"id": "my_module", "name": "My Module", "version": "1.0.0"}

        class MockContext:
            class logger:
                @staticmethod
                def info(msg): pass
                @staticmethod
                def warning(msg): pass

        self.mod = MyModule.__new__(MyModule)  # bỏ qua __init__ nếu cần Qt
        # Hoặc dùng mock context:
        self.mod = MyModule(manifest, MockContext())

    def test_get_state_defaults(self):
        state = self.mod.get_state()
        assert "param_a" in state

    def test_restore_state(self):
        self.mod.restore_state({"param_a": 5.0, "param_b": 2.0})
        state = self.mod.get_state()
        assert state["param_a"] == pytest.approx(5.0)

    def test_restore_state_tolerates_missing_keys(self):
        # State cũ thiếu key mới → không crash
        self.mod.restore_state({})
        state = self.mod.get_state()
        assert "param_a" in state  # fallback về default
```

### test_smoke_ui.py — Cho UI (cần PySide6)

```python
"""Smoke tests for UI — requires PySide6."""
from __future__ import annotations

import pytest

pyside6 = pytest.importorskip("PySide6", reason="PySide6 not installed")

from PySide6.QtWidgets import QApplication, QWidget
from modules.<category>.<module_id>.module import MyModule

_app = QApplication.instance() or QApplication([])


@pytest.fixture
def module():
    manifest = {"id": "my_module", "name": "My Module", "version": "1.0.0"}

    class MockContext:
        class logger:
            @staticmethod
            def info(msg): pass

    mod = MyModule(manifest, MockContext())
    mod.on_load()
    yield mod
    mod.on_unload()


def test_build_view_returns_qwidget(module):
    view = module.build_view()
    assert isinstance(view, QWidget)


def test_lifecycle_no_crash(module):
    module.build_view()
    module.on_activate()
    module.on_deactivate()
    # Không raise, không crash


def test_state_round_trip(module):
    module.build_view()
    initial = module.get_state()
    module.restore_state(initial)
    restored = module.get_state()
    assert restored == initial
```

### Chạy tests

```bash
# Trong thư mục root:
python -m pytest modules/<category>/<module_id>/tests/ -v

# Chỉ test logic (không cần Qt):
python -m pytest modules/<category>/<module_id>/tests/test_calculator.py \
                 modules/<category>/<module_id>/tests/test_manifest.py -v

# Tất cả tests của toàn project:
python -m pytest tests/ modules/ -v
```

---

## 8. State persistence

Module khai báo `"supports_state_restore": true` phải implement hai method:

```python
def get_state(self) -> dict:
    """Trả về dict JSON-serializable đại diện cho session state hiện tại."""
    return {
        "state_version": "1.0.0",   # nên có để migrate về sau
        "param_a": self._spin_a.value() if self._view else 0.0,
        "param_b": self._spin_b.value() if self._view else 1.0,
        "tab":     self._tabs.currentIndex() if self._view else 0,
    }

def restore_state(self, state: dict) -> None:
    """Phục hồi state. Phải chịu được state thiếu key hoặc schema cũ."""
    if not isinstance(state, dict):
        return
    if self._view is None:
        self.build_view()
    param_a = float(state.get("param_a", 0.0))
    param_b = float(state.get("param_b", 1.0))
    tab     = int(state.get("tab", 0))
    self._spin_a.setValue(param_a)
    self._spin_b.setValue(max(0.001, param_b))  # guard nếu cần
    self._tabs.setCurrentIndex(tab)
```

**Quy tắc bắt buộc:**

1. State phải là JSON-serializable (không chứa QWidget, datetime, numpy array)
2. `restore_state()` không được crash khi nhận state thiếu key
3. `restore_state()` không được crash khi nhận state `{}` hoặc `None`
4. Không lưu dữ liệu nặng vào state — chỉ lưu tham số cần để tái tạo kết quả

---

## 9. Export capability

Module khai báo `"supports_export": true` phải implement `export()`:

```python
def export(self, target_path: str, export_type: str = "default") -> None:
    """Export module output ra file."""
    if self._canvas is None:
        raise RuntimeError("Không có canvas để export")

    if export_type in ("default", "png", "image"):
        png_bytes = self._canvas.get_figure_bytes()
        with open(target_path, "wb") as f:
            f.write(png_bytes)
    else:
        raise ValueError(f"Kiểu export không hỗ trợ: {export_type!r}")
```

Shell gọi `module.export(path, export_type)` khi người dùng click nút Export. Module tự quyết định format nào hỗ trợ.

---

## 10. Dùng host services

Module nhận `context` từ host. Các service quan trọng:

```python
# Ghi log
self.context.logger.info(f"[{self.module_id}] step completed")
self.context.logger.warning("Thiếu dữ liệu")
self.context.logger.error("Lỗi nghiêm trọng", exc_info=True)

# Ghi activity event
self.context.activity_service.log_event(
    module_id=self.module_id,
    event_type="EXPORT",
    detail="PNG exported successfully"
)

# Đọc/ghi settings
precision = self.context.settings_service.get_module_setting(
    self.module_id, "precision", default=4
)
self.context.settings_service.set_module_setting(
    self.module_id, "precision", 4
)

# Cấp đường dẫn lưu file
export_dir = self.context.path_service.get_export_dir()
```

> **Quan trọng**: Không bao giờ import thẳng vào nội bộ shell. Chỉ dùng `self.context` để tương tác.

---

## 11. Headless test guard

Nếu module dùng PySide6, code import sẽ fail khi chạy test trên môi trường không có display. Dùng pattern sau:

```python
# ── Guards cho headless test ──────────────────────────────────────────────────
try:
    from PySide6.QtCore import Qt, Signal
    from PySide6.QtWidgets import (
        QHBoxLayout, QLabel, QSpinBox, QVBoxLayout, QWidget,
    )
    _QT = True
except ImportError:  # pragma: no cover
    _QT = False

try:
    import matplotlib
    matplotlib.use("Agg")  # non-interactive backend
    from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
    from matplotlib.figure import Figure
    _MPL = True
except ImportError:  # pragma: no cover
    _MPL = False

# Canvas base class để test_calculator.py không fail
_CanvasBase = QWidget if _QT else object

class MyCanvas(_CanvasBase):
    ...
```

Sau đó trong `test_calculator.py`, chỉ test `@staticmethod` methods hoặc pure Python — không đụng UI.

---

## 12. Checklist trước khi tích hợp

Trước khi coi module là sẵn sàng, kiểm tra toàn bộ danh sách sau:

### Manifest
- [ ] `module.json` có đủ tất cả trường bắt buộc
- [ ] `id` là snake_case, ổn định, không trùng module khác
- [ ] `entry_point` đúng cú pháp `module.path:ClassName`
- [ ] `version` đúng semantic versioning
- [ ] `permissions` chỉ khai báo quyền thật sự dùng
- [ ] `supports_state_restore` và `supports_export` phản ánh đúng thực tế

### Contract
- [ ] Class kế thừa `BaseModule`
- [ ] Implement đủ 5 method bắt buộc: `on_load`, `build_view`, `on_activate`, `on_deactivate`, `on_unload`
- [ ] `build_view()` trả `QWidget`, không trả `None`, không gọi `show()`
- [ ] `build_view()` idempotent (gọi nhiều lần cho cùng kết quả)
- [ ] `on_unload()` dọn sạch resource

### State
- [ ] `get_state()` trả dict JSON-serializable
- [ ] `restore_state()` không crash khi có key thiếu
- [ ] `restore_state()` không crash khi nhận `{}`

### UI
- [ ] Module không tự mở main window độc lập
- [ ] UI resize được trong host frame
- [ ] Lỗi không hiển thị traceback thô cho user

### Tests
- [ ] `test_manifest.py` pass (không cần Qt)
- [ ] `test_calculator.py` pass (không cần Qt)
- [ ] `test_smoke_ui.py` pass (cần PySide6)
- [ ] Không có warnings nào là regressions mới

### Tổng thể
- [ ] `README.md` mô tả module, cách dùng và giới hạn
- [ ] Module có thể được discover tự động khi đặt đúng vị trí trong `modules/`
- [ ] Module không import bất kỳ thứ gì từ module khác ngoài `core/`

---

## 13. Lỗi thường gặp

### Module không hiện trong Library

**Nguyên nhân**: Manifest thiếu trường bắt buộc hoặc `entry_point` sai format.

**Kiểm tra**:
```bash
python -m pytest modules/<category>/<module_id>/tests/test_manifest.py -v
```

---

### `ModuleNotFoundError` khi load

**Nguyên nhân**: `entry_point` dùng đường dẫn không match thư mục thực.

**Sửa**: Đảm bảo `entry_point` trong `module.json` match đúng import path Python, tính từ root project:

```json
// Đúng nếu file nằm tại:
// modules/statistics/my_module/entry.py
// và class tên MyModule
"entry_point": "modules.statistics.my_module.entry:MyModule"
```

---

### Test crash `ModuleNotFoundError: No module named 'PySide6'`

**Nguyên nhân**: Import PySide6 ở đầu file không được guard.

**Sửa**: Dùng try/except như trong mục [Headless test guard](#11-headless-test-guard) hoặc dùng `pytest.importorskip("PySide6")` trong smoke test.

---

### `restore_state()` crash khi mở module lần đầu

**Nguyên nhân**: `restore_state()` không guard trường hợp state rỗng.

**Sửa**:
```python
def restore_state(self, state: dict) -> None:
    if not isinstance(state, dict):  # Guard thiếu kiểu
        return
    value = float(state.get("my_key", 1.0))  # Default an toàn
    ...
```

---

### `parse_version` không raise cho version string không hợp lệ

**Nguyên nhân**: Versions như `"abc"` trước đây trả tuple rỗng thay vì raise.

**Trạng thái**: Đã fix trong `core/utils/helpers.py` — `parse_version()` giờ raise `ValueError` nếu không tìm thấy phần số nào.

---

*Cập nhật lần cuối: theo session module v2.0.0 — normal_distribution hoàn chỉnh*
