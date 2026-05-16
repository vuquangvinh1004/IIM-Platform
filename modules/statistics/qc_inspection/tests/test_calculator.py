"""Unit tests for QCInspectionEngine — pure Python, no Qt/matplotlib required."""
from __future__ import annotations

import random

import pytest

from modules.statistics.qc_inspection.module import (
    DEFAULT_N_PRODUCTS,
    DEFAULT_N_ROUNDS,
    MAX_PRODUCTS,
    QCInspectionEngine,
    QCRecord,
)


# ---------------------------------------------------------------------------
# QCRecord
# ---------------------------------------------------------------------------


class TestQCRecord:
    def test_rate_normal(self):
        rec = QCRecord(1, 10, 3)
        assert abs(rec.rate - 0.30) < 1e-12

    def test_rate_zero_defects(self):
        rec = QCRecord(1, 10, 0)
        assert rec.rate == 0.0

    def test_rate_all_defects(self):
        rec = QCRecord(1, 10, 10)
        assert rec.rate == 1.0

    def test_rate_zero_total(self):
        rec = QCRecord(1, 0, 0)
        assert rec.rate == 0.0


# ---------------------------------------------------------------------------
# Initial state
# ---------------------------------------------------------------------------


class TestInitialState:
    def test_default_n_products(self):
        eng = QCInspectionEngine()
        assert eng.n_products == DEFAULT_N_PRODUCTS

    def test_default_n_rounds(self):
        eng = QCInspectionEngine()
        assert eng.n_rounds == DEFAULT_N_ROUNDS

    def test_no_records(self):
        assert QCInspectionEngine().records == []

    def test_rounds_done_zero(self):
        assert QCInspectionEngine().rounds_done == 0

    def test_not_complete(self):
        assert not QCInspectionEngine().is_complete

    def test_not_pending(self):
        assert not QCInspectionEngine().is_pending_record

    def test_total_products_zero(self):
        assert QCInspectionEngine().total_products == 0

    def test_total_defects_zero(self):
        assert QCInspectionEngine().total_defects == 0

    def test_empirical_p_zero(self):
        assert QCInspectionEngine().empirical_p == 0.0


# ---------------------------------------------------------------------------
# Configure
# ---------------------------------------------------------------------------


class TestConfigure:
    def test_configure_sets_values(self):
        eng = QCInspectionEngine()
        eng.configure(20, 15)
        assert eng.n_products == 20
        assert eng.n_rounds == 15

    def test_configure_clamps_min(self):
        eng = QCInspectionEngine()
        eng.configure(0, 0)
        assert eng.n_products == 1
        assert eng.n_rounds == 1

    def test_configure_clamps_max_products(self):
        eng = QCInspectionEngine()
        eng.configure(MAX_PRODUCTS + 10, 5)
        assert eng.n_products == MAX_PRODUCTS


# ---------------------------------------------------------------------------
# generate_round
# ---------------------------------------------------------------------------


class TestGenerateRound:
    def test_returns_list_of_bool(self):
        eng = QCInspectionEngine()
        eng.configure(10, 5)
        products = eng.generate_round()
        assert len(products) == 10
        assert all(isinstance(v, bool) for v in products)

    def test_marks_pending(self):
        eng = QCInspectionEngine()
        eng.configure(5, 3)
        eng.generate_round()
        assert eng.is_pending_record

    def test_pending_false_before_generate(self):
        assert not QCInspectionEngine().is_pending_record

    def test_length_matches_n_products(self):
        random.seed(42)
        eng = QCInspectionEngine()
        eng.configure(15, 3)
        products = eng.generate_round()
        assert len(products) == 15


# ---------------------------------------------------------------------------
# record_manual
# ---------------------------------------------------------------------------


