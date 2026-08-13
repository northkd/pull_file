【会话指示 - experiment-audit (descriptor-impl)】

checklist_id: descriptor-impl
compact_level: 0
output_basename: EXPERIMENT_AUDIT_run03_3b
review_type: experiment-audit
project_path: automat-naconductor
round: 1

1. 本模板为单轮一次性审计。复制下方"prompt 正文"全部内容，粘贴到新的 Claude 对话中。
2. 审稿人返回回复后，复制回复全文回执行器，执行器解析后写入 EXPERIMENT_AUDIT_run03_3b.md 和 EXPERIMENT_AUDIT_run03_3b.json（不覆盖既有 EXPERIMENT_AUDIT.* 产物）。
3. 单一对话完成所有 7 项检查（A-G）——不要分多次对话。
4. 本批次使用 descriptor-impl 专项检查清单（描述符实现正确性审计），【非】默认 A-F 通用实验完整性清单。审稿人应聚焦于：公式实现是否与 docstring 一致、物理意义是否合理、单位是否一致、边界情况与数值稳定性、周期性边界条件、文献定义一致性、测试覆盖与可重复性。
5. 如需对单一检查项追问细节，可在同一对话中继续。
6. 何时开新对话：仅当需要重新审计（不同时间点的代码状态）时开新对话。
7. 审计对象为 4 个 --include 指定的 descriptors 文件；--exclude 排除 results/ 与 data/naconductor_featurized.csv。本项目无 paper/ 目录，声明来源是 program.md 与 README.md；无需上传 PDF 附件。

---

# Prompt 正文（复制以下内容到新的 Claude 对话）

You are an experiment integrity auditor specializing in **structural descriptor implementation correctness**. Read ALL file contents listed below and check the descriptor implementations against the descriptor-impl checklist (A-G).

This is a fresh, zero-context audit. The executor's framing is NOT evidence — read the file contents below yourself rather than trusting any executor summary.

## 你的任务

按以下 descriptor-impl 审计清单逐项检查，每项报告 Status (PASS | WARN | FAIL)、Evidence (精确的 file:line 引用)、Details (具体发现)。

## 审计清单 (descriptor-impl)

### A. 公式实现正确性 (Formula Implementation Correctness)
对每个描述符函数（compute_*）：
1. 代码实现是否与 docstring 描述的数学定义一致？
2. 是否有公式实现错误（符号错误、运算顺序错误、系数错误、分子分母颠倒）？
3. 中间步骤是否有数值精度问题（如先求和再除 vs 先除再求和）？
4. 聚合操作（mean/std/cv）的 ddof 参数是否与 docstring 声明一致？
FAIL if: 代码实现与 docstring 定义的数学公式不一致。

### B. 物理意义合理性 (Physical Meaning Validity)
对每个描述符：
1. docstring 描述的物理意义是否清晰且正确？
2. 描述符的取值范围是否符合物理预期（如比率应在 0-1 或合理区间，距离应为正数）？
3. 是否有物理上不合理的假设（如忽略温度、压强效应但未说明，或用阴离子半径 2 倍作为理想 X-X 距离这种简化是否注明）？
4. "BVSE 依赖的描述符返回 NaN" 这类降级处理是否在 docstring 中明确？
WARN if: 物理意义描述含糊或有明显未注明的简化假设。

### C. 单位一致性 (Unit Consistency)
1. 所有距离单位是否统一为 Å？
2. 所有体积单位是否统一为 Å³？
3. 无量纲量（比率、CV、占位和）是否真的无量纲？
4. Shannon 半径（NA_EFFECTIVE_RADII_A、ANION_EFFECTIVE_RADII_A）的单位是否与计算中使用的距离单位一致？
5. 截断距离（_anion_cutoff、access_threshold=3.0、cutoff=3.5、max_dist=4.0、+0.70Å）的单位是否均为 Å？
FAIL if: 同一计算中混用了不同单位，或常数值与单位不匹配。

