# AUTOMAT-NaConductor 改造实施计划

> 版本: 1.0 | 日期: 2026-08-02 | 状态: DRAFT
> 作者: Prometheus | 执行: Worker Agent (via `/start-work`)

---

## 0. 背景与动机

### 0.1 为什么改造 AUTOMAT

AUTOMAT 是一个"化学组成→特征→RF评估→keep/discard"的自动化描述符搜索框架。我们的任务是从 CIF 晶体结构中搜索 Na 离子电导率的物理描述符组合。直接使用 AUTOMAT 的兼容性仅 35%，原因：

1. **输入层不匹配**：AUTOMAT 只接受 Composition（化学式），我们需要 CIF 结构文件
2. **描述符层不匹配**：AUTOMAT 用 matminer 的组成描述符，我们需要局域结构描述符
3. **评估层不匹配**：AUTOMAT 用 RF + 3-fold CV + MAE，我们需要因果推断 + 多策略 CV + 去混杂分析
4. **搜索层不匹配**：AUTOMAT 的组合搜索无物理约束，我们需要双层约束（算符+物理对象）

但 AUTOMAT 的**迭代范式**（idea.md→idea.py→评估→keep/discard→审计追踪）值得保留。

### 0.2 核心研究问题

> 什么样的局域结构特征与 Na 离子电导率强相关？这种相关在控制体系混杂因素后是否依然稳定？

必须回答的分解问题：
- **Q1**：描述符 X 与 logσ 的相关中，有多少来自"区分体系"，多少来自"体系内物理"？
- **Q2**：控制体系混杂后，哪些描述符仍有独立信号？
- **Q3**：物理约束下的描述符组合能否比单描述符更好地预测电导率？
- **Q4**：这种组合优势是真实的还是过拟合/噪声？

### 0.3 关键约束

| 约束 | 说明 |
|------|------|
| 样本量 | ~80-90（3 体系：NASICON/硫化物/卤化物） |
| 输入 | CIF 文件（非化学式），CSV 用 `cif_path` 列 |
| 组合算符 | 仅 +（叠加）、×（协同）、同量纲比值；**禁止** log/√/幂次/任意除法 |
| 物理对象 | 仅同族或相邻族可组合，需物理机制解释 |
| 空位数据 | occupancy 不可靠（72/103 = 1），改用 Voronoi/BVSE 间隙位点 |
| 原始代码 | 不修改 `automat/` 原目录 |
| 已知基准 | 局域宽松因子 Spearman=0.597，瓶颈加权宽松因子(A2×NaNa) Spearman=0.623 |

---

## 1. 文件结构

改造后的目录树：

```
automat-naconductor/
├── program.md                    # 改造后的框架契约
├── run_info.yaml                 # 任务配置（YAML）
├── data/
│   ├── naconductor_raw.csv       # 原始数据（cif_path, system, anion, log_sigma, ...）
│   └── naconductor_featurized.csv  # 描述符计算后（41列描述符 + 噪声列 + 元数据）
├── descriptors/
│   ├── __init__.py               # 注册所有描述符函数
│   ├── family_a_polyhedron.py    # 组A: Na多面体（11个）
│   ├── family_b_network.py       # 组B: Na-Na网络（5个）
│   ├── family_c_concentration.py # 组C: Na浓度（3个）
│   ├── family_d_vacancy_topo.py  # 组D': 空位拓扑（5个）
│   ├── family_e_framework.py     # 组E: 骨架刚性（4个）
│   ├── family_f_longrange.py     # 组F: 长程关联（4个）
│   ├── family_g_electronic.py    # 组G: 电子结构代理（4个，高风险）
│   ├── family_h_symmetry.py      # 组H: 对称性破缺（5个，高风险）
│   └── _base.py                  # 基类和工具函数
├── featurizer.py                 # 从 CIF 批量计算描述符（替代 automat_utils.featurize_formula）
├── cv_strategies.py              # 多策略交叉验证
├── deconfound.py                 # 体系去混杂分析
├── stability_selection.py        # Stability Selection + 噪声基线
├── physical_grouping.py          # 物理分组 + 去冗余选代表
├── combination_search.py         # 物理约束组合搜索
├── combination_validate.py       # 组合验证（噪声基线/Factor Spanning/分层/bootstrap）
├── evaluate.py                   # 综合评估（替代 train.py）
├── pipeline.py                   # 4阶段流水线入口
├── idea_template.md              # idea.md 模板（改造版）
└── examples/
    └── naconductor/
        ├── 1/idea.py             # 第1代：单描述符筛选
        ├── 2/idea.py             # 第2代：物理分组去冗余
        ├── 3/idea.py             # 第3代：组合搜索
        └── 4/idea.py             # 第4代：组合验证
```

---

## 2. 实施任务详细规范

### C1: 复制 AUTOMAT 并改造数据层和配置系统

**目标**：建立 `automat-naconductor/` 目录，改造输入/配置系统适配 CIF + 体系标签 + 因果推断需求。

**输入**：
- `automat/` 原目录（只读参考）
- 原始数据集 `data/快慢离子导体数据集_103_备份.xlsx`

**输出**：
1. `automat-naconductor/` 目录结构（如上）
2. `automat-naconductor/run_info.yaml`：改造后的配置
3. `automat-naconductor/data/naconductor_raw.csv`：标准化输入 CSV
4. `automat-naconductor/program.md`：改造后的框架契约

**实现细节**：

#### C1.1 复制目录
```bash
cp -r automat/ automat-naconductor/
# 删除不需要的文件
rm -rf automat-naconductor/automat/descriptors/  # 将用新描述符替换
rm -rf automat-naconductor/examples/             # 将用新 example 替换
rm -rf automat-naconductor/autoresearch/          # GPT预训练系统，不需要
```

#### C1.2 run_info.yaml 改造
```yaml
# 原始 AUTOMAT 的 run_info.yaml
# task: Tc
# cv_folds: 3
# model: RandomForest(400 trees)
# ...

# 改造后
task: naconductor_conductivity
target_column: log_sigma          # 目标变量：log10(σ) S/cm
cif_column: cif_path             # 输入列：CIF文件路径
system_column: system             # 体系标签：NASICON/sulfide/halide
anion_column: anion_type          # 阴离子标签：O/S/F/Cl/Br/I
sample_id_column: material_id     # 样本ID

cv_strategies:
  anion_stratified:              # 阴离子分层3-fold
    n_folds: 3
    stratify_by: anion_type
  loso:                          # Leave-One-System-Out
    systems: [NASICON, sulfide, halide]
  within_system:                 # 体系内CV（每个体系单独做）
    n_folds: 3

deconfound:
  method: residual_partial       # 残差/偏相关去混杂
  confound_columns: [system]     # 混杂变量
  control_model: ridge           # 用 Ridge 回归去除混杂成分

stability_selection:
  n_bootstrap: 500               # bootstrap 次数
  subsample_ratio: 0.5           # 每次抽样比例
  selection_threshold: 0.6       # 选择频率阈值
  n_noise: 15                    # 噪声列数
  noise_seed: 42                 # 噪声种子（预固定）

combination:
  allowed_operators: [add, multiply, ratio_same_dim]  # 允许的算符
  max_combination_size: 3        # 最多3个描述符组合
  physical_groups:               # 物理分组定义（见 C6）
    A: [family_a_polyhedron]
    B: [family_b_network]
    C: [family_c_concentration]
    D_prime: [family_d_vacancy_topo]
    E: [family_e_framework]
    F: [family_f_longrange]
    G: [family_g_electronic]
    H: [family_h_symmetry]
  cross_group_rules:             # 跨族组合规则
    allowed:
      - [A, B]                   # "宽×通"
      - [A, D_prime]             # "宽松×间隙可达"
      - [A, C]                   # 仅 A/C 归一化
      - [B, D_prime]             # "连通×间隙接入"
      - [A, H]                   # "局域宽松×对称性破缺"
      - [E, A]                   # "骨架刚性×局域宽松"
    high_risk_groups: [G, H]     # 需额外去混杂验证

evaluation:
  primary_metric: deconfounded_spearman  # 主指标：去混杂后Spearman
  secondary_metrics:
    - raw_spearman
    - noise_baseline_percentile
    - factor_spanning_pvalue
    - loso_mae
    - anion_cv_mae
  model: ridge                   # 用 Ridge（而非 RF）做评估，减少过拟合

output:
  results_dir: results/
  figures_dir: figures/
  audit_file: results.tsv        # 审计追踪（保留 AUTOMAT 风格）
```

