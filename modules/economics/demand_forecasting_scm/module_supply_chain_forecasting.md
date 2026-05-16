# TÀI LIỆU THIẾT KẾ MODULE: MÔ PHỎNG DỰ BÁO NHU CẦU (SCM)

> **Phiên bản:** 2.0.0 (IIMP-compatible)
> **Cập nhật:** 12/04/2026
> **Trạng thái:** Phase 1 — Sẵn sàng triển khai
> **Thay thế:** v1.0.0 (Streamlit/Plotly) — không tương thích IIMP

---

## 0. Ghi chú điều chỉnh kiến trúc

Phiên bản gốc (v1.0.0) được thiết kế với Streamlit/Plotly. Tài liệu này là bản điều chỉnh
bắt buộc để tương thích với nền tảng IIMP:

| Quyết định | Lý do |
|---|---|
| Thay Streamlit → PySide6 | Streamlit tạo HTTP server riêng, không thể nhúng vào ModuleHostFrame (QWidget) của IIMP shell |
| Thay Plotly web → matplotlib FigureCanvasQTAgg | Plotly JS-based không tương thích Qt widget tree; matplotlib là stack chính thức của IIMP |
| Animation dự báo → QTimer + vẽ từng điểm | Thay thế Plotly animation, đúng hơn với Qt event loop |
| Pop-up/Overlay → QDialog modal | Cấm mở cửa sổ độc lập từ module theo IIMP_MODULE_SDK.md §2.2 |
| Chia 2 phase | Giảm phạm vi mỗi module xuống mức có thể test và bảo trì |
| Thêm statsmodels | Được phép theo IIMP_ARCHITECTURE.md §3.2 ("optional có ưu tiên") |

---

## 1. Thông tin module

| Thuộc tính | Giá trị |
|---|---|
| Module ID | `demand_forecasting_scm` |
| Tên hiển thị | Mô phỏng Dự báo Nhu cầu (SCM) |
| Category | `economics` |
| Thư mục | `modules/economics/demand_forecasting_scm/` |
| SDK version | `1.0.0` |
| min_platform_version | `1.0.0` |
| Permissions | `storage.read`, `storage.write`, `export.file`, `settings.read`, `settings.write` |
| supports_state_restore | `true` |
| supports_export | `true` |

---

## 2. Mục tiêu & phạm vi

**Mục tiêu nghiệp vụ:** Công cụ giáo dục và phân tích giúp người dùng đi từ dữ liệu chuỗi
thời gian thô đến việc lựa chọn mô hình dự báo nhu cầu tối ưu, đánh giá sai số và kiểm soát
độ chính xác theo thời gian.

**Đối tượng:** Sinh viên, giảng viên, nhà phân tích chuỗi cung ứng.

---

## 3. Lộ trình triển khai (2 Phase)

### Phase 1 — Core (triển khai trước, mục tiêu ổn định)

| Tab | Nội dung | Phương pháp |
|---|---|---|
| Tab 0: Data Hub | Nhập dữ liệu, làm sạch, vẽ biểu đồ, Smart Suggestion | — |
| Tab 1: Mẫu hình Ổn định | Sub-tabs: Thông tin chung + 3 phương pháp | Naive, Moving Average (MA), SES |
| Tab 2: Mẫu hình Xu hướng | Sub-tabs: Thông tin chung + 2 phương pháp | Linear Regression, Holt's Model |
| Panel Dự báo | QDialog modal, có animation QTimer | Hold-out validation |
| Panel Kiểm soát | QDialog modal | Tracking Signal, Control Chart |

### Phase 2 — Advanced (sau khi Phase 1 ổn định)

| Tab | Nội dung | Phương pháp |
|---|---|---|
| Tab 3: Mẫu hình Mùa vụ | Sub-tabs | Decomposition (cộng tính/nhân tính), Winters' Model |
| Tab 4: Mẫu hình Chu kỳ | Sub-tabs | Causal Models (hồi quy đa biến) |
| Tab 5: Mô hình Nâng cao | Sub-tabs | ARIMA (p, d, q) |

---

## 4. Tech stack (IIMP-compliant)