### D. 边界情况与数值稳定性 (Edge Cases & Numerical Stability)
对每个描述符函数：
1. 空列表/空结构是否返回 NaN 而非崩溃（IndexError/ZeroDivisionError）？
2. 零除是否被防护（如 _safe_cv 检查 abs(m) < 1e-12）？
3. 部分占位（occupancy < 1）是否正确处理（site_occupancies_by_symbol 累加）？
4. 含 N（无经典 Shannon 半径，ANION_EFFECTIVE_RADII_A["N"]=None）的阴离子是否正确降级（_effective_anion_radius 返回 None）？
5. 浮点比较是否使用了容差（1e-6、1e-12 等）而非精确等于？
6. find_interstitial_sites 的 Voronoi 失败是否被 try/except 捕获并返回空列表？
7. compute_interstitial_network_dim 的 0D/1D/2D 分类阈值（0.3、0.6）是否会导致边界值误分类？
WARN if: 存在未防护的零除或空列表访问。
FAIL if: 边界情况会导致崩溃而非返回 NaN。

### E. 周期性边界条件 (Periodic Boundary Conditions)
1. 距离计算是否考虑了周期性影像（用 lattice.get_distance_and_image 而非直接 np.linalg.norm）？
2. Voronoi 剖分（find_interstitial_sites）是否生成了 ±1 周期性影像？
3. 间隙位点去重是否考虑了周期性等价（get_distance_and_image < 0.5Å）？
4. get_na_x_bonds 和 _shell_neighbors 用 get_sites_in_sphere 是否正确处理了周期性？
5. compute_interstitial_network_dim 中间隙位点间距离用 np.linalg.norm(coords[i]-coords[j]) ——这是笛卡尔坐标距离，是否考虑了周期性影像？若未考虑，是否会导致网络维度被低估？
FAIL if: 在周期性结构中直接用欧氏距离计算近邻距离，且未说明或未补偿。

### F. 文献定义一致性 (Literature Definition Consistency)
1. NA_EFFECTIVE_RADII_A 的 Shannon 有效离子半径值是否与经典文献（Shannon 1976）一致？逐项核对：CN=4→0.99, CN=5→1.00, CN=6→1.02, CN=7→1.12, CN=8→1.18, CN=9→1.24, CN=12→1.39。
2. ANION_EFFECTIVE_RADII_A 的阴离子半径值是否与文献一致？O=1.40, S=1.84, Se=1.98, F=1.33, Cl=1.81, Br=1.96, I=2.20, H=1.40, N=None。
3. 配位数（CN）定义是否与 Shannon 表一致（第一配位壳层数）？
4. _shell_neighbors 的"最短键长 +0.70Å"规则是否有文献依据？是否注明来源（part1.py）？
5. BVSE/SoftBV 相关描述符（compute_bvse_barrier_estimate）是否明确标注依赖外部数据？
6. ELECTRONEGATIVITY 的 Pauling 值是否与标准表一致？
WARN if: 常数值与文献有偏差但未注明来源；或简化规则无文献依据且未注明。

### G. 测试覆盖与可重复性 (Test Coverage & Reproducibility)
1. test_descriptors.py 是否覆盖了被审计的 4 个描述符文件中的函数？
2. 是否有针对边界情况（空结构、部分占位、含 N 阴离子）的测试？
3. 随机种子是否固定（run_info.yaml 中 random_seed: 42）？
4. 描述符计算是否可重复（相同 CIF 输入→相同描述符输出）？
5. find_interstitial_sites 的 Voronoi 算法是否确定性（无随机性）？
6. _get_interstitial_data 的 docstring 声称"带缓存效果"但实际未缓存——这是否会导致重复计算？是否影响可重复性？
WARN if: 测试覆盖不足或缺失边界情况测试。

## 文件内容

--- 文件开始: descriptors/_base.py ---
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

def element_symbol(value: object) -> str:
    """Return an element symbol for an Element, Species, or species name."""
    symbol = getattr(value, "symbol", None)
    if symbol is not None:
        return str(symbol)
    return str(value).rstrip("+-0123456789")


def site_occupancies_by_symbol(site) -> dict[str, float]:
    """Aggregate a site's occupancies by charge-independent element symbol."""
    totals: dict[str, float] = {}
    for species, occupancy in site.species.items():
        symbol = element_symbol(species)
        totals[symbol] = totals.get(symbol, 0.0) + float(occupancy)
    return totals

