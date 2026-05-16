# CHANGELOG — Exponential Distribution Explorer

All notable changes to this module are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

---

## [1.0.0] — 2026-03-25

### Added
- Initial release of Exponential Distribution Explorer
- **Tab 1 — Phân phối Exp(μ)**: vẽ đường cong PDF với μ tùy chọn, đánh dấu
  trung bình (μ) và trung vị (m), tô vùng P(0≤X≤μ) ≈ 63,21%
- **Tab 2 — x → Xác suất**: tính và vẽ P(X≤x), P(X>x), P(a≤X≤b) với tô màu
  diện tích tương ứng dưới đường cong
- State persistence: lưu μ, tab hiện tại, mode, x/a/b và precision qua session
- Export PNG qua ExportService
- Tính chất không nhớ (memoryless) được chú thích trong Tab 1
- Bộ test đầy đủ: test_manifest, test_calculator (pure), test_smoke_ui (Qt)
