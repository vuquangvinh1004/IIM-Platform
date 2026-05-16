"""Unit tests for LLNDiceEngine — pure Python, no Qt/matplotlib required."""
from __future__ import annotations

import pytest

from modules.statistics.law_of_large_numbers_dice.module import LLNDiceEngine


# ---------------------------------------------------------------------------
# Initial state
# ---------------------------------------------------------------------------

class TestInitialState:
    def test_default_observed_faces(self):
        eng = LLNDiceEngine()
        assert eng.observed_faces == [1]

    def test_custom_observed_faces_sorted_unique(self):
        eng = LLNDiceEngine([3, 1, 3, 5])
        assert eng.observed_faces == [1, 3, 5]

    def test_cum_rolls_zero(self):
        assert LLNDiceEngine().cum_rolls == 0

    def test_cum_hits_zero(self):
        assert LLNDiceEngine().cum_hits == 0

    def test_rolls_empty(self):
        assert LLNDiceEngine().rolls == []

    def test_x_series_empty(self):
        assert LLNDiceEngine().x_series == []

    def test_y_series_empty(self):
        assert LLNDiceEngine().y_series == []

    def test_last_face_none(self):
        assert LLNDiceEngine().last_face is None


# ---------------------------------------------------------------------------
# Theoretical probability
# ---------------------------------------------------------------------------

class TestTheoreticalProb:
    def test_single_face(self):
        eng = LLNDiceEngine([1])
        assert abs(eng.theoretical_prob - 1 / 6) < 1e-12

    def test_three_faces(self):
        eng = LLNDiceEngine([1, 3, 5])
        assert abs(eng.theoretical_prob - 3 / 6) < 1e-12

    def test_all_faces(self):
        eng = LLNDiceEngine([1, 2, 3, 4, 5, 6])
        assert abs(eng.theoretical_prob - 1.0) < 1e-12

    def test_two_faces(self):
        eng = LLNDiceEngine([1, 2])
        assert abs(eng.theoretical_prob - 2 / 6) < 1e-12


# ---------------------------------------------------------------------------
# Roll
# ---------------------------------------------------------------------------

class TestRoll:
    def test_single_roll_updates_cum_rolls(self):
        eng = LLNDiceEngine()
        eng.roll()
        assert eng.cum_rolls == 1

    def test_face_in_valid_range(self):
        eng = LLNDiceEngine()
        for _ in range(100):
            face, _, _, _ = eng.roll()
            assert 1 <= face <= 6

    def test_hit_flag_correct(self):
        eng = LLNDiceEngine([2, 4, 6])
        for _ in range(200):
            face, hit, _, _ = eng.roll()
            assert hit == (face in {2, 4, 6})

    def test_rel_freq_in_valid_range(self):
        eng = LLNDiceEngine([1, 2, 3])
        for _ in range(50):
            _, _, _, freq = eng.roll()
            assert 0.0 <= freq <= 1.0

    def test_multiple_rolls_accumulate(self):
        eng = LLNDiceEngine([1])
        for _ in range(10):
            eng.roll()
        assert eng.cum_rolls == 10
        assert len(eng.rolls) == 10

    def test_roll_record_structure(self):
        eng = LLNDiceEngine([1])
        eng.roll()
        rec = eng.rolls[0]
        assert len(rec) == 6
        roll_no, face, hit, cum_t, cum_h, freq = rec
        assert roll_no == 1
        assert 1 <= face <= 6
        assert isinstance(hit, bool)
        assert cum_t == 1
        assert 0 <= cum_h <= 1
        assert 0.0 <= freq <= 1.0

    def test_roll_numbers_increment(self):
        eng = LLNDiceEngine([1])
        for _ in range(5):
            eng.roll()
        nos = [r[0] for r in eng.rolls]
        assert nos == [1, 2, 3, 4, 5]

    def test_x_series_matches_cum_rolls(self):
        eng = LLNDiceEngine([1])
        for _ in range(7):
            eng.roll()
        xs = eng.x_series
        assert xs == list(range(1, 8))

    def test_y_series_length_matches_rolls(self):
        eng = LLNDiceEngine([1])
        for _ in range(6):
            eng.roll()
        assert len(eng.y_series) == 6

    def test_last_face_updated(self):
        eng = LLNDiceEngine([1])
        eng.roll()
        face = eng.last_face
        assert face is not None
        assert 1 <= face <= 6


# ---------------------------------------------------------------------------
# Reset
# ---------------------------------------------------------------------------

class TestReset:
    def test_reset_clears_state(self):
        eng = LLNDiceEngine([1, 3, 5])
        for _ in range(10):
            eng.roll()
        eng.reset()
        assert eng.cum_rolls == 0
        assert eng.cum_hits == 0
        assert eng.rolls == []

    def test_reset_keeps_observed_faces(self):
        eng = LLNDiceEngine([2, 4, 6])
        for _ in range(5):
            eng.roll()
        eng.reset()
        assert eng.observed_faces == [2, 4, 6]

    def test_roll_after_reset_starts_fresh(self):
        eng = LLNDiceEngine([1])
        for _ in range(5):
            eng.roll()
        eng.reset()
        eng.roll()
        assert eng.cum_rolls == 1
        assert eng.rolls[0][0] == 1


# ---------------------------------------------------------------------------
# set_observed_faces
# ---------------------------------------------------------------------------

class TestSetObservedFaces:
    def test_changes_faces_and_resets(self):
        eng = LLNDiceEngine([1])
        for _ in range(5):
            eng.roll()
        eng.set_observed_faces([2, 3])
        assert eng.observed_faces == [2, 3]
        assert eng.cum_rolls == 0

    def test_theoretical_prob_updates(self):
        eng = LLNDiceEngine([1])
        eng.set_observed_faces([1, 2, 3])
        assert abs(eng.theoretical_prob - 0.5) < 1e-12


# ---------------------------------------------------------------------------
# State round-trip
# ---------------------------------------------------------------------------

class TestStateRoundTrip:
    def test_get_state_returns_dict(self):
        eng = LLNDiceEngine([1, 3])
        state = eng.get_state()
        assert isinstance(state, dict)
        assert "cum_rolls" in state
        assert "observed_faces" in state

    def test_restore_state_rehydrates(self):
        eng1 = LLNDiceEngine([1, 2, 3])
        for _ in range(20):
            eng1.roll()
        state = eng1.get_state()

        eng2 = LLNDiceEngine()
        eng2.restore_state(state)
        assert eng2.cum_rolls == eng1.cum_rolls
        assert eng2.cum_hits == eng1.cum_hits
        assert eng2.observed_faces == eng1.observed_faces
        assert len(eng2.rolls) == len(eng1.rolls)

    def test_restore_empty_state(self):
        eng = LLNDiceEngine()
        eng.restore_state({})
        assert eng.cum_rolls == 0


# ---------------------------------------------------------------------------
# Large simulation — convergence
# ---------------------------------------------------------------------------

class TestLargeSimulation:
    def test_convergence_trend(self):
        """After 5000 rolls, frequency should be within 5% of p."""
        import random as _r
        _r.seed(0)
        eng = LLNDiceEngine([1, 3, 5])  # p = 0.5
        for _ in range(5000):
            eng.roll()
        assert abs(eng.y_series[-1] - 0.5) < 0.05
