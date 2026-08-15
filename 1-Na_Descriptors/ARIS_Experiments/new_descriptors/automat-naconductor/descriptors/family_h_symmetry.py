"""H族: 对称性破缺描述符 (5个, 其中3个高风险 ⚠️)。

描述结构的对称性相关特征，包括空间群、Wyckoff 位置、部分占位等。
高风险描述符: space_group_number, wyckoff_diversity, partial_occupancy_ratio
(因为它们可能与电导率无直接物理因果关系)。
"""
from __future__ import annotations

import warnings
from pathlib import Path

import numpy as np
from pymatgen.core import Structure
from pymatgen.symmetry.analyzer import SpacegroupAnalyzer

from descriptors._base import (
    _safe_cv,
    _safe_mean,
    compute_polyhedron_volume,
    get_na_sites,
    site_occupancies_by_symbol,
)
from descriptors.exceptions import ConfigurationError


def _get_symprec() -> float:
    """从 run_info.yaml 读取 symmetry.symprec，读不到抛 ConfigurationError。

    不得取默认值——symprec 必须由配置显式提供。
    每次调用读一次文件，无缓存。
    """
    from run_config import load_run_info, config_get
    config = load_run_info(Path(__file__).resolve().parent.parent / "run_info.yaml")
    try:
        return float(config_get(config, "symmetry.symprec"))
    except KeyError as exc:
        raise ConfigurationError(
            f"run_info.yaml 缺少 symmetry.symprec: {exc}"
        ) from exc


def compute_space_group_number(struct: Structure) -> float:
    """空间群序号 (high_risk=True)。

    高风险: 空间群序号本身可能不直接关联离子传导，
    仅作为结构复杂性的代理指标。
    """
    symprec = _get_symprec()  # 移到 try 之外：配置缺失时 ValueError 必须逃出
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            sga = SpacegroupAnalyzer(struct, symprec=symprec)
            return float(sga.get_space_group_number())
    except Exception:
        return float("nan")


def compute_wyckoff_diversity(struct: Structure) -> float:
    """Wyckoff 位置多样性 (high_risk=True)。

    统计不等价 Wyckoff 位置的数量。
    高风险: 与电导率的物理关联不明确。
    """
    symprec = _get_symprec()  # 移到 try 之外：配置缺失时 ValueError 必须逃出
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            sga = SpacegroupAnalyzer(struct, symprec=symprec)
            symm_struct = sga.get_symmetrized_structure()
        # 等价位点组的数量 = 不等价 Wyckoff 位置数
        return float(len(symm_struct.equivalent_indices))
    except Exception:
        return float("nan")


def compute_partial_occupancy_ratio(struct: Structure) -> float:
    """部分占位比例 (high_risk=True)。

    占位不等于 1.0 或存在多种元素的位点占总位点数的比例。
    高风险: 部分占位可能是高温无序的反映，也可能是精修质量差。
    """
    if len(struct) == 0:
        return float("nan")

    partial_count = 0
    for site in struct:
        species_dict = site_occupancies_by_symbol(site)
        total_occ = sum(species_dict.values())
        # 多元素混合占位 或 占位不等于 1
        if len(species_dict) != 1 or abs(total_occ - 1.0) > 1e-3:
            partial_count += 1
        else:
            for occ in species_dict.values():
                if abs(occ - 1.0) > 1e-3:
                    partial_count += 1
                    break

    return float(partial_count / len(struct))


def compute_coordination_cv(struct: Structure) -> float:
    """配位数变异系数 (high_risk=False)。

    各 Na 位点配位数的 CV，反映配位环境的均匀性。
    """
    na_indices = get_na_sites(struct)
    if len(na_indices) < 2:
        return float("nan")

    try:
        from pymatgen.analysis.local_env import VoronoiNN
        vnn = VoronoiNN()
        cn_list: list[float] = []
        for na_idx in na_indices:
            try:
                cn = vnn.get_cn(struct, na_idx)
                cn_list.append(float(cn))
            except Exception:
                continue
        return _safe_cv(cn_list)
    except ImportError:
        return float("nan")


def compute_volume_cv(struct: Structure) -> float:
    """多面体体积变异系数 (high_risk=False)。

    各 Na 位点 Voronoi 多面体体积的 CV。
    """
    na_indices = get_na_sites(struct)
    if len(na_indices) < 2:
        return float("nan")

    volumes: list[float] = []
    for na_idx in na_indices:
        vol = compute_polyhedron_volume(struct, na_idx)
        if not np.isnan(vol):
            volumes.append(vol)

    return _safe_cv(volumes)