def get_na_sites(struct: Structure) -> list[int]:
    """获取结构中 Na 位点的索引列表。

    Na 位点 = 主要物种为 Na 的位点（考虑部分占位）。
    """
    na_indices: list[int] = []
    for i, site in enumerate(struct):
        na_occ = site_occupancies_by_symbol(site).get("Na", 0.0)
        if na_occ > 1e-6:
            na_indices.append(i)
    return na_indices


def get_anion_sites(struct: Structure) -> list[int]:
    """获取结构中阴离子位点的索引列表。"""
    anion_indices: list[int] = []
    for i, site in enumerate(struct):
        for symbol in site_occupancies_by_symbol(site):
            if symbol in ANION_ELEMENTS:
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
    species_dict = site_occupancies_by_symbol(site)
    if not species_dict:
        return ""
    return max(species_dict.items(), key=lambda kv: kv[1])[0]


def _site_occ(site, symbol: str) -> float:
    """获取位点上某元素的占位数。"""
    return site_occupancies_by_symbol(site).get(symbol, 0.0)


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

    interstitial_sites: list[dict] = []
    for vertex in vor.vertices:
        # 检查是否在原胞内 (用分数坐标)
        frac = lattice.get_fractional_coords(vertex)
        in_cell = all(-1e-6 <= f < 1.0 - 1e-6 for f in frac)
        if not in_cell:
            continue

        # 周期性影像已包含在 Voronoi 点集中；用其检查最近原子距离。
        dists = np.linalg.norm(all_points_arr - vertex, axis=1)
        min_dist = float(np.min(dists))
        if min_dist < min_dist_from_atom:
            continue

        interstitial_sites.append({
            "coords": np.array(vertex, dtype=float),
            "volume": 0.0,
        })

    # 去重: 同一区域可能因周期性影像重复出现
    if len(interstitial_sites) > 1:
        unique: list[dict] = [interstitial_sites[0]]
        for site in interstitial_sites[1:]:
            is_dup = False
            for u in unique:
                site_frac = lattice.get_fractional_coords(site["coords"])
                unique_frac = lattice.get_fractional_coords(u["coords"])
                distance, _image = lattice.get_distance_and_image(site_frac, unique_frac)
                if float(distance) < 0.5:
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
--- 文件结束: descriptors/_base.py ---

--- 文件开始: descriptors/family_c_concentration.py ---
"""C族: Na 浓度描述符 (3个)。

描述结构中 Na 的浓度和占位信息。
"""
from __future__ import annotations

from pymatgen.core import Structure

from descriptors._base import get_na_sites, site_occupancies_by_symbol


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
        na_occ = site_occupancies_by_symbol(site).get("Na", 0.0)
        total_occ += na_occ

    return float(total_occ)


def compute_na_site_count(struct: Structure) -> float:
    """Na 位点数 (不含占位权重)。"""
    na_indices = get_na_sites(struct)
    return float(len(na_indices))
--- 文件结束: descriptors/family_c_concentration.py ---

--- 文件开始: descriptors/family_d_vacancy_topo.py ---
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

    min_dists: list[float] = []

    for ist in sites:
        ist_frac = struct.lattice.get_fractional_coords(ist["coords"])
        dists = [
            float(struct.lattice.get_distance_and_image(ist_frac, struct[i].frac_coords)[0])
            for i in na_indices
        ]
        min_dists.append(min(dists))

    return _safe_mean(min_dists)


def compute_interstitial_channel_access(struct: Structure) -> float:
    """接入主通道的间隙位点比例。

    判据: 间隙位点与最近 Na 的距离 <= 3.0Å 视为接入主通道。
    """
    na_indices = get_na_sites(struct)
    sites = _get_interstitial_data(struct)

    if not sites or not na_indices:
        return float("nan")

    access_threshold = 3.0  # Å
    accessible = 0

    for ist in sites:
        ist_frac = struct.lattice.get_fractional_coords(ist["coords"])
        dists = [
            float(struct.lattice.get_distance_and_image(ist_frac, struct[i].frac_coords)[0])
            for i in na_indices
        ]
        if min(dists) <= access_threshold:
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
--- 文件结束: descriptors/family_d_vacancy_topo.py ---

--- 文件开始: descriptors/family_e_framework.py ---
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