| Thành phần | Công nghệ | Ghi chú |
|---|---|---|
| UI framework | PySide6 QWidget | Stack chính thức IIMP |
| Đồ thị | matplotlib FigureCanvasQTAgg | Stack chính thức IIMP |
| Animation dự báo | QTimer + redraw từng điểm | Qt-native, không blocking |
| Navigation chính | QTabWidget | setTabEnabled(index, False) để khóa tab |
| Sub-tabs trong tab | Nested QTabWidget | |
| Nhập dữ liệu bảng | QTableWidget editable | |
| Import CSV/Excel | QFileDialog + pandas.read_csv/read_excel | |
| Tham số slider | QSlider + QDoubleSpinBox + valueChanged signal | Realtime recalc |
| Bảng kết quả | QTableWidget read-only | |
| Panel Dự báo/Kiểm soát | QDialog (modal) | KHÔNG tạo standalone window |
| Cấu hình module | IIMP SettingsService | Persistent qua platform |
| State persistence | IIMP StateManager | get_state() / restore_state() |
| Export | IIMP ExportService | Xuất PNG đồ thị |
| Tính toán dự báo | statsmodels, numpy, pandas | statsmodels được phê duyệt |
| Smart Suggestion | statsmodels.tsa.stattools.adfuller (ADF test), numpy | |

---

## 5. Cấu trúc thư mục chuẩn (IIMP SDK §4)

```
modules/economics/demand_forecasting_scm/
├── module.json              ← manifest đầy đủ (bắt buộc)
├── entry.py                 ← export DemandForecastingModule
├── module.py                ← class DemandForecastingModule(BaseModule)
├── README.md
├── CHANGELOG.md
├── __init__.py
├── assets/
│   └── icon.png
├── ui/
│   ├── __init__.py
│   ├── main_view.py         ← QWidget gốc, QTabWidget navigation
│   ├── data_hub_tab.py      ← Tab 0: Data Hub
│   ├── stationary_tab.py    ← Tab 1: Mẫu hình Ổn định (Phase 1)
│   ├── trend_tab.py         ← Tab 2: Mẫu hình Xu hướng (Phase 1)
│   ├── method_view.py       ← Widget dùng chung cho mỗi phương pháp
│   ├── forecast_dialog.py   ← QDialog: Dự báo (animation + hold-out)
│   ├── control_dialog.py    ← QDialog: Kiểm soát (TS + Control Chart)
│   └── config_dialog.py     ← QDialog: Cấu hình benchmark, TS threshold
├── services/
│   ├── __init__.py
│   ├── forecasting_engine.py    ← Naive, MA, SES, Holt, Linear Regression
│   ├── error_metrics.py         ← MAE, RMSE, MAPE, Bias, TS, FVA
│   ├── data_analyzer.py         ← Smart Suggestion, outlier detection
│   └── chart_builder.py         ← matplotlib figure factories
├── models/
│   ├── __init__.py
│   ├── inputs.py                ← ForecastingInput, DataSet
│   ├── outputs.py               ← ForecastResult, ErrorMetrics
│   └── state.py                 ← ModuleState (version hóa)
└── tests/
    ├── __init__.py
    ├── test_manifest.py
    ├── test_forecasting_engine.py
    ├── test_error_metrics.py
    ├── test_data_analyzer.py
    └── test_smoke_ui.py
```

---

## 6. Cấu trúc UI Phase 1

### 6.1. Navigation chính

```
QWidget (root từ build_view())
└── QVBoxLayout
    ├── toolbar_bar (QWidget) — nút "Cấu hình" góc phải
    └── QTabWidget (main_tabs) — horizontal tabs
        ├── Tab 0: "Thiết lập chung" (Data Hub)      ← luôn enabled
        ├── Tab 1: "Mẫu hình Ổn định"                ← disabled cho đến khi unlock
        ├── Tab 2: "Mẫu hình Xu hướng"               ← disabled cho đến khi unlock
        ├── Tab 3: "[Mùa vụ — Phase 2]"               ← disabled, grayed out
        ├── Tab 4: "[Chu kỳ — Phase 2]"               ← disabled, grayed out
        └── Tab 5: "[Nâng cao — Phase 2]"             ← disabled, grayed out
```

### 6.2. Tab 0 — Data Hub

```
DataHubTab (QWidget)
└── QVBoxLayout
    ├── header: QLabel + QPushButton "Nhập dữ liệu" + QPushButton "Cấu hình"
    ├── chart_area: FigureCanvasQTAgg — đồ thị Yt (ẩn trước khi có data)
    ├── data_info_bar: QLabel — "N điểm | Kỳ X đến Y | Outlier: có/không"
    ├── outlier_widget: QGroupBox "Làm sạch dữ liệu"
    │   └── QCheckBox "Phát hiện outlier" + QDoubleSpinBox ngưỡng σ
    └── suggestion_panel: QGroupBox "Gợi ý mẫu hình" (ẩn trước khi có data)
        ├── row Ổn định: QLabel + badge ADF + QPushButton "Phân tích Ổn định"
        └── row Xu hướng: QLabel + badge trend + QPushButton "Phân tích Xu hướng"
```

DataInputDialog (QDialog modal):
```
├── QTabWidget
│   ├── "Nhập tay": QTableWidget (2 cột: Kỳ t, Nhu cầu Yt) + Add/Remove row
│   └── "Tải file": QPushButton "Chọn CSV/Excel" + QLabel preview path
└── QPushButton "Xác nhận" | QPushButton "Hủy"
```