class TestRecordManual:
    def test_increases_rounds_done(self):
        eng = QCInspectionEngine()
        eng.configure(10, 5)
        eng.generate_round()
        eng.record_manual([0, 2])
        assert eng.rounds_done == 1

    def test_defect_count_from_selection(self):
        eng = QCInspectionEngine()
        eng.configure(10, 5)
        eng.generate_round()
        rec = eng.record_manual([1, 3, 5])
        assert rec.defects == 3

    def test_total_matches_n_products(self):
        eng = QCInspectionEngine()
        eng.configure(12, 5)
        eng.generate_round()
        rec = eng.record_manual([])
        assert rec.total == 12

    def test_clears_pending_state(self):
        eng = QCInspectionEngine()
        eng.configure(8, 3)
        eng.generate_round()
        eng.record_manual([0])
        assert not eng.is_pending_record

    def test_zero_defects_allowed(self):
        eng = QCInspectionEngine()
        eng.configure(10, 5)
        eng.generate_round()
        rec = eng.record_manual([])
        assert rec.defects == 0
        assert rec.rate == 0.0

    def test_round_numbers_increment(self):
        eng = QCInspectionEngine()
        eng.configure(5, 4)
        round_nos = []
        for _ in range(4):
            eng.generate_round()
            rec = eng.record_manual([])
            round_nos.append(rec.round_no)
        assert round_nos == [1, 2, 3, 4]


# ---------------------------------------------------------------------------
# auto_complete
# ---------------------------------------------------------------------------


class TestAutoComplete:
    def test_fills_all_remaining(self):
        eng = QCInspectionEngine()
        eng.configure(10, 8)
        new_recs = eng.auto_complete()
        assert len(new_recs) == 8
        assert eng.is_complete

    def test_only_fills_remaining_after_manual(self):
        eng = QCInspectionEngine()
        eng.configure(10, 5)
        eng.generate_round()
        eng.record_manual([])
        new_recs = eng.auto_complete()
        assert len(new_recs) == 4
        assert eng.rounds_done == 5

    def test_total_products_correct(self):
        eng = QCInspectionEngine()
        eng.configure(10, 6)
        eng.auto_complete()
        assert eng.total_products == 60

    def test_defects_in_valid_range(self):
        eng = QCInspectionEngine()
        eng.configure(20, 20)
        eng.auto_complete()
        for rec in eng.records:
            assert 0 <= rec.defects <= 20

    def test_clears_pending_state(self):
        eng = QCInspectionEngine()
        eng.configure(5, 3)
        eng.generate_round()
        eng.auto_complete()
        assert not eng.is_pending_record


# ---------------------------------------------------------------------------
# is_complete
# ---------------------------------------------------------------------------


class TestIsComplete:
    def test_complete_after_all_rounds(self):
        eng = QCInspectionEngine()
        eng.configure(5, 3)
        for _ in range(3):
            eng.generate_round()
            eng.record_manual([])
        assert eng.is_complete

    def test_not_complete_before_last(self):
        eng = QCInspectionEngine()
        eng.configure(5, 3)
        eng.generate_round()
        eng.record_manual([])
        assert not eng.is_complete


# ---------------------------------------------------------------------------
# Statistics
# ---------------------------------------------------------------------------


class TestStatistics:
    def test_total_products_accumulated(self):
        eng = QCInspectionEngine()
        eng.configure(10, 3)
        for _ in range(3):
            eng.generate_round()
            eng.record_manual([])
        assert eng.total_products == 30

    def test_empirical_p_correct(self):
        eng = QCInspectionEngine()
        eng.configure(10, 2)
        eng.generate_round()
        eng.record_manual([0, 1, 2])   # 3 defects
        eng.generate_round()
        eng.record_manual([0])         # 1 defect
        # total_products=20, total_defects=4, p=0.2
        assert abs(eng.empirical_p - 0.2) < 1e-12

    def test_frequency_table_counts(self):
        eng = QCInspectionEngine()
        eng.configure(10, 4)
        eng.generate_round(); eng.record_manual([0, 1])       # 2 defects
        eng.generate_round(); eng.record_manual([0])           # 1 defect
        eng.generate_round(); eng.record_manual([0, 1])       # 2 defects
        eng.generate_round(); eng.record_manual([])            # 0 defects
        freq = eng.frequency_table()
        assert freq[0] == 1
        assert freq[1] == 1
        assert freq[2] == 2

    def test_frequency_table_empty_initially(self):
        assert QCInspectionEngine().frequency_table() == {}


