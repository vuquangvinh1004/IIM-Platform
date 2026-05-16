# INTEGRATED INTERACTIVE MODULE PLATFORM ROADMAP

> Cập nhật: 28/03/2026 (central_limit_theorem module — 803 tests, 0 failures)
> Phiên bản hiện tại: v1.0.0-rc2
> Mục tiêu: v1.0.0 với shell app ổn định, module runtime chuẩn hóa và bộ module mẫu đủ để chứng minh kiến trúc

---

## 1. Tổng quan tiến độ

```text
Phase 0  Product Definition and Specs     ██████████  100%
Phase 1  Foundation and App Shell         ██████████  100%
Phase 2  Module Runtime and Registry      ██████████  100%
Phase 3  Unified UI and Workspace         ██████████  100%
Phase 4  First-party Modules and SDK      ██████████  100%
Phase 5  Persistence and Module Manager   ██████████  100%
Phase 6  Testing, Packaging, Release      █████████░  95%
-----------------------------------------------------------
Tổng thể                                  █████████░  98%
```

---

## 2. Mục tiêu phát triển theo phase

### Phase 0. Product Definition and Specs

Mục tiêu: Chốt ngôn ngữ kiến trúc, chuẩn module và tài liệu định hướng cho AI Agent.

| Hạng mục | Trạng thái | Ưu tiên | Ghi chú |
| --- | --- | --- | --- |
| Mô tả sản phẩm cấp nền tảng | Done | Cao | Chốt mô hình shell và module |
| Architecture document | Done | Cao | IIMP_ARCHITECTURE.md |
| Roadmap document | Done | Cao | IIMP_ROADMAP.md |
| Định nghĩa module reference | Done | Cao | Mô phỏng phân phối chuẩn |
| Danh sách phase phát triển | Done | Cao | 6 phase kỹ thuật sau spec |

Deliverable: Có bộ tài liệu đủ để AI Agent phát triển nhất quán, không làm lệch bản chất sản phẩm.

### Phase 1. Foundation and App Shell

Mục tiêu: Xây dựng lõi ứng dụng desktop và khung vận hành chung.

| Hạng mục | Trạng thái | Ưu tiên | Ghi chú |
| --- | --- | --- | --- |
| Khởi tạo cấu trúc thư mục chuẩn | Done | Cao | Phải đúng theo architecture |
| Thiết lập config và paths | Done | Cao | Bao gồm data dir, logs, module_data |
| Main window skeleton | Done | Cao | Sidebar, toolbar, host frame, status bar |
| Logging infrastructure | Done | Cao | Rotation và startup logs |
| Constants và enums | Done | Cao | ModuleState, ArtifactType, PermissionType |
| Exception hierarchy | Done | Trung bình | ManifestError, ModuleLoadError, StateError |
| DB connection và models khung | Done | Cao | SQLite + SQLAlchemy |
| Test framework setup | Done | Cao | pytest, pytest-qt, pytest-cov |

Deliverable: Ứng dụng mở được, có main window, có shell layout chuẩn, có logger, DB setup và test setup.

### Phase 2. Module Runtime and Registry

Mục tiêu: Hoàn thiện hệ thống phát hiện, xác thực, load và quản lý vòng đời module.

| Hạng mục | Trạng thái | Ưu tiên | Ghi chú |
| --- | --- | --- | --- |
| `manifest_schema.py` | Done | Cao | Pydantic model cho manifest |
| `base_module.py` | Done | Cao | Contract chính thức |
| Module discovery | Done | Cao | Quét thư mục modules |
| Manifest validation | Done | Cao | Báo lỗi rõ ràng |
| Entry point loader | Done | Cao | importlib safe loading |
| Runtime registry | Done | Cao | Registry in-memory + sync DB |
| Module activation lifecycle | Done | Cao | load, activate, deactivate, unload |
| Compatibility check | Done | Trung bình | min_platform_version |
| Runtime fallback view | Done | Cao | Khi load thất bại không crash app |
| Integration tests runtime | Done | Cao | Discovery đến activation |

Deliverable: Có thể phát hiện, load và host module hợp lệ; module lỗi không làm app sập toàn cục.

### Phase 3. Unified UI and Workspace

Mục tiêu: Tạo trải nghiệm shell thống nhất cho người dùng cuối.

