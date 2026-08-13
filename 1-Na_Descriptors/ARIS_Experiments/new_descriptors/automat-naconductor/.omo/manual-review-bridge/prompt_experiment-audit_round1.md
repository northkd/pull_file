【会话指示 - experiment-audit】

1. 本模板为单轮一次性审计。复制下方"prompt 正文"全部内容，粘贴到新的 Claude 对话中。
2. 审稿人返回回复后，复制回复全文回执行器，执行器解析后写入 EXPERIMENT_AUDIT.md 和 EXPERIMENT_AUDIT.json。
3. 单一对话完成所有检查项——不要分多次对话。
4. 如需对单一检查项追问细节，可在同一对话中继续。
5. 何时开新对话：仅当需要重新审计（不同时间点的代码状态）时开新对话。
6. 本次使用的清单 profile：descriptor-impl
   checklist_id：descriptor-impl@v1
   ** 审稿人必须在报告第一行原样回显该 checklist_id。**
   若回显值与此处不符，本次审计作废，不得写入产物。
7. 本次审计范围：
   嵌入文件：descriptors/family_a_polyhedron.py, descriptors/family_b_network.py, descriptors/_base.py
   排除路径：results/, data/naconductor_featurized.csv

---

请将以下标识符原样回显为报告的第一行，放在任何其他内容之前：

checklist_id: descriptor-impl@v1

如果你使用的不是该标识符对应的清单，请说明，不要回显它。

你是一名特征实现审计员。下方代码从原始结构化对象计算数值描述符。你的任务是检查每个描述符是否计算了其名称和文档所声称的量，以及其值在管线将遇到的输入变异范围内是否良定义。

这是一次代码与规格审计。不要评估描述符在科学上是否有用——评估的是它们是否名副其实。

## 你的任务

按以下审计清单逐项检查，每项报告 Status (PASS | WARN | FAIL | NOT_APPLICABLE)、
Evidence (精确的 file:符号锚点 引用)、Details (具体发现)。

若某项所需的文件未在本 prompt 中提供，报 NOT_APPLICABLE 并说明缺什么，
不要因文件缺失而报 FAIL。

## 审计清单

### A. 公式保真度 (Formula Fidelity)
对每个描述符：
1. 其名称、docstring 和注册表元数据声称计算的是什么量？
2. 代码实际计算的是什么量？请把实现的公式显式写出来。
3. 两者是否一致？报告任何名称承诺一个量而函数体计算另一个量的描述符——
   包括符号约定、均值是对位点取还是对键取、以及"畸变"究竟是指方差、
   变异系数、最大值-最小值极差、还是二次伸长。
4. 当文献中存在该命名量的标准定义时，实现是否与之一致？请指出标准定义的名称。
FAIL if: 任何描述符的实现公式未计算其声称的量。

### B. 退化输入处理 (Degenerate Input Handling)
对每个描述符，追踪以下情况返回的值：
1. 恰好有一个迁移离子位点，或相关物种只有一个原子
2. 没有近邻落在截断半径内
3. 所有位点对称等价（被平均的量方差为零）
4. 位点占位是部分或分数的
5. 结构无序，或含混合占位位点
逐一报告：返回的是 NaN、哨兵值、零、还是一个静默的错误值？
FAIL if: 退化输入返回了一个有限值，且该值在下游无法与合法测量值区分。

### C. NaN 与哨兵路径 (NaN and Sentinel Paths)
1. 枚举每个描述符中所有产生 NaN 或哨兵值（999, -1, 0.0, inf）的代码路径。
2. 对每条路径：该结果值在下游能否与同量级的合法值区分？
3. NaN 的产生是否与输入的某个属性相关——空间群、晶系、化学组成、
   晶胞大小、位点数？如果解析器或几何例程在某一结构类上系统性失败，
   缺失模式本身就构成了一个编码变量。
FAIL if: 任何失败路径返回有限值；WARN if: 缺失可能与其结构相关且未记录。

### D. 晶胞设置不变性 (Cell-Setting Invariance)
1. 对每个描述符，同一晶体以原胞 vs 惯用胞给出时，值是否改变？
2. 超胞扩展下是否改变？
3. 解析器的占位容差设置对每个描述符看到的位点列表有什么影响？
4. 是否有描述符依赖于输入文件中位点的排列顺序？
FAIL if: 任何描述符的值依赖于同一晶体的晶胞设置。
这是本 profile 中影响最大的检查项——设置相关的描述符产生的值与数据来源
相关，而非与物理相关。

