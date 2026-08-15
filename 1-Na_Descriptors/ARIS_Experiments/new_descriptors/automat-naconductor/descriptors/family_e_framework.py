"""E族: 骨架刚性描述符 (4个)。

描述非 Na、非阴离子骨架阳离子的配位刚性与稳定性。
"""
from __future__ import annotations

import numpy as np
from pymatgen.core import Structure

from descriptors._base import (
    ANION_ELEMENTS,
    _effective_anion_radius,
    _safe_cv,
    _safe_mean,
    _shell_neighbors,
    element_symbol,
    get_framework_sites,
    get_na_sites,
    site_occupancies_by_symbol,
)


def _get_framework_data(
    struct: Structure,
    shell_tolerance: float = 0.70,
    min_shell_size: int = 4,
) -> dict:
    """收集骨架阳离子的配位信息。

    参数透传到 _shell_neighbors，默认值与参数化前逐位一致。
    """
    fw_indices = get_framework_sites(struct)
    species_symbols = {element_symbol(el) for el in struct.composition.elements}
    anions = species_symbols & ANION_ELEMENTS

    if not fw_indices or not anions:
        return {
            "bond_ratios": [],
            "poly_distortions": [],
            "na_distances": [],
            "sharing_vertices_count": 0,
            "total_framework_sites": len(fw_indices),
        }

    bond_ratios: list[float] = []
    poly_distortions: list[float] = []
    na_distances: list[float] = []

    na_indices = get_na_sites(struct)

    for fw_idx in fw_indices:
        shell = _shell_neighbors(
            struct, fw_idx, anions,
            shell_tolerance=shell_tolerance,
            min_shell_size=min_shell_size,
        )
        if not shell:
            continue

        distances = [float(n["distance"]) for n in shell]

        # X-X 键长 / 理想键长 (用 Shannon 半径估计)
        fw_sym = max(
            site_occupancies_by_symbol(struct[fw_idx]).items(),
            key=lambda kv: kv[1],
        )[0]
        anion_r = _effective_anion_radius(anions)
        # 简化: 用阴离子半径的 2 倍作为理想 X-X 距离
        if anion_r is not None and anion_r > 0:
            mean_dist = float(np.mean(distances))
            bond_ratios.append(mean_dist / (2.0 * anion_r))

        # 骨架多面体畸变
        if len(distances) > 1:
            cv = float(np.std(distances, ddof=0) / np.mean(distances))
            poly_distortions.append(cv)

        # 骨架-Na 间距
        for na_idx in na_indices:
            d = float(struct.get_distance(fw_idx, na_idx))
            na_distances.append(d)

    return {
        "bond_ratios": bond_ratios,
        "poly_distortions": poly_distortions,
        "na_distances": na_distances,
        "sharing_vertices_count": 0,  # 共享顶点比例需更复杂计算
        "total_framework_sites": len(fw_indices),
    }


def compute_framework_bond_rigidity(struct: Structure) -> float:
    """骨架 X-X 键长 / 理想键长的均值。

    理想键长 = 2 × 阴离子有效半径。
    值接近 1.0 说明骨架刚性高。
    """
    data = _get_framework_data(struct)
    return _safe_mean(data["bond_ratios"])


def compute_framework_poly_distortion(
    struct: Structure,
    shell_tolerance: float = 0.70,
    min_shell_size: int = 4,
) -> float:
    """骨架多面体畸变均值。

    骨架阳离子配位多面体键长的变异系数。
    参数透传到 _get_framework_data → _shell_neighbors，默认值与参数化前逐位一致。
    """
    data = _get_framework_data(
        struct,
        shell_tolerance=shell_tolerance,
        min_shell_size=min_shell_size,
    )
    return _safe_mean(data["poly_distortions"])


def compute_framework_na_distance_stability(struct: Structure) -> float:
    """骨架-Na 间距变异系数 (CV)。

    CV 越小说明骨架与 Na 的间距越均匀，
    意味着 Na 在骨架中运动势能面越平坦。
    """
    data = _get_framework_data(struct)
    return _safe_cv(data["na_distances"])


def compute_framework_sharing_topology(struct: Structure) -> float:
    """共享顶点比例。

    计算骨架多面体之间通过共享阴离子顶点连接的比例。
    简化实现: 统计阴离子被多个骨架阳离子共享的比例。
    """
    fw_indices = set(get_framework_sites(struct))
    species_symbols = {element_symbol(el) for el in struct.composition.elements}
    anions = species_symbols & ANION_ELEMENTS

    if not fw_indices or not anions:
        return float("nan")

    # 统计每个阴离子连接的骨架阳离子数
    anion_sharing: dict[int, int] = {}
    for fw_idx in fw_indices:
        shell = _shell_neighbors(struct, fw_idx, anions)
        for n in shell:
            if n["index"] is not None:
                anion_sharing[n["index"]] = anion_sharing.get(n["index"], 0) + 1

    if not anion_sharing:
        return float("nan")

    # 被两个或以上骨架阳离子共享的阴离子比例
    shared_count = sum(1 for v in anion_sharing.values() if v >= 2)
    return float(shared_count / len(anion_sharing))