def _get_framework_data(struct: Structure) -> dict:
    """收集骨架阳离子的配位信息。"""
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
        shell = _shell_neighbors(struct, fw_idx, anions)
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


def compute_framework_poly_distortion(struct: Structure) -> float:
    """骨架多面体畸变均值。

    骨架阳离子配位多面体键长的变异系数。
    """
    data = _get_framework_data(struct)
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
--- 文件结束: descriptors/family_e_framework.py ---

--- 文件开始: program.md ---
# Agent 结构描述符研究协议

本文件只规定 `results/agent/` 轨道。它与 `run_pipeline.py` 可以同时启动，
但在 C9 前必须独立运行和记录。

## 不可变契约

1. 先读取 `run_info.yaml` 的 `shared_input`、`data` 与 `tracks.agent`。原始 CSV
   和描述符注册表在一次研究批次中视为冻结输入。
2. 输入特征必须由注册的 CIF `Structure` 描述符计算；使用
   `train.py --descriptor-name <key>` 显式选择键。
3. 不预拆分训练、验证或测试集合。所有可用行通过共享的阴离子分层、留一体系和
   重复分层子采样 CV 接受审计。
4. 主指标是 `deconfounded_spearman`。控制设计以 `system` 为主，仅在秩上提供
   增量信息时再加入 `anion_type` 对比项。
5. 只写入 `results/agent/`。不得读取、修改、引用或根据 `results/pipeline/` 的
   中间/最终结果改变候选选择。

严格 CIF 预检和有限值检查是运行的一部分。若 CIF 缺失、不可解析，或描述符没有
足够的有效值，记录该次失败原因并停止该候选；不可用结果不能被写成成功指标。

## 单次 Agent 迭代

1. 在 `descriptors/idea.md` 说明候选的物理机制、涉及的物理族和预期混杂风险。
2. 仅在有新的、可说明的结构假设时修改/注册描述符；不得从标签反推特征。
3. 运行：

   ```bash
   python train.py --descriptor-name <descriptor-key> --run-id <iteration-id>
   ```

4. 审阅 TSV 中的 `raw_spearman`、`deconfounded_spearman`、`system_proxy_ratio`、
   各 CV 策略的可用性和 MAE。被标为 `skipped` 的策略应保持显式，不可补零或当作
   支持证据。
5. 在人工复核后，可用下一次命令的 `--status keep|discard|crash` 标记结果；默认
   状态是 `evaluated`。不要只因原始相关高或单一 CV 好看就标记为保留。
6. 运行 `python run_status.py`。它只根据 Agent 的有限去混杂 Spearman 记录和
   `tracks.agent.status` 停止条件输出 `CONTINUE` 或 `STOP`。

## 结果记录

`results/agent/results.tsv` 由评估器追加。其关键列是：

```text
run_id  descriptor_name  source_rows  finite_structural_values  analysis_rows
raw_spearman  deconfounded_spearman  system_proxy_ratio  label
anion_stratified_spearman  loso_spearman  repeated_subsample_spearman
composite_score  status
```

完整表还保留各策略 `skipped`/`reason`、MAE、折数和预处理可用性，以便追溯。
`results/agent/descriptor_features.csv` 是该次描述符值与 CIF 路径的审计副本；
`test_descriptors.py` 提供同样的独立结构审计，而非 held-out split 评估。

## 描述符纪律

- 不使用 `log`、`sqrt`、`power` 或任意无量纲依据的除法构造新特征。
- 组合必须有明确物理对象/族间机制；结果应标明探索性，不作因果陈述。
- 不使用非结构输入、结果文件或其他轨道的候选作为隐蔽信息来源。
- 某描述符与体系标签高度共线时，先报告它是体系代理的可能性，而不是宣称普适机制。

## C9 边界

C9 不是 Agent 的下一步自动操作。只有用户明确授权、Agent 和 Pipeline 两边均完成
并冻结后，才可对两个目录作**只读**比较。共同出现的候选只是独立三角验证或优先
复核线索；两轨都不建立因果关系。若结果不同，应报告搜索空间、混杂、缺失数据与
统计支持度的差异，而不是自动选择任一方。
--- 文件结束: program.md ---

--- 文件开始: run_info.yaml ---
# Na离子导体描述符搜索配置
# 基于 automat 框架，针对 Na 离子固态电解质结构描述符与电导率关系研究

