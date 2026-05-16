"""Unit tests for CLTEngine — pure Python, no Qt/matplotlib required."""
from __future__ import annotations

import math
import random

import pytest

from modules.statistics.central_limit_theorem.module import (
    DEFAULT_NORM_MEAN,
    DEFAULT_NORM_STD,
    DEFAULT_NUM_SAMPLES,
    DEFAULT_POP_MEAN,
    DEFAULT_POP_STD,
    DEFAULT_SAMPLE_SIZE,
    MAX_SAMPLE_SIZE,
    MAX_SAMPLES,
    CLTEngine,
    SampleRecord,
)


# ---------------------------------------------------------------------------
# SampleRecord
# ---------------------------------------------------------------------------


class TestSampleRecord:
    def test_n_returns_count(self):
        rec = SampleRecord(1, [100.0, 200.0, 300.0])
        assert rec.n == 3

    def test_mean_correct(self):
        rec = SampleRecord(1, [10.0, 20.0, 30.0])
        assert abs(rec.mean - 20.0) < 1e-10

    def test_std_sample_formula(self):
        # s = sqrt( sum((xi - xbar)^2) / (n-1) )
        rec = SampleRecord(1, [10.0, 20.0, 30.0])
        expected = math.sqrt(((10 - 20) ** 2 + (20 - 20) ** 2 + (30 - 20) ** 2) / 2)
        assert abs(rec.std - expected) < 1e-10

    def test_mean_single_value(self):
        rec = SampleRecord(1, [42.0])
        assert abs(rec.mean - 42.0) < 1e-10

    def test_std_single_value(self):
        rec = SampleRecord(1, [42.0])
        assert rec.std == 0.0

    def test_mean_empty_list(self):
        rec = SampleRecord(1, [])
        assert rec.mean == 0.0

    def test_std_empty_list(self):
        rec = SampleRecord(1, [])
        assert rec.std == 0.0


# ---------------------------------------------------------------------------
# Initial state
# ---------------------------------------------------------------------------


class TestInitialState:
    def test_default_sample_size(self):
        eng = CLTEngine()
        assert eng.sample_size == DEFAULT_SAMPLE_SIZE

    def test_default_num_samples(self):
        eng = CLTEngine()
        assert eng.num_samples == DEFAULT_NUM_SAMPLES

    def test_default_pop_mean(self):
        eng = CLTEngine()
        assert eng.pop_mean == DEFAULT_POP_MEAN

    def test_default_pop_std(self):
        eng = CLTEngine()
        assert eng.pop_std == DEFAULT_POP_STD

    def test_default_norm_mean(self):
        eng = CLTEngine()
        assert eng.norm_mean == DEFAULT_NORM_MEAN

    def test_default_norm_std(self):
        eng = CLTEngine()
        assert eng.norm_std == DEFAULT_NORM_STD

    def test_no_records(self):
        assert CLTEngine().records == []

    def test_samples_done_zero(self):
        assert CLTEngine().samples_done == 0

    def test_not_complete(self):
        assert not CLTEngine().is_complete

    def test_not_pending(self):
        assert not CLTEngine().is_pending

    def test_sample_means_empty(self):
        assert CLTEngine().sample_means == []

    def test_grand_mean_zero_when_empty(self):
        assert CLTEngine().grand_mean == 0.0

    def test_std_of_means_zero_when_empty(self):
        assert CLTEngine().std_of_means == 0.0


# ---------------------------------------------------------------------------
# Configure
# ---------------------------------------------------------------------------


class TestConfigure:
    def test_configure_sets_values(self):
        eng = CLTEngine()
        eng.configure(10, 20, 450.0, 15.0, 460.0, 18.0)
        assert eng.sample_size == 10
        assert eng.num_samples == 20
        assert eng.pop_mean == 450.0
        assert eng.pop_std == 15.0
        assert eng.norm_mean == 460.0
        assert eng.norm_std == 18.0

    def test_configure_clamps_sample_size_min(self):
        eng = CLTEngine()
        eng.configure(1, 10, 500.0, 20.0, 500.0, 20.0)
        assert eng.sample_size == 2

    def test_configure_clamps_sample_size_max(self):
        eng = CLTEngine()
        eng.configure(MAX_SAMPLE_SIZE + 10, 10, 500.0, 20.0, 500.0, 20.0)
        assert eng.sample_size == MAX_SAMPLE_SIZE

    def test_configure_clamps_num_samples_min(self):
        eng = CLTEngine()
        eng.configure(5, 0, 500.0, 20.0, 500.0, 20.0)
        assert eng.num_samples == 1

    def test_configure_clamps_num_samples_max(self):
        eng = CLTEngine()
        eng.configure(5, MAX_SAMPLES + 100, 500.0, 20.0, 500.0, 20.0)
        assert eng.num_samples == MAX_SAMPLES

    def test_configure_clamps_pop_std_min(self):
        eng = CLTEngine()
        eng.configure(5, 10, 500.0, 0.0, 500.0, 20.0)
        assert eng.pop_std == 0.01

    def test_configure_clamps_norm_std_min(self):
        eng = CLTEngine()
        eng.configure(5, 10, 500.0, 20.0, 500.0, -5.0)
        assert eng.norm_std == 0.01