| Hạng mục | Trạng thái | Ưu tiên | Ghi chú |
| --- | --- | --- | --- |
| Dashboard view | Done | Trung bình | Real DB stats: total/enabled/disabled counts + activity feed |
| Module library view | Done | Cao | Card/list, search, live filter |
| Workspace view | Done | Cao | Wraps ModuleHostFrame |
| Module manager view | Done | Cao | Enable/disable/uninstall/install-local, confirmation dialogs, DB-backed |
| Activity history view | Done | Trung bình | Full DB query, type filter, color-coded, 200 rows |
| Settings view | Done | Cao | All app settings with DB persistence via SettingsService |
| Shared theme system | Done | Cao | Light theme QSS baseline |
| Status strip | Done | Trung bình | DB, module count, shell state |
| Host frame behaviors | Done | Cao | Resize, replace, fallback, error view |

Deliverable: Người dùng có thể duyệt module, mở module và làm việc trong shell với trải nghiệm nhất quán.

### Phase 4. First-party Modules and SDK

Mục tiêu: Chứng minh nền tảng hoạt động thật bằng module mẫu và template phát triển.

| Hạng mục | Trạng thái | Ưu tiên | Ghi chú |
| --- | --- | --- | --- |
| Starter module template | Done | Cao | modules/templates/starter_module/ |
| Normal distribution module | Done | Cao | modules/statistics/normal_distribution/ — v2.0.0: 3 tab (phân phối N(μ,σ), α→Z/X, Z/X→α) |
| Exponential distribution module | ✅ Done | Cao | modules/statistics/exponential_distribution/ — v1.0.0: 2 tab (phân phối Exp(μ), x→Xác suất), 41 tests |
| Interactive geometry hoặc 3D demo module | ✅ Done | Trung bình | `modules/visualization/interactive_geometry/` — 5 hình dạng 3D, 57 tests |
| Export capability cho module | Done | Trung bình | Export PNG qua ExportService |
| Module README convention | Done | Trung bình | README.md cho từng module |
| Module unit tests sample | Done | Cao | tests/ trong normal_distribution |
| docs/module_sdk.md | Done | Cao | docs/module_sdk.md — step-by-step dev guide với code mẫu, test patterns, checklist |
| QC Kiểm tra Chất lượng module | ✅ Done | Cao | modules/statistics/qc_inspection/ — v1.0.0: 2 view (inspection + simulation), 78 tests; QC thủ công/tự động, biểu đồ Binomial/Poisson vs thực nghiệm |
| Định lý Giới hạn Trung tâm module | ✅ Done | Cao | modules/statistics/central_limit_theorem/ — v1.0.0: 2 view (weighing + simulation), 101 tests; cân thủ công (drag-drop) / tự động, histogram x̄ vs Student-t & Normal |
| PSO Tối ưu hóa Bầy đàn module | ✅ Done | Trung bình | modules/quantitative_methods/particle_swarm_optimization/ — subcategory: optimization; topology Star+Ring, Sphere+Ackley, animation 2D, convergence chart |
| PSO Tối ưu hóa Giao hàng module v1.0 | ✅ Done | Trung bình | modules/quantitative_methods/pso_logistics/ — subcategory: optimization; Discrete PSO (permutation space), bài toán TSP v1.0; topology Star+Ring, bản đồ tuyến đường 2D, đồ thị hội tụ, replay animation; 64 tests |

Deliverable: Có tối thiểu 2 module first-party và 1 starter template để AI Agent hoặc developer mở rộng tiếp.

### Phase 5. Persistence and Module Manager

Mục tiêu: Hoàn thiện lưu trữ, cấu hình và quản trị vòng đời module.

| Hạng mục | Trạng thái | Ưu tiên | Ghi chú |
| --- | --- | --- | --- |
| module_registry table integration | Done | Cao | _sync_registry_to_db + enable/disable/uninstall flow |
| module_settings persistence | Done | Cao | SettingsService.get/set_module_setting qua DB |
| module_sessions persistence | Done | Cao | StateManager.save_state/restore_state qua module_sessions |
| workspace_items support | Done | Trung bình | WorkspaceService CRUD: add/remove/pin/reorder; 15 unit tests pass |
| install local module flow | Done | Cao | install_local_module() với manifest validation + copy |
| disable and uninstall flow | Done | Cao | disable_module() + uninstall_module(), confirm dialog |
| activity logging | Done | Trung bình | APP_START/SHUTDOWN + MODULE_* events đã log đầy đủ |
| backup and restore DB | Deferred | Trung bình | Không bắt buộc ở v1.0 — Phase 5 hoàn thành không có mục này |

Deliverable: Module có thể được cài, bật, tắt, gỡ, lưu trạng thái và phục hồi cơ bản.

### Phase 6. Testing, Packaging, Release

Mục tiêu: Chuẩn bị phát hành v1.0.