task:
  name: naconductor
  description: >
    搜索 Na 离子固态导体的局域结构描述符组合，
    使其与 log10(σ/S·cm⁻¹) 的去混杂 Spearman 相关性最大化。
    描述符从 CIF 结构文件计算，禁止使用 log/√/幂运算构造新特征。
    目标是找到物理可解释、统计稳健的描述符组合，
    而非单纯追求预测精度。

data:
  raw_file: data/naconductor_raw.csv
  featurized_file: data/naconductor_featurized.csv
  target_column: log_sigma
  structure_column: cif_path
  material_id_column: material_id
  formula_column: formula
  system_column: system
  anion_type_column: anion_type
  # 不做 train/val/test 预拆分——用 CV 策略替代
  # 原始数据 84 行，全量参与交叉验证

cv_strategies:
  # 策略 1：阴离子分层 K 折；类别不足两例时显式跳过，支持不足时显式降折
  - name: anion_stratified_cv
    folds: 3
    stratify_by: anion_type
    random_seed: 42
    insufficient_class_policy: skip
    requested_fold_downshift: explicit
  # 策略 2：留一体系交叉验证（LOSO-CV）
  # 每次留出一个体系（NASICON/sulfide/halide）作为验证集
  - name: leave_one_system_out
    group_column: system
  # 策略 3：重复随机子采样
  - name: repeated_subsample
    n_repeats: 10
    test_fraction: 0.2
    stratify_by: system
    random_seed: 42

deconfound:
  # 混杂变量列表——这些变量与目标相关但不是因果通路
  # 在计算描述符-目标相关性时需要控制
  confounders:
    - system          # 主控制：体系类型（NASICON/sulfide/halide）
    - anion_type      # 增量控制；报告相对 system 的秩增量/冗余，不作独立因果解释
  categorical_coding: reference_class
  primary_control: system
  report_design_rank: true
  # 去混杂方法：偏相关 / DML（Double Machine Learning）
  method: partial_correlation  # 可选: partial_correlation, dml
  # 去混杂后的 Spearman rho 作为主要评价指标
  primary_metric: deconfounded_spearman

stability_selection:
  # 子采样 Lasso；填充和缩放在每个子样本 Pipeline 内独立拟合
  method: subsampled_lasso
  selection_alpha: 0.05
  preprocessing:
    - median_imputation
    - standard_scaling
  n_bootstrap: 100
  threshold: 0.6          # 被选中的频率阈值
  fraction: 0.5           # 每次自举采样比例
  random_seed: 42

combination:
  # 原始物理值上的受约束枚举；只在完整公式进入模型后做折内标准化
  method: constrained_enumeration
  raw_value_source: feature_df
  max_descriptors: 3
  min_descriptors: 2
  pair_rules:
    source_of_truth: descriptors.combination.PAIR_OPERATOR_RULES
    execution: enforced_by_declarative_registry
    commutative_operators: [add, multiply]
    canonical_unordered_pairs: true
    directional_ratios: explicit_registry_entries_only
    reject_zero_or_nonfinite_denominator: true
    default_ratio_allowed: false
  triple_rules:
    adjacency_source_of_truth: descriptors.combination.PAIR_OPERATOR_RULES
    same_family_source_of_truth: descriptors.combination.SAME_FAMILY_OPERATOR_RULES
    execution: enforced_by_declarative_registry
    enabled: true
    shape: two_from_one_family_plus_one_from_explicit_adjacent_family
    arbitrary_triples: false
  # 禁止的运算符——描述符构造中不允许使用
  forbidden_operators:
    - log          # 禁止对原始描述符取对数（因为目标已是 log）
    - sqrt         # 禁止开方（物理意义不明确）
    - power        # 禁止幂运算（过拟合风险高）
  # 下列语义目前是人工解释审查要求，不是程序化筛选条件。
  manual_physical_interpretation_review:
    enforced_by_search: false
    review_questions:
      - monotonic_with_ion_size
      - positive_correlation_with_vacancy