# ---------------------------------------------------------------------------
# generate_product
# ---------------------------------------------------------------------------


class TestGenerateProduct:
    def test_returns_positive_float(self):
        eng = CLTEngine()
        eng.configure(5, 3, 500.0, 20.0, 500.0, 20.0)
        w = eng.generate_product()
        assert isinstance(w, float)
        assert w > 0

    def test_pending_after_generate(self):
        eng = CLTEngine()
        eng.configure(5, 3, 500.0, 20.0, 500.0, 20.0)
        eng.generate_product()
        assert eng.is_pending

    def test_weight_around_population_mean(self):
        random.seed(42)
        eng = CLTEngine()
        eng.configure(5, 3, 500.0, 20.0, 500.0, 20.0)
        weights = [eng.generate_product() for _ in range(1000)]
        avg = sum(weights) / len(weights)
        # Should be within ~3 standard errors of 500
        se = 20.0 / math.sqrt(1000)
        assert abs(avg - 500.0) < 4 * se


# ---------------------------------------------------------------------------
# record_weight
# ---------------------------------------------------------------------------


class TestRecordWeight:
    def test_increments_current_weights(self):
        eng = CLTEngine()
        eng.record_weight(510.0)
        assert eng.products_weighed_this_round == 1

    def test_multiple_records(self):
        eng = CLTEngine()
        eng.record_weight(490.0)
        eng.record_weight(510.0)
        eng.record_weight(500.0)
        assert eng.products_weighed_this_round == 3

    def test_products_remaining_decreases(self):
        eng = CLTEngine()
        eng.configure(5, 3, 500.0, 20.0, 500.0, 20.0)
        eng.generate_product()
        eng.record_weight(505.0)
        assert eng.products_remaining_this_round == 4


# ---------------------------------------------------------------------------
# finish_sample
# ---------------------------------------------------------------------------


class TestFinishSample:
    def test_increases_samples_done(self):
        eng = CLTEngine()
        eng.configure(3, 5, 500.0, 20.0, 500.0, 20.0)
        eng.record_weight(490.0)
        eng.record_weight(500.0)
        eng.record_weight(510.0)
        eng.finish_sample()
        assert eng.samples_done == 1

    def test_returns_sample_record(self):
        eng = CLTEngine()
        eng.configure(3, 5, 500.0, 20.0, 500.0, 20.0)
        eng.record_weight(490.0)
        eng.record_weight(500.0)
        eng.record_weight(510.0)
        rec = eng.finish_sample()
        assert isinstance(rec, SampleRecord)
        assert rec.sample_no == 1
        assert rec.n == 3

    def test_clears_current_weights(self):
        eng = CLTEngine()
        eng.record_weight(500.0)
        eng.record_weight(510.0)
        eng.finish_sample()
        assert eng.products_weighed_this_round == 0

    def test_clears_pending_state(self):
        eng = CLTEngine()
        eng.configure(2, 3, 500.0, 20.0, 500.0, 20.0)
        eng.generate_product()
        eng.record_weight(500.0)
        eng.record_weight(510.0)
        eng.finish_sample()
        assert not eng.is_pending

    def test_sample_numbers_increment(self):
        eng = CLTEngine()
        eng.configure(2, 4, 500.0, 20.0, 500.0, 20.0)
        nos = []
        for _ in range(4):
            eng.record_weight(500.0)
            eng.record_weight(510.0)
            rec = eng.finish_sample()
            nos.append(rec.sample_no)
        assert nos == [1, 2, 3, 4]


# ---------------------------------------------------------------------------
# auto_complete
# ---------------------------------------------------------------------------