| Hạng mục | Trạng thái | Ưu tiên | Ghi chú |
| --- | --- | --- | --- |
| Coverage >= 80% cho core runtime | ✅ Done | Cao | 803 tests, 0 failures |
| UI smoke tests | ✅ Done | Cao | `tests/ui/test_smoke_shell.py` — 14 tests, skip gracefully khi không có PySide6 |
| Runtime regression tests | ✅ Done | Cao | `tests/integration/test_runtime_regression.py` |
| Module regression tests | ✅ Done | Cao | headless_test_module loader tests |
| PyInstaller build config | ✅ Done | Cao | `iimp.spec` — Windows one-dir build |
| Windows standalone test | Open | Cao | Cần máy thật không có Python — thực hiện thủ công trước release |
| Inno Setup installer | ✅ Done | Trung bình | `scripts/release/iimp_setup.iss` — đầy đủ cú pháp, sẵn sàng build |
| User documentation | ✅ Done | Cao | `docs/quickstart.md` |
| Release checklist v1.0 | ✅ Done | Cao | `docs/release_checklist.md` |
| Sample installer validation | Open | Trung bình | Pending Windows standalone test + ISCC build |

Deliverable: Ứng dụng có thể đóng gói, cài đặt và chạy ổn định trên Windows với bộ module mẫu.

---

## 3. Sprint ưu tiên đề xuất

### Sprint 1

Mục tiêu: Đặt nền tảng shell app.

1. Cấu trúc thư mục
2. Settings, paths, logger
3. Main window skeleton
4. DB setup
5. Test setup

### Sprint 2

Mục tiêu: Hoàn thiện runtime và registry.

1. Manifest schema
2. BaseModule
3. Discovery
4. Loader
5. Registry sync

### Sprint 3

Mục tiêu: Hoàn thiện UI shell.

1. Dashboard
2. Module library
3. Workspace host frame
4. Module manager
5. Theme và status strip

### Sprint 4

Mục tiêu: Xây module mẫu đầu tiên.

1. Starter module template
2. Normal distribution module
3. Export image
4. State save and restore
5. Module tests

### Sprint 5

Mục tiêu: Hoàn thiện persistence và manager.

1. Module settings
2. Session persistence
3. Install local module flow
4. Enable, disable, uninstall
5. Activity logging

### Sprint 6

Mục tiêu: Đóng gói và chuẩn bị release.

1. Coverage
2. UI smoke tests
3. PyInstaller
4. Installer
5. User docs

---

## 4. Tiêu chí chấp nhận cho từng nhóm tính năng

### 4.1. App Shell

Một task shell chỉ được chấp nhận nếu:

1. App mở được ổn định
2. Main window có sidebar, toolbar, host frame và status strip
3. Chuyển view không gây crash
4. Logging hoạt động
5. Có test smoke cơ bản

### 4.2. Module Runtime

Một task runtime chỉ được chấp nhận nếu:

1. Quét được module hợp lệ
2. Manifest lỗi được phát hiện và báo rõ ràng
3. Module có thể load và hiển thị trong host frame
4. Module lỗi không làm sập toàn bộ app
5. Có unit test và integration test tương ứng

### 4.3. Module Contract

Một task contract chỉ được chấp nhận nếu:

1. `BaseModule` được chuẩn hóa
2. Manifest schema được validate rõ ràng
3. Có ví dụ module mẫu dùng được
4. Có tài liệu SDK hoặc README liên quan
5. Có test cho compatibility tối thiểu

### 4.4. Persistence

Một task persistence chỉ được chấp nhận nếu:

1. Settings app lưu và đọc lại được
2. Module state có thể serialize và restore
3. DB transaction an toàn
4. Có migration nếu thay schema
5. Có test ít nhất một case đúng và một case lỗi

### 4.5. First-party Modules

Một task module mẫu chỉ được chấp nhận nếu:

1. Module tuân thủ manifest và BaseModule
2. Module mở được trong shell
3. Có tương tác thực sự, không chỉ placeholder
4. Có khả năng lưu state cơ bản nếu cần
5. Có tests và README riêng

---

## 5. Bug tracker khởi tạo

| ID | Mô tả | Mức độ | Trạng thái |
| --- | --- | --- | --- |
| BUG-01 | Chưa chốt chuẩn package install cho module local ngoài thư mục source | Medium | Open |
| BUG-02 | Chưa chuẩn hóa chiến lược fallback khi module thiếu dependency tùy chọn | High | ✅ Resolved — manifest `optional_dependencies` + `safe_import()` helper + loader pre-check với `DependencyMissingError` |
| BUG-03 | Chưa chốt state format versioning khi module thay đổi cấu trúc dữ liệu | High | ✅ Resolved — `_state_version` auto-inject khi save, version check + `migrate_state()` hook khi restore |
| BUG-04 | Chưa xác định mức độ hỗ trợ 3D backend ở v1.0 | Medium | ✅ Resolved — dùng mpl_toolkits.mplot3d (matplotlib built-in), không cần VisPy/OpenGL |
| BUG-05 | Chưa có tiêu chuẩn performance khi load nhiều module cùng lúc | Low | ✅ Resolved — (A) ManifestCache skip re-parse unchanged module.json, (C) batch DB sync single-query load, (E) StartupSplash với progress callback. Lazy loading (B) không bị ảnh hưởng |

