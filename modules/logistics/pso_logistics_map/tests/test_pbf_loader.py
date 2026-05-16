"""test_pbf_loader.py — Unit tests cho core/pbf_loader.py.

Các test lỗi/biên không cần file .pbf thật.
Test smoke với file thật sẽ bị skip nếu file chưa tồn tại.
"""
from __future__ import annotations

import math
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from modules.logistics.pso_logistics_map.core.pbf_loader import (
    _haversine_m,
    _apply_bbox,
    KNOWN_BBOXES,
    load_network,
)


# --------------------------------------------------------------------------- #
#  Haversine                                                                   #
# --------------------------------------------------------------------------- #

def test_haversine_same_point():
    assert _haversine_m(10.0, 106.0, 10.0, 106.0) == pytest.approx(0.0)


def test_haversine_known_distance():
    # Khoảng cách xấp xỉ 1° kinh độ tại xích đạo ≈ 111 320 m
    dist = _haversine_m(0.0, 0.0, 0.0, 1.0)
    assert 111_000 < dist < 112_000


def test_haversine_symmetry():
    d1 = _haversine_m(10.0, 106.0, 10.5, 106.5)
    d2 = _haversine_m(10.5, 106.5, 10.0, 106.0)
    assert d1 == pytest.approx(d2, rel=1e-9)


def test_haversine_positive():
    assert _haversine_m(10.0, 106.0, 10.1, 106.1) > 0


# --------------------------------------------------------------------------- #
#  load_network — error cases (không cần file .pbf)                           #
# --------------------------------------------------------------------------- #

def test_load_network_missing_file():
    with pytest.raises(FileNotFoundError, match="không tồn tại"):
        load_network("non_existent_file.pbf")


def test_load_network_bad_network_type():
    # Tạo file giả để qua check FileNotFoundError
    with pytest.raises(ValueError, match="network_type"):
        # Dùng file thật nếu có, nhưng lỗi phải raise trước khi đọc file
        # nên ta mock exists() = True
        with patch("pathlib.Path.exists", return_value=True):
            load_network("fake.pbf", network_type="helicopter")


def test_load_network_bad_bbox_length():
    with pytest.raises(ValueError, match="bbox"):
        with patch("pathlib.Path.exists", return_value=True):
            load_network("fake.pbf", bbox=(10.0, 106.0, 10.1))  # type: ignore


def test_load_network_bad_bbox_inverted():
    with pytest.raises(ValueError, match="bbox"):
        with patch("pathlib.Path.exists", return_value=True):
            load_network("fake.pbf", bbox=(10.9, 106.0, 10.0, 107.0))  # min_lat > max_lat


# --------------------------------------------------------------------------- #
#  KNOWN_BBOXES                                                                #
# --------------------------------------------------------------------------- #

def test_known_bboxes_not_empty():
    assert len(KNOWN_BBOXES) > 0


def test_known_bboxes_hcm_q1_exists():
    assert "hcm_q1" in KNOWN_BBOXES


def test_known_bboxes_all_valid():
    for name, bb in KNOWN_BBOXES.items():
        assert len(bb) == 4, f"{name}: phải có 4 phần tử"
        min_lat, min_lon, max_lat, max_lon = bb
        assert min_lat < max_lat, f"{name}: min_lat >= max_lat"
        assert min_lon < max_lon, f"{name}: min_lon >= max_lon"


# --------------------------------------------------------------------------- #
#  _apply_bbox                                                                 #
# --------------------------------------------------------------------------- #

def test_apply_bbox_keeps_nodes_inside():
    nodes = {
        1: (10.770, 106.700),   # inside
        2: (10.800, 106.700),   # outside (lat too high)
        3: (10.770, 106.720),   # outside (lon too high)
    }
    edges = [(1, 2, 100.0), (1, 3, 200.0), (2, 3, 300.0)]
    bbox = (10.760, 106.695, 10.790, 106.715)
    kn, ke = _apply_bbox(nodes, edges, bbox)
    assert set(kn.keys()) == {1}, "Chỉ node 1 nằm trong bbox"
    assert ke == [], "Không có edge nào có cả 2 đầu trong bbox"


def test_apply_bbox_keeps_edges_when_both_inside():
    nodes = {1: (10.770, 106.700), 2: (10.775, 106.705)}
    edges = [(1, 2, 100.0), (2, 1, 100.0)]
    bbox = (10.760, 106.695, 10.790, 106.715)
    kn, ke = _apply_bbox(nodes, edges, bbox)
    assert set(kn.keys()) == {1, 2}
    assert len(ke) == 2


def test_apply_bbox_empty_result():
    nodes = {1: (5.0, 100.0)}
    edges = []
    bbox = (10.0, 106.0, 11.0, 107.0)
    kn, ke = _apply_bbox(nodes, edges, bbox)
    assert kn == {}
    assert ke == []


# --------------------------------------------------------------------------- #
#  load_network — smoke test với file .pbf thật (skip nếu chưa có)           #
# --------------------------------------------------------------------------- #

_PBF_SAMPLE = Path(__file__).parent.parent / "assets" / "pbf" / "hcm_q1.pbf"


@pytest.mark.skipif(
    not _PBF_SAMPLE.exists(),
    reason="File .pbf mẫu chưa có (assets/pbf/hcm_q1.pbf)",
)
def test_load_network_smoke():
    nodes, edges = load_network(str(_PBF_SAMPLE), network_type="driving")
    assert len(nodes) > 0, "Phải có ít nhất 1 node"
    assert len(edges) > 0, "Phải có ít nhất 1 edge"


@pytest.mark.skipif(
    not _PBF_SAMPLE.exists(),
    reason="File .pbf mẫu chưa có",
)
def test_load_network_node_coords_in_range():
    nodes, _ = load_network(str(_PBF_SAMPLE), network_type="driving")
    for node_id, (lat, lon) in nodes.items():
        assert -90 <= lat <= 90, f"Latitude ngoài phạm vi: {lat}"
        assert -180 <= lon <= 180, f"Longitude ngoài phạm vi: {lon}"


@pytest.mark.skipif(
    not _PBF_SAMPLE.exists(),
    reason="File .pbf mẫu chưa có",
)
def test_load_network_edges_positive_weight():
    _, edges = load_network(str(_PBF_SAMPLE), network_type="driving")
    for u, v, length in edges:
        assert length > 0, f"Edge ({u},{v}) có length <= 0: {length}"


@pytest.mark.skipif(
    not _PBF_SAMPLE.exists(),
    reason="File .pbf mẫu chưa có",
)
def test_load_network_edge_nodes_known():
    """Tất cả node trong edges phải có trong nodes dict."""
    nodes, edges = load_network(str(_PBF_SAMPLE), network_type="driving")
    node_set = set(nodes.keys())
    for u, v, _ in edges:
        assert u in node_set, f"u={u} không có trong nodes"
        assert v in node_set, f"v={v} không có trong nodes"