### E. 截断与参数来源 (Cutoff and Parameter Provenance)
对每一个数值常数——距离截断、离子或共价半径、容差、壳层宽度、去重距离：
1. 是否有标明来源（发表的数据表、标准约定、推导）？
2. 还是从内部前驱脚本继承的，这是一条来源链而非正当理由？
3. 对每个常数做适度扰动后，描述符跨结构的排序是否会改变？是否有此类敏感性检查？
FAIL if: 常数未记录来源 且 描述符排序对其敏感。

### F. 确定性与顺序依赖 (Determinism and Order Dependence)
1. 同一输入文件是否总产生同一值？
2. 位点顺序、近邻列表顺序、浮点累加顺序是否影响结果？
3. 是否有任何 set 或 dict 迭代，或任何不稳定排序，出现在通向返回值的路径上？
4. 是否存在随机性？若有，是否设了种子？
FAIL if: 同一输入的重复求值可能给出不同结果。

### G. 广延性分类 (Extensivity Classification)
对每个描述符，分类为强度量（intensive，与系统大小无关）或
广延量（extensive，随晶胞内容物缩放），并指出：
1. 该分类是否在注册表元数据中有记录？
2. 广延量是否在未归一化的情况下跨不同晶胞内容的结构做比较或排序？
3. 对于管线允许组合的任意描述符对：组合的广延性是否从其操作数推出？
   两个广延量的比值是强度量；一个广延量与一个强度量的乘积是广延量，
   因而依赖晶胞大小。
输出每个描述符的显式 intensive/extensive 赋值。下游的量纲与组合约束依赖它。
FAIL if: 广延描述符跨结构比较时未归一化。

### H. 跨族冗余 (Cross-Family Redundancy)
1. 是否有分属不同族的两个描述符计算了同一底层量（只是名称不同），
   或通过单调变换相关的量？
2. 同一族内是否有两个描述符仅在对同一逐位点量的聚合方式上不同
  （均值 vs 中位数 vs 最大值）？
3. 注册表中的族分配反映的是每个描述符测量的物理对象，
   还是反映它写在哪个源文件里？
报告任何族标签宣称了实现所不具备的独立性的描述符对。
FAIL if: 声明的跨族对是单个量的代数重述。

## 强制输出：描述符登记表

除逐项判定外，必须输出一张覆盖本次送审全部描述符的表格。这张表是本 profile
的主要交付物，下游的量纲约束、族代表选择与组合规则都消费它：

| descriptor | family (registry) | claimed quantity | implemented quantity | agree? | dimension | intensive/extensive | cell-setting invariant? | NaN paths |
|---|---|---|---|---|---|---|---|---|

对无法从所提供文件判定的单元格，填 `unverifiable`，不要留空、不要猜测。

## 输出格式

每项检查报告：
- Status: PASS | WARN | FAIL | NOT_APPLICABLE
- Evidence: 精确的 file:line 引用
- Details: 具体发现

请按以下结构输出（每项检查用 ### 开头，字母与标题之间用句点分隔）：

### A. [检查项标题]: [PASS | WARN | FAIL | NOT_APPLICABLE]
- Evidence: [file:line references]
- Details: [findings]

### B. [检查项标题]: [PASS | WARN | FAIL | NOT_APPLICABLE]
...

最后必须单独输出一行总判定，格式严格如下：

## Overall Verdict: [PASS | WARN | FAIL]

## Action Items
- [specific fixes if WARN or FAIL]

## Claim Impact
- Claim 1: [supported | needs_qualifier | unsupported]

[descriptor-impl profile only: 在此追加描述符登记表，见 §11.6]

## 文件内容

--- 文件开始: descriptors/family_a_polyhedron.py ---
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


def _collect_na_x_data(struct: Structure) -> dict:
    """收集所有 Na 位点的 Na-X 键信息，返回中间数据字典。"""
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
        shell = _shell_neighbors(struct, na_idx, anions)
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


def compute_poly_distortion_mean(struct: Structure) -> float:
    """Na 多面体畸变均值。

    每个Na位点 Na-X 键长的变异系数(CV)，然后对所有Na位点取均值。
    """
    data = _collect_na_x_data(struct)
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
--- 文件结束: descriptors/family_a_polyhedron.py ---

--- 文件开始: descriptors/family_b_network.py ---
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
--- 文件结束: descriptors/family_b_network.py ---

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

[执行器提示：本次审计对象为上述三个描述符实现文件的代码逻辑。results/ 目录与 data/naconductor_featurized.csv 已按 --exclude 排除，未嵌入。若某检查项因缺少这些文件而无法判定，请报 NOT_APPLICABLE 并说明缺什么，不要因文件缺失而报 FAIL。]