combination_validation:
  status: exploratory
  causal_claim: false
  evidence_blocks:
    - noise_baseline
    - factor_spanning
    - per_system
    - bootstrap_ci
  bootstrap:
    method: system_stratified
    random_seed: 42
  factor_spanning:
    primary_method: fold_safe_oof_target_residual_prediction
    control_design: rank_aware_system_primary_plus_incremental_anion
    formula_preprocessing: fold_local_median_imputation_and_scaling
    partial_association_role: supplementary_only
  selection_uncertainty:
    nested_outer_group_selection_available: false

evaluation:
  # 主要评价指标
  primary: deconfounded_spearman
  # 辅助评价指标
  secondary:
    - cv_spearman       # 交叉验证 Spearman rho
    - cv_mae            # 交叉验证 MAE
    - cv_rmse           # 交叉验证 RMSE
    - stability_score   # 稳定性选择得分
  # 模型
  model:
    # Ridge 回归：84 样本用 RF 容易过拟合，Ridge 正则化更稳健
    name: ridge
    alpha: 1.0          # L2 正则化强度
    random_seed: 42
    fold_preprocessing:
      - median_imputation
      - standard_scaling
  # 相关性方法
  correlation_method: spearman   # 使用 Spearman 秩相关（非参数，适合小样本）

# 两条轨道只共享这一冻结输入契约；任何运行结果均不共享。
shared_input:
  frozen: true
  raw_file: data/naconductor_raw.csv
  descriptor_registry: descriptors/__init__.py
  registry_revision: structural-registry-v1-2026-08-03
  semantics: >
    Agent 与 pipeline 可以同时启动，并只读取本节指定的原始 CSV 与注册表。
    在 C9 前禁止任一轨道读取、修改或据另一轨道的结果作筛选决定。

tracks:
  pipeline:
    output_dir: results/pipeline
    reads: [shared_input]
    must_not_read: [results/agent]
    status: exploratory

  agent:
    results_file: results/agent/results.tsv
    ideas_file: results/agent/ideas.tsv
    feature_cache_file: results/agent/descriptor_features.csv
    figure_file: results/agent/figures/metric_history.png
    reads: [shared_input]
    must_not_read: [results/pipeline]
    status:
      primary_metric: deconfounded_spearman
      max_iterations: 30
      patience: 8
      semantics: >
        仅对 status 为 evaluated、keep 或 discard 的有限去混杂 Spearman
        计入耐心；crash 和不可用 CV 策略不会伪造改善或消耗耐心。

c9_cross_track_review:
  user_authorization_required: true
  inputs_must_be_completed_and_frozen: true
  read_only_inputs: [results/agent, results/pipeline]
  interpretation: >
    结果一致仅是独立三角验证或优先复核线索，不构成因果证据；
    两条轨道均不建立因果关系。
--- 文件结束: run_info.yaml ---

--- 文件开始: test_descriptors.py ---
"""Compatibility entry point for a strict structural descriptor audit.

This compatibility-named command audits one explicit descriptor against the
frozen raw CIF dataset and writes only an Agent-track audit CSV.  It does not
read or write Pipeline results.
"""
from __future__ import annotations

import sys
from typing import Any

from automat_utils import format_agent_metrics, prepare_structural_evaluation, write_structural_audit
from train import parse_agent_args


def parse_audit_args(argv: list[str] | None = None):
    """Use the same explicit descriptor/CIF contract as ``train.py``."""
    return parse_agent_args(argv)


def run_structural_audit(args: Any) -> tuple[dict[str, Any], str]:
    """Return metrics and write the reproducible descriptor-value audit."""
    frame, metrics = prepare_structural_evaluation(args)
    audit_path = write_structural_audit(
        frame,
        descriptor_name=args.descriptor_name,
        audit_file=args.audit_file,
        metrics=metrics,
    )
    return metrics, str(audit_path)