Quy tắc xử lý bug:

1. Khi fix bug phải cập nhật bảng này.
2. Nếu bug làm thay đổi business rule hoặc contract, phải cập nhật cả architecture.
3. Mọi bug runtime hoặc state persistence bắt buộc có regression test.

---

## 6. Hướng dẫn sử dụng AI Agent

### 6.1. Prompt khởi đầu bắt buộc

Sử dụng prompt sau khi bắt đầu bất kỳ phiên làm việc mới nào:

```text
Đọc IIMP_ARCHITECTURE.md và IIMP_ROADMAP.md trước khi code. Tuân thủ tech stack, cấu trúc thư mục, chuẩn manifest, BaseModule contract, module lifecycle, acceptance criteria và checklist sau mỗi task.
```

### 6.2. Prompt cho task tính năng mới

```text
Trước khi bắt đầu:
1. Đọc IIMP_ARCHITECTURE.md
2. Đọc IIMP_ROADMAP.md
3. Xác định phase và sprint của task

Nhiệm vụ: [mô tả tính năng]

Sau khi hoàn thành:
1. Cập nhật trạng thái task trong ROADMAP
2. Cập nhật CHANGELOG trong ARCHITECTURE
3. Viết tests liên quan
4. Báo cáo file đã thay đổi và kết quả test
```

### 6.3. Prompt cho task fix bug

```text
Trước khi bắt đầu:
1. Đọc IIMP_ARCHITECTURE.md mục runtime, module contract và coding standards
2. Đọc IIMP_ROADMAP.md mục bug tracker

Nhiệm vụ: Fix [BUG-ID]

Sau khi hoàn thành:
1. Cập nhật bug tracker
2. Thêm regression test
3. Ghi rõ root cause và solution vào CHANGELOG
4. Báo cáo test pass
```

### 6.4. Prompt cho task refactor

```text
Trước khi bắt đầu:
1. Kiểm tra module boundaries trong IIMP_ARCHITECTURE.md
2. Đảm bảo không làm thay đổi hành vi nghiệp vụ và contract hiện hành

Nhiệm vụ: [mô tả refactor]

Sau khi hoàn thành:
1. Xác nhận không đổi business behavior
2. Cập nhật CHANGELOG nếu cấu trúc hoặc interface đổi
3. Chạy full tests liên quan
```

### 6.5. Checklist bắt buộc sau mỗi task

- [ ] Chạy tests liên quan
- [ ] Không vi phạm module boundaries
- [ ] Không phá manifest hoặc BaseModule contract
- [ ] Cập nhật ROADMAP
- [ ] Cập nhật ARCHITECTURE CHANGELOG
- [ ] Nếu có schema change thì có migration notes
- [ ] Báo cáo tóm tắt thay đổi

---

## 7. Tài liệu AI Agent phải đọc theo từng nhu cầu

| Nhu cầu | File cần đọc |
| --- | --- |
| Kiến trúc tổng thể | IIMP_ARCHITECTURE.md |
| Chuẩn module contract | IIMP_ARCHITECTURE.md mục 5 |
| Schema database | IIMP_ARCHITECTURE.md mục 8 |
| Tiến độ project | IIMP_ROADMAP.md |
| Task ưu tiên tiếp theo | IIMP_ROADMAP.md mục 2 và 3 |
| Bug hiện có | IIMP_ROADMAP.md mục 5 |

---

## 8. Quy tắc báo cáo tiến độ

Mỗi lần AI Agent hoàn thành task phải báo theo mẫu tối thiểu:

1. Task đã thực hiện
2. Files đã thay đổi
3. Kết quả test
4. Rủi ro còn lại
5. Cập nhật nào đã ghi vào ROADMAP và ARCHITECTURE

Không được chỉ báo “đã xong” mà không có các thông tin trên.

---

## 9. Tiêu chí sẵn sàng phát hành v1.0

v1.0 chỉ được xem là sẵn sàng khi thỏa đồng thời:

