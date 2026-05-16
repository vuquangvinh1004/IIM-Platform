"""probe_vietnam_pbf.py — Script kiểm tra parse file Vietnam .pbf với bbox lọc.

Chạy từ thư mục gốc của project:
    python modules/logistics/pso_logistics_map/scripts/probe_vietnam_pbf.py

Điều chỉnh PBF_FILE và BBOX trước khi chạy.
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

# Đảm bảo import từ project root
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent))

from modules.logistics.pso_logistics_map.core.pbf_loader import (
    KNOWN_BBOXES,
    load_network,
)
from modules.logistics.pso_logistics_map.core.graph_builder import (
    build_graph,
    load_or_build,
)
from modules.logistics.pso_logistics_map.core.nearest_node import NearestNodeIndex
from modules.logistics.pso_logistics_map.core.distance_matrix import build_matrix

# --------------------------------------------------------------------------- #
#  CẤU HÌNH — điều chỉnh theo đường dẫn thật của bạn                          #
# --------------------------------------------------------------------------- #

# Đường dẫn đến file .pbf Vietnam đã tải
PBF_FILE = Path(__file__).parent.parent / "vietnam-260413.osm.pbf"

# Bbox muốn lọc — chọn một trong KNOWN_BBOXES hoặc tự định nghĩa
# (min_lat, min_lon, max_lat, max_lon)
BBOX_NAME = "hcm_q1"
BBOX = KNOWN_BBOXES[BBOX_NAME]

# Cache sẽ lưu ở đây (lần sau load ngay, không parse lại)
CACHE_FILE = PBF_FILE.parent / "cache" / f"{BBOX_NAME}_driving.pkl"

# --------------------------------------------------------------------------- #

def main() -> None:
    print(f"File .pbf : {PBF_FILE}")
    print(f"Bbox      : {BBOX_NAME} = {BBOX}")
    print(f"Cache     : {CACHE_FILE}")
    print()

    if not PBF_FILE.exists():
        print(f"[LỖI] Không tìm thấy file: {PBF_FILE}")
        print("Hãy chỉnh lại biến PBF_FILE trong script này.")
        sys.exit(1)

    # --- Bước 1: Parse + filter ---
    print("=== Bước 1: Load network (stream toàn file, lọc theo bbox) ===")
    t0 = time.perf_counter()
    nodes, edges = load_network(str(PBF_FILE), network_type="driving", bbox=BBOX)
    elapsed = time.perf_counter() - t0
    print(f"  Nodes trong bbox : {len(nodes):,}")
    print(f"  Edges trong bbox : {len(edges):,}")
    print(f"  Thời gian        : {elapsed:.1f}s")
    print()

    if len(nodes) == 0:
        print("[LỖI] Không có node nào trong bbox. Kiểm tra lại BBOX.")
        sys.exit(1)

    # --- Bước 2: Build graph ---
    print("=== Bước 2: Build NetworkX DiGraph ===")
    t0 = time.perf_counter()
    G = build_graph(nodes, edges)
    elapsed = time.perf_counter() - t0
    print(f"  G.nodes : {G.number_of_nodes():,}")
    print(f"  G.edges : {G.number_of_edges():,}")
    print(f"  Thời gian: {elapsed:.2f}s")
    print()

    # Kiểm tra node attributes
    sample_node = next(iter(G.nodes))
    attrs = G.nodes[sample_node]
    print(f"  Ví dụ node {sample_node}: lat={attrs['y']:.6f}, lon={attrs['x']:.6f}")
    print()

    # --- Bước 3: KDTree ---
    print("=== Bước 3: Xây KDTree nearest-node index ===")
    t0 = time.perf_counter()
    index = NearestNodeIndex(G)
    elapsed = time.perf_counter() - t0
    print(f"  KDTree built: {elapsed:.3f}s")

    # Snap một điểm mẫu ở trung tâm Quận 1
    test_lat, test_lon = 10.7769, 106.7009   # gần Bến Thành
    nearest = index.find(test_lat, test_lon)
    n_lat = G.nodes[nearest]["y"]
    n_lon = G.nodes[nearest]["x"]
    print(f"  Query ({test_lat}, {test_lon}) → node {nearest} ({n_lat:.6f}, {n_lon:.6f})")
    print()

    # --- Bước 4: Distance matrix (5 điểm mẫu) ---
    print("=== Bước 4: Tính distance matrix 5×5 (mẫu) ===")
    # Lấy 5 node đầu tiên làm mẫu
    sample_nodes = list(G.nodes)[:5]
    t0 = time.perf_counter()
    mat = build_matrix(G, sample_nodes)
    elapsed = time.perf_counter() - t0
    print(f"  Matrix shape : {mat.shape}")
    print(f"  Thời gian    : {elapsed:.3f}s")
    import numpy as np
    has_inf = np.any(np.isinf(mat))
    print(f"  Có cặp inf   : {has_inf}")
    print()

    # --- Bước 5: Lưu cache ---
    print("=== Bước 5: Build + lưu cache (load_or_build) ===")
    if CACHE_FILE.exists():
        print(f"  Cache đã tồn tại: {CACHE_FILE}")
        print("  Xóa cache nếu muốn rebuild.")
    else:
        t0 = time.perf_counter()
        G2 = load_or_build(str(PBF_FILE), str(CACHE_FILE), bbox=BBOX)
        elapsed = time.perf_counter() - t0
        print(f"  Cache đã lưu: {CACHE_FILE}")
        print(f"  Graph nodes: {G2.number_of_nodes():,}  (từ cache: {elapsed:.2f}s lần sau)")

    print()
    print("=== TẤT CẢ OK — Pipeline sẵn sàng cho Phase 2 (TSP) ===")
    print()
    print("Bbox sẵn có:")
    for name, bb in KNOWN_BBOXES.items():
        print(f"  {name:20s}: {bb}")


if __name__ == "__main__":
    main()
