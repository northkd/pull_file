"""A族: Na多面体描述符 (11个)。

描述 Na 位点的局域配位环境，包括键长、畸变、体积等。
核心描述符: a2_max_dist (局域宽松因子，已知 Spearman=0.597)。
"""
from __future__ import annotations

import numpy as np
from pymatgen.core import Structure

from descriptors._base import (
    ANION_ELEMENTS,
    _effective_anion_radius,
    _effective_na_radius,
    _safe_cv,
    _safe_mean,
    _shell_neighbors,
    compute_polyhedron_volume,
    element_symbol,
    get_na_sites,
)


def _collect_na_x_data(
    struct: Structure,
    shell_tolerance: float = 0.70,
    min_shell_size: int = 4,
) -> dict:
    """收集所有 Na 位点的 Na-X 键信息，返回中间数据字典。

    参数透传到 _shell_neighbors，默认值与参数化前逐位一致。
    """
    na_indices = get_na_sites(struct)
    species_symbols = {element_symbol(el) for el in struct.composition.elements}
    anions = species_symbols & ANION_ELEMENTS

    if not na_indices or not anions:
        return {
            "all_distances": [],
            "per_site_max": [],
            "per_site_min": [],
            "per_site_mean": [],
            "per_site_distortion": [],
            "per_site_cn": [],
            "per_site_volume": [],
            "per_site_bonds": [],
            "anions": anions,
            "na_indices": na_indices,
        }

    all_distances: list[float] = []
    per_site_max: list[float] = []
    per_site_min: list[float] = []
    per_site_mean: list[float] = []
    per_site_distortion: list[float] = []
    per_site_cn: list[int] = []
    per_site_volume: list[float] = []
    per_site_bonds: list[list[tuple]] = []

    for na_idx in na_indices:
        shell = _shell_neighbors(
            struct, na_idx, anions,
            shell_tolerance=shell_tolerance,
            min_shell_size=min_shell_size,
        )
        distances = [float(n["distance"]) for n in shell]

        if not distances:
            continue

        # 键向量 (用于 PCA 分析)
        center_coords = np.array(struct[na_idx].coords, dtype=float)
        bond_vectors = []
        for n in shell:
            vec = np.array(n["coords"], dtype=float) - center_coords
            bond_vectors.append((n["symbol"], n["distance"], vec))

        all_distances.extend(distances)
        per_site_max.append(max(distances))
        per_site_min.append(min(distances))
        per_site_mean.append(float(np.mean(distances)))
        per_site_cn.append(len(shell))
        per_site_bonds.append(bond_vectors)

        # 畸变 = 变异系数 (CV)
        if len(distances) > 1:
            cv = float(np.std(distances, ddof=0) / np.mean(distances))
            per_site_distortion.append(cv)

        # 多面体体积
        vol = compute_polyhedron_volume(struct, na_idx)
        if not np.isnan(vol):
            per_site_volume.append(vol)

    return {
        "all_distances": all_distances,
        "per_site_max": per_site_max,
        "per_site_min": per_site_min,
        "per_site_mean": per_site_mean,
        "per_site_distortion": per_site_distortion,
        "per_site_cn": per_site_cn,
        "per_site_volume": per_site_volume,
        "per_site_bonds": per_site_bonds,
        "anions": anions,
        "na_indices": na_indices,
    }


def compute_a2_max_dist(struct: Structure) -> float:
    """Na-X 最长键长均值 (Å)。

    即局域宽松因子的分子部分。
    已知 Spearman 相关: 0.597 (与 log10 电导率)。
    """
    data = _collect_na_x_data(struct)
    return _safe_mean(data["per_site_max"])


def compute_poly_distortion_mean(
    struct: Structure,
    shell_tolerance: float = 0.70,
    min_shell_size: int = 4,
) -> float:
    """Na 多面体畸变均值。

    每个Na位点 Na-X 键长的变异系数(CV)，然后对所有Na位点取均值。
    参数透传到 _collect_na_x_data → _shell_neighbors，默认值与参数化前逐位一致。
    """
    data = _collect_na_x_data(
        struct,
        shell_tolerance=shell_tolerance,
        min_shell_size=min_shell_size,
    )
    return _safe_mean(data["per_site_distortion"])