# ---------------------------------------------------------------------------
# Reset
# ---------------------------------------------------------------------------


class TestReset:
    def test_reset_clears_records(self):
        eng = QCInspectionEngine()
        eng.configure(5, 2)
        eng.auto_complete()
        eng.reset()
        assert eng.records == []

    def test_reset_clears_pending(self):
        eng = QCInspectionEngine()
        eng.configure(5, 2)
        eng.generate_round()
        eng.reset()
        assert not eng.is_pending_record

    def test_reset_keeps_config(self):
        eng = QCInspectionEngine()
        eng.configure(15, 7)
        eng.auto_complete()
        eng.reset()
        assert eng.n_products == 15
        assert eng.n_rounds == 7


# ---------------------------------------------------------------------------
# State round-trip
# ---------------------------------------------------------------------------


class TestStateRoundTrip:
    def test_get_state_returns_dict(self):
        eng = QCInspectionEngine()
        state = eng.get_state()
        assert isinstance(state, dict)
        assert "state_version" in state

    def test_restore_state_rehydrates(self):
        eng = QCInspectionEngine()
        eng.configure(10, 3)
        eng.auto_complete()
        state = eng.get_state()

        eng2 = QCInspectionEngine()
        eng2.restore_state(state)
        assert eng2.n_products == 10
        assert eng2.n_rounds == 3
        assert eng2.rounds_done == 3
        assert eng2.is_complete

    def test_restore_empty_state_uses_defaults(self):
        eng = QCInspectionEngine()
        eng.restore_state({})
        assert eng.n_products == DEFAULT_N_PRODUCTS
        assert eng.n_rounds == DEFAULT_N_ROUNDS
        assert eng.records == []

    def test_restore_never_sets_pending(self):
        """Pending round must never survive serialisation."""
        eng = QCInspectionEngine()
        eng.configure(5, 2)
        eng.generate_round()
        state = eng.get_state()

        eng2 = QCInspectionEngine()
        eng2.restore_state(state)
        assert not eng2.is_pending_record


# ---------------------------------------------------------------------------
# Configurable defect rate
# ---------------------------------------------------------------------------


class TestDefectRate:
    """Tests for user-configurable defect probability."""

    def test_default_defect_prob(self):
        eng = QCInspectionEngine()
        assert eng.defect_prob == 0.25

    def test_configure_with_custom_rate(self):
        eng = QCInspectionEngine()
        eng.configure(10, 5, defect_prob=0.10)
        assert abs(eng.defect_prob - 0.10) < 1e-12

    def test_configure_without_rate_keeps_default(self):
        eng = QCInspectionEngine()
        eng.configure(10, 5)
        assert eng.defect_prob == 0.25

    def test_configure_clamps_min_rate(self):
        eng = QCInspectionEngine()
        eng.configure(10, 5, defect_prob=0.001)
        assert eng.defect_prob == 0.01

    def test_configure_clamps_max_rate(self):
        eng = QCInspectionEngine()
        eng.configure(10, 5, defect_prob=1.5)
        assert eng.defect_prob == 1.0

    def test_low_rate_produces_fewer_defects(self):
        random.seed(123)
        eng = QCInspectionEngine()
        eng.configure(40, 50, defect_prob=0.05)
        eng.auto_complete()
        avg_rate = eng.empirical_p
        assert avg_rate < 0.15  # should be around 0.05

    def test_high_rate_produces_more_defects(self):
        random.seed(123)
        eng = QCInspectionEngine()
        eng.configure(40, 50, defect_prob=0.80)
        eng.auto_complete()
        avg_rate = eng.empirical_p
        assert avg_rate > 0.60  # should be around 0.80

    def test_defect_prob_persisted_in_state(self):
        eng = QCInspectionEngine()
        eng.configure(10, 5, defect_prob=0.15)
        state = eng.get_state()
        assert state["defect_prob"] == 0.15

        eng2 = QCInspectionEngine()
        eng2.restore_state(state)
        assert abs(eng2.defect_prob - 0.15) < 1e-12

    def test_defect_prob_property(self):
        eng = QCInspectionEngine()
        eng._defect_prob = 0.42
        assert eng.defect_prob == 0.42