1. Toàn bộ Phase 1 đến Phase 6 hoàn thành ở mức tối thiểu cho phạm vi v1.0
2. Test coverage đạt mục tiêu cho phần core và runtime
3. Không còn bug mức High ở runtime, persistence, manifest validation hoặc module activation
4. Build standalone chạy được trên Windows không cần cài Python
5. Có tài liệu hướng dẫn sử dụng cơ bản và hướng dẫn tạo module starter
6. Có tối thiểu 2 module mẫu hoạt động thực tế
7. Đã kiểm thử ít nhất 1 module tính toán trực quan và 1 module minh họa tương tác

---

## 9.5. Nguyên tắc phát triển bền vững

> Dựa trên "A Philosophy of Software Design" (Ousterhout) — xem chi tiết tại `IIMP_ARCHITECTURE.md §2.3`.
>
> Phần này định nghĩa cách **quản lý complexity tích lũy** trong suốt vòng đời dự án.

### 9.5.1. Ngân sách technical debt (Strategic Programming — Ch. 3)

Mỗi sprint **bắt buộc** dành 10–20% effort cho:

| Loại công việc | Ví dụ cụ thể |
|---|---|
| Xóa pass-through method và shallow class không cần thiết | Bất kỳ class nào chỉ forward sang class khác |
| Cải thiện docstring cho public API còn thiếu | `BaseModule` subclass chưa có docstring |
| Refactor tên mơ hồ hoặc không nhất quán | `id` → `module_id`, `widget` → `view`, `data` → tên có nghĩa |
| Gộp logic bị split không hợp lý | Business logic trong widget handler → service |
| Cải thiện error handling bị nuốt im lặng | Thêm log trước mỗi bare `except: pass` |

**Quy tắc:** Không bao giờ để "sửa nhanh" (tactical fix) tích lũy mà không có entry trong backlog để cleanup sau. Mọi workaround phải có TODO comment với lý do và kế hoạch xóa bỏ.

### 9.5.2. Design review trước mỗi Phase mới

Trước khi bắt đầu một Phase mới trong roadmap, thực hiện design review:

**Checklist design review:**

- [ ] Có class nào trở nên nông (shallow) sau khi bị refactor nhiều lần không?
- [ ] Có thông tin nào đang bị rò rỉ (leak) giữa tầng không (ví dụ: UI biết về DB schema)?
- [ ] Có pass-through method nào xuất hiện kể từ Phase trước không?
- [ ] Tên trong codebase còn nhất quán sau khi thêm nhiều component mới không?
- [ ] Exception handling còn ở đúng tầng hay đã drift lên quá cao?
- [ ] Docstring của public interface còn phản ánh đúng behavior hiện tại không?

**Output:** Nếu review tìm ra vấn đề, tạo task cleanup vào backlog của sprint đầu của Phase mới — ưu tiên cao hơn feature mới trừ khi có lý do kỹ thuật rõ ràng.

### 9.5.3. Nguyên tắc "Design It Twice" cho quyết định lớn (Ch. 11)

Trước khi thiết kế một component hoặc API mới có ảnh hưởng rộng (cross-layer hoặc SDK-facing), phải:

1. Thiết kế phương án A đầy đủ (interface + rationale)
2. Thiết kế phương án B khác biệt cơ bản (không chỉ là biến thể nhỏ)
3. So sánh hai phương án theo các tiêu chí: simplicity of interface, depth of implementation, information hiding, ease of testing
4. Chọn phương án tốt hơn và ghi rõ lý do trong CHANGELOG

**Áp dụng cho:** Thêm platform service mới, thay đổi `BaseModule` interface, thêm permission type mới, thiết kế module phức tạp đa-tab.

---

## 10. Cập nhật roadmap

### 2026-03-24

ADDED | OpenAI GPT-5.4 Thinking | Khởi tạo roadmap phát triển chuẩn cho Integrated Interactive Module Platform từ giai đoạn đặc tả đến đóng gói phát hành. Xác định phase, sprint, acceptance criteria, bug tracker khởi tạo và bộ hướng dẫn bắt buộc cho AI Agent.

### 2026-07-14

COMPLETED | GitHub Copilot (Claude Sonnet 4.6) | Phase 1 Foundation and App Shell — 100%.

- Khởi tạo toàn bộ cấu trúc thư mục chuẩn theo IIMP_ARCHITECTURE.md
- `config/` (paths, settings, database), `core/utils/` (constants, exceptions, logger, helpers, validators)
- `core/storage/` (models 7 bảng, connection, session, alembic migrations)
- `core/app_kernel/` (bootstrap, startup_checks, lifecycle, shutdown_manager)
- `core/module_runtime/` (base_module, manifest_schema, loader, module_context, registry, discovery, event_bus, state_manager, sandbox_policy)
- `core/services/` (module_service, settings_service, activity_service, export_service, path_service, ui_services, permission_service, workspace_service)
- `ui/` (main_window, 6 views, module_host_frame, status_strip, module_card, QSS light theme)
- `tests/` (conftest, unit tests: manifest, helpers, registry; integration: discovery)
- `main.py` — entry point đầy đủ
- `modules/templates/starter_module/` — template hoàn chỉnh