def compute_max_bond_length(struct: Structure) -> float:
    """Na-X 最长键长均值 (Å) — a2_max_dist 的别名。"""
    return compute_a2_max_dist(struct)


def compute_min_bond_length(struct: Structure) -> float:
    """Na-X 最短键长均值 (Å)。"""
    data = _collect_na_x_data(struct)
    return _safe_mean(data["per_site_min"])


def compute_mean_bond_length(struct: Structure) -> float:
    """Na-X 平均键长均值 (Å)。"""
    data = _collect_na_x_data(struct)
    return _safe_mean(data["per_site_mean"])


def compute_target_bond_center(struct: Structure) -> float:
    """Na-X 目标键长中心 (Å)。

    R0 = R_Na(CN_mode) + R_anion_avg，
    由 Shannon 有效离子半径加权得到。
    """
    data = _collect_na_x_data(struct)
    if not data["per_site_cn"]:
        return float("nan")

    # 众数配位数
    from collections import Counter
    cn_counter = Counter(data["per_site_cn"])
    mode_cn = cn_counter.most_common(1)[0][0]

    na_r = _effective_na_radius(mode_cn)
    anion_r = _effective_anion_radius(data["anions"])
    if anion_r is None:
        return float("nan")

    return float(na_r + anion_r)


def compute_poly_volume_mean(struct: Structure) -> float:
    """Na 多面体体积均值 (Å³)，基于 Voronoi 分配。"""
    data = _collect_na_x_data(struct)
    return _safe_mean(data["per_site_volume"])


def compute_coordination_number_mean(struct: Structure) -> float:
    """Na 主配位数均值，基于 VoronoiNN 第一壳层。"""
    data = _collect_na_x_data(struct)
    if not data["per_site_cn"]:
        return float("nan")
    return float(np.mean(data["per_site_cn"]))


def compute_ellipsoid_oblateness(struct: Structure) -> float:
    """Na-X 键向量椭球扁率。

    对每个 Na 位点的 Na-X 键向量做 PCA，
    取 λ_max / λ_min 后对所有 Na 位点取均值。
    值越大说明配位越扁平/各向异性。
    """
    data = _collect_na_x_data(struct)
    if not data["per_site_bonds"]:
        return float("nan")

    oblateness_list: list[float] = []
    for bonds in data["per_site_bonds"]:
        if len(bonds) < 3:
            continue
        vecs = np.array([bv[2] for bv in bonds], dtype=float)
        # 中心化
        vecs_centered = vecs - vecs.mean(axis=0)
        # 协方差矩阵
        cov = np.cov(vecs_centered.T)
        if cov.ndim != 2 or cov.shape[0] < 2:
            continue
        try:
            eigenvalues = np.linalg.eigvalsh(cov)
            eigenvalues = np.sort(eigenvalues)
            eigenvalues = eigenvalues[eigenvalues > 1e-12]
            if len(eigenvalues) >= 2:
                oblateness_list.append(float(eigenvalues[-1] / eigenvalues[0]))
        except np.linalg.LinAlgError:
            continue

    return _safe_mean(oblateness_list)


def compute_direction_ratio(struct: Structure) -> float:
    """方向比: 每个Na位点最长键 / 次长键，然后取均值。

    反映瓶颈通道的方向性。
    """
    na_indices = get_na_sites(struct)
    species_symbols = {element_symbol(el) for el in struct.composition.elements}
    anions = species_symbols & ANION_ELEMENTS

    if not na_indices or not anions:
        return float("nan")

    ratios: list[float] = []
    for na_idx in na_indices:
        shell = _shell_neighbors(struct, na_idx, anions)
        distances = sorted([float(n["distance"]) for n in shell])
        if len(distances) >= 2:
            ratios.append(distances[-1] / distances[-2])

    return _safe_mean(ratios)


def compute_bottleneck_anisotropy(struct: Structure) -> float:
    """瓶颈各向异性 (BVSE 依赖)。

    需要 BVSE 势能面数据，当前返回 NaN。
    未来可集成 SoftBV 计算结果。
    """
    return float("nan")
