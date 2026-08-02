"""结构描述符基础工具与物理族定义。

提供描述符计算所需的公共辅助函数、物理族定义、跨组约束规则，
以及 Shannon 有效离子半径、阴离子集合等常量。
"""
from __future__ import annotations

import warnings
from collections import Counter

import numpy as np
from pymatgen.core import Structure
from scipy.spatial import Voronoi

# ============================================================
# 阴离子元素集合
# ============================================================
ANION_ELEMENTS: set[str] = {"O", "S", "Se", "F", "Cl", "Br", "I", "N", "H"}

# ============================================================
# Na+ 有效离子半径 (Å)，按配位数索引
# 来源: Shannon 经典有效离子半径表
# ============================================================
NA_EFFECTIVE_RADII_A: dict[int, float] = {
    4: 0.99,
    5: 1.00,
    6: 1.02,
    7: 1.12,
    8: 1.18,
    9: 1.24,
    12: 1.39,
}
NA_FALLBACK_CN = 6

# ============================================================
# 阴离子有效离子半径 (Å)，N 无经典值故为 None
# ============================================================
ANION_EFFECTIVE_RADII_A: dict[str, float | None] = {
    "O": 1.40,
    "S": 1.84,
    "Se": 1.98,
    "F": 1.33,
    "Cl": 1.81,
    "Br": 1.96,
    "I": 2.20,
    "H": 1.40,
    "N": None,
}

# ============================================================
# 电负性 (Pauling 标度)，用于 G 族电子代理描述符
# ============================================================
ELECTRONEGATIVITY: dict[str, float] = {
    "Na": 0.93,
    "O": 3.44,
    "S": 2.58,
    "F": 3.98,
    "Cl": 3.16,
    "Br": 2.96,
    "I": 2.66,
    "Se": 2.55,
    "N": 3.04,
    "H": 2.20,
}

# ============================================================
# 八大物理族定义
# ============================================================
PHYSICAL_FAMILIES: dict[str, dict[str, str]] = {
    "A": {"name": "Na多面体", "module": "family_a_polyhedron"},
    "B": {"name": "Na-Na网络", "module": "family_b_network"},
    "C": {"name": "Na浓度", "module": "family_c_concentration"},
    "D_prime": {"name": "空位拓扑", "module": "family_d_vacancy_topo"},
    "E": {"name": "骨架刚性", "module": "family_e_framework"},
    "F": {"name": "长程关联", "module": "family_f_longrange"},
    "G": {"name": "电子代理", "module": "family_g_electronic"},
    "H": {"name": "对称性破缺", "module": "family_h_symmetry"},
}

# ============================================================
# 跨组组合约束
# ============================================================
CROSS_GROUP_RULES: dict[str, object] = {
    # 允许的跨组对
    "allowed_pairs": [
        ("A", "B"),
        ("A", "D_prime"),
        ("A", "C"),
        ("B", "D_prime"),
        ("A", "H"),
        ("E", "A"),
    ],
    # 高风险族
    "high_risk_families": ["G", "H"],
    # 特殊限制: A↔C 仅允许比率运算，不允许乘法
    "per_operator_restrictions": {
        ("A", "C"): {"allowed_ops": ["ratio"], "forbidden_ops": ["multiply"]},
    },
}


# ============================================================
# 辅助函数
# ============================================================

def get_na_sites(struct: Structure) -> list[int]:
    """获取结构中 Na 位点的索引列表。

    Na 位点 = 主要物种为 Na 的位点（考虑部分占位）。
    """
    na_indices: list[int] = []
    for i, site in enumerate(struct):
        species_dict = site.species.as_dict()
        na_occ = species_dict.get("Na", 0.0)
        if na_occ > 1e-6:
            na_indices.append(i)
    return na_indices


def get_anion_sites(struct: Structure) -> list[int]:
    """获取结构中阴离子位点的索引列表。"""
    anion_indices: list[int] = []
    for i, site in enumerate(struct):
        for el in site.species.elements:
            if str(el) in ANION_ELEMENTS:
                anion_indices.append(i)
                break
    return anion_indices


def get_framework_sites(struct: Structure) -> list[int]:
    """获取骨架位点索引：非 Na、非阴离子的位点。"""
    na_set = set(get_na_sites(struct))
    anion_set = set(get_anion_sites(struct))
    return [i for i in range(len(struct)) if i not in na_set and i not in anion_set]


def _major_species(site) -> str:
    """获取位点上占位最多的元素符号。"""
    species_dict = site.species.as_dict()
    if not species_dict:
        return ""
    return max(species_dict.items(), key=lambda kv: kv[1])[0]