class TestAutoComplete:
    def test_fills_all_remaining(self):
        eng = CLTEngine()
        eng.configure(5, 8, 500.0, 20.0, 500.0, 20.0)
        new_recs = eng.auto_complete()
        assert len(new_recs) == 8
        assert eng.is_complete

    def test_only_fills_remaining_after_manual(self):
        eng = CLTEngine()
        eng.configure(5, 5, 500.0, 20.0, 500.0, 20.0)
        # Manually record one sample
        for _ in range(5):
            eng.record_weight(random.gauss(500, 20))
        eng.finish_sample()
        new_recs = eng.auto_complete()
        assert len(new_recs) == 4
        assert eng.samples_done == 5

    def test_all_weights_positive(self):
        random.seed(42)
        eng = CLTEngine()
        eng.configure(10, 20, 500.0, 20.0, 500.0, 20.0)
        eng.auto_complete()
        for rec in eng.records:
            for w in rec.weights:
                assert w > 0

    def test_clears_pending_state(self):
        eng = CLTEngine()
        eng.configure(5, 3, 500.0, 20.0, 500.0, 20.0)
        eng.generate_product()
        eng.auto_complete()
        assert not eng.is_pending

    def test_each_sample_has_correct_size(self):
        eng = CLTEngine()
        eng.configure(7, 10, 500.0, 20.0, 500.0, 20.0)
        eng.auto_complete()
        for rec in eng.records:
            assert rec.n == 7


# ---------------------------------------------------------------------------
# is_complete
# ---------------------------------------------------------------------------


class TestIsComplete:
    def test_complete_after_all_samples(self):
        eng = CLTEngine()
        eng.configure(3, 3, 500.0, 20.0, 500.0, 20.0)
        for _ in range(3):
            for _ in range(3):
                eng.record_weight(random.gauss(500, 20))
            eng.finish_sample()
        assert eng.is_complete

    def test_not_complete_before_last(self):
        eng = CLTEngine()
        eng.configure(3, 3, 500.0, 20.0, 500.0, 20.0)
        for _ in range(3):
            eng.record_weight(random.gauss(500, 20))
        eng.finish_sample()
        assert not eng.is_complete


# ---------------------------------------------------------------------------
# Statistics
# ---------------------------------------------------------------------------


class TestStatistics:
    def test_sample_means_count(self):
        eng = CLTEngine()
        eng.configure(5, 3, 500.0, 20.0, 500.0, 20.0)
        eng.auto_complete()
        assert len(eng.sample_means) == 3

    def test_grand_mean_is_mean_of_means(self):
        eng = CLTEngine()
        eng.configure(5, 3, 500.0, 20.0, 500.0, 20.0)
        eng.auto_complete()
        expected = sum(eng.sample_means) / 3
        assert abs(eng.grand_mean - expected) < 1e-10

    def test_std_of_means_correct(self):
        eng = CLTEngine()
        eng.configure(5, 4, 500.0, 20.0, 500.0, 20.0)
        eng.auto_complete()
        means = eng.sample_means
        gm = sum(means) / len(means)
        expected = math.sqrt(sum((m - gm) ** 2 for m in means) / (len(means) - 1))
        assert abs(eng.std_of_means - expected) < 1e-10

    def test_std_of_means_single_sample(self):
        eng = CLTEngine()
        eng.configure(5, 1, 500.0, 20.0, 500.0, 20.0)
        eng.auto_complete()
        assert eng.std_of_means == 0.0

    def test_clt_convergence(self):
        """With large m, std_of_means should be close to σ/√n."""
        random.seed(123)
        eng = CLTEngine()
        eng.configure(30, 500, 500.0, 20.0, 500.0, 20.0)
        eng.auto_complete()
        theoretical_se = 20.0 / math.sqrt(30)
        # Should be within 20% of theoretical
        assert abs(eng.std_of_means - theoretical_se) / theoretical_se < 0.20


# ---------------------------------------------------------------------------
# Reset
# ---------------------------------------------------------------------------


class TestReset:
    def test_reset_clears_records(self):
        eng = CLTEngine()
        eng.configure(5, 3, 500.0, 20.0, 500.0, 20.0)
        eng.auto_complete()
        eng.reset()
        assert eng.records == []

    def test_reset_clears_current_weights(self):
        eng = CLTEngine()
        eng.record_weight(500.0)
        eng.reset()
        assert eng.products_weighed_this_round == 0

    def test_reset_clears_pending(self):
        eng = CLTEngine()
        eng.configure(5, 3, 500.0, 20.0, 500.0, 20.0)
        eng.generate_product()
        eng.reset()
        assert not eng.is_pending

    def test_reset_keeps_config(self):
        eng = CLTEngine()
        eng.configure(10, 15, 450.0, 18.0, 460.0, 22.0)
        eng.auto_complete()
        eng.reset()
        assert eng.sample_size == 10
        assert eng.num_samples == 15
        assert eng.pop_mean == 450.0
        assert eng.pop_std == 18.0


