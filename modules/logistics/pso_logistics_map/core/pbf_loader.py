"""pbf_loader.py — Đọc mạng đường từ file OSM .pbf cục bộ bằng pyosmium.

Không gọi bất kỳ API internet nào. File .pbf phải tồn tại cục bộ trong
assets/pbf/ của module. Mọi lỗi đều được raise rõ ràng.

Public API:
    load_network(pbf_path, network_type, bbox) -> (nodes, edges)
        nodes : dict[node_id: int, (lat: float, lon: float)]
        edges : list[tuple[u_id: int, v_id: int, length_m: float]]

    BBox = (min_lat, min_lon, max_lat, max_lon)  -- WGS-84 decimal degrees

    KNOWN_BBOXES : dict[str, BBox]  -- bbox sẵn cho các khu vực hay dùng
"""
from __future__ import annotations

import math
from pathlib import Path

import osmium


# --------------------------------------------------------------------------- #
#  BBox type + known areas                                                     #
# --------------------------------------------------------------------------- #

# (min_lat, min_lon, max_lat, max_lon) in WGS-84 decimal degrees
BBox = tuple[float, float, float, float]

# BBox sẵn cho các khu vực HCM hay dùng
KNOWN_BBOXES: dict[str, BBox] = {
    "hcm_q1":        (10.760, 106.695, 10.790, 106.715),   # Quận 1
    "hcm_q3":        (10.773, 106.680, 10.800, 106.700),   # Quận 3
    "hcm_inner":     (10.740, 106.660, 10.810, 106.730),   # Nội ô Q1–Q5
    "hcm_full":      (10.600, 106.580, 10.950, 107.050),   # Thành phố HCM
    "hanoi_hoankiem":(21.021, 105.843, 21.038, 105.862),   # Hoàn Kiếm
    "hanoi_inner":   (20.990, 105.790, 21.070, 105.900),   # Nội thành Hà Nội
}


# --------------------------------------------------------------------------- #
#  Highway tag sets per network type                                           #
# --------------------------------------------------------------------------- #

_HIGHWAY_TAGS: dict[str, set[str]] = {
    "driving": {
        "motorway", "motorway_link",
        "trunk", "trunk_link",
        "primary", "primary_link",
        "secondary", "secondary_link",
        "tertiary", "tertiary_link",
        "residential", "living_street",
        "unclassified", "road",
    },
    "walking": {
        "footway", "pedestrian", "path", "steps", "bridleway",
        "residential", "living_street", "service",
    },
    "cycling": {
        "cycleway", "path", "track",
        "residential", "living_street",
        "tertiary", "unclassified",
    },
}


# --------------------------------------------------------------------------- #
#  Haversine distance (metres)                                                 #
# --------------------------------------------------------------------------- #

