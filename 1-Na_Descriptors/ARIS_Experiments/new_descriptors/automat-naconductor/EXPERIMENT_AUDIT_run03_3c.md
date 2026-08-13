checklist_id: descriptor-impl@v1

# EXPERIMENT_AUDIT_run03_3c

**Profile**: descriptor-impl@v1 (A–H 八项 + 强制描述符登记表)
**送审文件**: `descriptors/_base.py`, `descriptors/family_f_longrange.py`, `descriptors/family_g_electronic.py`, `descriptors/family_h_symmetry.py`
**排除路径**: `results/`, `data/naconductor_featurized.csv`
**覆盖描述符**: 13 个（F 族 4、G 族 4、H 族 5）+ `_base.py` 内 12 个共享辅助函数

> **锚点说明**：本次嵌入文件正文未附行号，故按 prompt 中文段落的要求使用 `file:符号锚点`（`文件路径:函数名` 或 `文件路径:模块级常量名`）。凡涉及函数内某一具体语句，在 Details 中直接引用该语句原文。
>
> **嵌入完整性预检**：本批 4 个文件的 Python 缩进结构完整，未发现函数体缩进丢失或语句错位；所有 `def` 的函数体、`for`/`if` 嵌套层级均可解析为合法语法。本报告不含因粘贴伪影产生的判定。

---

### A. Formula Fidelity（公式保真度）: FAIL

- **Evidence**: `family_g_electronic.py:compute_covalency_index`, `family_g_electronic.py:compute_na_x_en_diff`, `family_g_electronic.py:compute_framework_d_electron_weighted`, `family_g_electronic.py:compute_charge_balance_deviation`, `family_f_longrange.py:compute_path_tortuosity`, `family_f_longrange.py:compute_nana_nana_angle_mean`, `family_f_longrange.py:compute_nana_second_neighbor_dist`, `family_f_longrange.py:compute_nana_spacing_uniformity`, `family_h_symmetry.py:compute_coordination_cv`, `family_h_symmetry.py:compute_wyckoff_diversity`, `_base.py:compute_polyhedron_volume`, `_base.py:_effective_anion_radius`, `_base.py:find_interstitial_sites`, `_base.py:get_na_sites`

- **Details**:

**A-1 [BLOCKER] `compute_covalency_index` 计算的是 Pauling 离子性，不是共价性——名称与结论方向双重反号。**

- 声称量：docstring 写 "Pauling 共价性指数"，并明确写 "值越大说明共价性越强"。
- 实现式：`covalency = 1.0 - np.exp(-(delta ** 2) / 4.0)`，其中 `delta = χ_X − χ_Na`。
- 文献标准定义：Pauling（*The Nature of the Chemical Bond*, 1932/1960）给出的**离子性百分数**（fraction of ionic character）正是 `1 − exp(−(Δχ)²/4)`；其互补量 `exp(−(Δχ)²/4)` 才是共价性分数。
- 后果：该量对 Δχ 单调**递增**，即 Δχ 越大取值越大——而 Δχ 越大意味着键越**离子性**。docstring 的物理解读与实现恰好相反。任何以"共价性增强 → 电导率如何变化"为叙事的下游解释都会得到反号结论。最小修复二选一：改名为 `ionicity_index` 并修正 docstring 方向，或把公式改为 `np.exp(-(delta**2)/4.0)`。二者不等价，必须显式选择。

**A-2 [BLOCKER] `compute_na_x_en_diff` 的 docstring 声明按位点求均值，实现按键求均值。**

- 声称量：docstring 写 "计算 χ(X) − χ(Na)，然后取所有 **Na 位点**均值"。
- 实现式：`en_diffs` 是跨所有 Na 位点、所有壳层键的**扁平列表**，最后 `_safe_mean(en_diffs)`。即
 `⟨Δχ⟩ = Σ_i Σ_{b∈shell(i)} Δχ_b / Σ_i |shell(i)|`
 而非声称的
 `(1/N_Na) Σ_i [ (1/|shell(i)|) Σ_{b∈shell(i)} Δχ_b ]`。
- 后果：配位数大的 Na 位点被隐式加权更重。在 Na 位点配位数不均一的结构（正是本项目关心的那类）中二者不相等。这不是舍入级差异，而是加权方案的定义性差异。

**A-3 [BLOCKER] `compute_path_tortuosity` 没有计算任何路径，实现的是二近邻/一近邻距离比。**

- 声称量：函数名 `path_tortuosity`；docstring 第一句 "估计: Na-Na 直线距离 / 最短路径距离 的均值"。
- 文献标准定义：曲折度 τ = 实际路径长度 / 直线距离，恒 ≥ 1，需要路径搜索（图上最短路，或 NEB/BVSE 路径积分）。代码中不存在任何图构建、路径搜索或路径长度积分。
- 实现式：`τ̂ = (1/N) Σ_i d₂(i)/d₁(i)`，`d₁, d₂` 为该 Na 到其他 Na 位点最小镜像距离的第一、第二顺序统计量。
- 另注 docstring 内部自相矛盾：第一句写的比值是"直线/路径"（≤1），标准定义是"路径/直线"（≥1），实现的第三种量与两者都无关。三处三个不同的量。
- 后果：该描述符与 `compute_nana_second_neighbor_dist` 共用同一 `dists` 向量，只差一个除以 `d₁`（见 H 项）。它不携带任何"路径"信息，任何以迁移路径几何为由的物理解释都不成立。

**A-4 [BLOCKER] `compute_nana_nana_angle_mean` 的邻居选取与向量构造使用了不同的周期镜像，算出的角不是最近邻夹角。**

- 邻居选取：`d = float(struct.get_distance(na_idx, other_idx))`——pymatgen 的 `Structure.get_distance` 返回**最小镜像**距离。
- 向量构造：`v1 = np.array(struct[dists[0][0]].coords, dtype=float) - center`——`site.coords` 是该位点**存储在原胞内的**笛卡尔坐标，不是最小镜像位置。
- 后果：当最近邻实际位于某个周期镜像上（在小原胞、层状或链状 Na 亚晶格中是常态），`v1` 指向的是原胞内那个副本，方向与真实最近邻向量完全无关，长度可达晶胞对角线量级。返回的"三体角"不是任何几何量的估计。两个位点分数坐标相近时 `v1` 可远小于真实键长，此时 `+ 1e-12` 保护项防止除零，却把结果推向一个由数值噪声决定的角度。
- 这条同时是 D 项失败的主因之一。

**A-5 [BLOCKER] `compute_nana_second_neighbor_dist` 求的是"到不同索引位点的第二小距离"，不是第二配位壳层距离。**

- 声称量："对每个 Na，找第二近的 Na 距离"，配合族名"长程关联"，读者会理解为第二配位壳层。
- 实现式：`d₂(i) =` 排序后 `dists[1]`，其中 `dists` 只遍历 `other_idx != na_idx` 的**不同索引**位点，每个索引只贡献一个最小镜像距离。
- 两处偏差：
 1. **自身周期镜像被完全排除**。在原胞中，一个 Na 位点最近的若干邻居往往就是它自己的平移镜像。这些距离一个都不进入 `dists`。
 2. **简并未合并**。若第一配位壳层有多个等距邻居（高对称结构的常态），`dists[0] == dists[1]`，返回的"第二近邻距离"数值上等于第一近邻距离。此时 `compute_path_tortuosity` 恒返回 1.0。
- 后果：该量既不是第一壳层距离也不是第二壳层距离，而是一个依赖于"晶胞里恰好放了几个独立 Na 索引"的顺序统计量。见 D 项。

**A-6 [BLOCKER] `compute_coordination_cv` 中的"配位数"是 Voronoi 面数，不是化学配位数。**

