"""G族: 电子代理描述符 (4个, 全部高风险 ⚠️)。

用电负性等标量作为电子结构代理，不依赖 DFT 计算。
这些描述符是经验性的，物理可解释性较弱，需谨慎使用。
"""
from __future__ import annotations

import numpy as np
from pymatgen.core import Structure

from descriptors._base import (
    ANION_ELEMENTS,
    ELECTRONEGATIVITY,
    _safe_mean,
    _shell_neighbors,
    element_symbol,
    get_framework_sites,
    get_na_sites,
    site_occupancies_by_symbol,
)


def compute_na_x_en_diff(struct: Structure) -> float:
    """Na-X 电负性差均值。

    对每个 Na 位点的第一壳层阴离子，
    计算 χ(X) - χ(Na)，然后取所有 Na 位点均值。
    """
    na_indices = get_na_sites(struct)
    species_symbols = {element_symbol(el) for el in struct.composition.elements}
    anions = species_symbols & ANION_ELEMENTS

    if not na_indices or not anions:
        return float("nan")

    en_diffs: list[float] = []
    for na_idx in na_indices:
        shell = _shell_neighbors(struct, na_idx, anions)
        for n in shell:
            sym = n["symbol"]
            en_x = ELECTRONEGATIVITY.get(sym)
            en_na = ELECTRONEGATIVITY.get("Na")
            if en_x is not None and en_na is not None:
                en_diffs.append(en_x - en_na)

    return _safe_mean(en_diffs)


def compute_charge_balance_deviation(struct: Structure) -> float:
    """电荷平衡偏差。

    简化估计: 用占位加权和估算总正电荷和总负电荷的偏差。
    Na 贡献 +1，阴离子假设 -2 (O/S/Se) 或 -1 (F/Cl/Br/I/H/N)。
    """
    fallback_oxidation_states = {
        "Na": 1, "Li": 1, "K": 1, "Rb": 1, "Cs": 1,
        "Mg": 2, "Ca": 2, "Sr": 2, "Ba": 2, "Zn": 2,
        "Al": 3, "Fe": 3, "Cr": 3, "Ga": 3, "In": 3,
        "Si": 4, "Ge": 4, "Sn": 4, "Ti": 4, "Zr": 4, "Hf": 4, "Mn": 4,
        "P": 5, "V": 5, "As": 5, "Sb": 5, "Nb": 5, "Ta": 5,
        "O": -2, "S": -2, "Se": -2,
        "F": -1, "Cl": -1, "Br": -1, "I": -1, "H": -1, "N": -1,
    }
    net_charge = 0.0
    total_absolute_charge = 0.0

    for site in struct:
        for species, occupancy in site.species.items():
            symbol = element_symbol(species)
            oxidation_state = getattr(species, "oxi_state", None)
            if oxidation_state is None:
                oxidation_state = fallback_oxidation_states.get(symbol)
            if oxidation_state is None:
                continue
            charge = float(occupancy) * float(oxidation_state)
            net_charge += charge
            total_absolute_charge += abs(charge)

    if total_absolute_charge < 1e-12:
        return float("nan")

    return float(abs(net_charge) / max(total_absolute_charge, 1e-12))


def compute_covalency_index(struct: Structure) -> float:
    """Pauling 共价性指数均值。

    对每个 Na-X 键: 1 - exp(-(χ_X - χ_Na)² / 4)，
    然后取均值。值越大说明共价性越强。
    """
    na_indices = get_na_sites(struct)
    species_symbols = {element_symbol(el) for el in struct.composition.elements}
    anions = species_symbols & ANION_ELEMENTS

    if not na_indices or not anions:
        return float("nan")

    covalencies: list[float] = []
    en_na = ELECTRONEGATIVITY.get("Na", 0.93)

    for na_idx in na_indices:
        shell = _shell_neighbors(struct, na_idx, anions)
        for n in shell:
            en_x = ELECTRONEGATIVITY.get(n["symbol"])
            if en_x is not None:
                delta = en_x - en_na
                covalency = 1.0 - np.exp(-(delta ** 2) / 4.0)
                covalencies.append(float(covalency))

    return _safe_mean(covalencies)


def compute_framework_d_electron_weighted(struct: Structure) -> float:
    """骨架 d 电子加权占比。

    骨架阳离子中含 d 电子的元素 (过渡金属) 的占位权重总和，
    除以骨架阳离子总占位权重。
    """
    fw_indices = get_framework_sites(struct)
    if not fw_indices:
        return float("nan")

    # 过渡金属: 原子序数 21-30, 39-48, 57-80, 89-112 的子集
    # 简化: 常见过渡金属符号
    d_block = {
        "Sc", "Ti", "V", "Cr", "Mn", "Fe", "Co", "Ni", "Cu", "Zn",
        "Y", "Zr", "Nb", "Mo", "Tc", "Ru", "Rh", "Pd", "Ag", "Cd",
        "Hf", "Ta", "W", "Re", "Os", "Ir", "Pt", "Au", "Hg",
        "La", "Ce", "Pr", "Nd", "Sm", "Eu", "Gd", "Tb", "Dy", "Ho", "Er", "Tm", "Yb", "Lu",
    }

    d_occ = 0.0
    total_occ = 0.0

    for fw_idx in fw_indices:
        site = struct[fw_idx]
        species_dict = site_occupancies_by_symbol(site)
        for el_sym, occ in species_dict.items():
            total_occ += occ
            if el_sym in d_block:
                d_occ += occ

    if total_occ < 1e-12:
        return float("nan")

    return float(d_occ / total_occ)