COMPLETED | GitHub Copilot (Claude Sonnet 4.6) | Phase 2 Module Runtime and Registry — 100%.

- Tất cả components runtime đã được implement trong cùng sprint với Phase 1

COMPLETED | GitHub Copilot (Claude Sonnet 4.6) | Phase 3 Unified UI and Workspace — 100%.

- dashboard_view.py: real DB stats (total/enabled/disabled module counts) + activity feed (last 20 records)
- module_manager_view.py: full enable/disable/uninstall/install-local UI với confirmation dialogs, DI via set_services()
- activity_history_view.py: QTableWidget, type filter, 200-row query, color-coded event types
- settings_view.py: all 4 app settings keys (theme, log_level, max_recent, restore_state) với DB persistence
- _navigate() refreshes data-driven views (refresh() called on navigation)

COMPLETED | GitHub Copilot (Claude Sonnet 4.6) | Phase 5 Persistence and Module Manager — 90%.

- ModuleService: enable_module(), disable_module(), uninstall_module(), install_local_module() đã triển khai
- ModuleRegistry: unregister() đã thêm
- main.py: settings_service passed to MainWindow; APP_START/APP_SHUTDOWN activity logs đã có
- Còn open: workspace_items support, backup/restore DB

COMPLETED | GitHub Copilot (Claude Sonnet 4.6) | Phase 4 First-party Modules and SDK — 100%.

- `modules/statistics/normal_distribution/` hoàn chỉnh: module.json, entry.py, module.py, README.md, tests/ (3 files)
- `NormalDistributionModule` port từ C4_Mo_phong_phan_phoi_chuan.py với Qt canvas, state persistence, export PNG
- `modules/visualization/interactive_geometry/` — module 3D mới v1.0.0:
  - 5 hình dạng (sine_2d, paraboloid, saddle, sphere, torus), điều khiển góc nhìn, colormap, resolution
  - module.json, entry.py, module.py (compute_surface + surface_stats + full Qt widget), README.md
  - tests/: test_manifest.py (9 tests), test_geometry_core.py (48 tests), test_smoke_ui.py (3 Qt tests)
  - 57 tests mới, 0 failures
- `modules/templates/headless_test_module/` — template không cần PySide6 cho CI
- `docs/module_sdk.md` — step-by-step dev guide với code mẫu, test patterns, checklist

ADDED | OpenAI GPT-5.4 Thinking | Đặt module mô phỏng phân phối chuẩn làm reference module đầu tiên cho phase xây dựng first-party modules, dùng để kiểm tra loader, host frame, export, persistence và UX của nền tảng.

### 2026-03-25

COMPLETED | GitHub Copilot (Claude Sonnet 4.6) | Exponential Distribution Explorer module v1.0.0.

- `modules/statistics/exponential_distribution/` — module thống kê mới hoàn chỉnh:
  - **Tab 1 — Phân phối Exp(μ)**: vẽ PDF với đường trung bình (μ), trung vị (m), tô vùng P(0≤X≤μ)≈63,21%
  - **Tab 2 — x → Xác suất**: tính P(X≤x), P(X>x), P(a≤X≤b) kèm tô màu diện tích tương ứng
  - State persistence: μ, tab, mode, x/a/b, precision lưu/restore qua session
  - Export PNG qua ExportService
  - `module.json`, `entry.py`, `module.py`, `__init__.py`, `README.md`, `CHANGELOG.md`
  - `tests/`: test_manifest.py (8 tests), test_calculator.py (22 tests), test_smoke_ui.py (11 tests)
  - **41 tests, 0 failures**

### 2026-03-26

COMPLETED | GitHub Copilot (Claude Sonnet 4.6) | Phase 6 Testing, Packaging, Release — 95%.

- UI smoke tests: `tests/ui/conftest.py` + `tests/ui/test_smoke_shell.py` — 14 tests (skip gracefully khi không có PySide6)
  - DashboardView, ModuleLibraryView, ModuleManagerView, SettingsView, ActivityHistoryView, MainWindow
  - `patched_db` fixture cô lập in-memory SQLite cho mỗi test