- 实现：`vnn = VoronoiNN()`（默认 `tol=0`），`cn = vnn.get_cn(struct, na_idx)`。`tol=0` 时保留所有权重为正的 Voronoi 面，返回的 CN 是 Voronoi 多面体的**面数**，典型值 12–20，包含大量立体角极小的面。
- 与之对照，同仓库 `_base.py:NA_EFFECTIVE_RADII_A` 的键为 4/5/6/7/8/9/12——Shannon 表的**化学配位数**语义。`_base.py:_effective_na_radius` 对未列入的 CN 静默回落到 CN=6。
- 后果：仓库内"配位数"一词承载两种互不相容的定义，且两者会在同一条流水线上相遇。若 A 族有任何描述符把 Voronoi CN 喂给 `_effective_na_radius`，回落分支将**几乎恒定触发**（Voronoi CN 极少落在 {4,5,6,7,8,9,12} 内），使有效半径退化为常数 1.02 Å。本批次未嵌入 A 族文件，该联动标 unverifiable，但仓库级定义冲突本身已可判定。

**A-7 [BLOCKER] `_base.py:compute_polyhedron_volume` 算的是 Voronoi 元胞体积，不是配位多面体体积。**

- docstring："使用 pymatgen 的 VoronoiNN 计算**配位多面体**体积。"
- 实现：对 `get_voronoi_polyhedra` 返回的每个近邻取 `neighbor_info.get("volume", 0.0)` 求和。pymatgen 中该字段是中心原子到该 Voronoi 面所张的**锥体体积**；全部求和得到的是该位点 **Voronoi 元胞的总体积**。
- 二者是不同的几何对象：配位多面体是以配位阴离子为顶点的凸包（标准定义见 Robinson/Gibbs/Ribbe 1971 的多面体畸变体系）；Voronoi 元胞是空间镶嵌划分单元，其体积之和等于晶胞体积。前者对 NaO₆ 约 15–25 Å³，后者对同一位点通常显著更大，且随周围原子密度而非配位几何变化。
- 该函数被 `family_h_symmetry.py:compute_volume_cv` 消费，故 `volume_cv` 实际是"Na 位点 Voronoi 元胞体积的 CV"。

**A-8 [BLOCKER] `compute_framework_d_electron_weighted` 名为"d 电子加权"，实现是 d/f 区元素的二值占位分数；且元素集合把整个镧系当作 d 区。**

- 声称量：函数名含 `d_electron_weighted`；docstring "骨架阳离子中含 d 电子的元素 (过渡金属) 的占位权重总和，除以骨架阳离子总占位权重"。
- 实现式：`d_occ / total_occ`，其中 `d_occ` 是 `el_sym in d_block` 的占位数之和——**权重是 1，不是 d 电子数**。Ti⁴⁺（d⁰）与 Fe²⁺（d⁶）贡献完全相同。名称中的 "weighted" 在实现中无对应物。
- `d_block` 集合含 `La, Ce, Pr, Nd, Sm, Eu, Gd, Tb, Dy, Ho, Er, Tm, Yb, Lu`——除 La（5d¹）外全部是 f 区元素，与 docstring 的 "(过渡金属)" 不符；同时遗漏 Pm。
- 分母口径偏差：`get_framework_sites` 返回"非 Na 且非阴离子"的位点，其中"阴离子"判据是位点上**存在任一** `ANION_ELEMENTS` 元素（见 A-10）。含混合占位（如 Na/O 共占）的位点会被同时排除出骨架，分母因此不是 docstring 说的"骨架阳离子总占位权重"。

**A-9 [WARN] `compute_nana_spacing_uniformity` 的名称暗示近邻间距，实现是全对距离。**

- 实现式：对**所有** `C(N_Na, 2)` 个 Na-Na 对取最小镜像距离，求 CV。
- "间距 (spacing)" 在离子导体语境中默认指近邻间距。全对距离集合中绝大多数是远距离对，其分布形状由晶胞大小与形状主导（见 D 项）。这不只是命名问题：CV 的分母（均值）随晶胞增大而增大，使"越小越均匀"的解读在跨晶胞比较时失效。

**A-10 [WARN] `get_na_sites` 的 docstring 声明多数派判据，实现是 1e-6 阈值。**

- docstring："Na 位点 = **主要物种为 Na** 的位点（考虑部分占位）。"
- 实现：`if na_occ > 1e-6: na_indices.append(i)`。
- 后果：Na 占位 0.01 / Zr 占位 0.99 的混合位点会被记为 Na 位点，且在所有 F/H 族统计中与满占 Na 位点**等权**（占位数从不参与加权）。同一文件的 `_major_species` 采用真正的多数派判据，两套判据在 `_shell_neighbors` 与 `get_na_sites` 之间混用。

**A-11 [WARN] `_effective_anion_radius` 的 docstring 声明加权平均，实现是元素符号集合上的等权算术平均。**

- 实现：`sum(r for _, r in values) / len(values)`，`values` 来自 `sorted(anion_symbols)`——`anion_symbols` 是**集合**，与化学计量、占位数、位点数均无关。
- 后果：Na₃PS₄ 与 Na₇P₃S₁₁ 得到相同值；含 0.01 当量 Cl 掺杂的氧化物与 1:1 的 O/Cl 化合物也得到相同值 (1.40+1.81)/2。docstring 的 "加权" 二字在代码中无对应物。
- 本批次 F/G/H 未消费该函数，故不计入 BLOCKER 计数，但它是共享地基。

**A-12 [WARN] `find_interstitial_sites` 返回的 `volume` 字段恒为 0.0，docstring 声明它是 Voronoi 区域体积。**

- docstring："volume 为对应 Voronoi 区域体积 (Å³)"。
- 实现：`interstitial_sites.append({"coords": ..., "volume": 0.0})`，全函数无任何体积计算。
- 这是一个**有文档承诺但从未实现**的字段。下游消费者读到的是合法浮点数 0.0，不是 NaN，见 C 项。

**A-13 [WARN] `compute_wyckoff_diversity` 统计的是对称等价轨道数，不是 Wyckoff 位置数。**

- 实现：`len(symm_struct.equivalent_indices)`——`SymmetrizedStructure.equivalent_indices` 是等价位点组的列表，其长度是**轨道数**。
- 同一 Wyckoff 字母可以被多个化学上不同的轨道占据（如两组独立的 4a 位）。轨道数 ≥ Wyckoff 字母数。多数情况下两者数值接近，故列 WARN 而非 FAIL，但"Wyckoff 多样性"这一命名会诱导下游把它读作空间群的位置对称性统计量，实际它是"独立结晶学位点数"。

**A-14 [WARN] `compute_charge_balance_deviation` 的 docstring 只描述了 Na 与阴离子，实现含 40 元素固定价态表；且 N 被赋 −1。**

- docstring："Na 贡献 +1，阴离子假设 -2 (O/S/Se) 或 -1 (F/Cl/Br/I/H/N)"。实现的 `fallback_oxidation_states` 还包含 Li/K/Rb/Cs/Mg/Ca/Sr/Ba/Zn/Al/Fe/Cr/Ga/In/Si/Ge/Sn/Ti/Zr/Hf/Mn/P/V/As/Sb/Nb/Ta 共 27 个骨架阳离子，各锁定单一价态。
- 化学错误：`"N": -1`。氮化物中 N 的标准氧化态是 **−3**。Na₃N、Na₃PN₂ 之类体系会被系统性判为电荷不平衡。`"H": -1`（氢化物）对含 OH⁻/H₂O 的体系同样反号——那里 H 是 +1。
- 单价态锁定的后果：Fe 恒 +3、Mn 恒 +4，混合价体系（层状氧化物候选中常见）必然产生非零偏差，而这个偏差度量的是"该元素是否恰好处于表中假定的价态"，不是结构的真实电荷失衡。
- 见 C-4：表外元素被 `continue` 静默跳过。

---

### B. Degenerate Input Handling（退化输入）: FAIL

- **Evidence**: `_base.py:_safe_cv`, `_base.py:_safe_std`, `family_f_longrange.py:compute_nana_spacing_uniformity`, `family_f_longrange.py:compute_path_tortuosity`, `family_h_symmetry.py:compute_coordination_cv`, `family_h_symmetry.py:compute_volume_cv`, `family_h_symmetry.py:compute_partial_occupancy_ratio`, `_base.py:site_occupancies_by_symbol`, `_base.py:get_na_sites`

- **Details**:

**B-1 [BLOCKER] `_safe_cv` 缺少 n<2 闸门，单元素输入静默返回 0.0——而 `_safe_std` 有这个闸门。**

