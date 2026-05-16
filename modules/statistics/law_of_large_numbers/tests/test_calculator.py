"""Unit tests for LLNCoinEngine — pure Python, no Qt/matplotlib dependency."""
from __future__ import annotations

import pytest

from modules.statistics.law_of_large_numbers.module import LLNCoinEngine


class TestInitialState:
    def test_starts_empty(self):
        engine = LLNCoinEngine()
        assert engine.cum_tosses == 0
        assert engine.cum_heads == 0
        assert engine.batches == []

    def test_x_series_empty(self):
        assert LLNCoinEngine().x_series == []

    def test_y_series_empty(self):
        assert LLNCoinEngine().y_series == []


class TestToss:
    def test_single_toss_updates_totals(self):
        engine = LLNCoinEngine()
        heads, cum, freq = engine.toss(1)
        assert cum == 1
        assert heads in (0, 1)
        assert freq == pytest.approx(heads / 1)

    def test_batch_of_10_totals(self):
        engine = LLNCoinEngine()
        _, cum, _ = engine.toss(10)
        assert cum == 10

    def test_multiple_interactions_accumulate(self):
        engine = LLNCoinEngine()
        engine.toss(5)
        engine.toss(5)
        assert engine.cum_tosses == 10
        assert len(engine.batches) == 2

    def test_rel_freq_in_valid_range(self):
        engine = LLNCoinEngine()
        _, _, freq = engine.toss(100)
        assert 0.0 <= freq <= 1.0

    def test_invalid_n_raises(self):
        engine = LLNCoinEngine()
        with pytest.raises(ValueError):
            engine.toss(0)

    def test_batch_record_structure(self):
        engine = LLNCoinEngine()
        engine.toss(3)
        batch_no, n, heads, cum_t, cum_h, freq = engine.batches[0]
        assert batch_no == 1
        assert n == 3
        assert cum_t == 3
        assert 0 <= heads <= 3
        assert cum_h == heads
        assert freq == pytest.approx(heads / 3)

    def test_batch_numbers_increment(self):
        engine = LLNCoinEngine()
        for _ in range(5):
            engine.toss(1)
        batch_nos = [b[0] for b in engine.batches]
        assert batch_nos == [1, 2, 3, 4, 5]

    def test_x_series_matches_cum_tosses(self):
        engine = LLNCoinEngine()
        engine.toss(2)
        engine.toss(3)
        assert engine.x_series == [2, 5]

    def test_y_series_length_matches_batches(self):
        engine = LLNCoinEngine()
        for _ in range(4):
            engine.toss(10)
        assert len(engine.y_series) == 4


class TestReset:
    def test_reset_clears_state(self):
        engine = LLNCoinEngine()
        engine.toss(50)
        engine.reset()
        assert engine.cum_tosses == 0
        assert engine.cum_heads == 0
        assert engine.batches == []

    def test_toss_after_reset_starts_fresh(self):
        engine = LLNCoinEngine()
        engine.toss(10)
        engine.reset()
        _, cum, _ = engine.toss(5)
        assert cum == 5
        assert len(engine.batches) == 1
        assert engine.batches[0][0] == 1  # batch_no restarts at 1


class TestStateRoundTrip:
    def test_get_state_returns_dict(self):
        engine = LLNCoinEngine()
        engine.toss(10)
        state = engine.get_state()
        assert isinstance(state, dict)
        assert "cum_tosses" in state
        assert "cum_heads" in state
        assert "batches" in state

    def test_restore_state_rehydrates_correctly(self):
        engine1 = LLNCoinEngine()
        for _ in range(5):
            engine1.toss(4)

        state = engine1.get_state()
        engine2 = LLNCoinEngine()
        engine2.restore_state(state)

        assert engine2.cum_tosses == engine1.cum_tosses
        assert engine2.cum_heads == engine1.cum_heads
        assert len(engine2.batches) == len(engine1.batches)

    def test_restore_empty_state(self):
        engine = LLNCoinEngine()
        engine.restore_state({})
        assert engine.cum_tosses == 0
        assert engine.batches == []


class TestLargeSimulation:
    def test_convergence_trend(self):
        """After many tosses the relative frequency should stay near 0.5."""
        import random
        random.seed(42)
        engine = LLNCoinEngine()
        for _ in range(200):
            engine.toss(10)
        final_freq = engine.cum_heads / engine.cum_tosses
        # 2000 tosses → should be within 5% of 0.5 with overwhelming probability
        assert abs(final_freq - 0.5) < 0.05