#### C1.3 naconductor_raw.csv 格式
```
material_id,cif_path,system,anion_type,log_sigma
NASICON_001,../cifs/NASICON_001.cif,NASICON,O,-2.5
sulfide_002,../cifs/sulfide_002.cif,sulfide,S,-1.8
halide_003,../cifs/halide_003.cif,halide,F,-3.2
...
```

**注意**：`cif_path` 使用相对于 CSV 文件的路径，确保可移植性。

**验收标准**：
- [ ] `automat-naconductor/` 目录存在，原 `automat/` 未被修改
- [ ] `run_info.yaml` 包含上述所有字段
- [ ] `naconductor_raw.csv` 行数与原始数据集一致（~80-90行纯Na样本）
- [ ] CSV 中 `cif_path` 指向的文件路径真实存在
- [ ] `program.md` 反映了改造后的框架契约

---

### C2: 实现 41 个描述符的计算模块

**目标**：为 8 个物理族实现全部 41 个描述符的计算函数，输入 CIF 路径，输出描述符值。

**输入**：
- CIF 文件路径
- 现有 `part1.py` 的描述符计算逻辑（参考，不直接导入）

**输出**：
- `descriptors/` 目录下的 8 个族文件 + `__init__.py` + `_base.py`
- 每个描述符函数签名：`def compute_xxx(struct: Structure) -> float`
- `featurizer.py`：批量计算入口

**实现细节**：

#### C2.1 基类 `_base.py`
```python
"""描述符基类和工具函数"""
from pymatgen.core import Structure
from typing import Protocol

class DescriptorFunc(Protocol):
    """描述符函数协议：输入Structure，输出float"""
    def __call__(self, struct: Structure) -> float: ...

# 物理族定义
PHYSICAL_FAMILIES = {
    "A": {"name": "Na多面体", "module": "family_a_polyhedron"},
    "B": {"name": "Na-Na网络", "module": "family_b_network"},
    "C": {"name": "Na浓度", "module": "family_c_concentration"},
    "D_prime": {"name": "空位拓扑", "module": "family_d_vacancy_topo"},
    "E": {"name": "骨架刚性", "module": "family_e_framework"},
    "F": {"name": "长程关联", "module": "family_f_longrange"},
    "G": {"name": "电子结构代理", "module": "family_g_electronic"},
    "H": {"name": "对称性破缺", "module": "family_h_symmetry"},
}

# 跨族组合规则
CROSS_GROUP_RULES = {
    "allowed": [
        ("A", "B"), ("A", "D_prime"), ("A", "C"),
        ("B", "D_prime"), ("A", "H"), ("E", "A"),
    ],
    "high_risk": ["G", "H"],
}

def get_na_sites(struct: Structure) -> list:
    """获取结构中所有Na位点的索引和坐标"""
    ...

def get_anion_sites(struct: Structure) -> list:
    """获取结构中所有阴离子位点的索引"""
    ...

def get_framework_sites(struct: Structure) -> list:
    """获取骨架阳离子位点（非Na、非阴离子）"""
    ...
```

#### C2.2 组 A：Na多面体族（11个描述符）

文件：`descriptors/family_a_polyhedron.py`

```python
"""组A: Na多面体局域环境描述符
物理对象: Na位点的第一配位壳层
物理含义: Na位点的"宽松程度"和"各向异性"
"""
from pymatgen.core import Structure
from pymatgen.analysis.local_env import VoronoiNN
import numpy as np

# ── 已有描述符（从 part1.py 逻辑迁移）──

def compute_a2_max_dist(struct: Structure) -> float:
    """A2: Na-X最长键长（局域宽松因子的核心）
    物理含义: Na多面体最松方向的距离，越大越宽松
    计算: 取所有Na位点的最远配位阴离子距离的均值
    """
    ...

def compute_poly_distortion_mean(struct: Structure) -> float:
    """多面体畸变均值
    物理含义: Na多面体偏离理想形状的程度
    计算: 各Na位点配位键长的变异系数均值
    """
    ...

def compute_max_bond_length(struct: Structure) -> float:
    """Na-X最长键长（同A2，保留别名）"""
    ...

def compute_min_bond_length(struct: Structure) -> float:
    """Na-X最短键长
    物理含义: Na多面体最紧方向的距离
    """
    ...

def compute_mean_bond_length(struct: Structure) -> float:
    """Na-X平均键长"""
    ...

def compute_target_bond_center(struct: Structure) -> float:
    """Na-X目标键长中心
    物理含义: 基于键价模型的理论Na-X键长
    计算: 各Na-X对的R0加权均值
    """
    ...

def compute_poly_volume_mean(struct: Structure) -> float:
    """Na多面体体积均值
    计算: 用Voronoi方法估算各Na配位多面体体积
    """
    ...

def compute_coordination_number_mean(struct: Structure) -> float:
    """Na主配位数均值
    计算: VoronoiNN方法确定各Na的配位数
    """
    ...

# ── 新增描述符 ──

def compute_ellipsoid_oblateness(struct: Structure) -> float:
    """配位椭球扁率（新增）
    物理含义: Na多面体的形状各向异性
    计算: 对Na-X键长向量做PCA，最大特征值/最小特征值，取均值
    公式: λ_max / λ_min for each Na site, then mean
    """
    ...

def compute_direction_ratio(struct: Structure) -> float:
    """最松方向与次松方向比值（新增）
    物理含义: 通道是"一个方向宽"还是"全方位宽"
    计算: 第1长键长 / 第2长键长，取均值
    """
    ...

def compute_bottleneck_anisotropy(struct: Structure) -> float:
    """迁移瓶颈各向异性（新增，需BVSE数据）
    物理含义: 不同方向的迁移难度差异
    计算: 需要BVSE数据，如果无数据则返回NaN
    注意: 如果BVSE不可用，此描述符自动跳过
    """
    ...
```

#### C2.3 组 B：Na-Na 网络族（5个描述符）

文件：`descriptors/family_b_network.py`

```python
"""组B: Na-Na网络描述符
物理对象: Na位点之间的连通性
物理含义: Na迁移的"通道丰富度"
"""
from pymatgen.core import Structure
import networkx as nx

def compute_nana_composite(struct: Structure) -> float:
    """NaNa综合指标
    物理含义: Na网络连通性的综合度量
    计算: 加权组合（连通分量占比 × 平均邻居数 × 网络维度）
    """
    ...

def compute_avg_na_neighbors(struct: Structure) -> float:
    """平均Na邻居数
    计算: 截断距离内（如4.5Å）平均每个Na有多少Na邻居
    """
    ...

def compute_largest_component_ratio(struct: Structure) -> float:
    """最大连通分量占比
    计算: 最大Na-Na连通子图包含的Na数 / 总Na数
    """
    ...

def compute_network_dimension(struct: Structure) -> float:
    """网络维度
    计算: Na-Na网络是0D/1D/2D/3D
    """
    ...

def compute_component_count(struct: Structure) -> float:
    """连通分量数"""
    ...
```

#### C2.4 组 C：Na 浓度族（3个描述符）

文件：`descriptors/family_c_concentration.py`

```python
"""组C: Na宏观浓度描述符
物理对象: 晶格中Na的宏观丰度
物理含义: Na的供给量
组合规则: 仅做分母（A/X形式），不做乘积（C×X禁止）
"""

def compute_na_concentration(struct: Structure) -> float:
    """Na浓度 = Na原子数 / 晶胞总原子数"""
    ...

def compute_na_occupancy_sum(struct: Structure) -> float:
    """Na占位总和（考虑部分占位）"""
    ...

def compute_na_site_count(struct: Structure) -> float:
    """Na位点数"""
    ...
```

#### C2.5 组 D'：空位拓扑族（5个描述符，替代原D族）

文件：`descriptors/family_d_vacancy_topo.py`

```python
"""组D': 空位拓扑描述符
物理对象: Na迁移通道中的间隙位点（Voronoi/BVSE确定）
物理含义: Na可以跳过去的位置的几何特征
注意: 不使用 occupancy 推断空位！
"""
from pymatgen.core import Structure
from pymatgen.analysis.local_env import VoronoiNN

def compute_interstitial_count(struct: Structure) -> float:
    """间隙位点数（新增）
    计算: Voronoi分解找体积 > Na³ 半径的空隙位点数
    方法: VoronoiNN 的 get_voronoi_polyhedra 找空隙
    """
    ...

def compute_interstitial_na_distance(struct: Structure) -> float:
    """间隙-Na最近距离均值（新增）
    计算: 各间隙位点到最近Na位点的距离均值
    物理含义: Na跳到间隙需要多远
    """
    ...

def compute_interstitial_channel_access(struct: Structure) -> float:
    """间隙接入主通道比例（新增）
    计算: 与最大Na连通分量有路径的间隙位点 / 总间隙位点
    物理含义: 空位是否"连着主干道"
    """
    ...

def compute_interstitial_network_dim(struct: Structure) -> float:
    """间隙网络维度（新增）
    计算: 间隙位点间的连通维度
    """
    ...

def compute_bvse_barrier_estimate(struct: Structure) -> float:
    """Na-间隙BVSE能垒估计（新增，可选）
    计算: 如果有SoftBV数据则读取，否则用键价模型近似
    注意: 需要SoftBV工具或预计算数据，否则返回NaN
    """
    ...
```

