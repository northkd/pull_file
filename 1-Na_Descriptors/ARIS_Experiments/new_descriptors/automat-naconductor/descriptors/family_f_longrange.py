"""F族: 长程关联描述符 (4个)。

描述超越最近邻的 Na-Na 空间关联，包括三体角、次近邻距离等。
"""
from __future__ import annotations

import numpy as np
from pymatgen.core import Structure

from descriptors._base import _safe_cv, _safe_mean, get_na_sites


def compute_nana_nana_angle_mean(struct: Structure) -> float:
    """Na-Na-Na 三体角均值 (度)。

    对每个 Na 位点，取其最近两个 Na 邻居构成夹角，
    对所有 Na 位点取均值。
    """
    na_indices = get_na_sites(struct)
    if len(na_indices) < 3:
        return float("nan")

    angles: list[float] = []
    for na_idx in na_indices:
        center = np.array(struct[na_idx].coords, dtype=float)
        # 找最近 Na 邻居
        dists: list[tuple[int, float]] = []
        for other_idx in na_indices:
            if other_idx == na_idx:
                continue
            d = float(struct.get_distance(na_idx, other_idx))
            dists.append((other_idx, d))
        dists.sort(key=lambda x: x[1])
        if len(dists) < 2:
            continue

        # 取最近两个计算夹角
        v1 = np.array(struct[dists[0][0]].coords, dtype=float) - center
        v2 = np.array(struct[dists[1][0]].coords, dtype=float) - center
        cos_angle = np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2) + 1e-12)
        cos_angle = np.clip(cos_angle, -1.0, 1.0)
        angle_deg = float(np.degrees(np.arccos(cos_angle)))
        angles.append(angle_deg)

    return _safe_mean(angles)


def compute_nana_second_neighbor_dist(struct: Structure) -> float:
    """Na 次近邻距离均值 (Å)。

    对每个 Na，找第二近的 Na 距离，然后取均值。
    """
    na_indices = get_na_sites(struct)
    if len(na_indices) < 3:
        return float("nan")

    second_dists: list[float] = []
    for na_idx in na_indices:
        dists: list[float] = []
        for other_idx in na_indices:
            if other_idx == na_idx:
                continue
            d = float(struct.get_distance(na_idx, other_idx))
            dists.append(d)
        dists.sort()
        if len(dists) >= 2:
            second_dists.append(dists[1])

    return _safe_mean(second_dists)


def compute_path_tortuosity(struct: Structure) -> float:
    """迁移路径曲折度。

    估计: Na-Na 直线距离 / 最短路径距离 的均值。
    简化实现: 对最近邻 Na 对，比较直线距离与绕行距离。
    用 (第二近邻距离 / 第一近邻距离) 的比率近似。
    """
    na_indices = get_na_sites(struct)
    if len(na_indices) < 2:
        return float("nan")

    ratios: list[float] = []
    for na_idx in na_indices:
        dists: list[float] = []
        for other_idx in na_indices:
            if other_idx == na_idx:
                continue
            d = float(struct.get_distance(na_idx, other_idx))
            dists.append(d)
        dists.sort()
        if len(dists) >= 2 and dists[0] > 1e-6:
            ratios.append(dists[1] / dists[0])

    return _safe_mean(ratios)


def compute_nana_spacing_uniformity(struct: Structure) -> float:
    """Na-Na 间距变异系数 (CV)。

    所有 Na-Na 对距离的 CV，值越小说明 Na 分布越均匀。
    """
    na_indices = get_na_sites(struct)
    if len(na_indices) < 2:
        return float("nan")

    all_dists: list[float] = []
    for i in range(len(na_indices)):
        for j in range(i + 1, len(na_indices)):
            d = float(struct.get_distance(na_indices[i], na_indices[j]))
            all_dists.append(d)

    return _safe_cv(all_dists)
