# Changelog — QC Kiểm tra Chất lượng

Định dạng: [Phiên bản] — ngày — Tác giả — Mô tả

---

## [1.0.0] — 2026-03-26 — GitHub Copilot (Claude Sonnet 4.6)

### Added

- `QCInspectionEngine`: engine thuần Python — generate_round, record_manual, auto_complete, frequency_table, get_state/restore_state
- `_ProductWidget`: widget Qt vẽ sản phẩm bằng QPainter (thành phẩm ✓ xanh / phế phẩm ✕ đỏ, border xanh khi chọn)
- `_ProductGridFrame`: khay sản phẩm dạng lưới cuộn, tối đa 8 SP/hàng, nút Ghi nhận
- `_RecordsTable`: bảng kết quả (Lần | Tổng SP | Số PP | Tỷ lệ PP) với màu sắc phản hồi
- `_FreqTableWidget`: bảng tần số phế phẩm (k | Tần số | Tần suất)
- `_FreqChartCanvas`: biểu đồ cột tần số phế phẩm (matplotlib)
- `_DistributionCanvas`: 2 đồ thị cạnh nhau — Bin(n, p̂) và Po(μ=n·p̂) vs. tần suất thực tế
- `_SimulationView`: trang mô phỏng với thống kê tổng hợp, section tần số, section phân phối
- `_InspectionPage`: trang kiểm tra chính với header + description + controls + khay SP + bảng KQ
- `QCInspectionModule`: module chính kế thừa BaseModule, state persistence qua settings_service
- `module.json`: manifest đầy đủ (id, permissions, sdk_version, supports_state_restore)
- `tests/`: test_manifest (9 cases), test_calculator (28 cases), test_smoke_ui (13 cases)