#### C2.6 组 E：骨架刚性族（4个描述符）

文件：`descriptors/family_e_framework.py`

```python
"""组E: 骨架刚性描述符
物理对象: 阴离子框架的力学特征
物理含义: 骨架有多"硬"/"软"，Na迁移时能否"让路"
"""

def compute_framework_bond_rigidity(struct: Structure) -> float:
    """骨架X-X键长刚性指数（新增）
    计算: 骨架阳离子-阴离子键长 / 理想键长(R0)，取均值
    物理含义: >1表示被拉伸，<1表示被压缩
    """
    ...

def compute_framework_poly_distortion(struct: Structure) -> float:
    """骨架多面体畸变（新增）
    计算: 骨架阳离子配位多面体的键长变异系数均值
    物理含义: 骨架已变形程度 → 变形越大越"让路"
    """
    ...

def compute_framework_na_distance_stability(struct: Structure) -> float:
    """骨架-Na间距稳定性（新增）
    计算: 骨架阳离子到最近Na距离的变异系数
    物理含义: Na与骨架的相对位置是否均匀
    """
    ...

def compute_framework_sharing_topology(struct: Structure) -> float:
    """骨架共享拓扑（新增）
    计算: 骨架多面体共享顶点数 / (共享顶点+共享边+共享面)总数
    物理含义: 共享顶点多=开放，共享面多=紧密
    """
    ...
```

#### C2.7 组 F：长程关联族（4个描述符）

文件：`descriptors/family_f_longrange.py`

```python
"""组F: 长程关联描述符
物理对象: 第二配位壳层及更远的结构关联
物理含义: 超出最近邻的长程结构特征，影响多步迁移
"""

def compute_nana_nana_angle_mean(struct: Structure) -> float:
    """Na-Na-Na三体角分布均值（新增）
    计算: 相邻3个Na的夹角统计均值
    物理含义: Na迁移路径是直线还是弯折
    """
    ...

def compute_nana_second_neighbor_dist(struct: Structure) -> float:
    """Na-Na次近邻距离（新增）
    计算: 各Na位点的第2近Na-Na距离均值
    物理含义: 跳了一步之后下一个Na有多远
    """
    ...

def compute_path_tortuosity(struct: Structure) -> float:
    """迁移路径曲折度（新增）
    计算: 沿Na-Na网络的折线距离 / Na-Na直线距离
    物理含义: 迁移路径有多弯（1.0=直线，越大越弯）
    """
    ...

def compute_nana_spacing_uniformity(struct: Structure) -> float:
    """Na-Na间距均匀性（新增）
    计算: Na-Na距离的变异系数(CV = std/mean)
    物理含义: Na位点分布是否均匀（低CV=均匀）
    """
    ...
```

#### C2.8 组 G：电子结构代理族（4个描述符，⚠️高风险）

文件：`descriptors/family_g_electronic.py`

```python
"""组G: 电子结构代理描述符（⚠️高风险族）
物理对象: 化学键的电子特征
风险: 容易成为体系代理信号，必须做去混杂验证
    电负性差主要由阴离子类型决定 → 阴离子类型 ≈ 体系标签
"""

# 电负性查表
ELECTRONEGATIVITY = {"Na": 0.93, "O": 3.44, "S": 2.58, "F": 3.98,
                      "Cl": 3.16, "Br": 2.96, "I": 2.66, ...}

def compute_na_x_en_diff(struct: Structure) -> float:
    """Na-X电负性差（新增，⚠️高风险）
    计算: mean(|χ_X - χ_Na|) for all Na-X pairs
    物理含义: Na-X键的离子性程度
    风险: 主要由阴离子类型决定 → 体系代理信号
    """
    ...

def compute_charge_balance_deviation(struct: Structure) -> float:
    """电荷平衡偏差（新增，⚠️高风险）
    计算: |Σ(阳离子氧化态×个数) - |Σ(阴离子氧化态×个数)||
    物理含义: 结构是否电荷平衡
    风险: 氧化态组合也与体系相关
    """
    ...

def compute_covalency_index(struct: Structure) -> float:
    """Na-X键共价性指数（新增，⚠️高风险）
    计算: mean(1 - exp(-(χ_X - χ_Na)²/4))，Pauling公式
    物理含义: Na-X键的共价成分
    风险: 同电负性差风险
    """
    ...

def compute_framework_d_electron_weighted(struct: Structure) -> float:
    """骨架阳离子d电子数加权均值（新增，⚠️高风险）
    计算: Σ(骨架阳离子d电子数 × 摩尔分数)
    物理含义: 骨架的极化能力
    风险: 骨架阳离子类型与体系相关
    """
    ...
```

#### C2.9 组 H：对称性破缺族（5个描述符，⚠️高风险）

文件：`descriptors/family_h_symmetry.py`

```python
"""组H: 对称性破缺描述符（⚠️高风险族）
物理对象: 结构偏离理想对称性的程度
风险: 不同体系天然有不同的空间群 → 体系代理信号
"""

def compute_space_group_number(struct: Structure) -> float:
    """空间群序号（新增，⚠️高风险）
    计算: 直接从CIF读取空间群国际编号
    物理含义: 高序号=低对称=更多迁移通道可能
    风险: 体系与空间群强相关
    """
    ...

def compute_wyckoff_diversity(struct: Structure) -> float:
    """Na位点Wyckoff位置多样性（新增，⚠️高风险）
    计算: Na占据的不同Wyckoff位置种类数
    物理含义: Na位点的对称性多样性
    风险: Wyckoff与空间群（体系）相关
    """
    ...

def compute_partial_occupancy_ratio(struct: Structure) -> float:
    """Na部分占位比例（新增）
    计算: 部分占位Na位点数 / Na总位点数
    物理含义: 占位无序程度
    风险: 中等——部分占位与体系相关但不完全
    """
    ...

def compute_coordination_cv(struct: Structure) -> float:
    """配位数变异系数（新增）
    计算: 各Na位点配位数的 std/mean
    物理含义: Na位点的局域环境是否一致
    风险: 较低——配位数是局域量
    """
    ...

def compute_volume_cv(struct: Structure) -> float:
    """多面体体积变异系数（新增）
    计算: 各Na多面体体积的 std/mean
    物理含义: Na位点空间是否均匀
    风险: 较低——体积是局域量
    """
    ...
```

#### C2.10 `__init__.py` 注册