- Inno Setup installer script: `scripts/release/iimp_setup.iss`
  - AppId, versioning, compression lzma2/ultra64, ArchitecturesAllowed=x64
  - [Dirs] tạo user data dirs khi install, [Code] uninstall previous version tự động
  - Sẵn sàng chạy với ISCC.exe sau khi build PyInstaller xong
- Tổng test suite: 264 passed, 23 skipped, 0 failures
- Còn 2 items cần thực hiện thủ công: Windows standalone test + sample installer validation (yêu cầu máy không có Python)

### 2026-03-27

RESOLVED | GitHub Copilot (Claude Opus 4.6) | BUG-02 — Dependency fallback strategy.

- `core/utils/imports.py` — `safe_import()` + `check_dependencies()` helper
- `core/module_runtime/manifest_schema.py` — thêm field `optional_dependencies: list[str]`
- `core/module_runtime/loader.py` — `check_optional_dependencies()` pre-check trước import; `DependencyMissingError` raised khi thiếu
- `core/utils/exceptions.py` — thêm `DependencyMissingError(ModuleLoadError)`
- `tests/unit/test_imports.py` — 8 tests cho safe_import + check_dependencies
- `tests/unit/test_dependency_check.py` — 9 tests cho loader pre-check + manifest schema
- **17 tests mới, 0 failures**

RESOLVED | GitHub Copilot (Claude Opus 4.6) | BUG-03 — State format versioning.

- `core/module_runtime/base_module.py` — thêm `migrate_state(old_state, old_version) → dict` hook
- `core/module_runtime/state_manager.py` — `save_state()` auto-inject `_state_version` từ manifest `data_contract_version`; `restore_state()` version check + migration pipeline
- `tests/integration/test_state_versioning.py` — 9 tests: injection, match/mismatch, migration success/failure, legacy compat
- **9 tests mới, 0 failures**
- Tổng test suite: **595 passed**

### Entry 6 — BUG-05: Performance khi load nhiều module

RESOLVED | GitHub Copilot (Claude Opus 4.6) | BUG-05 — Startup performance optimization.

- `config/paths.py` — thêm `CACHE_DIR` cho manifest cache
- `core/module_runtime/manifest_cache.py` — **ManifestCache** class: mtime-based cache cho parsed manifests, save/load JSON, invalidate/clear API
- `core/module_runtime/discovery.py` — tích hợp ManifestCache (skip re-parse nếu module.json không đổi) + `on_progress` callback cho splash screen
- `core/services/module_service.py` — batch DB sync: single `session.query().all()` thay vì N `filter_by()` queries; forward `on_progress` callback
- `ui/widgets/splash_screen.py` — **StartupSplash** widget: progress bar + status label, shown during discovery
- `main.py` — tích hợp splash screen: show trước discovery, update progress, finish trước MainWindow.show()
- `tests/unit/test_manifest_cache.py` — 8 tests: cache miss/hit, mtime invalidation, save/reload, clear, corrupt file
- `tests/integration/test_discovery_perf.py` — 6 tests: progress callback, cache integration
- `tests/unit/test_batch_sync.py` — 1 test: batch query verification
- **15 tests mới, 0 failures**
- Tổng test suite: **610 tests (513 passed, 97 skipped)**

### 2026-04-13

COMPLETED | GitHub Copilot (Claude Sonnet 4.6) | PSO — Tối ưu hóa Bầy đàn module v1.0.0 — Phase 4 First-party Modules.

- `modules/quantitative_methods/particle_swarm_optimization/` — module mới hoàn chỉnh:
  - Subcategory `optimization` đã được thêm vào `quantitative_methods`
  - **Core engine** (pure Python, headless testable):
    - `core/objective_functions.py` — Sphere + Ackley + registry pattern (dễ thêm hàm mới)
    - `core/particle.py` — Lớp Particle với pbest update
    - `core/swarm.py` — Lớp Swarm: step() + run(), topology Star/Ring, boundary Clip/Reflect, inertia linear decay
  - **Models**: `models/config.py` (PSOConfig dataclass), `models/state.py` (STATE_VERSION + default_state)
  - **Worker**: `workers/simulation_worker.py` — `SimulationWorker(QThread)`, emit iteration_done/simulation_done/error_occurred — không block UI thread
  - **Module UI**: `module.py` — split-panel (controls left, tabs right):
    - Tab 0: Không gian 2D — contour nền + particle scatter + gBest marker (cập nhật mỗi 5 iter)
    - Tab 1: Đồ thị hội tụ — gBest fitness theo vòng lặp (cập nhật mỗi iter)
    - Control panel: đầy đủ tham số PSO, nút Chạy/Dừng, progress bar, kết quả, export
  - **BaseModule**: on_load, build_view, on_activate, on_deactivate, on_unload (stop worker + wait), get_state, restore_state
  - Export PNG qua ExportService (ask_save_path + write_bytes)
  - State persistence: config + last_gbest + convergence_history
  - `module.json`, `entry.py`, `README.md`
  - `tests/`: test_manifest.py (6 tests), test_objective_functions.py (16 tests), test_particle.py (6 tests), test_swarm.py (22 tests), test_smoke_ui.py (6 tests)
  - **56 tests, 0 failures**