def _site_occ(site, symbol: str) -> float:
    """获取位点上某元素的占位数。"""
    return site.species.as_dict().get(symbol, 0.0)


def get_na_x_bonds(
    struct: Structure,
    na_idx: int,
    max_dist: float = 4.0,
) -> list[tuple[int, float]]:
    """获取 Na 位点与近邻阴离子的键信息。

    参数:
        struct: pymatgen Structure 对象
        na_idx: Na 位点索引
        max_dist: 最大搜索距离 (Å)

    返回:
        (anion_site_idx, distance) 列表，按距离升序
    """
    center = struct[na_idx]
    raw = struct.get_sites_in_sphere(
        center.coords, max_dist, include_index=True, include_image=True
    )
    bonds: list[tuple[int, float]] = []
    for item in raw:
        site = item[0]
        dist = float(item[1])
        idx = int(item[2]) if len(item) >= 3 and item[2] is not None else None
        if idx == na_idx and dist < 1e-6:
            continue
        sym = _major_species(site)
        if sym in ANION_ELEMENTS:
            if idx is not None:
                bonds.append((idx, dist))
    bonds.sort(key=lambda x: x[1])
    return bonds


def _anion_cutoff(anion_symbols: set[str]) -> float:
    """根据阴离子类型确定截断距离 (Å)。"""
    cutoffs = {
        "O": 3.20, "F": 3.20, "N": 3.35,
        "S": 3.85, "Cl": 3.85, "H": 3.20,
        "Se": 4.05, "Br": 4.05, "I": 4.35,
    }
    return max((cutoffs.get(sym, 4.0) for sym in anion_symbols), default=4.0)


def _shell_neighbors(
    struct: Structure,
    center_index: int,
    anion_symbols: set[str],
) -> list[dict]:
    """提取 Na 位点的第一配位壳层 Na-X 近邻。

    沿用 part1.py 的简化规则: 取最短键长 +0.70Å 内的阴离子，
    若不足 4 个则补至 4。
    """
    center = struct[center_index]
    cutoff = _anion_cutoff(anion_symbols)
    raw = struct.get_sites_in_sphere(
        center.coords, cutoff, include_index=True, include_image=True
    )
    center_coords = np.array(center.coords, dtype=float)
    neighbors: list[dict] = []
    for item in raw:
        site = item[0]
        dist = float(item[1])
        idx = int(item[2]) if len(item) >= 3 and item[2] is not None else None
        if idx == center_index and dist < 1e-6:
            continue
        sym = _major_species(site)
        if sym in ANION_ELEMENTS:
            coords_arr = np.array(site.coords, dtype=float)
            neighbors.append({
                "symbol": sym, "distance": dist,
                "coords": coords_arr, "index": idx,
            })
    neighbors.sort(key=lambda x: x["distance"])
    if not neighbors:
        return []
    first = neighbors[0]["distance"]
    kept = [n for n in neighbors if n["distance"] <= first + 0.70]
    if len(kept) <= 3 and len(neighbors) > len(kept):
        kept = neighbors[:min(4, len(neighbors))]
    return kept


def _effective_na_radius(cn: int | None) -> float:
    """根据配位数返回 Na+ 有效离子半径 (Å)。

    未列入的 CN 使用 CN=6 的默认值。
    """
    if cn is not None and cn in NA_EFFECTIVE_RADII_A:
        return NA_EFFECTIVE_RADII_A[cn]
    return NA_EFFECTIVE_RADII_A[NA_FALLBACK_CN]


def _effective_anion_radius(anion_symbols: set[str]) -> float | None:
    """计算阴离子有效离子半径加权平均值 (Å)。

    若阴离子中包含 N（无经典值），返回 None。
    """
    if not anion_symbols:
        return None
    values: list[tuple[str, float]] = []
    missing: list[str] = []
    for sym in sorted(anion_symbols):
        r = ANION_EFFECTIVE_RADII_A.get(sym)
        if r is None:
            missing.append(sym)
        else:
            values.append((sym, r))
    if missing or not values:
        return None
    return sum(r for _, r in values) / len(values)