```python
"""描述符注册表
每个描述符: (计算函数, 所属族, 是否高风险)
"""
from .family_a_polyhedron import *
from .family_b_network import *
# ... 等等

AVAILABLE_STRUCTURE_DESCRIPTORS = {
    # 组A: Na多面体
    "a2_max_dist":              (compute_a2_max_dist,              "A", False),
    "poly_distortion_mean":     (compute_poly_distortion_mean,     "A", False),
    "max_bond_length":          (compute_max_bond_length,          "A", False),
    "min_bond_length":          (compute_min_bond_length,          "A", False),
    "mean_bond_length":         (compute_mean_bond_length,         "A", False),
    "target_bond_center":       (compute_target_bond_center,       "A", False),
    "poly_volume_mean":         (compute_poly_volume_mean,         "A", False),
    "coordination_number_mean": (compute_coordination_number_mean, "A", False),
    "ellipsoid_oblateness":     (compute_ellipsoid_oblateness,     "A", False),
    "direction_ratio":          (compute_direction_ratio,          "A", False),
    "bottleneck_anisotropy":    (compute_bottleneck_anisotropy,    "A", True),  # 需BVSE
    # 组B: Na-Na网络
    "nana_composite":           (compute_nana_composite,           "B", False),
    "avg_na_neighbors":         (compute_avg_na_neighbors,         "B", False),
    "largest_component_ratio":  (compute_largest_component_ratio,  "B", False),
    "network_dimension":        (compute_network_dimension,        "B", False),
    "component_count":          (compute_component_count,          "B", False),
    # 组C: Na浓度
    "na_concentration":         (compute_na_concentration,         "C", False),
    "na_occupancy_sum":         (compute_na_occupancy_sum,         "C", False),
    "na_site_count":            (compute_na_site_count,            "C", False),
    # 组D': 空位拓扑
    "interstitial_count":       (compute_interstitial_count,       "D_prime", False),
    "interstitial_na_distance": (compute_interstitial_na_distance, "D_prime", False),
    "interstitial_channel_access": (compute_interstitial_channel_access, "D_prime", False),
    "interstitial_network_dim": (compute_interstitial_network_dim, "D_prime", False),
    "bvse_barrier_estimate":    (compute_bvse_barrier_estimate,    "D_prime", True),  # 需BVSE
    # 组E: 骨架刚性
    "framework_bond_rigidity":  (compute_framework_bond_rigidity,  "E", False),
    "framework_poly_distortion":(compute_framework_poly_distortion,"E", False),
    "framework_na_dist_stability": (compute_framework_na_distance_stability, "E", False),
    "framework_sharing_topo":   (compute_framework_sharing_topology,"E", False),
    # 组F: 长程关联
    "nana_nana_angle_mean":     (compute_nana_nana_angle_mean,     "F", False),
    "nana_second_neighbor":     (compute_nana_second_neighbor_dist,"F", False),
    "path_tortuosity":          (compute_path_tortuosity,          "F", False),
    "nana_spacing_uniformity":  (compute_nana_spacing_uniformity,  "F", False),
    # 组G: 电子结构代理 ⚠️
    "na_x_en_diff":             (compute_na_x_en_diff,             "G", True),
    "charge_balance_dev":       (compute_charge_balance_deviation, "G", True),
    "covalency_index":          (compute_covalency_index,          "G", True),
    "framework_d_electron":     (compute_framework_d_electron_weighted, "G", True),
    # 组H: 对称性破缺 ⚠️
    "space_group_number":       (compute_space_group_number,       "H", True),
    "wyckoff_diversity":        (compute_wyckoff_diversity,        "H", True),
    "partial_occupancy_ratio":  (compute_partial_occupancy_ratio,  "H", True),
    "coordination_cv":          (compute_coordination_cv,          "H", False),
    "volume_cv":                (compute_volume_cv,                "H", False),
}
```

#### C2.11 `featurizer.py` 批量计算入口

```python
"""从CIF批量计算描述符（替代 automat_utils.featurize_formula）
输入: naconductor_raw.csv（含cif_path列）
输出: naconductor_featurized.csv（41列描述符 + 噪声列 + 元数据）
"""
import pandas as pd
from pymatgen.core import Structure
from .descriptors import AVAILABLE_STRUCTURE_DESCRIPTORS

def featurize_cif(cif_path: str) -> dict:
    """从单个CIF计算所有描述符"""
    struct = Structure.from_file(cif_path)
    result = {}
    for name, (func, family, is_high_risk) in AVAILABLE_STRUCTURE_DESCRIPTORS.items():
        try:
            result[name] = func(struct)
        except Exception as e:
            result[name] = float('nan')  # 计算失败返回NaN
            # 记录警告
    return result

def featurize_dataset(csv_path: str, output_path: str) -> pd.DataFrame:
    """批量计算所有样本的描述符"""
    df = pd.read_csv(csv_path)
    features = []
    for _, row in df.iterrows():
        feat = featurize_cif(row['cif_path'])
        feat['material_id'] = row['material_id']
        features.append(feat)
    feat_df = pd.DataFrame(features)
    # 合并元数据
    result = df.merge(feat_df, on='material_id')
    result.to_csv(output_path, index=False)
    result.to_json(output_path.replace('.csv', '.json'), orient='records')
    return result
```

**验收标准**：
- [ ] 8 个族文件各包含对应的描述符计算函数
- [ ] `__init__.py` 注册 41 个描述符，每个标注族和高风险标记
- [ ] `featurizer.py` 可从 CIF 批量计算并输出 CSV + JSON
- [ ] A2 在已知样本上的值与 part1.py 一致（误差 < 5%）
- [ ] BVSE 相关描述符在无数据时优雅返回 NaN
- [ ] 高风险族描述符标注 is_high_risk=True

---

### C3: 实现特征矩阵构建与噪声注入

**目标**：构建标准化特征矩阵，注入噪声列作为基线参照。

**输入**：`naconductor_featurized.csv`

**输出**：
- 标准化特征矩阵（z-score）
- 15-20 个噪声列
- 每个噪声列的描述（seed、分布、与目标的相关系数）

**实现细节**：

#### C3.1 标准化
```python
"""特征矩阵构建"""
from sklearn.preprocessing import StandardScaler

def build_feature_matrix(df: pd.DataFrame, descriptor_cols: list,
                         n_noise: int = 15, noise_seed: int = 42) -> tuple:
    """
    构建: (标准化特征矩阵, 噪声元信息)

    参数:
        df: 含描述符列的DataFrame
        descriptor_cols: 描述符列名列表
        n_noise: 噪声列数
        noise_seed: 噪声种子（预固定，不可调）

    噪声生成方法:
        1. 预固定 seed=42
        2. 生成 n_noise 个标准正态列，每列与目标(log_sigma)独立
        3. 标准化到与真实描述符相同的尺度
        4. 记录每个噪声列与目标的实际相关系数（作为基线参照）

    返回:
        X: 标准化特征矩阵（真实描述符 + 噪声列）
        noise_info: 噪声列元信息 DataFrame
    """
    rng = np.random.RandomState(noise_seed)

    # 1. 去除 NaN 列（如 BVSE 不可用的描述符）
    valid_cols = [c for c in descriptor_cols if df[c].notna().sum() > len(df) * 0.5]

    # 2. z-score 标准化
    X_real = StandardScaler().fit_transform(df[valid_cols].values)

    # 3. 生成噪声列
    n_samples = len(df)
    noise_cols = []
    noise_info = []
    for i in range(n_noise):
        col_name = f"noise_{i:03d}"
        noise = rng.randn(n_samples)
        noise = StandardScaler().fit_transform(noise.reshape(-1, 1)).flatten()
        noise_cols.append(noise)

        # 计算噪声与目标的实际相关（可能非零——这是设计如此）
        corr = np.corrcoef(noise, df['log_sigma'].values)[0, 1]
        noise_info.append({
            'column': col_name,
            'seed': noise_seed,
            'distribution': 'standard_normal',
            'actual_corr_with_target': corr,
        })

    X_noise = np.column_stack(noise_cols)
    X = np.column_stack([X_real, X_noise])

    noise_info_df = pd.DataFrame(noise_info)

    return X, valid_cols, noise_info_df
```

**关键设计决策**：

**为什么噪声可能与目标相关？** 这是设计如此——噪声注入的目的就是测量"随机能有多幸运"。15 个噪声列中，偶尔会有一个与目标偶然相关的，它的选择频率就是"随机基线"。真实描述符必须显著高于这个基线才有意义。

**保障措施**：
1. 噪声种子预固定（seed=42），不可事后调优
2. 15-20 个噪声列确保统计稳定性
3. 重复 500 次 bootstrap，取 95th percentile 作为阈值
4. 真实描述符选择频率必须 > 0.6 且 > 噪声 95th percentile

**验收标准**：
- [ ] 输出矩阵 shape = (n_samples, n_descriptors + n_noise)
- [ ] 所有真实描述符列已 z-score 标准化（均值≈0, 标准差≈1）
- [ ] 噪声列与目标的相关系数记录在 noise_info_df 中
- [ ] NaN 列已自动排除
- [ ] 噪声种子固定为 42

---

### C4: 实现多策略交叉验证系统

**目标**：实现 3 种 CV 策略，替代 AUTOMAT 的简单 3-fold。

**输入**：特征矩阵 + 元数据（体系标签、阴离子标签）

**输出**：每种策略的每折指标

**实现细节**：