```
_safe_std:  if len(values) < 2: return NaN      # 有闸门
_safe_cv :  if not values:      return NaN      # 只挡空列表
```

单元素输入时 `np.std([x], ddof=0) == 0.0`，故 `_safe_cv([x]) == 0.0`。这是**合法量程内的有限值**，且恰好落在"最均匀"这一端——即最有利的取值。

三个本批次消费者全部受影响：

| 描述符 | 退化触发条件 | 返回值 | 下游读法 |
|---|---|---|---|
| `compute_nana_spacing_uniformity` | 恰好 2 个 Na 位点（1 个距离对） | **0.0** | "Na 分布完全均匀" |
| `compute_coordination_cv` | 仅 1 个 Na 位点的 `get_cn` 成功 | **0.0** | "配位环境完全一致" |
| `compute_volume_cv` | 仅 1 个 Na 位点的多面体体积非 NaN | **0.0** | "多面体体积完全一致" |

注意 `compute_nana_spacing_uniformity` 的守卫是 `len(na_indices) < 2`，即 2 个 Na 位点**通过**守卫，随后必然返回 0.0。守卫与退化条件之间差整整一个数量级。

**B-2 [BLOCKER] `compute_coordination_cv` / `compute_volume_cv` 的逐位点 `except` 把部分失败降级为"更均匀"。**

`compute_coordination_cv` 内层：

```
try:    cn = vnn.get_cn(struct, na_idx)
except Exception:  continue
```

`compute_volume_cv` 通过 `if not np.isnan(vol)` 过滤。两者都**不记录**参与统计的位点数。若 10 个 Na 位点中 8 个抛异常，CV 由剩下 2 个算出；若 9 个抛异常，返回 0.0。返回值不携带任何样本量信息，下游无法区分"真实均匀"与"只剩一个样本"。

**B-3 [BLOCKER] 高对称结构上 `compute_path_tortuosity` 恒返回 1.0。**

当第一配位壳层存在多个等距 Na 邻居（立方、菱方、NASICON 的高对称设定中普遍如此），`dists[0] == dists[1]`，比值恒为 1。返回 1.0 是曲折度的**理论下界**，读作"路径完全平直"。真实原因是简并，不是几何。1.0 与一个真实测得的 1.0 在下游不可区分。

**B-4 [WARN] 分数占位在所有 F/H 族描述符中被完全忽略。**

`get_na_sites` 只做布尔判定（A-10），返回索引列表；F 族四个描述符、H 族 `coordination_cv`/`volume_cv` 全部对索引列表做无权统计。占位 0.05 的 Na 与占位 1.0 的 Na 等权。对本项目而言这是实质问题：分数占位正是"空位拓扑"信息的载体，而 F/H 族把它抹平了。

**B-5 [WARN] `compute_partial_occupancy_ratio` 的 `else` 分支是死代码。**

```
if len(species_dict) != 1 or abs(total_occ - 1.0) > 1e-3:
    partial_count += 1
else:
    for occ in species_dict.values():
        if abs(occ - 1.0) > 1e-3: partial_count += 1; break
```

进入 `else` 意味着 `len(species_dict) == 1` 且 `|total_occ − 1| ≤ 1e-3`。此时唯一的 `occ` 就等于 `total_occ`，故内层条件恒假。该分支永不执行。它不改变返回值，但说明作者对 `site_occupancies_by_symbol` 的聚合语义有误解。

**B-6 [WARN] `site_occupancies_by_symbol` 按元素符号聚合，使混合价位点在 `partial_occupancy_ratio` 中不可见。**

Fe²⁺ 0.5 / Fe³⁺ 0.5 聚合为 `{Fe: 1.0}`，`len == 1` 且总占位 1.0 → 判为**有序位点**。若该描述符的意图包含"精修中的无序程度"，混合价无序被系统性漏计。

**B-7 [PASS 分项] 无 Na / 无阴离子 / 无骨架的守卫存在且返回 NaN。**

`compute_na_x_en_diff`、`compute_covalency_index` 有 `if not na_indices or not anions: return NaN`；`compute_framework_d_electron_weighted` 有 `if not fw_indices: return NaN` 与 `if total_occ < 1e-12: return NaN`；`compute_charge_balance_deviation` 有 `if total_absolute_charge < 1e-12: return NaN`。这几条路径正确。

---

### C. NaN and Sentinel Paths（NaN 与哨兵路径）: FAIL

- **Evidence**: `_base.py:_safe_cv`, `_base.py:find_interstitial_sites`, `_base.py:compute_polyhedron_volume`, `family_g_electronic.py:compute_charge_balance_deviation`, `family_g_electronic.py:compute_na_x_en_diff`, `family_h_symmetry.py:compute_space_group_number`, `family_h_symmetry.py:compute_wyckoff_diversity`, `family_h_symmetry.py:compute_coordination_cv`

- **Details**:

**C-1 全量 NaN / 哨兵路径清单**

| 描述符 | NaN 路径 | 哨兵（有限值）路径 | 可区分性 |
|---|---|---|---|
| `nana_nana_angle_mean` | `len(na)<3`；`angles` 空 | — | NaN 与晶胞大小相关（C-5） |
| `nana_second_neighbor_dist` | `len(na)<3`；`second_dists` 空 | — | 同上 |
| `path_tortuosity` | `len(na)<2`；`ratios` 空 | **1.0**（简并，B-3） | ✗ 不可区分 |
| `nana_spacing_uniformity` | `len(na)<2`；均值≈0 | **0.0**（n=1 对，B-1） | ✗ 不可区分 |
| `na_x_en_diff` | 无 Na / 无阴离子 / 壳层全空 | 单一阴离子体系恒为常数（C-3） | ✗ 常数即无信息 |
| `charge_balance_deviation` | `total_absolute_charge<1e-12` | **偏小的有限值**（C-4） | ✗ 不可区分 |
| `covalency_index` | 同 `na_x_en_diff` | 同 `na_x_en_diff` | ✗ |
| `framework_d_electron_weighted` | 无骨架位点；`total_occ<1e-12` | **0.0**（无过渡金属，合法） | ✓ 合法 0.0 |
| `space_group_number` | 裸 `except Exception` | **1.0**（无序结构降至 P1，C-6） | ✗ 不可区分 |
| `wyckoff_diversity` | 裸 `except Exception` | **len(struct)**（P1 回落，C-6/G-2） | ✗ 不可区分 |
| `partial_occupancy_ratio` | `len(struct)==0` | — | ✓ |
| `coordination_cv` | `len(na)<2`；`cn_list` 空；`ImportError` | **0.0**（n=1，B-1/B-2） | ✗ |
| `volume_cv` | `len(na)<2`；`volumes` 空 | **0.0**（n=1，B-1） | ✗ |
| `find_interstitial_sites`（helper） | — | **`[]`**（裸 except）；**`volume=0.0`** 恒定 | ✗ 见 C-2 |
| `compute_polyhedron_volume`（helper） | 裸 `except`；`total_vol <= 0` | — | ✓ 返回 NaN |

**C-2 [BLOCKER] `find_interstitial_sites` 的裸 `except` 把 Qhull 失败降级为"零个间隙位"，且 `volume` 恒为 0.0。**

```
try:  vor = Voronoi(all_points_arr)
except Exception:  return []
```

空列表在任何"计数"型下游消费者处会变成 **0**，一个完全合法的有限值。Qhull 在共面/共线点集上退化——**这类点集恰好出现在高对称小原胞上**。因此缺失（伪装成 0）与空间群相关（见 C-5）。叠加 A-12 的恒 0 体积字段，该函数有两条独立的"合法零"路径。

**C-3 [BLOCKER] 单一阴离子体系上 `na_x_en_diff` 与 `covalency_index` 退化为常数。**

两者的取值只依赖壳层中出现的**阴离子元素符号**，与距离、角度、占位、几何均无关。对全氧化物结构，每根键的 Δχ 都是 3.44 − 0.93 = **2.51**，故 `na_x_en_diff ≡ 2.51`，`covalency_index ≡ 1 − exp(−2.51²/4) = 0.7924`，对该体系内**每一个结构逐值相同**。