### 6.3. Tab Mẫu hình (Ổn định / Xu hướng)

```
PatternTab (QWidget)
└── QTabWidget (sub_tabs)
    ├── "Thông tin chung": FigureCanvasQTAgg (Yt) + QLabel mô tả phương pháp
    ├── "Naive"             (Ổn định)  → MethodView
    ├── "Moving Average"               → MethodView
    ├── "SES"               (Ổn định)  → MethodView
    ├── "Linear Regression" (Xu hướng) → MethodView
    └── "Holt's Model"      (Xu hướng) → MethodView
```

### 6.4. MethodView — Widget dùng chung

```
MethodView (QWidget)
└── QVBoxLayout
    ├── [KHUNG TRÊN] QSplitter horizontal
    │   ├── Trái: FigureCanvasQTAgg — Yt + Ft overlay
    │   └── Phải: QVBoxLayout controls
    │       ├── QGroupBox "Tham số"
    │       │   ├── "Số kỳ phân tích:" QSlider + QSpinBox (linked)
    │       │   └── Tham số riêng theo phương pháp:
    │       │       • MA:   "k:" QSpinBox
    │       │       • SES:  "α:" QDoubleSpinBox 0.01–1.0, step 0.01
    │       │       • Holt: "α:" QDoubleSpinBox + "β:" QDoubleSpinBox
    │       ├── QHBoxLayout nút chức năng:
    │       │   ├── QPushButton "Phân tích"
    │       │   ├── QPushButton "Dự báo"    (enabled sau Phân tích)
    │       │   └── QPushButton "Kiểm soát" (enabled sau Phân tích)
    │       └── QGroupBox "Tiêu chí sai số" (hiện sau Phân tích)
    │           ├── QFormLayout: MAE, RMSE, MAPE, Bias, Bias%
    │           └── QLabel "FVA so với Benchmark: X%"
    └── [KHUNG DƯỚI] QSplitter horizontal
        ├── Trái: FigureCanvasQTAgg — đồ thị sai số et
        └── Phải: QTableWidget — (t, Yt, Ft, et, et², |et|/Yt, CumBias)
```

Realtime: QDoubleSpinBox.valueChanged + QSlider.valueChanged → _recalculate() →
cập nhật đồ thị + bảng + metrics ngay lập tức.

### 6.5. ForecastDialog

```
ForecastDialog (QDialog, modal, resizable)
└── QVBoxLayout
    ├── FigureCanvasQTAgg
    │   • Yt: đường liền nét xanh
    │   • Ft training: đường nét đứt đỏ, xuất hiện dần qua QTimer (80ms/điểm)
    │   • Ft hold-out: đường nét đứt cam (nếu n_train < n_total)
    │   • Marker tròn tại mỗi điểm Ft
    ├── QGroupBox "Hold-out Validation" (hiện nếu có hold-out)
    │   └── QFormLayout: MAE, RMSE, MAPE trên tập validation
    └── QPushButton "Đóng"
```

### 6.6. ControlDialog

```
ControlDialog (QDialog, modal, resizable)
└── QVBoxLayout
    ├── QLabel "Ngưỡng Tracking Signal: ±X"
    ├── FigureCanvasQTAgg — Tracking Signal
    │   • Đường TS theo thời gian
    │   • Giới hạn ±threshold (ngang đỏ)
    │   • Vùng OK: xanh nhạt | Vi phạm: đỏ nhạt
    ├── FigureCanvasQTAgg — Control Chart
    │   • Đường et
    │   • Vùng ±1σ xanh nhạt | ±2σ vàng nhạt | ±3σ đỏ nhạt
    └── QPushButton "Đóng"
```

### 6.7. ConfigDialog

```
ConfigDialog (QDialog, modal)
└── QFormLayout
    ├── "Benchmark mặc định:" QComboBox ["Naive", "MA(2)", "MA(3)"]
    ├── "Ngưỡng Tracking Signal (±):" QDoubleSpinBox (default: 4.0)
    └── QPushButton "Lưu" | QPushButton "Hủy"
```

---

## 7. Danh sách phương pháp Phase 1

### 7.1. Mẫu hình Ổn định

| Phương pháp | Tham số | Thư viện |
|---|---|---|
| Naive | — | numpy |
| Moving Average (MA) | k (1–20) | numpy |
| Simple Exponential Smoothing (SES) | α (0.01–1.0) | statsmodels SimpleExpSmoothing hoặc numpy |

### 7.2. Mẫu hình Xu hướng