```python
"""多策略交叉验证"""
from sklearn.model_selection import StratifiedKFold, LeaveOneGroupOut, KFold
from sklearn.linear_model import Ridge
from scipy.stats import spearmanr
import numpy as np

class MultiStrategyCV:
    """三种CV策略的统一接口"""

    def __init__(self, alpha: float = 1.0):
        self.model = Ridge(alpha=alpha)

    def anion_stratified_cv(self, X, y, anion_labels, n_folds=3):
        """策略1: 阴离子分层3-fold
        确保每折中各阴离子类型的比例一致
        """
        skf = StratifiedKFold(n_splits=n_folds, shuffle=True, random_state=42)
        fold_results = []
        for train_idx, test_idx in skf.split(X, anion_labels):
            self.model.fit(X[train_idx], y[train_idx])
            y_pred = self.model.predict(X[test_idx])
            fold_results.append({
                'fold': len(fold_results) + 1,
                'spearman': spearmanr(y[test_idx], y_pred)[0],
                'mae': np.mean(np.abs(y[test_idx] - y_pred)),
                'n_train': len(train_idx),
                'n_test': len(test_idx),
            })
        return fold_results

    def loso_cv(self, X, y, system_labels):
        """策略2: Leave-One-System-Out
        每次留出一个体系作为测试集
        回答: 模型对未见体系的泛化能力
        """
        logo = LeaveOneGroupOut()
        fold_results = []
        for train_idx, test_idx in logo.split(X, y, groups=system_labels):
            self.model.fit(X[train_idx], y[train_idx])
            y_pred = self.model.predict(X[test_idx])
            fold_results.append({
                'left_out_system': system_labels[test_idx[0]],
                'spearman': spearmanr(y[test_idx], y_pred)[0],
                'mae': np.mean(np.abs(y[test_idx] - y_pred)),
                'n_train': len(train_idx),
                'n_test': len(test_idx),
            })
        return fold_results

    def within_system_cv(self, X, y, system_labels, n_folds=3):
        """策略3: 体系内CV
        对每个体系单独做3-fold CV
        回答: 在同一体系内，描述符是否仍有预测力
        """
        results_by_system = {}
        for system in np.unique(system_labels):
            mask = system_labels == system
            X_sys = X[mask]
            y_sys = y[mask]
            if len(y_sys) < n_folds + 2:  # 样本太少跳过
                results_by_system[system] = {'skipped': True, 'n_samples': len(y_sys)}
                continue
            kf = KFold(n_splits=n_folds, shuffle=True, random_state=42)
            fold_results = []
            for train_idx, test_idx in kf.split(X_sys):
                self.model.fit(X_sys[train_idx], y_sys[train_idx])
                y_pred = self.model.predict(X_sys[test_idx])
                fold_results.append({
                    'spearman': spearmanr(y_sys[test_idx], y_pred)[0],
                    'mae': np.mean(np.abs(y_sys[test_idx] - y_pred)),
                })
            results_by_system[system] = {
                'folds': fold_results,
                'mean_spearman': np.mean([f['spearman'] for f in fold_results]),
                'n_samples': len(y_sys),
            }
        return results_by_system
```

**验收标准**：
- [ ] 3 种策略均能运行并输出每折指标
- [ ] 阴离子分层 CV 每折中各阴离子比例一致
- [ ] LOSO 输出 3 个 left-out 结果（NASICON/硫化物/卤化物）
- [ ] 体系内 CV 对样本太少的体系优雅跳过
- [ ] 使用 Ridge（而非 RF）作为评估模型

---

### C5: 实现体系去混杂分析模块

**目标**：回答核心因果问题——描述符 X 与 logσ 的相关中，多少来自"区分体系"，多少来自"体系内物理"。

**这是什么**：去混杂分析（deconfounding）的核心思想是——如果我们发现"最远Na-X键长"与"电导率"强相关，但这个相关主要是因为氧化物体系比硫化物体系键长更长、电导率更低，那这个相关就是"虚假的"（由体系混杂导致）。去混杂就是用统计方法把这个混杂成分去掉，看剩余的纯物理信号。

**输入**：描述符值 + 目标值 + 体系标签

**输出**：
- 每个描述符的：raw Spearman、deconfounded Spearman、体系代理比例
- 去混杂分解："X% 来自体系区分，Y% 来自体系内物理"

**实现细节**：

```python
"""体系去混杂分析"""
from sklearn.linear_model import Ridge
from scipy.stats import spearmanr
import numpy as np

class DeconfoundAnalyzer:
    """体系去混杂分析器
    方法: 残差偏相关法（Residual Partial Correlation）

    步骤:
    1. 用体系标签拟合描述符X → 得到 X_residual（去掉体系可预测的部分）
    2. 用体系标签拟合目标Y → 得到 Y_residual（去掉体系可预测的部分）
    3. corr(X_residual, Y_residual) = 去混杂后的纯物理相关
    4. 体系代理比例 = 1 - deconfounded_ρ²/raw_ρ²

    直觉: 如果X与Y的相关完全来自"氧化物vs硫化物"的差异，
    那去掉体系信息后，X_residual与Y_residual就不相关了。
    """

    def __init__(self, alpha: float = 1.0):
        self.alpha = alpha

    def _one_hot_system(self, system_labels):
        """将体系标签转为 one-hot 编码"""
        systems = np.unique(system_labels)
        one_hot = np.zeros((len(system_labels), len(systems)))
        for i, s in enumerate(systems):
            one_hot[:, i] = (system_labels == s).astype(float)
        # 去掉一列避免共线性
        return one_hot[:, :-1]

    def analyze_single_descriptor(self, X, y, system_labels, desc_name: str) -> dict:
        """分析单个描述符的去混杂结果"""
        X = X.reshape(-1, 1) if X.ndim == 1 else X
        system_onehot = self._one_hot_system(system_labels)

        # 原始相关
        raw_rho, raw_p = spearmanr(X.flatten(), y)

        # Step 1: 用体系预测描述符，取残差
        model_x = Ridge(alpha=self.alpha).fit(system_onehot, X)
        X_residual = X.flatten() - model_x.predict(system_onehot).flatten()

        # Step 2: 用体系预测目标，取残差
        model_y = Ridge(alpha=self.alpha).fit(system_onehot, y)
        y_residual = y - model_y.predict(system_onehot)

        # Step 3: 残差相关 = 去混杂后的纯物理相关
        deconf_rho, deconf_p = spearmanr(X_residual, y_residual)

        # Step 4: 体系代理比例
        if abs(raw_rho) > 1e-10:
            system_proxy_ratio = 1.0 - (deconf_rho**2 / raw_rho**2)
        else:
            system_proxy_ratio = float('nan')

        # 分类标签
        if system_proxy_ratio > 0.7:
            label = "体系代理"  # >70% 来自体系区分
        elif system_proxy_ratio > 0.4:
            label = "混合信号"  # 40-70% 混合
        elif deconf_rho > 0.3:
            label = "强物理信号"  # 去混杂后仍强相关
        elif deconf_rho > 0.15:
            label = "弱物理信号"
        else:
            label = "噪声级"

        return {
            'descriptor': desc_name,
            'raw_spearman': raw_rho,
            'raw_pvalue': raw_p,
            'deconfounded_spearman': deconf_rho,
            'deconfounded_pvalue': deconf_p,
            'system_proxy_ratio': system_proxy_ratio,
            'label': label,
            'decomposition': f"{system_proxy_ratio*100:.0f}% 来自体系区分，"
                            f"{(1-system_proxy_ratio)*100:.0f}% 来自体系内物理",
        }

    def analyze_all(self, feature_df, y, system_labels) -> pd.DataFrame:
        """分析所有描述符"""
        results = []
        for col in feature_df.columns:
            if col.startswith('noise_'):
                continue
            result = self.analyze_single_descriptor(
                feature_df[col].values, y, system_labels, col
            )
            results.append(result)
        return pd.DataFrame(results).sort_values('deconfounded_spearman',
                                                   key=abs, ascending=False)
```

**验收标准**：
- [ ] 每个描述符输出 raw_spearman + deconfounded_spearman + system_proxy_ratio + label
- [ ] 已知体系代理信号（如阴离子柔软性分数）被正确标记为"体系代理"
- [ ] 已知物理信号（如A2）去混杂后仍有显著相关
- [ ] 分解语句格式正确：`X% 来自体系区分，Y% 来自体系内物理`
- [ ] 高风险族（G/H）的描述符如果被标记为体系代理，不影响低风险族结果

---

### C6: 实现 Stability Selection 与物理分组去冗余

**目标**：
1. 用 Stability Selection + 噪声基线筛选单描述符
2. 按物理分组去冗余，选代表

**输入**：标准化特征矩阵（含噪声列）+ 目标 + 去混杂结果

**输出**：
1. Stability Selection 结果：每个描述符的选择频率 + 噪声基线
2. 物理分组后的代表描述符列表（8-10个）

**实现细节**：

