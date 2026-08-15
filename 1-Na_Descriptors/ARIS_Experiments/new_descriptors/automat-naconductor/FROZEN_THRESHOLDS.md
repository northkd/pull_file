# FROZEN_THRESHOLDS.md

## 冻结版本 1

- **冻结日期**：2026-08-13
- **冻结时 commit hash**：0971742

## 冻结取值

| 项 | 键 | 冻结值 | 理由 | 当前有无代码消费者 |
|---|---|---|---|---|
| W3-3 Stage 1 固定基数 | `stage1.top_k` | 10 | 替代 0.2/0.3/0.7 三个无外部依据的阈值；固定基数使有效检验假设数可数 | **无**——Stage 1 当前不做 top-k 筛选，全量进入 Stage 2 |
| W4-3 per-system 最小 n | `evidence.per_system.min_n` | 5 | n=3 时 Spearman 只能取 ±1/±0.5，n=4 仅六个可能值，|rho|≥0.5 是结构性下界而非证据 | 有——`CombinationValidator._per_system` 读取 |
| W4-3 全枚举精确置换上限 | `evidence.per_system.exact_perm_max_n` | 8 | n ≤ 8 时 n! 全枚举可行 | 有——`_exact_permutation_p_value` 读取 |
| W4-3 蒙特卡洛置换上限 | `evidence.per_system.monte_carlo_max_n` | 10 | n = 9、10 用 10000 次蒙特卡洛置换，p_method 记 monte_carlo_permutation 以示区分 | 有——`_exact_permutation_p_value` 读取 |
| W4-3 蒙特卡洛抽次数 | `evidence.per_system.monte_carlo_draws` | 10000 | 10000 次随机置换在统计精度与运行时间间的折中 | 有——`_exact_permutation_p_value` 读取 |
| W5-2 相关簇聚类阈值 | `stability_selection.cluster_threshold` | 0.8 | 以 |rho| ≥ 0.8 为同簇 | **无**——W5-2 实现未做 |

## 冻结声明

以上取值在数据集不存在时冻结。任何修改必须新增 FROZEN_THRESHOLDS 的新版本并保留本版，禁止就地编辑。

## 壳层规则敏感性扫描（设定冻结，执行待数据）

`descriptors/_base.py` 的 `_shell_neighbors` 使用两个硬编码规则：
- 截断增量 `shell_tolerance`（默认 `0.70` Å，取最短键长 + 此值内的阴离子）
- 最小壳层大小 `min_shell_size`（默认 `4`，不足时补至此数）

两者均无文献依据（唯一出处 `script/part1.py:368`）。`_shell_neighbors` 已参数化，
默认值与参数化前行为逐位一致。

### 扫描设定（6 种）

| 设定编号 | shell_tolerance (Å) | min_shell_size (on/off) |
|---|---|---|
| 1 | 0.60 | 4 (on) |
| 2 | 0.60 | 0 (off) |
| 3 | 0.70 | 4 (on) |
| 4 | 0.70 | 0 (off) |
| 5 | 0.80 | 4 (on) |
| 6 | 0.80 | 0 (off) |

### 每种设定必须记录的指标

1. 全部 `_shell_neighbors` 传递依赖描述符（由 `compute_helper_closures` 动态派生，
   实测 16 个）的取值，而非仅记录 `poly_distortion_mean` / `framework_poly_distortion` 两个；
2. 每个描述符取值与基线设定 (0.70 / min_shell_size=4) 的 Spearman 秩相关；
3. **每种设定下的参与位点数** —— `len(distances) > 1` 守卫会静默丢弃 CN=1 的位点，
   取均值的位点集合因此随壳层规则变化，不记录这个数就无法解释取值差异。
   口径写死：Na 侧 = `len(per_site_distortion)`（即实际进入 `poly_distortion_mean`
   分母的位点数），骨架侧 = `len(poly_distortions)`（即实际进入
   `framework_poly_distortion` 分母的位点数）。两者均为通过 `len(distances) > 1`
   守卫的位点集合，不是 `len(per_site_cn)`（后者含 CN=1 位点）。

### 冻结声明

本设定在数据集不存在时冻结，执行待 CIF 到位。修改须新版本，禁止就地编辑。

## symprec 参数（设定冻结，执行待数据）