这不是 NaN 问题而是零方差问题，但后果同级：在按体系分层的数据集上，这两列实际编码的是"该条目属于氧化物/硫化物/卤化物哪一类"——即**体系标签的确定性函数**。任何跨体系相关性都是构造性混杂，不是物理关联；任何体系内相关性恒为 0 或未定义。

**C-4 [BLOCKER] `compute_charge_balance_deviation` 对表外元素静默 `continue`，使返回值向"平衡"方向偏。**

```
if oxidation_state is None:  continue
```

被跳过的元素既不进 `net_charge` 也不进 `total_absolute_charge`。设结构含大量表外元素（W、Mo、Bi、Te、稀土等，全部不在 `fallback_oxidation_states` 中），则分子分母同时缩水，比值趋近于剩余（多为 Na 与常见阴离子的）子系统的平衡度，通常远小于真实失衡。返回一个**偏小的有限值**，与"电荷严格平衡"不可区分。

**C-5 [BLOCKER] NaN 产生模式与晶胞设定/结构类系统相关。**

- `len(na_indices) < 3` 守卫（`nana_nana_angle_mean`、`nana_second_neighbor_dist`）：同一晶体以**原胞**给出时可能只有 1–2 个独立 Na 索引 → NaN；以**惯用胞**或超胞给出时 ≥3 → 有限值。缺失与"该 CIF 来自哪个数据库、以何种设定归档"直接绑定。
- `find_interstitial_sites` 的 Qhull 退化偏向高对称小原胞（C-2）。
- `SpacegroupAnalyzer(symprec=0.01)` 的失败/降级偏向坐标精度低或存在分数占位的条目（C-6）。

三条缺失机制全部与**数据来源属性**而非物理相关，且代码中无任何记录。若 Stage 1 用完整性或缺失模式做过滤，这一层会把 provenance 直接引入选择过程。

**C-6 [BLOCKER] 分数占位结构在 H 族两个描述符上产生"合法但退化"的取值，而非 NaN。**

`SpacegroupAnalyzer` 把不同占位的位点视作不同物种，分数占位结构通常被判为 **P1（空间群号 1）**。此时：

- `compute_space_group_number` 返回 **1.0**——与一个真实的三斜结构不可区分；
- `compute_wyckoff_diversity` 返回 **等于晶胞位点总数**的值——见 G-2，此时该描述符退化为纯粹的晶胞大小代理。

两者都不是 NaN，都在合法量程内，都无任何标记。

---

### D. Cell-Setting Invariance（晶胞设定不变性）: FAIL

> Prompt 明确标注本项为 "the single most consequential check in this profile"。本批次在此项上失败最严重。

- **Evidence**: `family_f_longrange.py`（全部 4 个函数）, `family_h_symmetry.py:compute_wyckoff_diversity`, `family_g_electronic.py:compute_charge_balance_deviation`, `_base.py:_major_species`, `_base.py:_shell_neighbors`, `_base.py:find_interstitial_sites`

- **Details**:

**D-1 [BLOCKER] F 族四个描述符全部晶胞设定相关。根因是"只遍历不同索引的位点、排除自身周期镜像"。**

四个函数共用同一模式：

```
for other_idx in na_indices:
    if other_idx == na_idx: continue
    d = struct.get_distance(na_idx, other_idx)
```

`get_distance` 取最小镜像，但**遍历范围是晶胞内的独立索引**。同一晶体的 Na-Na 距离集合因此随晶胞设定而变。

具体算例——设某晶体 Na 亚晶格为简单立方，a = 4 Å：

- **原胞（1 个 Na）**：`len(na)=1`。`angle_mean`/`second_neighbor_dist` → NaN（守卫 <3）；`path_tortuosity` → NaN（守卫 <2）；`spacing_uniformity` → NaN。
- **2×2×2 超胞（8 个 Na）**：`dists` 含 4.0（多个，最小镜像后）、5.66、6.93 等。`second_neighbor_dist` = 4.0（简并），`tortuosity` = 1.0，`spacing_uniformity` = 全 28 对距离的 CV。
- **3×3×3 超胞（27 个 Na）**：全对距离集合再次改变，均值与标准差均变，`spacing_uniformity` **数值不同**。

`nana_spacing_uniformity` 尤其严重：它是**全对**距离的 CV，超胞每增大一级，长距离对的数量以 O(N²) 增长而最小镜像距离上限只以 O(N^{1/3}) 增长，CV 单调漂移且不收敛到任何晶体学不变量。

**D-2 [BLOCKER] `compute_nana_nana_angle_mean` 额外依赖原胞内坐标表示，即使位点数相同也不不变。**

见 A-4。`site.coords` 依赖于每个位点被归约到哪个原胞副本——同一晶体、同一空间群、同一位点数，仅把某个 Na 的分数坐标从 0.99 写成 −0.01（数学上等价），`v1`/`v2` 就变，返回角就变。这是**比超胞依赖更强的一种不不变性**：它依赖于 CIF 文件中坐标的书写约定。

**D-3 [BLOCKER] `compute_wyckoff_diversity` 的不变性是条件性的。**

- 对称性识别成功时：spglib 能识别超胞中的额外平移，等价轨道数与原胞一致 → **不变**。
- 对称性识别失败/降至 P1 时（分数占位、坐标精度差、symprec=0.01 过紧）：每个位点自成一个轨道，返回值 = `len(struct)` → **完全等于晶胞大小**。

同一列中，一部分条目是晶体学不变量、另一部分是晶胞尺寸计数。这比"一致地不不变"更难在下游察觉。

**D-4 [WARN] `compute_charge_balance_deviation` 依赖输入是否携带氧化态标注。**

```
oxidation_state = getattr(species, "oxi_state", None)
if oxidation_state is None: oxidation_state = fallback_oxidation_states.get(symbol)
```

同一晶体：若解析结果给出 `Species("Fe2+")`，用 +2；若给出 `Element("Fe")`，回落表用 +3。返回值不同。这不是晶胞设定依赖，而是同类的**输入表示依赖**：该列部分编码了"源文件是否标注了氧化态"这一 provenance 属性。比值本身对超胞不变（分子分母同倍缩放），这一点是正确的。

**D-5 [WARN] `_major_species` 的平局由 dict 插入序决定，故依赖文件中的元素书写顺序。**

`max(species_dict.items(), key=lambda kv: kv[1])` 在 50/50 混合占位时返回**先插入**的那个符号。`site.species` 的顺序源自解析器读取 CIF 的字段顺序。后果：一个 Na₀.₅K₀.₅ 位点或 O₀.₅S₀.₅ 位点是否被 `_shell_neighbors` 计为阴离子，取决于 CIF 里哪个元素写在前面。这条同时属于 F 项。

**D-6 [WARN] `find_interstitial_sites` 的去重阈值 0.5 Å 非传递，保留结果依赖顶点枚举顺序。**

```
for u in unique:
    if float(distance) < 0.5: is_dup = True; break
```

去重是"与已保留集合中任一元素近则丢弃"，这不是等价关系。若三个顶点两两距离为 0.4/0.4/0.7 Å，先处理哪一个决定最终保留 1 个还是 2 个。`vor.vertices` 的顺序由 Qhull 对输入点序的处理决定，而输入点序 = 结构中位点顺序。

**D-7 [NOT_APPLICABLE] 解析器占位容差（D.3 子项）。**

需要 `featurizer.py` / CIF 解析层（`CifParser(occupancy_tolerance=...)` 的实际取值）才能判定。本批次仅嵌入 `_base.py` 与三个 family 文件，未提供解析器。可确定的是**受影响面**：`get_na_sites` 的 1e-6 阈值、`compute_partial_occupancy_ratio` 的 1e-3 阈值、`site_occupancies_by_symbol` 的聚合口径，三者对占位容差引起的占位重标定全部敏感。缺失文件：`featurizer.py` 或等价的结构读入模块。

**D-8 [NOT_APPLICABLE] 注册表元数据中是否声明了不变性。**