#### C6.1 Stability Selection
```python
"""Stability Selection + 噪声基线"""
from sklearn.linear_model import LassoCV
from sklearn.utils import resample
import numpy as np

class StabilitySelector:
    """Stability Selection 实现

    核心思想: 一个描述符如果在很多次随机子采样中都被选中，
    说明它不是偶然被选的——它稳定地含有信号。

    噪声基线: 噪声列也被放进特征矩阵一起做 Stability Selection。
    真实描述符的选择频率必须显著高于噪声的 95th percentile 才算有效。

    参数:
        n_bootstrap: 子采样次数（默认500）
        subsample_ratio: 每次抽样比例（默认0.5）
        selection_threshold: 选择频率阈值（默认0.6）
        n_noise: 噪声列数（默认15）
        noise_seed: 噪声种子（默认42，预固定）
    """

    def __init__(self, n_bootstrap=500, subsample_ratio=0.5,
                 selection_threshold=0.6, random_state=42):
        self.n_bootstrap = n_bootstrap
        self.subsample_ratio = subsample_ratio
        self.selection_threshold = selection_threshold
        self.random_state = random_state

    def run(self, X, y, feature_names) -> dict:
        """
        运行 Stability Selection

        返回:
            selection_freq: 每个特征的选择频率
            noise_threshold: 噪声列的 95th percentile 选择频率
            stable_features: 选择频率 > max(threshold, noise_threshold) 的特征
        """
        n_samples = X.shape[0]
        n_subsample = int(n_samples * self.subsample_ratio)

        # 记录每个特征被选中的次数
        selection_count = np.zeros(X.shape[1])
        rng = np.random.RandomState(self.random_state)

        for _ in range(self.n_bootstrap):
            # 随机子采样
            idx = resample(range(n_samples), n_samples=n_subsample,
                          random_state=rng)
            X_sub, y_sub = X[idx], y[idx]

            # LassoCV 自动选 lambda
            model = LassoCV(cv=3, random_state=rng).fit(X_sub, y_sub)

            # 非零系数 = 被选中
            selected = np.abs(model.coef_) > 1e-8
            selection_count += selected

        selection_freq = selection_count / self.n_bootstrap

        # 噪声基线
        noise_mask = np.array([name.startswith('noise_') for name in feature_names])
        noise_freqs = selection_freq[noise_mask]
        noise_95th = np.percentile(noise_freqs, 95) if len(noise_freqs) > 0 else 0.0

        # 有效阈值 = max(设定阈值, 噪声95th)
        effective_threshold = max(self.selection_threshold, noise_95th)

        stable_mask = selection_freq > effective_threshold
        stable_features = [feature_names[i] for i in range(len(feature_names))
                          if stable_mask[i] and not noise_mask[i]]

        return {
            'selection_freq': dict(zip(feature_names, selection_freq)),
            'noise_95th_percentile': noise_95th,
            'effective_threshold': effective_threshold,
            'stable_features': stable_features,
        }
```

#### C6.2 物理分组去冗余
```python
"""物理分组 + 去冗余选代表"""
from scipy.stats import spearmanr
import numpy as np

class PhysicalGrouper:
    """按物理分组去冗余，选代表

    核心思想: 同一物理族内描述符高度相关（它们描述同一个物理对象），
    保留最有信息量的那个作为代表，避免冗余。

    选代表标准（优先级从高到低）:
    1. 去混杂后 Spearman 绝对值最大
    2. 直接性：越接近原始测量越好（键长 > 衍生量 > 组合量）
    3. 稳定性：Stability Selection 选择频率更高
    """

    def __init__(self, family_map, cross_group_rules):
        """
        family_map: {descriptor_name: family_name}
        cross_group_rules: 见 _base.py CROSS_GROUP_RULES
        """
        self.family_map = family_map
        self.cross_group_rules = cross_group_rules

    def select_representatives(self, stable_descriptors, deconfound_results,
                               feature_df, max_per_family=2) -> list:
        """
        从稳定描述符中按族选代表

        参数:
            stable_descriptors: Stability Selection 稳定描述符列表
            deconfound_results: C5 的去混杂分析结果
            feature_df: 特征 DataFrame（用于算族内相关）
            max_per_family: 每族最多保留几个代表（默认2）

        返回:
            representatives: 代表描述符列表
            family_summary: 每族的选代表理由
        """
        # 按族分组
        families = {}
        for desc in stable_descriptors:
            family = self.family_map.get(desc, 'unknown')
            if family not in families:
                families[family] = []
            families[family].append(desc)

        representatives = []
        family_summary = {}

        for family, members in families.items():
            # 按去混杂Spearman排序
            deconf_df = deconfound_results.set_index('descriptor')
            members_sorted = sorted(
                members,
                key=lambda d: abs(deconf_df.loc[d, 'deconfounded_spearman'])
                             if d in deconf_df.index else 0,
                reverse=True
            )

            # 选 top-N 代表
            selected = []
            for desc in members_sorted:
                # 检查与已选代表的相关性（如果 > 0.9 则跳过）
                too_similar = False
                for s in selected:
                    rho = abs(spearmanr(feature_df[desc], feature_df[s])[0])
                    if rho > 0.9:
                        too_similar = True
                        break
                if not too_similar:
                    selected.append(desc)
                if len(selected) >= max_per_family:
                    break

            representatives.extend(selected)
            family_summary[family] = {
                'members': members,
                'selected': selected,
                'reason': f"按去混杂Spearman排序，每族最多{max_per_family}个，"
                         f"族内相关>0.9去冗余",
            }

        return representatives, family_summary
```

**验收标准**：
- [ ] Stability Selection 输出每个描述符的选择频率（0-1）
- [ ] 噪声列的选择频率显著低于真实描述符
- [ ] 有效阈值 = max(0.6, 噪声95th)
- [ ] 物理分组后代表描述符数在 8-12 个范围内
- [ ] 同族内相关 > 0.9 的只保留一个
- [ ] 每族最多 2 个代表

---

### C7: 实现物理约束组合搜索与评估

**目标**：在双层约束下穷举描述符组合，评估每个组合的去混杂性能。

**这是什么**：组合搜索的核心思想——单个描述符可能只捕捉了一个维度的信息，两个描述符组合可能捕捉协同效应（如"通道宽 × 连通好 = 高电导"）。但不是所有组合都有物理意义，必须用双层约束过滤。

**输入**：8-10 个代表描述符 + 物理分组 + 跨族规则

**输出**：~80-120 个候选组合的去混杂评估结果

**实现细节**：

```python
"""物理约束组合搜索"""
from itertools import combinations
from scipy.stats import spearmanr
import numpy as np
import pandas as pd

class ConstrainedCombinationSearch:
    """物理约束组合搜索

    双层约束:
    层1-算符约束: 仅 +（叠加）、×（协同）、同量纲比值
    层2-物理对象约束: 仅同族或相邻族可组合

    搜索方式: 穷举所有合法组合（~80-120个）
    评估: 对每个组合计算去混杂Spearman
    """

    def __init__(self, family_map, cross_group_rules, allowed_operators):
        self.family_map = family_map
        self.cross_group_rules = cross_group_rules
        self.allowed_operators = allowed_operators

    def _is_cross_group_allowed(self, desc1, desc2) -> tuple:
        """检查两个描述符是否允许跨族组合"""
        f1 = self.family_map.get(desc1)
        f2 = self.family_map.get(desc2)

        if f1 == f2:
            return True, "同族自由组合"

        pair = tuple(sorted([f1, f2]))
        allowed_pairs = [tuple(sorted(r)) for r in self.cross_group_rules['allowed']]

        if pair in allowed_pairs:
            return True, f"相邻族组合({f1}↔{f2})"

        return False, f"不相邻族({f1}↔{f2})，禁止组合"

    def _generate_combinations(self, representatives) -> list:
        """穷举所有合法的双描述符和三描述符组合"""
        combos = []

        # 单描述符也纳入评估（作为基线）
        for d in representatives:
            combos.append({
                'type': 'single',
                'descriptors': [d],
                'operators': [],
                'formula': d,
                'families': [self.family_map[d]],
            })

        # 双描述符组合
        for d1, d2 in combinations(representatives, 2):
            allowed, reason = self._is_cross_group_allowed(d1, d2)
            if not allowed:
                continue

            # 加法组合
            if 'add' in self.allowed_operators:
                combos.append({
                    'type': 'add',
                    'descriptors': [d1, d2],
                    'operators': ['add'],
                    'formula': f"{d1} + {d2}",
                    'families': [self.family_map[d1], self.family_map[d2]],
                    'reason': reason,
                })

            # 乘法组合
            if 'multiply' in self.allowed_operators:
                combos.append({
                    'type': 'multiply',
                    'descriptors': [d1, d2],
                    'operators': ['multiply'],
                    'formula': f"{d1} × {d2}",
                    'families': [self.family_map[d1], self.family_map[d2]],
                    'reason': reason,
                })

            # 同量纲比值（仅同族或同物理量）
            if 'ratio_same_dim' in self.allowed_operators:
                f1, f2 = self.family_map[d1], self.family_map[d2]
                if f1 == f2:  # 同族才允许比值
                    combos.append({
                        'type': 'ratio',
                        'descriptors': [d1, d2],
                        'operators': ['ratio'],
                        'formula': f"{d1} / {d2}",
                        'families': [f1, f2],
                        'reason': f"同族比值({f1})",
                    })

        # 三描述符组合（仅同族 + 一个相邻族）
        for d1, d2, d3 in combinations(representatives, 3):
            families = [self.family_map[d1], self.family_map[d2], self.family_map[d3]]
            # 至少两个同族
            from collections import Counter
            fam_count = Counter(families)
            if max(fam_count.values()) < 2:
                continue
            # 第三个必须与主族相邻
            # ... (类似逻辑)

        return combos

    def evaluate_combination(self, combo, feature_df, y, system_labels) -> dict:
        """评估单个组合"""
        descs = combo['descriptors']
        ops = combo['operators']

        # 计算组合值
        if combo['type'] == 'single':
            combo_values = feature_df[descs[0]].values
        elif combo['type'] == 'add':
            combo_values = feature_df[descs[0]].values + feature_df[descs[1]].values
        elif combo['type'] == 'multiply':
            combo_values = feature_df[descs[0]].values * feature_df[descs[1]].values
        elif combo['type'] == 'ratio':
            denom = feature_df[descs[1]].values
            denom = np.where(np.abs(denom) < 1e-10, 1e-10, denom)  # 防除零
            combo_values = feature_df[descs[0]].values / denom

        # 标准化
        combo_values = (combo_values - combo_values.mean()) / combo_values.std()

        # 原始 Spearman
        raw_rho, raw_p = spearmanr(combo_values, y)

        # 去混杂 Spearman（复用 C5 的方法）
        # ...

        return {
            'formula': combo['formula'],
            'type': combo['type'],
            'raw_spearman': raw_rho,
            'deconfounded_spearman': deconf_rho,
            'system_proxy_ratio': system_proxy_ratio,
            'families': combo['families'],
            'reason': combo.get('reason', ''),
        }

    def search(self, representatives, feature_df, y, system_labels) -> pd.DataFrame:
        """穷举搜索所有合法组合"""
        combos = self._generate_combinations(representatives)
        print(f"穷举 {len(combos)} 个候选组合...")

        results = []
        for i, combo in enumerate(combos):
            result = self.evaluate_combination(combo, feature_df, y, system_labels)
            results.append(result)

        results_df = pd.DataFrame(results)
        results_df = results_df.sort_values('deconfounded_spearman',
                                             key=abs, ascending=False)
        return results_df
```

