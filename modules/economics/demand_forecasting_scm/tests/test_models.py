"""Tests for models/inputs.py — DataPoint, DataSet, ForecastingInput."""
from __future__ import annotations

import pytest

from modules.economics.demand_forecasting_scm.models.inputs import (
    DataPoint,
    DataSet,
    ForecastingInput,
)


# ---------------------------------------------------------------------------
# DataPoint
# ---------------------------------------------------------------------------


class TestDataPoint:
    def test_valid_creation(self):
        p = DataPoint(t=1, y=100.0)
        assert p.t == 1
        assert p.y == 100.0
        assert p.is_outlier is False

    def test_outlier_flag(self):
        p = DataPoint(t=1, y=999.0, is_outlier=True)
        assert p.is_outlier is True

    def test_t_must_be_positive(self):
        with pytest.raises(ValueError, match="t phải >= 1"):
            DataPoint(t=0, y=10.0)

    def test_t_negative_raises(self):
        with pytest.raises(ValueError):
            DataPoint(t=-1, y=10.0)

    def test_y_non_numeric_raises(self):
        with pytest.raises(TypeError):
            DataPoint(t=1, y="abc")  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# DataSet
# ---------------------------------------------------------------------------


class TestDataSet:
    def _make(self, values: list[float]) -> DataSet:
        return DataSet(points=[DataPoint(t=i + 1, y=v) for i, v in enumerate(values)])

    def test_empty_dataset(self):
        ds = DataSet()
        assert ds.n == 0
        assert ds.is_empty()

    def test_y_values(self):
        ds = self._make([10, 20, 30])
        assert ds.y_values == [10.0, 20.0, 30.0]

    def test_t_values(self):
        ds = self._make([10, 20, 30])
        assert ds.t_values == [1, 2, 3]

    def test_n(self):
        ds = self._make([5, 6, 7, 8])
        assert ds.n == 4

    def test_active_points_excludes_outliers(self):
        points = [
            DataPoint(t=1, y=10.0),
            DataPoint(t=2, y=999.0, is_outlier=True),
            DataPoint(t=3, y=12.0),
        ]
        ds = DataSet(points=points)
        active = ds.active_points
        assert len(active) == 2
        assert all(not p.is_outlier for p in active)

    def test_unsorted_t_raises(self):
        points = [DataPoint(t=2, y=10.0), DataPoint(t=1, y=20.0)]
        with pytest.raises(ValueError, match="sắp xếp tăng dần"):
            DataSet(points=points)

    def test_duplicate_t_raises(self):
        points = [DataPoint(t=1, y=10.0), DataPoint(t=1, y=20.0)]
        with pytest.raises(ValueError, match="trùng nhau"):
            DataSet(points=points)

    def test_roundtrip_serialization(self):
        original = self._make([100.0, 200.0, 150.0])
        original.points[1].is_outlier = True
        data = original.to_dict_list()
        restored = DataSet.from_dict_list(data)
        assert restored.n == 3
        assert restored.y_values == [100.0, 200.0, 150.0]
        assert restored.points[1].is_outlier is True


# ---------------------------------------------------------------------------
# ForecastingInput
# ---------------------------------------------------------------------------


class TestForecastingInput:
    def _dataset(self, n: int = 12, start: float = 100.0, step: float = 5.0) -> DataSet:
        return DataSet(points=[DataPoint(t=i + 1, y=start + i * step) for i in range(n)])

    def test_default_n_train_is_full(self):
        ds = self._dataset(10)
        inp = ForecastingInput(dataset=ds, method="naive")
        assert inp.n_train == 10
        assert not inp.has_holdout

    def test_partial_n_train_creates_holdout(self):
        ds = self._dataset(12)
        inp = ForecastingInput(dataset=ds, method="ses", n_train=8)
        assert inp.n_train == 8
        assert inp.has_holdout

    def test_n_train_zero_raises(self):
        ds = self._dataset(10)
        with pytest.raises(ValueError, match="n_train"):
            ForecastingInput(dataset=ds, method="naive", n_train=0)

    def test_n_train_exceeds_dataset_raises(self):
        ds = self._dataset(5)
        with pytest.raises(ValueError, match="n_train"):
            ForecastingInput(dataset=ds, method="naive", n_train=10)

    def test_alpha_out_of_range_raises(self):
        ds = self._dataset()
        with pytest.raises(ValueError, match="alpha"):
            ForecastingInput(dataset=ds, method="ses", alpha=0.0)
        with pytest.raises(ValueError, match="alpha"):
            ForecastingInput(dataset=ds, method="ses", alpha=1.1)

    def test_beta_out_of_range_raises(self):
        ds = self._dataset()
        with pytest.raises(ValueError, match="beta"):
            ForecastingInput(dataset=ds, method="holt", beta=0.0)

    def test_k_zero_raises(self):
        ds = self._dataset()
        with pytest.raises(ValueError, match="k"):
            ForecastingInput(dataset=ds, method="moving_average", k=0)

    def test_empty_dataset_raises(self):
        with pytest.raises(ValueError, match="rỗng"):
            ForecastingInput(dataset=DataSet(), method="naive")