本批次未嵌入 `descriptors/__init__.py` 或任何注册表文件。三个 family 文件中**不存在** family/dimension/extensivity/invariance 字段——`high_risk` 标记只出现在 docstring 文本中，不是可消费的元数据。缺失文件：`descriptors/__init__.py`。

---

### E. Cutoff and Parameter Provenance（常数出处）: FAIL

- **Evidence**: `_base.py:_anion_cutoff`, `_base.py:_shell_neighbors`, `_base.py:NA_EFFECTIVE_RADII_A`, `_base.py:ANION_EFFECTIVE_RADII_A`, `_base.py:ELECTRONEGATIVITY`, `_base.py:find_interstitial_sites`, `_base.py:get_na_x_bonds`, `_base.py:get_na_sites`, `family_h_symmetry.py:compute_space_group_number`, `family_h_symmetry.py:compute_partial_occupancy_ratio`, `family_g_electronic.py:compute_charge_balance_deviation`

- **Details**:

**E-1 常数出处逐条清单**

| 常数 | 位置 | 出处状态 | 排序敏感性 |
|---|---|---|---|
| `ELECTRONEGATIVITY` 全表 | `_base.py` | ✓ 已注明 "Pauling 标度"；核对全部 10 项均与 Pauling 标准值一致 | — |
| `NA_EFFECTIVE_RADII_A` (CN 4–12) | `_base.py` | ✓ 已注明 Shannon；0.99/1.00/1.02/1.12/1.18/1.24/1.39 全部与 Shannon 1976 一致 | 低 |
| `NA_FALLBACK_CN = 6` | `_base.py` | ✗ 无出处；静默回落（A-6） | **高** |
| `ANION_EFFECTIVE_RADII_A` O/S/Se/F/Cl/Br/I | `_base.py` | ✓ 与 Shannon 1976 CN=6 值一致 | 低 |
| `ANION_EFFECTIVE_RADII_A["H"] = 1.40` | `_base.py` | ✗ **与 O²⁻ 逐位相同**，疑为复制；H⁻ 无对应 Shannon CN6 项 | 中 |
| `ANION_EFFECTIVE_RADII_A["N"] = None`（注释"N 无经典值"） | `_base.py` | ✗ 注释存疑：Shannon 1976 列有 N³⁻（CN=4，≈1.46 Å） | 中 |
| `_anion_cutoff` 全部 9 个值（3.20–4.35） | `_base.py` | ✗ **完全无出处**，无推导、无引用 | **高** |
| `_shell_neighbors` 的 `+0.70` Å | `_base.py` | ✗ docstring 自述"沿用 **part1.py** 的简化规则"——provenance chain，不是 justification | **高** |
| `_shell_neighbors` 的"补至 4" | `_base.py` | ✗ 同上；`len(kept) <= 3` 与 `neighbors[:4]` 两个魔数 | **高** |
| `get_na_x_bonds` 的 `max_dist=4.0` | `_base.py` | ✗ 无出处；与 `_anion_cutoff` 的体系相关截断**不一致**（两套并存） | 中 |
| `get_na_sites` 的 `1e-6` 占位阈值 | `_base.py` | ✗ 无出处；与 docstring 的多数派判据矛盾（A-10） | **高** |
| `find_interstitial_sites` 的 `min_dist_from_atom=1.5` | `_base.py` | ✗ 无出处 | **高** |
| `find_interstitial_sites` 去重阈值 `0.5` | `_base.py` | ✗ 无出处；且非传递（D-6） | **高** |
| `find_interstitial_sites` 的 `±1` 影像范围 | `_base.py` | ✗ 无出处；对长轴晶胞可能不足 | 中 |
| `in_cell` 判据 `-1e-6 <= f < 1.0 - 1e-6` | `_base.py` | ✗ 上下界**不对称**（下界含 −1e-6，上界排除 [1−1e−6, 1)），无出处 | 低 |
| `symprec=0.01` ×2 | `family_h_symmetry.py` | ✗ 无出处；pymatgen 默认亦为 0.01，但代码未声明这是有意继承默认值 | **高** |
| `partial_occupancy_ratio` 的 `1e-3` | `family_h_symmetry.py` | ✗ 无出处；小于常见 CIF 占位报数精度，会把舍入误差判为分数占位 | **高** |
| `fallback_oxidation_states` 40 项 | `family_g_electronic.py` | ✗ 无出处；单价态锁定（A-14） | **高** |
| `d_block` 元素集合 | `family_g_electronic.py` | ✗ 无出处；含整个镧系（A-8） | 中 |
| Pauling 式中的 `/4.0` | `family_g_electronic.py` | ✓ 是 Pauling 原式常数（但用错了互补分支，A-1） | — |
| `_safe_cv` 的 `1e-12` 零均值阈值 | `_base.py` | 惯例值，可接受 | 低 |

**E-2 [BLOCKER] 无出处 + 排序敏感的组合**（本项的 FAIL 判据）

至少四处同时满足"常数无出处"与"跨结构排序对其敏感"：

1. **`_shell_neighbors` 的 +0.70 Å 与补至 4**：壳层成员集合是 G 族两个描述符的**唯一**输入。0.70 → 0.60 会改变壳层组成。更严重的是"补至 4"引入**阶跃**：当第 4 个邻居的距离恰在 `first + 0.70` 附近时，微小的晶格参数差异会使壳层大小在 3 与 4 之间跳变，取值不连续。
2. **`_anion_cutoff` 取 `max`**：`return max((cutoffs.get(sym, 4.0) for sym in anion_symbols), default=4.0)`。含 O 与 I 的混合体系对 O 邻居也用 4.35 Å 截断。同一 Na-O 键在纯氧化物中用 3.20 Å 判定、在氧碘化物中用 4.35 Å 判定——**同一物理对象在不同体系中用不同规则测量**。这直接把体系标签写进了描述符定义。
3. **`symprec=0.01`**：空间群号与 Wyckoff 轨道数对 symprec 高度敏感，尤其在接近对称的实验精修结构上。0.01 → 0.1 会使相当比例的条目跳到更高对称群，两个 H 族描述符的取值与排序同时改变。
4. **`partial_occupancy_ratio` 的 1e-3**：占位报为 0.998 的位点被判为分数占位，报为 0.9995 的不被判。阈值恰好落在 CIF 常见报数精度上。

**E-3 [BLOCKER] 代码中不存在任何常数敏感性检查。**

四个文件中无参数扫描、无对 cutoff/symprec/tolerance 的稳健性断言、无记录所用常数版本的机制。

---

### F. Determinism and Order Dependence（确定性与顺序依赖）: WARN

- **Evidence**: `_base.py:_major_species`, `_base.py:_shell_neighbors`, `_base.py:find_interstitial_sites`, `_base.py:site_occupancies_by_symbol`, `family_g_electronic.py:compute_charge_balance_deviation`, `family_f_longrange.py`（`dists.sort()`）

- **Details**:

**F-1 [PASS 分项] 无随机性；同一输入文件重复求值给出同一结果。**

四个文件中不存在 `random`、`np.random`、采样、`shuffle` 或哈希序依赖的迭代（集合仅用于成员测试与 `max`，两者顺序无关）。Qhull 对固定点序确定。因此 prompt 给出的 FAIL 判据（"repeated evaluation of the same input can differ"）**不成立**，故本项判 WARN 而非 FAIL。

**F-2 [高优先] 位点顺序影响取值的三条路径。**

1. `_major_species` 的平局（D-5）：50/50 混合占位位点的元素归类由 dict 插入序决定。影响 `get_anion_sites`、`_shell_neighbors`、`get_na_x_bonds` → 传导至 G 族两个描述符与骨架位点集合。
2. `_shell_neighbors` 的补至 4 分支：`neighbors.sort(key=lambda x: x["distance"])` 是稳定排序，等距邻居保持 `get_sites_in_sphere` 的返回序；`neighbors[:min(4, len(neighbors))]` 于是在等距的不同元素邻居中**按输入序**挑选。在混合阴离子体系上，选到 O 还是 S 改变 `na_x_en_diff` 的取值。
3. `find_interstitial_sites` 的非传递去重（D-6）：保留的位点数与代表点依赖顶点枚举序。

**F-3 [中优先] 浮点累加顺序。**