**验收标准**：
- [ ] 候选组合数在 80-150 范围内（合理穷举）
- [ ] 不存在禁止的组合（跨不相邻族 / 非法算符）
- [ ] 每个组合有 formula、raw_spearman、deconfounded_spearman
- [ ] 已知有效组合（A2×NaNa）出现在 Top-10 中
- [ ] 乘法组合的值已标准化后再算相关

---

### C8: 实现组合验证与最终报告生成

**目标**：对 Top-5 组合做完整验证，生成最终报告。

**输入**：Top-5 组合 + 特征矩阵 + 目标 + 体系标签

**输出**：最终验证报告（含 4 重验证）

**实现细节**：

```python
"""组合验证"""
from scipy.stats import spearmanr
from sklearn.linear_model import Ridge
from sklearn.utils import resample
import numpy as np

class CombinationValidator:
    """4 重组合验证

    V1: 噪声组合基线 —— 用噪声列构造同样数量的"假组合"，看随机能到多高
    V2: Factor Spanning Test —— 组合是否包含独立于已知因子的新信息
    V3: 体系分层评估 —— 在每个体系内分别评估组合
    V4: Bootstrap 置信区间 —— 组合性能的统计不确定性
    """

    def validate_noise_baseline(self, combo_values, y, n_noise_combos=100,
                                 rng_seed=42):
        """V1: 噪声组合基线

        方法: 用噪声列构造与真实组合相同形式的"假组合"，
        计算 Spearman，取 95th percentile 作为基线。
        真实组合必须超过此基线。
        """
        rng = np.random.RandomState(rng_seed)
        noise_corrs = []
        for _ in range(n_noise_combos):
            # 随机选2个噪声列做同样形式的组合
            noise_pair = rng.choice(range(len(noise_cols)), 2, replace=False)
            fake_combo = noise_cols_data[:, noise_pair[0]] * noise_cols_data[:, noise_pair[1]]
            fake_combo = (fake_combo - fake_combo.mean()) / fake_combo.std()
            rho = abs(spearmanr(fake_combo, y)[0])
            noise_corrs.append(rho)

        baseline_95th = np.percentile(noise_corrs, 95)
        real_rho = abs(spearmanr(combo_values, y)[0])

        return {
            'noise_baseline_95th': baseline_95th,
            'real_spearman': real_rho,
            'passes_baseline': real_rho > baseline_95th,
            'margin': real_rho - baseline_95th,
        }

    def validate_factor_spanning(self, combo_values, y, known_factors):
        """V2: Factor Spanning Test

        方法: 已知最强的描述符（如A2）构成一个"因子空间"。
        如果组合在正交于此空间的残差中仍有预测力 → 包含新信息。
        否则 → 只是已知因子的线性变换。

        直觉: 如果 A2×NaNa 的信息完全被 A2+NaNa 包含，
        那乘法组合就没有新增信息。
        """
        # 用已知因子拟合目标
        X_factors = np.column_stack(known_factors)
        model = Ridge(alpha=1.0).fit(X_factors, y)
        y_residual = y - model.predict(X_factors)

        # 组合对残差的预测力
        combo_2d = combo_values.reshape(-1, 1)
        model_combo = Ridge(alpha=1.0).fit(combo_2d, y_residual)
        y_pred_residual = model_combo.predict(combo_2d)
        spanning_rho = spearmanr(y_residual, y_pred_residual)[0]

        return {
            'spanning_spearman': spanning_rho,
            'has_independent_info': abs(spanning_rho) > 0.15,
            'interpretation': "组合包含已知因子未捕捉的新信息" if abs(spanning_rho) > 0.15
                            else "组合信息已被已知因子包含",
        }

    def validate_per_system(self, combo_values, y, system_labels):
        """V3: 体系分层评估

        在每个体系内分别评估组合性能。
        理想结果: 至少在2个体系内组合仍有正Spearman。
        """
        results = {}
        for system in np.unique(system_labels):
            mask = system_labels == system
            if mask.sum() < 5:
                results[system] = {'skipped': True, 'n': mask.sum()}
                continue
            rho, p = spearmanr(combo_values[mask], y[mask])
            results[system] = {
                'spearman': rho,
                'pvalue': p,
                'n_samples': mask.sum(),
                'significant': p < 0.1,  # 宽松阈值（小样本）
            }
        n_systems_positive = sum(1 for v in results.values()
                                 if isinstance(v, dict) and v.get('spearman', 0) > 0)
        return {
            'per_system': results,
            'n_systems_positive': n_systems_positive,
            'robust_across_systems': n_systems_positive >= 2,
        }

    def validate_bootstrap_ci(self, combo_values, y, n_bootstrap=1000,
                               ci_level=0.95, rng_seed=42):
        """V4: Bootstrap 置信区间"""
        rng = np.random.RandomState(rng_seed)
        boot_rhos = []
        n = len(y)
        for _ in range(n_bootstrap):
            idx = rng.choice(n, n, replace=True)
            rho = spearmanr(combo_values[idx], y[idx])[0]
            boot_rhos.append(rho)

        alpha = (1 - ci_level) / 2
        ci_low = np.percentile(boot_rhos, alpha * 100)
        ci_high = np.percentile(boot_rhos, (1 - alpha) * 100)

        return {
            'mean_spearman': np.mean(boot_rhos),
            'ci_low': ci_low,
            'ci_high': ci_high,
            'ci_width': ci_high - ci_low,
            'ci_does_not_cross_zero': (ci_low > 0) or (ci_high < 0),
        }

    def full_validation(self, combo_values, y, system_labels, known_factors,
                        noise_cols_data) -> dict:
        """完整4重验证"""
        v1 = self.validate_noise_baseline(combo_values, y, noise_cols_data=noise_cols_data)
        v2 = self.validate_factor_spanning(combo_values, y, known_factors)
        v3 = self.validate_per_system(combo_values, y, system_labels)
        v4 = self.validate_bootstrap_ci(combo_values, y)

        # 综合判定
        passes = sum([
            v1['passes_baseline'],
            v2['has_independent_info'],
            v3['robust_across_systems'],
            v4['ci_does_not_cross_zero'],
        ])

        return {
            'noise_baseline': v1,
            'factor_spanning': v2,
            'per_system': v3,
            'bootstrap_ci': v4,
            'n_tests_passed': passes,
            'overall_verdict': 'STRONG' if passes >= 3 else
                             'MODERATE' if passes >= 2 else 'WEAK',
        }
```