`descriptors/family_h_symmetry.py` 的 `compute_space_group_number` 与
`compute_wyckoff_diversity` 使用 `symprec=0.01`（已改为从 `run_info.yaml` 读取）。

- 冻结值：`symmetry.symprec: 0.01`
- 敏感性扫描设定：`0.001 / 0.01 / 0.1`（三值，执行待数据）
- 唯一权威来源是 `run_info.yaml` 的 `symmetry.symprec`；本文件仅为记录，不被代码读取

### 冻结声明

本设定在数据集不存在时冻结，执行待 CIF 到位。修改须新版本，禁止就地编辑。

## 数值指纹基线（描述符默认路径不变性）

`scripts/descriptor_fingerprint.py` 用 5 个硬编码合成 Structure（覆盖分数占位、
CN=1 Na 位点、单一/混合阴离子、高对称小原胞）对全部 41 个描述符跑出数值指纹，
基线 CSV 为 `scripts/fingerprint_HEAD.csv`。已在 HEAD（dbfe98a）与 2722960 之间
做逐单元格 diff，零差异，确认默认路径数值未变。

**此后任何重构必须先跑指纹 diff**：重构后重新生成 fingerprint，与基线 CSV 逐格
比对，零差异方可合入。有差异则逐列列出并停下报告，不得自行解释。

## 修订记录

- v1 于 `0fc912f` 入库，当时 `exact_perm_max_n = 10`，理由写"n<10 时 n! 可全枚举"。
- 该理由为假（实现中全枚举只到 n ≤ 8），于 `6ceb106` 就地修正为 `exact_perm_max_n = 8` 并新增 `monte_carlo_max_n` / `monte_carlo_draws`。
- 修正发生在任何取值被用于计算之前（数据集不存在）。
- **此后禁止就地编辑，任何修改必须新增 FROZEN_THRESHOLDS_v2 并保留本版。**

### 2026-08-14 壳层扫描范围修订

**改动内容**：壳层扫描范围从硬编码 2 个描述符（poly_distortion_mean /
framework_poly_distortion）改为动态派生 _shell_neighbors 的全部 16 个传递依赖者。

**理由**：原范围只覆盖受影响者中的 2/16，不足以评估壳层规则变化的完整影响。
_shell_neighbors 的传递依赖者由 compute_helper_closures 派生，实测 16 个：
a2_max_dist / coordination_number_mean / covalency_index / direction_ratio /
ellipsoid_oblateness / framework_bond_rigidity / framework_na_distance_stability /
framework_poly_distortion / framework_sharing_topology / max_bond_length /
mean_bond_length / min_bond_length / na_x_en_diff / poly_distortion_mean /
poly_volume_mean / target_bond_center。

**声明**：本改动发生在任何数据落地之前（数据集不存在）。

### 2026-08-14 H5b：残差化后 p 值口径规则预注册（R1/R2/R3）

本条冻结**三条规则**（不是数值），不是 FROZEN_THRESHOLDS_v2；它对残差化后的 p
值口径做规则级预注册，发生在任何数据落地之前。实现延后至解冻窗口，届时实现必须
与本条一致；不一致则以本条为准。

- **R1（自由度口径）**：残差化后的一切 p 值以
  `n_effective = n − k_used − 1` 为准，`k_used = 实际进入设计矩阵的控制列数`
  （drop_first 后）。任何渐近分布（含 Spearman t 近似、Fisher-z）的样本量参数
  都使用 `n_effective`，不得使用残差化前的 n。
- **R2（置换零分布）**：残差化后的零分布若采用置换，一律**组内**置换，组 = 残差化
  所用那一级（如 `system`）；且**只置换 y**（x 与 controls 配对保持，残差化在置换
  下重算），禁止跨组置换或同时置换 (x, y)。
- **R3（singleton 组排除）**：某 `system` 组只含 1 个样本时，该组整体排除并记入
  `excluded_ledger`，理由码 `singleton_group`；`n` 与 `k_used` 按排除后重算。

**声明**：本冻结发生在任何数据落地之前。规则级冻结，非数值冻结；R1/R2/R3 的代码
实现延后至解冻窗口，届时实现必须与本条一致，不一致则以本条为准。本轮**不实现**
R1/R2/R3 的代码（PIPELINE_DEFERRED.md 6f 记录的缺陷仍按封版处理）。
