"""C族: Na 浓度描述符 (3个)。

描述结构中 Na 的浓度和占位信息。
"""
from __future__ import annotations

from pymatgen.core import Structure

from descriptors._base import get_na_sites


def compute_na_concentration(struct: Structure) -> float:
    """Na 原子数 / 晶胞总原子数。

    注意: 这里是原子数比率，不是体积浓度。
    """
    na_indices = get_na_sites(struct)
    total = len(struct)
    if total == 0:
        return float("nan")
    return float(len(na_indices) / total)


def compute_na_occupancy_sum(struct: Structure) -> float:
    """考虑部分占位的 Na 总和。

    对每个含 Na 位点，累加 Na 的占位权重。
    """
    na_indices = get_na_sites(struct)
    if not na_indices:
        return float("nan")

    total_occ = 0.0
    for idx in na_indices:
        site = struct[idx]
        na_occ = site.species.as_dict().get("Na", 0.0)
        total_occ += na_occ

    return float(total_occ)


def compute_na_site_count(struct: Structure) -> float:
    """Na 位点数 (不含占位权重)。"""
    na_indices = get_na_sites(struct)
    return float(len(na_indices))