def find_interstitial_sites(
    struct: Structure,
    min_dist_from_atom: float = 1.5,
) -> list[dict]:
    """用 scipy.spatial.Voronoi 寻找周期性晶胞中的间隙位点。

    算法 (errata P2 修正):
    1. 将所有原子坐标转为笛卡尔坐标
    2. 生成周期性影像 (±1 个晶胞在三个方向)
    3. 对所有点（原始+影像）做 Voronoi 剖分
    4. 筛选 Voronoi 顶点: 仅保留在原胞内的顶点，
       且该顶点与最近原子距离 >= min_dist_from_atom

    返回:
        间隙位点列表，每个元素为 {"coords": np.ndarray, "volume": float}
        coords 为笛卡尔坐标 (Å)，volume 为对应 Voronoi 区域体积 (Å³)
    """
    if len(struct) == 0:
        return []

    # 原始原子笛卡尔坐标
    cart_coords = np.array([site.coords for site in struct], dtype=float)
    lattice = struct.lattice

    # 生成周期性影像
    all_points: list[np.ndarray] = [cart_coords]
    for i in (-1, 0, 1):
        for j in (-1, 0, 1):
            for k in (-1, 0, 1):
                if i == 0 and j == 0 and k == 0:
                    continue
                shift = i * lattice.matrix[0] + j * lattice.matrix[1] + k * lattice.matrix[2]
                all_points.append(cart_coords + shift)

    all_points_arr = np.vstack(all_points)

    # Voronoi 剖分
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            vor = Voronoi(all_points_arr)
    except Exception:
        return []

    # 晶胞边界 (Å)
    origin = np.array([0.0, 0.0, 0.0])
    a_vec = lattice.matrix[0]
    b_vec = lattice.matrix[1]
    c_vec = lattice.matrix[2]

    # 将笛卡尔坐标转回分数坐标以判断是否在原胞内
    n_orig = len(struct)

    interstitial_sites: list[dict] = []
    for ridge_idx, ridge in enumerate(vor.ridge_vertices):
        if -1 in ridge:
            continue  # 跳过无限远脊
        vertices = [vor.vertices[v] for v in ridge if v >= 0]
        if len(vertices) < 3:
            continue

        # 取脊的中点作为候选间隙位点
        ridge_center = np.mean(vertices, axis=0)

        # 检查是否在原胞内 (用分数坐标)
        frac = lattice.get_fractional_coords(ridge_center)
        in_cell = all(-1e-6 <= f < 1.0 - 1e-6 for f in frac)
        if not in_cell:
            continue

        # 检查与最近原子的距离
        dists = np.linalg.norm(cart_coords - ridge_center, axis=1)
        min_dist = float(np.min(dists))
        if min_dist < min_dist_from_atom:
            continue

        # 估算该间隙的 Voronoi 区域体积（用包含的顶点凸包体积近似）
        from scipy.spatial import ConvexHull
        try:
            vol = float(ConvexHull(np.array(vertices)).volume)
        except Exception:
            vol = 0.0

        interstitial_sites.append({
            "coords": ridge_center,
            "volume": vol,
        })

    # 去重: 同一区域可能因周期性影像重复出现
    if len(interstitial_sites) > 1:
        unique: list[dict] = [interstitial_sites[0]]
        for site in interstitial_sites[1:]:
            is_dup = False
            for u in unique:
                if np.linalg.norm(site["coords"] - u["coords"]) < 0.5:
                    is_dup = True
                    break
            if not is_dup:
                unique.append(site)
        interstitial_sites = unique

    return interstitial_sites


def compute_polyhedron_volume(struct: Structure, na_idx: int) -> float:
    """计算 Na 位点的 Voronoi 多面体体积 (Å³)。

    使用 pymatgen 的 VoronoiNN 计算配位多面体体积。
    """
    try:
        from pymatgen.analysis.local_env import VoronoiNN
        vnn = VoronoiNN()
        poly_info = vnn.get_voronoi_polyhedra(struct, na_idx)
        total_vol = 0.0
        for neighbor_info in poly_info.values():
            total_vol += neighbor_info.get("volume", 0.0)
        return float(total_vol) if total_vol > 0 else float("nan")
    except Exception:
        return float("nan")


def _safe_mean(values: list[float]) -> float:
    """安全求均值，空列表返回 NaN。"""
    if not values:
        return float("nan")
    return float(np.mean(values))


def _safe_std(values: list[float]) -> float:
    """安全求标准差，空列表返回 NaN。"""
    if len(values) < 2:
        return float("nan")
    return float(np.std(values, ddof=0))


def _safe_cv(values: list[float]) -> float:
    """安全求变异系数 (CV=std/mean)，空列表或零均值返回 NaN。"""
    if not values:
        return float("nan")
    m = float(np.mean(values))
    if abs(m) < 1e-12:
        return float("nan")
    return float(np.std(values, ddof=0) / m)