`site_occupancies_by_symbol` 的 `totals[symbol] = totals.get(symbol, 0.0) + float(occupancy)`、`compute_charge_balance_deviation` 的逐位点累加、`compute_polyhedron_volume` 的锥体体积求和——全部依赖遍历序。数值影响在 1e-15 相对量级，本身不改变排序，但在 `abs(total_occ - 1.0) > 1e-3` 这类**阈值比较**前累加时，理论上可在边界处翻转判定。实践风险低。

**F-4 [PASS 分项] F 族的 `dists.sort()` 无顺序问题。**

排序对象是距离**值**列表而非索引对，等距平局不改变 `dists[0]`/`dists[1]` 的数值。

---

### G. Extensivity Classification（强度量/广延量分类）: FAIL

- **Evidence**: `family_h_symmetry.py:compute_wyckoff_diversity`, `family_h_symmetry.py:compute_space_group_number`, `_base.py:CROSS_GROUP_RULES`, `_base.py:PHYSICAL_FAMILIES`, `family_f_longrange.py:compute_nana_spacing_uniformity`

- **Details**:

**G-1 [BLOCKER] 注册表中不记录 extensivity——三个 family 文件与 `_base.py` 中不存在该字段。**

`PHYSICAL_FAMILIES` 只有 `name` 与 `module` 两个键。`CROSS_GROUP_RULES` 有 `allowed_pairs`、`high_risk_families`、`per_operator_restrictions`，无量纲、无强度/广延标记。`high_risk` 仅以 docstring 文本形式存在，不可被 Stage 3 的约束层消费。

**G-2 [BLOCKER] `compute_wyckoff_diversity` 是条件性广延量，且以裸计数形式输出、无任何归一化。**

对称性识别成功 → 强度量（轨道数，与晶胞倍数无关）；识别失败/P1 → 广延量（= `len(struct)`，随晶胞线性增长）。同一列混装两种性质。函数不返回任何标志位区分二者，`_base.py` 与 family 文件中也无 `len(struct)` 归一化。任何跨结构比较都在未归一化条件下进行。

**G-3 [BLOCKER] `compute_space_group_number` 不是标量量，是名义型标签被当作 float 输出。**

空间群号是**名义（categorical）**编号，1–230 之间的顺序不承载物理序（SG 62 与 SG 63 的物理距离不是 1）。`CROSS_GROUP_RULES["allowed_pairs"]` 含 `("A", "H")`，即允许 A 族（Å / Å³ / 无量纲）与 H 族做 `+ / × / 同量纲比值` 运算。若 `space_group_number` 是 H 族的代表被选中，与任何 A 族量做乘积或比值在量纲上无意义。`per_operator_restrictions` 只限制了 `("A","C")`，未限制含 H 的组合。

**G-4 [BLOCKER] `compute_nana_spacing_uniformity` 名义上无量纲强度量，实际随晶胞含量漂移。**

CV 本应是无量纲强度量。但其输入（全对最小镜像距离集合）随晶胞尺寸改变（D-1），故该量在构造上是强度量、在行为上随晶胞含量变化。这是最容易被跨结构比较误用的一类。

**G-5 逐描述符 intensive/extensive 判定**

- **强度量且行为一致**（5 个）：`na_x_en_diff`、`covalency_index`、`charge_balance_deviation`、`framework_d_electron_weighted`、`partial_occupancy_ratio`。
- **强度量且不变**（2 个）：`coordination_cv`、`volume_cv`（局部性质的跨位点 CV；原胞/惯用胞按多重性等比例包含同一批对称独立位点，CV 不变）。
- **构造上强度量、行为上随晶胞变化**（5 个）：`nana_nana_angle_mean`、`nana_second_neighbor_dist`、`path_tortuosity`、`nana_spacing_uniformity`、`wyckoff_diversity`（条件性）。
- **名义型、非标量**（1 个）：`space_group_number`。

**G-6 [NOT_APPLICABLE] 组合的 extensivity 传播（G.3 子项）。**

`CROSS_GROUP_RULES` 只给出允许的族对，未给出算子级的量纲传播规则，且 F 族**完全不出现在 `allowed_pairs` 中**——无法从本批次文件判定 F 族是否可参与组合、以何算子参与。缺失文件：`descriptors/__init__.py`、`combination.py`。

---

### H. Cross-Family Redundancy（跨族冗余）: WARN

- **Evidence**: `family_f_longrange.py`（4 个函数共用同一 `dists` 构造）, `family_g_electronic.py:compute_na_x_en_diff` vs `compute_covalency_index`, `family_h_symmetry.py:compute_coordination_cv` vs `compute_volume_cv`, `_base.py:PHYSICAL_FAMILIES`

- **Details**:

判 WARN 而非 FAIL 的理由：prompt 的 FAIL 判据是 "a **declared cross-family pair** is an algebraic restatement of a single quantity"。判定"已声明的跨族对"需要注册表与其余 family 文件（A/B/C/D'/E），本批次未嵌入。**族内**冗余则确定存在且严重。

**H-1 [高优先] G 族两个描述符是同一逐键量的单调变换。**

`na_x_en_diff` 逐键量 = Δ；`covalency_index` 逐键量 = `1 − exp(−Δ²/4)`。对全部 9 个阴离子，Δ = χ_X − 0.93 > 0，在此区间上 `1 − exp(−Δ²/4)` 严格单调增。故：

- **单一阴离子体系**：两者互为确定性双射，Pearson/Spearman 恒为 ±1（且两者各自都是常数，见 C-3）。
- **混合阴离子体系**：均值算子与非线性变换不交换，故不严格单调，但秩相关极高。

两者占 G 族 4 个名额中的 2 个，实际提供约 1 个自由度。

**H-2 [高优先] F 族四个描述符全部源自同一个 `dists` 向量。**

四个函数各自独立地重建了同一个量：对每个 Na 位点，到其余 Na 索引的最小镜像距离排序列表。

| 描述符 | 从 `dists` 取什么 |
|---|---|
| `nana_second_neighbor_dist` | `mean_i(dists[1])` |
| `path_tortuosity` | `mean_i(dists[1] / dists[0])` |
| `nana_spacing_uniformity` | 全对距离的 CV |
| `nana_nana_angle_mean` | 用 `dists[0]`/`dists[1]` **选索引**，再用原胞坐标构角（A-4） |

`second_neighbor_dist` 与 `path_tortuosity` 的差别仅是除以 `dists[0]`。若数据集内 `dists[0]`（Na-Na 最近邻距离）的变异远小于 `dists[1]`（在同族结构中通常如此），二者近似只差一个常数因子，秩相关接近 1。族内应只保留一个代表。

**H-3 [高优先] H 族 `coordination_cv` 与 `volume_cv` 源自同一次 Voronoi 镶嵌。**

两者都调用 `VoronoiNN` 对同一批 Na 位点做同一次剖分：前者取面数的 CV，后者取（经 `compute_polyhedron_volume`）元胞体积的 CV。Voronoi 面数与元胞体积在同一结构内强相关（面多通常体积大）。两者的失败模式也同源——同一批位点抛异常。

**H-4 [BLOCKER 级命名问题] F 族的族名"长程关联"与其四个实现不符。**

`PHYSICAL_FAMILIES["F"] = {"name": "长程关联"}`，模块 docstring 写"描述**超越最近邻**的 Na-Na 空间关联"。实际：四个函数中三个只用 `dists[0]` 与 `dists[1]`（第一、第二顺序统计量），第四个（`spacing_uniformity`）用全对距离但受最小镜像截断在半个晶胞对角线以内。**没有任何一个函数计算超出第二近邻的关联**——无径向分布函数、无关联长度、无衰减尺度拟合、无 k 空间量。

这直接影响族代表选择：族标签断言 F 与 B（"Na-Na 网络"，近邻连通性）测量不同的物理对象，而实现上 F 的输入与 B 是同一批 Na-Na 近邻距离。B 族文件本批次未嵌入，故该跨族对判定标 **unverifiable**。

**H-5 [NOT_APPLICABLE] 族分配是否反映物理对象（H.3 子项）。**