**最终报告格式**：

```markdown
# Na离子导体描述符组合搜索 - 最终报告

## 1. 单描述符筛选结果（阶段1）

| 描述符 | 族 | raw ρ | 去混杂 ρ | 体系代理比例 | 标签 | 选择频率 |
|--------|-----|-------|---------|------------|------|---------|
| a2_max_dist | A | 0.597 | 0.35 | 66% | 混合信号 | 0.85 |
| ... | ... | ... | ... | ... | ... | ... |

噪声基线 95th percentile = 0.XX

## 2. 物理分组去冗余结果（阶段2）

| 族 | 成员 | 选中代表 | 理由 |
|----|------|---------|------|
| A | a2_max_dist, poly_distortion, ... | a2_max_dist | 去混杂ρ最高 |
| ... | ... | ... | ... |

## 3. 组合搜索结果（阶段3）

### Top-5 组合

| 排名 | 公式 | 类型 | raw ρ | 去混杂 ρ | 体系代理% | 物理解释 |
|------|------|------|-------|---------|----------|---------|
| 1 | A2 × NaNa | 乘法 | 0.623 | 0.XX | XX% | 通道宽松×连通性好=高电导 |
| ... | ... | ... | ... | ... | ... | ... |

## 4. 组合验证结果（阶段4）

### 最优组合：A2 × NaNa

**4重验证**：
- V1 噪声基线: 通过 ✅ (0.623 > 噪声95th=0.XX)
- V2 Factor Spanning: 通过 ✅ (spanning ρ=0.XX > 0.15)
- V3 体系分层: 通过 ✅ (3/3 体系内正Spearman)
- V4 Bootstrap CI: [0.XX, 0.XX] ✅ (不含0)

**综合判定**: STRONG

**去混杂分解**: X% 来自体系区分，Y% 来自体系内物理

**一句话物理解释**: Na位点的宽松程度与Na网络的连通性的协同效应——
宽松的多面体提供低能垒的迁移路径，连通的网络提供连续的迁移通道，
两者同时满足时电导率最高。
```

**验收标准**：
- [ ] 4 重验证均可运行并输出结果
- [ ] 噪声基线可计算且 95th percentile 合理
- [ ] Factor Spanning Test 能区分"新增信息"和"已知因子的线性变换"
- [ ] 体系分层评估至少在 2/3 体系内有结果
- [ ] Bootstrap CI 不依赖正态假设
- [ ] 最终报告 Markdown 格式完整

---

## 3. 4 阶段流水线集成

```python
"""pipeline.py: 4阶段流水线入口"""

def run_stage1(feature_df, y, system_labels, anion_labels):
    """阶段1: 单描述符筛选
    输出: 每个描述符的 raw_spearman, deconfounded_spearman, label, 选择频率
    通过标准: 选择频率 > max(0.6, 噪声95th) AND (去混杂标签≠噪声级)
    保留: 8-12 个描述符
    """
    # Step 1.1: 去混杂分析
    deconf = DeconfoundAnalyzer().analyze_all(feature_df, y, system_labels)

    # Step 1.2: Stability Selection
    stab = StabilitySelector().run(X, y, feature_names)

    # Step 1.3: 标注
    results = merge(deconf, stab)
    results['label'] = classify(results)  # 强信号/弱信号/体系代理/噪声

    # Step 1.4: 筛选
    keep = results[
        (results['selection_freq'] > effective_threshold) &
        (results['label'] != '噪声级')
    ]

    return keep


def run_stage2(stable_descriptors, deconfound_results, feature_df):
    """阶段2: 物理分组去冗余
    输出: 8-10 个代表描述符
    """
    grouper = PhysicalGrouper(family_map, cross_group_rules)
    representatives, family_summary = grouper.select_representatives(
        stable_descriptors, deconfound_results, feature_df, max_per_family=2
    )
    return representatives, family_summary


def run_stage3(representatives, feature_df, y, system_labels):
    """阶段3: 物理约束组合搜索
    输出: Top-5 组合（按去混杂Spearman排序）
    """
    searcher = ConstrainedCombinationSearch(family_map, cross_group_rules,
                                             allowed_operators)
    results_df = searcher.search(representatives, feature_df, y, system_labels)
    top5 = results_df.head(5)
    return top5


def run_stage4(top5_combos, feature_df, y, system_labels, known_factors,
               noise_cols_data):
    """阶段4: 组合验证
    输出: 每个Top-5组合的4重验证结果 + 最终报告
    """
    validator = CombinationValidator()
    validation_results = []
    for _, combo in top5_combos.iterrows():
        combo_values = compute_combo_values(combo, feature_df)
        result = validator.full_validation(
            combo_values, y, system_labels, known_factors, noise_cols_data
        )
        result['formula'] = combo['formula']
        validation_results.append(result)

    # 生成最终报告
    report = generate_final_report(validation_results, top5_combos)
    return validation_results, report


def run_full_pipeline(csv_path: str):
    """完整4阶段流水线"""
    # C1: 加载数据
    df = pd.read_csv(csv_path)

    # C2: 计算描述符
    feat_df = featurize_dataset(csv_path, output_path)

    # C3: 构建特征矩阵 + 噪声
    X, valid_cols, noise_info = build_feature_matrix(feat_df, descriptor_cols)

    # Stage 1-4
    stage1_results = run_stage1(...)
    stage2_results = run_stage2(...)
    stage3_results = run_stage3(...)
    stage4_results, report = run_stage4(...)

    # 保存结果
    report.to_markdown('results/final_report.md')
    return report
```

---

## 4. 执行顺序与依赖

```
C1 (数据层) ──→ C2 (描述符) ──→ C3 (特征矩阵)
                                      │
                                      ├─→ C4 (CV策略)
                                      ├─→ C5 (去混杂)
                                      └─→ C6 (Stability + 分组)
                                              │
                                              └─→ C7 (组合搜索) ──→ C8 (验证)
```

- C1, C2, C3 必须顺序执行
- C4, C5, C6 可并行（但都依赖 C3）
- C7 依赖 C6（需要代表描述符列表）
- C8 依赖 C7（需要 Top-5 组合）

---

## 5. 风险与缓解

| 风险 | 概率 | 影响 | 缓解 |
|------|------|------|------|
| BVSE 能垒计算不可用 | 高 | D'族减少1个描述符 | 设为NaN，自动跳过 |
| 高风险族(G/H)全部被淘汰 | 中 | 减少8个描述符 | 先运行再看，不强求 |
| 80样本做组合搜索统计功效不足 | 中 | CI过宽 | 依赖bootstrap CI，报告中说明限制 |
| Voronoi 间隙位点计算对某些结构失败 | 中 | 部分样本NaN | 允许NaN，有效样本数>50即可 |
| 骨架多面体识别困难（复杂阴离子） | 低 | E族描述符不稳定 | 简化为基于配位数的方法 |
| 体系内CV样本太少（卤化物~15个） | 中 | 体系内结果不稳定 | 体系内CV仅作参考，不作为主要判定 |

---

## 6. 已知基准与预期结果

| 基准 | 来源 | 预期 |
|------|------|------|
| A2 (最远Na-X键长) raw Spearman = 0.597 | 阶段3 | 应在新框架中复现 |
| A2×NaNa raw Spearman = 0.623 | 阶段3 | 应出现在 Top-5 |
| NaNa综合 raw Spearman ≈ 0.5 | 阶段3 | 应在阶段1通过筛选 |
| 阴离子柔软性分数 = 体系代理 | 阶段3 | 应被去混杂分析标记为"体系代理" |
| LOSO MAE = 2.97 (vs random 3-fold = 1.34) | GPT分析 | 去混杂后LOSO应改善 |

---

## 7. 产出清单

| 产出 | 路径 | 格式 |
|------|------|------|
| 改造框架代码 | `automat-naconductor/` | Python |
| 描述符计算结果 | `automat-naconductor/data/naconductor_featurized.csv` | CSV+JSON |
| 去混杂分析表 | `automat-naconductor/results/deconfound_results.csv` | CSV |
| Stability Selection 结果 | `automat-naconductor/results/stability_selection.csv` | CSV |
| 组合搜索结果 | `automat-naconductor/results/combination_search.csv` | CSV |
| 最终验证报告 | `automat-naconductor/results/final_report.md` | Markdown |
| 审计追踪 | `automat-naconductor/results.tsv` | TSV (AUTOMAT风格) |
| 各阶段可视化 | `automat-naconductor/figures/` | PNG/PDF |

---

*计划结束。确认后可由 Worker Agent 通过 `/start-work` 执行。*
