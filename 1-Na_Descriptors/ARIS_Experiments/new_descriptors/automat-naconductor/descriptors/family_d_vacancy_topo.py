"""D'族: 空位拓扑描述符 (5个)。

使用 scipy.spatial.Voronoi 方法（errata P2 修正版）寻找间隙位点。
不使用 VoronoiNN.get_voronoi_polyhedra。
BVSE 依赖的描述符返回 NaN。
"""
from __future__ import annotations

import numpy as np
from pymatgen.core import Structure

from descriptors._base import (
    _safe_mean,
    find_interstitial_sites,
    get_na_sites,
)


def _get_interstitial_data(struct: Structure) -> list[dict]:
    """获取间隙位点数据（带缓存效果）。"""
    return find_interstitial_sites(struct)


def compute_interstitial_count(struct: Structure) -> float:
    """间隙位点数。

    基于 scipy.spatial.Voronoi 周期性影像方法。
    """
    sites = _get_interstitial_data(struct)
    return float(len(sites))


def compute_interstitial_na_distance(struct: Structure) -> float:
    """间隙-Na 最近距离均值 (Å)。

    对每个间隙位点，找最近的 Na 位点距离，然后取均值。
    """
    na_indices = get_na_sites(struct)
    sites = _get_interstitial_data(struct)

    if not sites or not na_indices:
        return float("nan")

    na_coords = np.array([struct[i].coords for i in na_indices], dtype=float)
    min_dists: list[float] = []

    for ist in sites:
        ist_coords = ist["coords"]
        dists = np.linalg.norm(na_coords - ist_coords, axis=1)
        min_dists.append(float(np.min(dists)))

    return _safe_mean(min_dists)


def compute_interstitial_channel_access(struct: Structure) -> float:
    """接入主通道的间隙位点比例。

    判据: 间隙位点与最近 Na 的距离 <= 3.0Å 视为接入主通道。
    """
    na_indices = get_na_sites(struct)
    sites = _get_interstitial_data(struct)

    if not sites or not na_indices:
        return float("nan")

    na_coords = np.array([struct[i].coords for i in na_indices], dtype=float)
    access_threshold = 3.0  # Å
    accessible = 0

    for ist in sites:
        ist_coords = ist["coords"]
        dists = np.linalg.norm(na_coords - ist_coords, axis=1)
        if float(np.min(dists)) <= access_threshold:
            accessible += 1

    return float(accessible / len(sites))


def compute_interstitial_network_dim(struct: Structure) -> float:
    """间隙网络维度。

    基于间隙位点之间的连通性 (距离 < 3.5Å 为连通)，
    用 DFS 判断最大连通分量的维度。
    """
    sites = _get_interstitial_data(struct)
    if len(sites) < 2:
        return 0.0

    coords = np.array([s["coords"] for s in sites], dtype=float)
    n = len(coords)
    cutoff = 3.5  # Å

    # 构建邻接表
    neighbors: list[set[int]] = [set() for _ in range(n)]
    for i in range(n):
        for j in range(i + 1, n):
            d = float(np.linalg.norm(coords[i] - coords[j]))
            if d <= cutoff:
                neighbors[i].add(j)
                neighbors[j].add(i)

    # DFS 找连通分量
    visited: set[int] = set()
    max_comp_size = 0
    for start in range(n):
        if start in visited:
            continue
        stack = [start]
        comp_size = 0
        visited.add(start)
        while stack:
            cur = stack.pop()
            comp_size += 1
            for nxt in neighbors[cur]:
                if nxt not in visited:
                    visited.add(nxt)
                    stack.append(nxt)
        max_comp_size = max(max_comp_size, comp_size)

    # 0D: 大部分孤立; 1D: 链状; 2D/3D 依赖空间覆盖
    ratio = max_comp_size / n if n > 0 else 0.0
    if ratio < 0.3:
        return 0.0
    elif ratio < 0.6:
        return 1.0
    else:
        return 2.0


def compute_bvse_barrier_estimate(struct: Structure) -> float:
    """BVSE 能垒估计 (BVSE 依赖)。

    需要 SoftBV/BVSE 预计算数据，当前返回 NaN。
    """
    return float("nan")