`PHYSICAL_FAMILIES` 的定义就是 `family → module` 的映射，即族 = 源文件。这是一个**结构性**观察：族分配在数据结构层面等同于文件分配，不存在独立的"物理对象"字段可供核对。完整判定需要全部 8 个 family 文件与注册表。缺失文件：`descriptors/__init__.py`、`family_a_polyhedron.py`、`family_b_network.py`、`family_c_concentration.py`、`family_d_vacancy_topo.py`、`family_e_framework.py`。

---

## Overall Verdict: FAIL

## Action Items

### 阻断级（必须在任何数值被引用前修复）

1. **`_safe_cv` 补 n<2 闸门**（`_base.py:_safe_cv`）——与 `_safe_std` 对齐，返回 NaN。这一条同时修复 `nana_spacing_uniformity`、`coordination_cv`、`volume_cv` 三个描述符的 0.0 哨兵。**优先级最高，改动最小。**
2. **修正 `compute_covalency_index` 的方向**——二选一：改名为 `ionicity_index` 并改 docstring，或把公式换成 `exp(−Δ²/4)`。必须在文档中记录选了哪一个。
3. **F 族四个描述符全部重写邻居枚举**——改用 `struct.get_neighbors(site, r)` 或 `get_all_neighbors`，把**周期镜像作为独立邻居**纳入，并用返回的镜像坐标构造向量。这是 D 项的根因，不修则 F 族四列全部编码晶胞设定而非物理。
4. **`compute_nana_nana_angle_mean` 的向量必须与距离用同一镜像**（A-4/D-2）。
5. **`compute_path_tortuosity` 改名或重写**——它不是曲折度。若保留当前实现，改名为 `nana_d2_d1_ratio` 并删掉 docstring 中的路径叙述；若要真正的曲折度，需要图上最短路，属于新功能。
6. **`compute_na_x_en_diff` 明确加权口径**——按位点均值（改为两层均值）或按键均值（改 docstring）。二选一并记录。
7. **`compute_charge_balance_deviation`**：`N` 改 −3；表外元素改为**返回 NaN 或计入失败计数**，不得 `continue`；docstring 补全 40 项价态表；记录"是否使用了输入携带的氧化态"作为伴随标志。
8. **`compute_framework_d_electron_weighted`**：从 `d_block` 移除 Ce–Lu（或改名为 `d_f_block_fraction`）；若要保留 "weighted" 之名，须按实际 d 电子数加权。
9. **`compute_coordination_cv` 的 CN 定义**：显式声明用的是 Voronoi 面数，或改用 `CrystalNN`/`MinimumDistanceNN` 得到化学 CN；同时移除逐位点裸 `except`，改为记录成功位点数并在成功数 <2 时返回 NaN。
10. **`compute_polyhedron_volume` 改名**为 `compute_voronoi_cell_volume`，或改为真正的配位多面体凸包体积（`scipy.spatial.ConvexHull` over 壳层阴离子坐标）。
11. **`find_interstitial_sites`**：裸 `except` 改为返回 `None` 或抛出（不得返回 `[]`）；`volume` 字段要么实现要么删除；去重改为等价类（并查集）以消除顺序依赖。
12. **H 族两个 spglib 描述符补失败/降级标志**——至少额外输出一列 `symmetry_detection_ok`，使 P1 回落可被下游识别。
13. **注册表补三列元数据**：`dimension`、`intensive|extensive|nominal`、`cell_setting_invariant`。Stage 3 的组合约束层与 W3-5 增量有效性闸门都消费它，目前它不存在。

### 高优先（影响解释与族代表选择）

14. `get_na_sites` 的 docstring 与实现对齐（多数派 vs 1e-6），并决定占位是否参与加权。
15. `_anion_cutoff` 的 `max` 语义改为**逐邻居按元素**取截断，消除"体系标签进入测量规则"。
16. `_shell_neighbors` 的 `+0.70` 与"补至 4"补出处或改为有物理依据的判据（如 BVSE 截断、Voronoi 面立体角阈值）；至少加一次 0.6/0.7/0.8 的排序稳健性扫描。
17. `symprec` 提升为可配置参数并做 0.01/0.05/0.1 三点敏感性检查。
18. `partial_occupancy_ratio` 的 1e-3 阈值提高到 5e-3 或按 CIF 报数精度设定；`site_occupancies_by_symbol` 增加保留氧化态的变体以使混合价可见。
19. `_major_species` 的平局改为确定性判据（如按元素符号字典序），消除文件书写顺序依赖。
20. 族内冗余去重：G 族在 `na_x_en_diff` / `covalency_index` 中只保留一个；F 族在 `second_neighbor_dist` / `path_tortuosity` 中只保留一个。
21. F 族族名"长程关联"与实现不符——要么补一个真正的长程量（RDF 关联长度、Na-Na 网络谱半径等），要么改族名。

### 中优先

22. `_effective_anion_radius` 的"加权"改为真实的化学计量加权，或删掉 docstring 中的"加权"。
23. `ANION_EFFECTIVE_RADII_A["H"]` 补出处或删除；`"N": None` 的注释改为"本项目未采用"（Shannon 表列有 N³⁻）。
24. `compute_partial_occupancy_ratio` 删除死 `else` 分支。
25. `find_interstitial_sites` 的 `in_cell` 上下界改为对称。
26. `get_na_x_bonds` 的 `max_dist=4.0` 与 `_anion_cutoff` 两套截断合并为一套。

## Claim Impact

本 prompt 未附具体 claim 文本，以下按 profile 的隐含主张与本批次描述符可支撑的头条断言逐条判定：

- **Claim 1（profile 隐含主张：13 个描述符各自计算其名称与 docstring 所声明的量，且在流水线将遇到的输入变化范围内取值良定义）**: **unsupported** ——13 个中 8 个存在名称/文档与实现的定义性不符（A-1 至 A-8），5 个在退化或常见输入上返回有限的错误值（B-1 至 B-3）。
- **Claim 2（F 族"长程关联"测量超越最近邻的 Na-Na 空间关联）**: **unsupported** ——四个实现全部止于第二顺序统计量（H-4）。
- **Claim 3（G 族描述符提供不依赖 DFT 的电子结构代理信息）**: **unsupported** ——`na_x_en_diff` 与 `covalency_index` 在单一阴离子体系上是常数、跨体系时是体系标签的确定性函数（C-3）；`covalency_index` 方向反号（A-1）；`charge_balance_deviation` 在表外元素上向平衡方向偏（C-4）。
- **Claim 4（H 族对称性描述符可作为结构复杂性代理）**: **needs_qualifier** ——`partial_occupancy_ratio` 实现与文档基本一致（除死分支与混合价盲区），可用；但 `space_group_number` 是名义型标签不可参与算术，`wyckoff_diversity` 在 P1 回落时退化为晶胞大小计数。限定条件：须附 `symmetry_detection_ok` 标志，且 `space_group_number` 不得进入任何组合运算。
- **Claim 5（任何以 F/G/H 族描述符为基础、跨不同晶胞设定的数据集计算出的相关系数，反映的是物理而非数据来源）**: **unsupported** ——F 族四列与 `wyckoff_diversity` 的取值随原胞/惯用胞/超胞改变（D-1 至 D-3），`charge_balance_deviation` 随源文件是否标注氧化态改变（D-4）。

---

## 描述符登记表

> `dimension` 列给出实现实际产出的量纲（非 docstring 声称的）。`cell-setting invariant?` 列的 "conditional" 指同一列内不同条目性质不同。`unverifiable` 表示判定所需文件未在本批次嵌入。