| Phương pháp | Tham số | Thư viện |
|---|---|---|
| Linear Regression | — (fit a, b tự động) | numpy.polyfit hoặc statsmodels.OLS |
| Holt's Model | α (mức độ), β (xu hướng) | statsmodels.tsa.holtwinters.Holt |

---

## 8. Các công thức then chốt

- e_t = Y_t - F_t
- MAE = sum(|e_t|) / n
- RMSE = sqrt(sum(e_t^2) / n)
- MAPE = (1/n) * sum(|e_t| / Y_t) * 100
- TS_t = sum(e_i, i=1..t) / MAD_t    (MAD_t ≈ MAE_t)
- FVA = (1 - MAE_model / MAE_benchmark) * 100%

Lưu ý: FVA > 0% nghĩa là model tốt hơn benchmark; FVA < 0% nghĩa là nên dùng benchmark.

---

## 9. Smart Suggestion — logic phân tích tự động

| Kiểm tra | Công cụ | Kết quả |
|---|---|---|
| Xu hướng tuyến tính | numpy.polyfit bậc 1, R² | Badge "Có xu hướng" nếu R² > 0.5 |
| Tính dừng (stationarity) | statsmodels.tsa.stattools.adfuller | Badge "Ổn định (p<0.05)" nếu p < 0.05 |
| Phát hiện mùa vụ | ACF statsmodels | Phase 2 — bỏ qua trong Phase 1 |

Badge màu:
- Xanh lá: gợi ý mạnh, nút "Phân tích..." được enable → unlock tab tương ứng
- Vàng: có khả năng
- Xám: không phát hiện, tab không unlock

---

## 10. State model (StateManager)

```python
# models/state.py
class DemandForecastingState:
    version: str = "1.0.0"
    dataset: list[dict]          # [{t: int, y: float}, ...]
    active_tab_index: int
    active_subtab_indices: dict  # {tab_name: subtab_index}
    method_params: dict          # {method_name: {param: value}}
    config: dict                 # benchmark, ts_threshold
    unlocked_tabs: list[str]     # ["stationary", "trend"]
```

---

## 11. Permissions & Host Services sử dụng

| Service | Mục đích |
|---|---|
| SettingsService | Lưu config (benchmark, TS threshold) |
| StateManager | Lưu/phục hồi dataset và trạng thái tab |
| ExportService | Export PNG đồ thị qua IIMP export flow |
| context.get_data_path() | Lấy đường dẫn lưu module data cục bộ |

---

## 12. Definition of Done — Phase 1

- [ ] module.json hợp lệ, pass manifest validation của IIMP
- [ ] DemandForecastingModule kế thừa đúng BaseModule, 5 lifecycle methods đầy đủ
- [ ] Tab 0 (Data Hub): nhập tay + import CSV/Excel hoạt động
- [ ] Tab 0: outlier detection bằng z-score hoạt động
- [ ] Tab 0: Smart Suggestion phát hiện trend + stationarity, unlock tab tương ứng
- [ ] Tab 1 (Ổn định): Naive, MA, SES — realtime recalc khi thay đổi tham số
- [ ] Tab 2 (Xu hướng): Linear Regression, Holt's Model — realtime recalc
- [ ] Bảng chi tiết (t, Yt, Ft, et, et², |et|/Yt, CumBias) hiển thị đúng
- [ ] Metrics MAE, RMSE, MAPE, Bias, Bias%, FVA tính đúng theo công thức
- [ ] ForecastDialog: animation QTimer, hold-out validation
- [ ] ControlDialog: Tracking Signal chart + Control Chart
- [ ] ConfigDialog: lưu/đọc benchmark và TS threshold qua SettingsService
- [ ] get_state() / restore_state() hoạt động
- [ ] export() xuất PNG đồ thị hiện tại qua ExportService
- [ ] Tests: manifest, forecasting_engine, error_metrics, data_analyzer, smoke UI
- [ ] Không crash shell khi unload

---

## 13. Hướng dẫn cho AI Agent

Khi triển khai Phase 1, agent phải:

1. Không dùng Streamlit, không dùng Plotly — dùng PySide6 + matplotlib
2. Tất cả widget là QWidget, không tự mở QMainWindow
3. Sử dụng FigureCanvasQTAgg từ matplotlib.backends.backend_qtagg
4. Animation dùng QTimer với interval 80ms, mỗi tick vẽ thêm 1 điểm Ft
5. Realtime recalc: QDoubleSpinBox.valueChanged và QSlider.valueChanged kết nối
   trực tiếp vào _recalculate()
6. ForecastDialog và ControlDialog phải là QDialog, không phải QWidget.show() standalone
7. Tất cả I/O file qua QFileDialog + đường dẫn từ host context
8. State lưu qua context.state_manager, không ghi file tự phát
9. Khi tạo module: validate module.json qua manifest_schema.py trước khi test
