"""B族: Na-Na 网络描述符 (5个)。

描述 Na 离子之间的连通拓扑，包括平均邻居数、最大连通分量、网络维度等。
核心描述符: nana_composite (NaNa综合，已知与 A2 乘积 Spearman=0.623)。
"""
from __future__ import annotations

import numpy as np
from pymatgen.core import Structure

from descriptors._base import _safe_mean, get_na_sites

# Na-Na 连通截断距离 (Å)
NANA_CUTOFF = 4.5


def _build_na_graph(struct: Structure, cutoff: float = NANA_CUTOFF) -> dict:
    """构建 Na-Na 连通图并返回网络统计量。"""
    na_indices = get_na_sites(struct)
    n = len(na_indices)

    if n < 2:
        return {
            "avg_neighbors": float("nan"),
            "largest_component_ratio": float("nan"),
            "dimension": float("nan"),
            "component_count": 0 if n == 0 else 1,
            "neighbor_counts": [],
            "components": [],
        }

    # 邻接表
    neighbors: list[set[int]] = [set() for _ in range(n)]
    for i in range(n):
        for j in range(i + 1, n):
            d = float(struct.get_distance(na_indices[i], na_indices[j]))
            if d <= cutoff:
                neighbors[i].add(j)
                neighbors[j].add(i)

    # DFS 找连通分量
    visited: set[int] = set()
    components: list[set[int]] = []
    for start in range(n):
        if start in visited:
            continue
        stack = [start]
        comp: set[int] = set()
        visited.add(start)
        while stack:
            cur = stack.pop()
            comp.add(cur)
            for nxt in neighbors[cur]:
                if nxt not in visited:
                    visited.add(nxt)
                    stack.append(nxt)
        components.append(comp)

    largest = max(len(c) for c in components) if components else 0
    largest_frac = largest / n if n > 0 else 0.0
    counts = [len(nb) for nb in neighbors]

    # 网络维度估计: 基于分数坐标覆盖范围
    coords = np.array([struct[i].frac_coords for i in na_indices], dtype=float)
    spans = []
    for ax in range(3):
        cs = np.sort(coords[:, ax])
        gaps = np.diff(cs)
        wrap_gap = (cs[0] + 1.0) - cs[-1]
        max_gap = max(float(gaps.max()) if len(gaps) else 0.0, wrap_gap)
        spans.append(1.0 - max_gap)
    s_sorted = sorted(spans, reverse=True)

    if largest_frac >= 0.8 and s_sorted[2] > 0.55:
        dim = 3.0
    elif largest_frac >= 0.5 and s_sorted[1] > 0.55:
        dim = 2.0
    elif largest_frac >= 0.3 and s_sorted[0] > 0.55:
        dim = 1.0
    else:
        dim = 0.0

    return {
        "avg_neighbors": float(np.mean(counts)) if counts else float("nan"),
        "largest_component_ratio": largest_frac,
        "dimension": dim,
        "component_count": len(components),
        "neighbor_counts": counts,
        "components": components,
    }


def compute_nana_composite(struct: Structure) -> float:
    """NaNa 综合: 加权组合连通性指标。

    = connected_ratio × avg_neighbors(归一化) × network_dim(归一化)
    实际实现: 用百分位秩方法，与 part1.py 的 finalize_batch_descriptors 一致。
    对单个结构: 使用连通分量占比 × 平均邻居数 × (维度+1)/4 作为简化估计。
    """
    info = _build_na_graph(struct)
    ratio = info["largest_component_ratio"]
    avg_nb = info["avg_neighbors"]
    dim = info["dimension"]

    if any(np.isnan(v) for v in [ratio, avg_nb]):
        return float("nan")

    # 简化组合: ratio ∈ [0,1], avg_nb 归一化到 [0,1] (假设最大约8),
    # dim 归一化到 [0,1] (0→0.25, 1→0.5, 2→0.75, 3→1.0)
    avg_nb_norm = min(avg_nb / 8.0, 1.0)
    dim_norm = (dim + 1.0) / 4.0
    return float(ratio * avg_nb_norm * dim_norm)


def compute_avg_na_neighbors(struct: Structure) -> float:
    """截断距离 4.5Å 内平均 Na 邻居数。"""
    info = _build_na_graph(struct)
    return info["avg_neighbors"]


def compute_largest_component_ratio(struct: Structure) -> float:
    """最大 Na-Na 连通分量占比。"""
    info = _build_na_graph(struct)
    val = info["largest_component_ratio"]
    return float(val) if not np.isnan(val) else float("nan")


def compute_network_dimension(struct: Structure) -> float:
    """Na 网络维度: 0/1/2/3 分别对应低连通/1D/2D/3D。"""
    info = _build_na_graph(struct)
    return info["dimension"]


def compute_component_count(struct: Structure) -> float:
    """Na-Na 连通分量数。"""
    info = _build_na_graph(struct)
    return float(info["component_count"])