| descriptor | family (registry) | claimed quantity | implemented quantity | agree? | dimension | intensive/extensive | cell-setting invariant? | NaN paths |
|---|---|---|---|---|---|---|---|---|
| `compute_nana_nana_angle_mean` | F (长程关联) | 每个 Na 位点最近两个 Na 邻居张成的三体角，跨位点均值 | 用最小镜像距离**选出**两个邻居索引，再用**原胞内坐标**构向量求夹角，跨位点均值 | **no** (A-4) | 度 (°) | intensive（构造上）；行为随晶胞变 | **no** — 依赖晶胞设定与坐标归约约定 (D-1/D-2) | `len(na)<3`；`angles` 空 |
| `compute_nana_second_neighbor_dist` | F (长程关联) | 每个 Na 的第二近邻 Na 距离，跨位点均值 | 到其余**不同索引** Na 的最小镜像距离的第二顺序统计量 `dists[1]`；排除自身周期镜像；简并时 = `dists[0]` | **no** (A-5) | Å | intensive（构造上）；行为随晶胞变 | **no** (D-1) | `len(na)<3`；`second_dists` 空 |
| `compute_path_tortuosity` | F (长程关联) | 迁移路径曲折度（直线距离/最短路径距离） | `mean_i(dists[1]/dists[0])`；无任何路径搜索 | **no** (A-3) | 无量纲 | intensive（构造上）；行为随晶胞变 | **no** (D-1) | `len(na)<2`；`ratios` 空；**哨兵 1.0**（简并，B-3） |
| `compute_nana_spacing_uniformity` | F (长程关联) | Na-Na 间距变异系数 | **全对** Na-Na 最小镜像距离的 CV（ddof=0） | partial (A-9) | 无量纲 | intensive（构造上）；随晶胞含量单调漂移 (G-4) | **no** (D-1) | `len(na)<2`；均值≈0；**哨兵 0.0**（n=1 对，B-1） |
| `compute_na_x_en_diff` | G (电子代理) | 每个 Na 位点第一壳层阴离子的 χ(X)−χ(Na)，跨**位点**均值 | 跨所有 Na 位点、所有壳层键的**扁平**均值（按键加权） | **no** (A-2) | 无量纲（Pauling 单位） | **intensive** | **yes** | 无 Na / 无阴离子；壳层全空；**单一阴离子体系恒为常数** (C-3) |
| `compute_charge_balance_deviation` | G (电子代理) | 电荷平衡偏差；Na +1、阴离子 −2/−1 | `\|Σ occ·ox\| / Σ \|occ·ox\|`，用输入氧化态否则 40 项固定价态表；表外元素**静默跳过**；N 记 −1 | **no** (A-14/C-4) | 无量纲 | **intensive** | **yes**（对超胞不变）；但依赖输入是否标注氧化态 (D-4) | `total_absolute_charge<1e-12`；**表外元素致偏小有限值** (C-4) |
| `compute_covalency_index` | G (电子代理) | Pauling 共价性指数，值越大共价性越强 | `mean_bonds(1 − exp(−Δχ²/4))` = Pauling **离子性**分数 | **no** (A-1，方向反号) | 无量纲 | **intensive** | **yes** | 同 `na_x_en_diff`；**单一阴离子体系恒为常数** (C-3) |
| `compute_framework_d_electron_weighted` | G (电子代理) | 骨架阳离子中含 d 电子元素的占位权重占比 | 骨架位点中属于 `d_block`（含整个镧系）的占位数 / 骨架总占位数；**二值权重非 d 电子数** | **no** (A-8) | 无量纲 | **intensive** | **yes** | 无骨架位点；`total_occ<1e-12`；合法 0.0（无 TM） |
| `compute_space_group_number` | H (对称性破缺) | 空间群序号 | `SpacegroupAnalyzer(symprec=0.01).get_space_group_number()` | yes（数值层面） | 名义型标签（非标量） | **nominal** — 既非 intensive 也非 extensive (G-3) | **yes**（原理上）；分数占位时降至 1 | 裸 `except`；**哨兵 1.0**（P1 回落，C-6） |
| `compute_wyckoff_diversity` | H (对称性破缺) | 不等价 Wyckoff 位置数量 | `len(symm_struct.equivalent_indices)` = 对称等价**轨道**数 | partial (A-13) | 计数（无量纲） | **conditional**：识别成功→intensive；P1 回落→**extensive (= len(struct))** (G-2) | **conditional** (D-3) | 裸 `except`；**哨兵 = len(struct)**（P1 回落，C-6） |
| `compute_partial_occupancy_ratio` | H (对称性破缺) | 占位≠1 或多元素位点占总位点数的比例 | 同左（按元素符号聚合，阈值 1e-3）；混合价不可见；`else` 分支为死代码 | **yes**（带 B-5/B-6 限定） | 无量纲 | **intensive** | **yes** | `len(struct)==0` |
| `compute_coordination_cv` | H (对称性破缺) | 各 Na 位点配位数的 CV | 各 Na 位点 **Voronoi 面数**（`VoronoiNN(tol=0).get_cn`）的 CV；逐位点异常静默跳过 | **no** (A-6/B-2) | 无量纲 | **intensive** | **yes** | `len(na)<2`；`cn_list` 空；`ImportError`；**哨兵 0.0**（成功位点 n=1，B-1） |
| `compute_volume_cv` | H (对称性破缺) | 各 Na 位点 Voronoi 多面体体积的 CV | 各 Na 位点 **Voronoi 元胞**体积（锥体体积求和）的 CV | **no** (A-7) | 无量纲 | **intensive** | **yes** | `len(na)<2`；`volumes` 空；**哨兵 0.0**（n=1，B-1） |

### 附：`_base.py` 共享辅助函数（非描述符，但被上表消费）

| helper | 声称行为 | 实际行为 | agree? | 影响面 |
|---|---|---|---|---|
| `get_na_sites` | 主要物种为 Na 的位点 | Na 占位 > 1e-6 的位点；占位不参与加权 | **no** (A-10) | F 族 4 个 + H 族 2 个 + 骨架集合 |
| `get_anion_sites` | 阴离子位点 | 含**任一** `ANION_ELEMENTS` 元素的位点（与 `_major_species` 判据不一致） | partial | `get_framework_sites` → G 族 |
| `get_framework_sites` | 非 Na 非阴离子位点 | 同左；混合占位位点被双重排除 | yes（但口径≠"阳离子"） | `framework_d_electron_weighted` |
| `_major_species` | 占位最多的元素 | 同左；**平局按 dict 插入序** | partial (D-5) | `_shell_neighbors`、`get_na_x_bonds`、`get_anion_sites` |
| `_shell_neighbors` | 第一配位壳层 Na-X 近邻 | 最短键长 +0.70 Å 内的阴离子，不足 4 补至 4；截断取全结构阴离子的 **max** | partial (E-2) | G 族 2 个 |
| `_effective_anion_radius` | 阴离子有效半径**加权**平均 | 元素符号**集合**上的等权算术平均；含 N 返回 None | **no** (A-11) | 本批次未消费 |
| `_effective_na_radius` | 按 CN 查 Shannon 半径 | 同左；未列入 CN **静默回落 CN=6** | partial | 本批次未消费；与 A-6 联动 |
| `find_interstitial_sites` | Voronoi 间隙位点，含区域体积 | 同左但 **`volume` 恒 0.0**；裸 `except` 返回 `[]`；去重非传递 | **no** (A-12/C-2/D-6) | 本批次未消费 |
| `compute_polyhedron_volume` | 配位多面体体积 | Voronoi **元胞**体积 | **no** (A-7) | `volume_cv` |
| `_safe_cv` | 变异系数，空列表或零均值返回 NaN | 同左；**缺 n<2 闸门**，单元素返回 0.0 | **no** (B-1) | `spacing_uniformity`、`coordination_cv`、`volume_cv` |
| `_safe_std` | 标准差，空列表返回 NaN | 同左；有 n<2 闸门（与 `_safe_cv` 不一致） | yes | — |
| `_safe_mean` | 均值，空列表返回 NaN | 同左 | yes | — |

### 缺失文件汇总（判定被标 `unverifiable` / `NOT_APPLICABLE` 的依据）

| 缺失文件 | 阻挡的判定 |
|---|---|
| `descriptors/__init__.py`（注册表） | A.1 registry metadata 声称量；G.1 extensivity 是否被记录；H.3 族分配依据 |
| `featurizer.py` / CIF 读入层 | D.3 解析器占位容差对位点表的影响 |
| `combination.py` | G.3 组合的 extensivity 传播；F 族是否参与组合 |
| `family_a/b/c/d_prime/e_*.py` | H.1 跨族冗余对（尤其 F↔B、H↔A 的多面体体积） |