def main(argv: list[str] | None = None) -> None:
    args = parse_audit_args(argv)
    try:
        metrics, audit_path = run_structural_audit(args)
    except (FileNotFoundError, KeyError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(2) from None

    print("Structural audit (not a held-out test split)")
    for line in format_agent_metrics(metrics):
        print(line)
    print(f"structural_audit_file:      {audit_path}")
    print("track_isolation:             agent writes results/agent only; no pipeline output read")


if __name__ == "__main__":
    main()
--- 文件结束: test_descriptors.py ---

--- 文件开始: README.md ---
# automat-naconductor

`automat-naconductor` 用 CIF 晶体结构计算 Na 离子导体描述符，并提供两条
**可同时运行、彼此隔离**的研究轨道：

| 轨道 | 入口 | 产物 | 作用 |
| --- | --- | --- | --- |
| Pipeline | `run_pipeline.py` | `results/pipeline/` | 受物理规则约束的组合搜索与 V1–V4 探索性验证 |
| Agent | `train.py` | `results/agent/` | 对 Agent 明确提出的单个结构描述符进行独立审计 |

两条轨道只共享 `run_info.yaml: shared_input` 中冻结的原始 CSV 和描述符注册表。
它们可以无顺序依赖地并发启动；在用户授权的 C9 之前，Agent 不读取
`results/pipeline/`，Pipeline 也不读取 `results/agent/`。

## 数据与统计契约

- 输入是 `data/naconductor_raw.csv` 中的 `cif_path`。相对路径以该 CSV 所在
  目录为准解析。
- 每次 Agent 评估都对全部 CIF 做存在性和可解析性预检。预检失败会在创建
  任何 Agent 输出前失败退出；全 NaN 描述符同样会失败，不会产生假阳性结果。
- `log_sigma` 已是目标变量。主指标是控制以 `system` 为主、仅保留秩增量
  `anion_type` 对比项后的 `deconfounded_spearman`。
- Ridge 的填补和标准化均在每一个 CV 训练折内拟合。阴离子分层、留一体系和
  重复分层子采样中，任何不可行的策略会显式记录为 `skipped`，而不是被当作零分
  或导致整个评估崩溃。
- 当前检出的是关联性/预测稳健性证据，不建立因果关系。

当前工作区若缺少原始 CSV 指向的 CIF，两个入口都会给出清晰的预检错误；不要把
旧的全缺失特征化文件当作研究结果。

## 并发启动

在项目根目录 `automat-naconductor/` 中，以下命令可以在两个终端并发运行：

```bash
python run_pipeline.py
python train.py --descriptor-name a2_max_dist --run-id agent-001
```

Pipeline 的默认输出目录是 `results/pipeline/`。Agent 的结果、描述符值审计和图
分别位于 `results/agent/results.tsv`、`results/agent/descriptor_features.csv` 和
`results/agent/figures/`；CLI 会拒绝将 Agent 工件写入 Pipeline 路径。

Agent 的独立结构审计（历史 `test_descriptors.py` 的兼容入口）为：

```bash
python test_descriptors.py --descriptor-name a2_max_dist
```

它不是预拆分的 held-out 测试，而是对同一冻结 CIF 数据进行可复核的结构审计。

## Agent 轨道

`train.py` 不选择隐式默认描述符。每次运行必须显式给出
`--descriptor-name`，其键来自 `descriptors.AVAILABLE_STRUCTURE_DESCRIPTORS` 的
活跃描述符。一次成功评估会：

1. 严格加载 raw CSV 与 CIF `Structure`；
2. 计算该结构描述符；
3. 使用 `DeconfoundAnalyzer` 的秩感知控制设计；
4. 使用共享 `MultiStrategyCV` 的 Ridge 管线；
5. 将审计 CSV 和一行 TSV 指标写入 `results/agent/`。

停止判断和绘图也只读取 Agent 产物：

```bash
python run_status.py
python plot_run_results.py
```

`run_status.py` 只以有限的 `deconfounded_spearman` 记录判断改善；`crash` 行和
不可用 CV 策略不会制造"没有改善"的证据。具体的最大迭代数与耐心值在
`tracks.agent.status` 中配置。

## Pipeline 轨道

```bash
python run_pipeline.py --top-k 10
```

Pipeline 依次完成描述符审计、稳定性选择、受约束的二/三元组合搜索和 V1–V4
探索性验证。它默认写入 `results/pipeline/`，也不将 Agent 的候选或结果作为输入。
如需在测试中指定另一个输出目录，可显式传 `--output-dir`。

## C9：仅在用户授权后进行只读比较

当且仅当用户明确要求 C9，并且两边的输出都已经完成、冻结后，才可对
`results/agent/` 和 `results/pipeline/` 做只读对比。两轨发现相同的候选只代表独立
三角验证或应优先复核的线索；不代表"非常可靠"的定论，更不构成因果证据。两轨
结果不一致同样是需要追溯搜索空间、混杂和数据支持度的研究信息。

## 主要文件

- `run_info.yaml`：冻结输入、CV/去混杂设置、两条轨道的输出隔离契约。
- `descriptors/`：CIF 结构描述符注册、特征化、CV、去混杂、稳定性和组合验证。
- `train.py`、`automat_utils.py`：Agent 的结构描述符评估器。
- `test_descriptors.py`：Agent 的独立结构审计入口。
- `run_status.py`、`plot_run_results.py`：只针对 Agent TSV 的停止判断与可视化。
- `program.md`：Agent 研究纪律与可审计记录格式。
--- 文件结束: README.md ---

## 输出格式

For each check (A-G), report:
- Status: PASS | WARN | FAIL
- Evidence: exact file:line references
- Details: what specifically was found

Overall verdict: PASS | WARN | FAIL

Be thorough. Read every descriptor function line by line. Cite specific file:line for every finding.

请按以下结构输出：

## A. 公式实现正确性 (Formula Implementation Correctness)
- Status: [PASS | WARN | FAIL]
- Evidence: [file:line references]
- Details: [findings]

## B. 物理意义合理性 (Physical Meaning Validity)
- Status: [PASS | WARN | FAIL]
- Evidence: [file:line references]
- Details: [findings]

## C. 单位一致性 (Unit Consistency)
- Status: [PASS | WARN | FAIL]
- Evidence: [file:line references]
- Details: [findings]

## D. 边界情况与数值稳定性 (Edge Cases & Numerical Stability)
- Status: [PASS | WARN | FAIL]
- Evidence: [file:line references]
- Details: [findings]

## E. 周期性边界条件 (Periodic Boundary Conditions)
- Status: [PASS | WARN | FAIL]
- Evidence: [file:line references]
- Details: [findings]

## F. 文献定义一致性 (Literature Definition Consistency)
- Status: [PASS | WARN | FAIL]
- Evidence: [file:line references]
- Details: [findings]

## G. 测试覆盖与可重复性 (Test Coverage & Reproducibility)
- Status: [PASS | WARN | FAIL]
- Evidence: [file:line references]
- Details: [findings]

## Overall Verdict: [PASS | WARN | FAIL]

## Action Items
- [specific fixes if WARN or FAIL]

## Claim Impact
- Claim 1 (来自 program.md / README.md 的声明): [supported | needs_qualifier | unsupported]
- Claim 2: ...

[执行器提示]
- 本次审计使用 descriptor-impl 检查清单（描述符实现正确性专项审计），非默认 A-F 通用实验完整性清单。
- 精简等级: Level 0（全文嵌入，未超 80K 字符阈值）。
- 嵌入文件: 8 个（4 个 --include 指定的 descriptors 文件 + program.md + run_info.yaml + test_descriptors.py + README.md）。
- 排除项: results/ 目录、data/naconductor_featurized.csv（按 --exclude 参数）；项目无 EXPERIMENT_TRACKER.md 和 NARRATIVE_REPORT.md。
- 声明来源: program.md（Agent 研究协议）+ README.md（数据与统计契约）+ run_info.yaml（冻结配置）；本项目无 paper/ 目录，无需上传 PDF 附件。
- 输出文件命名: EXPERIMENT_AUDIT_run03_3b.md / .json（不覆盖既有 EXPERIMENT_AUDIT.* 产物）。
- 审计对象函数清单:
  * _base.py: get_na_sites, get_anion_sites, get_framework_sites, get_na_x_bonds, _anion_cutoff, _shell_neighbors, _effective_na_radius, _effective_anion_radius, find_interstitial_sites, compute_polyhedron_volume, _safe_mean, _safe_std, _safe_cv
  * family_c_concentration.py: compute_na_concentration, compute_na_occupancy_sum, compute_na_site_count
  * family_d_vacancy_topo.py: compute_interstitial_count, compute_interstitial_na_distance, compute_interstitial_channel_access, compute_interstitial_network_dim, compute_bvse_barrier_estimate
  * family_e_framework.py: compute_framework_bond_rigidity, compute_framework_poly_distortion, compute_framework_na_distance_stability, compute_framework_sharing_topology