# ---------------------------------------------------------------------------
# State round-trip
# ---------------------------------------------------------------------------


class TestStateRoundTrip:
    def test_get_state_returns_dict(self):
        eng = CLTEngine()
        state = eng.get_state()
        assert isinstance(state, dict)
        assert "state_version" in state

    def test_restore_state_rehydrates(self):
        random.seed(42)
        eng = CLTEngine()
        eng.configure(10, 5, 450.0, 18.0, 460.0, 22.0)
        eng.auto_complete()
        state = eng.get_state()

        eng2 = CLTEngine()
        eng2.restore_state(state)
        assert eng2.sample_size == 10
        assert eng2.num_samples == 5
        assert eng2.pop_mean == 450.0
        assert eng2.pop_std == 18.0
        assert eng2.norm_mean == 460.0
        assert eng2.norm_std == 22.0
        assert eng2.samples_done == 5
        assert eng2.is_complete

    def test_restore_preserves_sample_data(self):
        random.seed(42)
        eng = CLTEngine()
        eng.configure(5, 3, 500.0, 20.0, 500.0, 20.0)
        eng.auto_complete()
        original_means = eng.sample_means[:]

        eng2 = CLTEngine()
        eng2.restore_state(eng.get_state())
        assert eng2.sample_means == original_means

    def test_restore_empty_state_uses_defaults(self):
        eng = CLTEngine()
        eng.restore_state({})
        assert eng.sample_size == DEFAULT_SAMPLE_SIZE
        assert eng.num_samples == DEFAULT_NUM_SAMPLES
        assert eng.pop_mean == DEFAULT_POP_MEAN
        assert eng.pop_std == DEFAULT_POP_STD
        assert eng.records == []

    def test_restore_never_sets_pending(self):
        eng = CLTEngine()
        eng.configure(5, 3, 500.0, 20.0, 500.0, 20.0)
        eng.generate_product()
        state = eng.get_state()

        eng2 = CLTEngine()
        eng2.restore_state(state)
        assert not eng2.is_pending

    def test_state_version_present(self):
        eng = CLTEngine()
        state = eng.get_state()
        assert state["state_version"] == "1.0.0"


# ---------------------------------------------------------------------------
# Distribution math helpers
# ---------------------------------------------------------------------------


class TestDistributionHelpers:
    """Test the static PDF methods used for chart overlay curves."""

    def test_normal_pdf_at_mean(self):
        from modules.statistics.central_limit_theorem.module import _CLTDistributionCanvas
        pdf = _CLTDistributionCanvas._normal_pdf(0, 0, 1)
        expected = 1 / math.sqrt(2 * math.pi)
        assert abs(pdf - expected) < 1e-10

    def test_normal_pdf_symmetry(self):
        from modules.statistics.central_limit_theorem.module import _CLTDistributionCanvas
        left = _CLTDistributionCanvas._normal_pdf(-1, 0, 1)
        right = _CLTDistributionCanvas._normal_pdf(1, 0, 1)
        assert abs(left - right) < 1e-10

    def test_normal_pdf_custom_params(self):
        from modules.statistics.central_limit_theorem.module import _CLTDistributionCanvas
        mu, sigma = 500.0, 20.0
        pdf = _CLTDistributionCanvas._normal_pdf(500.0, mu, sigma)
        expected = 1 / (sigma * math.sqrt(2 * math.pi))
        assert abs(pdf - expected) < 1e-10

    def test_student_t_pdf_at_zero_df1(self):
        from modules.statistics.central_limit_theorem.module import _CLTDistributionCanvas
        pdf = _CLTDistributionCanvas._student_t_pdf(0, 1)
        # t(df=1) at 0 = 1/pi ≈ 0.31831
        expected = 1 / math.pi
        assert abs(pdf - expected) < 1e-6

    def test_student_t_pdf_symmetry(self):
        from modules.statistics.central_limit_theorem.module import _CLTDistributionCanvas
        left = _CLTDistributionCanvas._student_t_pdf(-2, 10)
        right = _CLTDistributionCanvas._student_t_pdf(2, 10)
        assert abs(left - right) < 1e-10

    def test_student_t_pdf_converges_to_normal(self):
        """With large df, Student-t should approximate standard normal."""
        from modules.statistics.central_limit_theorem.module import _CLTDistributionCanvas
        t_pdf = _CLTDistributionCanvas._student_t_pdf(1.0, 1000)
        n_pdf = _CLTDistributionCanvas._normal_pdf(1.0, 0, 1)
        assert abs(t_pdf - n_pdf) < 0.01