---

### 2026-07-14

COMPLETED | GitHub Copilot (Claude Sonnet 4.6) | PSO — Tối ưu hóa Giao hàng module v1.0.0 — Phase 4 First-party Modules.

- `modules/quantitative_methods/pso_logistics/` — module mới hoàn chỉnh:
  - Subcategory `optimization`, bài toán **TSP v1.0** (Travelling Salesman Problem — 1 xe, thăm tất cả điểm)
  - **Không gian tìm kiếm rời rạc** (permutation space) — khác với PSO vector liên tục
  - **Core engine** (pure Python, headless testable):
    - `core/operators.py` — swap / insert / reverse\_segment / move\_toward / apply\_random\_ops
    - `core/route_evaluator.py` — build\_distance\_matrix (n+1)×(n+1), tsp\_tour\_distance
    - `core/discrete_particle.py` — DiscreteParticle với \_\_slots\_\_, update\_pbest()
    - `core/discrete_swarm.py` — DiscreteSwarm: step() + run(), topology Star/Ring, stochastic n\_ops rule
  - **Models**: `models/entities.py` (Depot+Customer+Vehicle+Route), `models/config.py` (LogisticsPSOConfig), `models/state.py` (STATE\_VERSION="1.0.0")
  - **Problem**: `problems/tsp_problem.py` — TSPProblem.generate(seed) — deterministic từ data\_seed, evaluate(), decode\_route\_ids()
  - **Worker**: `workers/simulation_worker.py` — SimulationWorker(QThread); tái sinh TSPProblem trong worker từ cùng seed → thread-safe, không truyền object qua boundary
  - **Module UI**: `module.py` — split-panel (controls 300px left, QTabWidget right):
    - Tab 0 "Bản đồ Tuyến đường" — RouteMapCanvas: depot + customers + best-route polyline + faded particle routes
    - Tab 1 "Đồ thị Hội tụ" — ConvergenceCanvas: gbest fitness vs iteration
    - 2 loại animation tách biệt (D3): PSO iteration via QThread signal; Replay via QTimer sau khi xong
  - **Manifest** `module.json` — IIMP SDK 1.0.0, permissions đầy đủ, supports\_state\_restore+supports\_export
  - **Tests**: 64 tests, 0 failures
    - test\_manifest.py — 6 tests
    - test\_operators.py — 12 tests
    - test\_tsp\_problem.py — 12 tests
    - test\_discrete\_swarm.py — 15 tests (including ring/star topology, stop\_flag, reproducibility, callback)
    - test\_smoke\_ui.py — 6 tests (build\_view, lifecycle, get\_state, restore\_state)

### 2026-05-05

ADDED | GitHub Copilot (Claude Sonnet 4.6) | DESIGN_PHILOSOPHY_INTEGRATION | Tích hợp nguyên tắc quản lý complexity từ A Philosophy of Software Design:
- Bổ sung §9.5 "Nguyên tắc phát triển bền vững" với 3 subsection:
  - §9.5.1: Ngân sách technical debt (10–20% effort/sprint cho cleanup)
  - §9.5.2: Design review checklist trước mỗi Phase mới
  - §9.5.3: Quy tắc "Design It Twice" cho quyết định architectural quan trọng
- Các nguyên tắc này đồng bộ với §2.3 trong IIMP_ARCHITECTURE.md và §2.3 trong IIMP_MODULE_SDK.md

### 2026-05-16

COMPLETED | GitHub Copilot (GPT-5.4) | GitHub repository publication.

- Khởi tạo Git repository cục bộ và nối với remote `vuquangvinh1004/IIM-Platform`
- Publish toàn bộ source hiện tại lên `origin/main`
- Chuẩn hóa `.gitignore` để loại `node_modules/`, cache runtime và dữ liệu bản đồ cỡ lớn khỏi lịch sử push
- Loại file `modules/logistics/pso_logistics_map/vietnam-260413.osm.pbf` khỏi lịch sử publish để đáp ứng giới hạn 100 MB của GitHub

---

END OF ROADMAP DOCUMENT

Last Updated: 2026-07-14
Version: 1.0.0-rc2