def _haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Return great-circle distance in metres between two WGS-84 points."""
    R = 6_371_000.0
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lam = math.radians(lon2 - lon1)
    a = math.sin(d_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lam / 2) ** 2
    return R * 2.0 * math.asin(math.sqrt(a))


# --------------------------------------------------------------------------- #
#  osmium handler                                                              #
# --------------------------------------------------------------------------- #

class _NetworkHandler(osmium.SimpleHandler):
    """Stream OSM ways and collect highway edges + referenced node locations.

    Requires apply_file(..., locations=True) so that way.nodes carry lat/lon.
    """

    def __init__(self, allowed_highway_tags: set[str]) -> None:
        super().__init__()
        self._allowed = allowed_highway_tags
        self.nodes: dict[int, tuple[float, float]] = {}   # {node_id: (lat, lon)}
        self.edges: list[tuple[int, int, float]] = []     # [(u, v, metres)]

    def way(self, w: osmium.osm.Way) -> None:  # type: ignore[name-defined]
        if "highway" not in w.tags:
            return
        if w.tags.get("highway") not in self._allowed:
            return

        oneway_val = w.tags.get("oneway", "no")
        is_oneway = oneway_val in ("yes", "1", "true")

        node_list = list(w.nodes)
        for i in range(len(node_list) - 1):
            u_ref = node_list[i]
            v_ref = node_list[i + 1]

            if not u_ref.location.valid() or not v_ref.location.valid():
                continue

            u_id = u_ref.ref
            v_id = v_ref.ref
            u_lat, u_lon = u_ref.location.lat, u_ref.location.lon
            v_lat, v_lon = v_ref.location.lat, v_ref.location.lon

            self.nodes[u_id] = (u_lat, u_lon)
            self.nodes[v_id] = (v_lat, v_lon)

            dist = _haversine_m(u_lat, u_lon, v_lat, v_lon)
            self.edges.append((u_id, v_id, dist))
            if not is_oneway:
                self.edges.append((v_id, u_id, dist))


# --------------------------------------------------------------------------- #
#  BBox filter helper                                                          #
# --------------------------------------------------------------------------- #

def _apply_bbox(
    nodes: dict[int, tuple[float, float]],
    edges: list[tuple[int, int, float]],
    bbox: BBox,
) -> tuple[dict[int, tuple[float, float]], list[tuple[int, int, float]]]:
    """Filter nodes and edges to those inside the bounding box.

    A node is kept if its (lat, lon) falls within [min_lat, max_lat] x [min_lon, max_lon].
    An edge (u, v) is kept only when BOTH endpoints are inside the bbox
    (ensures the returned graph has no dangling node references).
    """
    min_lat, min_lon, max_lat, max_lon = bbox
    kept_nodes = {
        nid: (lat, lon)
        for nid, (lat, lon) in nodes.items()
        if min_lat <= lat <= max_lat and min_lon <= lon <= max_lon
    }
    kept_set = set(kept_nodes)
    kept_edges = [
        (u, v, w) for u, v, w in edges
        if u in kept_set and v in kept_set
    ]
    return kept_nodes, kept_edges


# --------------------------------------------------------------------------- #
#  Public API                                                                  #
# --------------------------------------------------------------------------- #

def load_network(
    pbf_path: str | Path,
    network_type: str = "driving",
    bbox: BBox | None = None,
) -> tuple[dict[int, tuple[float, float]], list[tuple[int, int, float]]]:
    """Load road network from a local OSM .pbf file.

    Args:
        pbf_path     : Absolute or relative path to the .pbf file.
        network_type : One of ``"driving"``, ``"walking"``, ``"cycling"``.
        bbox         : Optional bounding box ``(min_lat, min_lon, max_lat, max_lon)``.
                       When provided, only nodes **and** edges whose both endpoints
                       fall inside the box are returned.  Use ``KNOWN_BBOXES`` for
                       pre-defined areas, e.g. ``KNOWN_BBOXES["hcm_q1"]``.

    Returns:
        nodes : ``dict[node_id, (lat, lon)]``
        edges : ``list[(u_node_id, v_node_id, length_metres)]``

    Raises:
        FileNotFoundError : ``pbf_path`` does not exist.
        ValueError        : ``network_type`` is not recognised, or bbox has wrong format.
        RuntimeError      : .pbf contains no valid highway edges for that type / bbox.
    """
    path = Path(pbf_path)
    if not path.exists():
        raise FileNotFoundError(f"File .pbf không tồn tại: {path}")
    if network_type not in _HIGHWAY_TAGS:
        raise ValueError(
            f"network_type phải là một trong {list(_HIGHWAY_TAGS)}; "
            f"nhận được: {network_type!r}"
        )
    if bbox is not None:
        if len(bbox) != 4:
            raise ValueError("bbox phải có dạng (min_lat, min_lon, max_lat, max_lon)")
        min_lat, min_lon, max_lat, max_lon = bbox
        if min_lat >= max_lat or min_lon >= max_lon:
            raise ValueError(
                f"bbox không hợp lệ: min_lat={min_lat} >= max_lat={max_lat} "
                f"hoặc min_lon={min_lon} >= max_lon={max_lon}"
            )

    handler = _NetworkHandler(_HIGHWAY_TAGS[network_type])
    handler.apply_file(str(path), locations=True)

    nodes, edges = handler.nodes, handler.edges

    if bbox is not None:
        nodes, edges = _apply_bbox(nodes, edges, bbox)

    if not nodes:
        area_hint = f" trong bbox {bbox}" if bbox else ""
        raise RuntimeError(
            f"Không tìm thấy mạng '{network_type}' nào trong file {path}{area_hint}. "
            "Kiểm tra lại file .pbf, bbox, hoặc thử network_type khác."
        )

    return nodes, edges
