# Experiment Audit Report

**Date**: 2026-08-09
**Auditor**: Claude Web (manual bridge, read-only cross-model)
**Project**: automat-naconductor
**Audit Skill**: experiment-audit
**Checklist**: descriptor-impl (A-G 七项描述符实现正确性专项审计)
**Compact Level**: 0 (全文嵌入)
**Output Basename**: EXPERIMENT_AUDIT_run03_3b (不覆盖既有 EXPERIMENT_AUDIT.* 产物)
**Reviewer Model**: claude-web
**Reviewer Backend**: manual-bridge

## Overall Verdict: FAIL

七项中 **A / B / D / E / G 五项 FAIL，C / F 两项 WARN**。零项 PASS。

判定不依赖任何单一发现：即便撤销争议最大的条目（如 F-2 的 N³⁻ 半径存疑），A-3（分子分母物理对象不匹配）、A-4（永不返回 3D）、B-1（三个广延量）、E-1（缺 PBC，可执行反例）、G-1/G-2（零单元测试 + 独立性不成立）中的任意两条都足以单独触发 FAIL。

## Integrity Status: fail

## Checks

### A. 公式实现正确性 (Formula Implementation Correctness): FAIL

**Evidence**: `_base.py:122-133`（docstring 125 vs 代码 130）；`_base.py:260-277`（docstring 261 vs 代码 277）；`_base.py:295` vs `_base.py:340`；`_base.py:386-390`；`family_c_concentration.py:12-21`；`family_e_framework.py:45-60, 81-88`；`family_d_vacancy_topo.py:83-131`；`family_d_vacancy_topo.py:19-21`

**Details**:

- **A-1 (BLOCKER)** `get_na_sites` 的判据与 docstring 直接矛盾。`_base.py:125` 声明 "Na 位点 = **主要物种**为 Na 的位点"，但 `_base.py:130` 实际判据是 `na_occ > 1e-6`——**任意痕量占位**。一个 Zr₀.₉Na₀.₁ 混占位点在代码里是 Na 位点，在 docstring 里不是。同文件 `_major_species`（`_base.py:153-159`）实现的才是多数派判据，且被 `get_na_x_bonds:191`、`_shell_neighbors:232` 用来判阴离子。**同一模块内两套互不相容的位点归类规则并存**，且 `get_framework_sites`（`_base.py:146-150`）以 `get_na_sites ∪ get_anion_sites` 的补集定义骨架——任何 Na/骨架混占位点会同时被判为 Na 位点并被踢出骨架集合，NASICON 的分数占位结构正是高发区。

- **A-2 (BLOCKER)** `_effective_anion_radius` 声称加权平均，实为无权算术平均。`_base.py:261` 写 "加权平均值"，`_base.py:277` 是 `sum(r) / len(values)`——对 **结构全局出现过的阴离子种类集合**取等权平均，与丰度、占位、配位壳层组成全部无关。含 O 与 S 的氧硫化物一律得 1.62 Å，无论该位点实际被谁配位。这不是"简化"，是 docstring 与实现的定义级不符。

- **A-3 (BLOCKER)** `compute_framework_bond_rigidity` 分子分母是两个不同的物理对象。`family_e_framework.py:45` 取的 `shell` 是骨架阳离子 M 的阴离子近邻，`:59` 的 `mean_dist` 因此是 **M–X 键长**；`:60` 的分母 `2.0 * anion_r` 是 **X–X 阴离子接触距离**。docstring（`:82-85`）把分子写成 "X-X 键长" 并声称 "值接近 1.0 说明骨架刚性高"。代入 Shannon 半径的代数恒等式立即可见问题：若 d(M–X) ≈ r_M + r_X，则 ratio = (r_M + r_X) / (2 r_X) = **0.5 + r_M/(2 r_X)**。实测典型值：P–O 0.550、Si–O 0.579、Zr–O 0.739、In–Cl 0.704。**判据"接近 1.0"在整个真实材料域不可达**，取值被压在 0.55–0.74。该量在代数上等价于 r_M/r_X 的单调函数，即一个**阳离子/阴离子半径比的组分描述符**，几乎不含结构信息。同一函数 `:52-55` 计算了 `fw_sym`（骨架阳离子符号）**却从未使用**——这正是原设计意图（理想键长应为 r_M + r_X）被丢弃的物证。

- **A-4 (BLOCKER)** `compute_interstitial_network_dim` 算的不是维度。`family_d_vacancy_topo.py:86-87` 声称 "用 DFS 判断最大连通分量的维度"。DFS 只返回连通分量的**基数**，与拓扑维度无关。`:125-131` 把 `max_comp_size/n` 映射到 {0.0, 1.0, 2.0}，**永不返回 3.0**——一个完全贯通的三维通道网络（ratio = 1.0）与一个二维层状网络得到同一个值 2.0。这是 D′ 族最重要描述符的定义级失效，且 docstring `:130` 的注释 "2D/3D 依赖空间覆盖" 承认了该分支缺失却未实现。此外 `:90-91` 在 `len(sites) < 2` 时返回 **0.0 而非 NaN**，把"无间隙位点/未定义"与"真实 0D"折叠成同一数值。

- **A-5 (HIGH)** `compute_na_concentration` 计的是位点数不是原子数。`family_c_concentration.py:13,15` 明确写 "Na **原子数** / 晶胞总原子数"、"这里是原子数比率"，`:21` 实际是 `len(na_indices)/len(struct)`——分子是位点计数（占位权重被 A-1 的 1e-6 阈值抹平，Na₀.₅ 位点计为 1），分母是位点数。同文件 `compute_na_occupancy_sum`（`:24-39`）证明作者知道正确的占位加权写法却未用在这里。

- **A-6 (HIGH)** `_get_interstitial_data` 的 "带缓存效果" 是假声明。`family_d_vacancy_topo.py:20-21` 直接透传 `find_interstitial_sites`，无任何缓存。D′ 族四个非平凡描述符各调一次 → **同一结构上 27N 点的 Voronoi 剖分被重复执行 4 次**。不影响数值（确定性），但 docstring 陈述为假。

- **A-7 (MEDIUM)** `find_interstitial_sites` 的 `volume` 字段永远是 0.0。`_base.py:295` 承诺 "volume 为对应 Voronoi 区域体积 (Å³)"，`_base.py:340` 硬编码 `"volume": 0.0`。当前无下游消费者，但任何未来使用者会得到静默的 0。

- **A-8 (MEDIUM)** `_safe_std` 的 docstring 与守卫不一致，且 ddof 全程未声明。`_base.py:387` 只承诺 "空列表返回 NaN"，`:388` 实际在 `len < 2` 时也返回 NaN（实测 `_safe_std([2.5]) = nan`）。三个聚合函数均用 `ddof=0`（`:390, :400`）与 `family_e_framework.py:64`，但**没有一处 docstring 声明总体标准差 vs 样本标准差**——清单 A4 要求的"ddof 与 docstring 一致"因 docstring 未声明而无法满足。`family_e_framework.py:64` 还就地重写了一遍 CV，绕过了 `_safe_cv` 的零均值守卫（`_base.py:398`）。

### B. 物理意义合理性 (Physical Meaning Validity): FAIL

> 清单 B 仅定义了 WARN 门槛；此处显式上调，理由见 B-1/B-2，二者不是"未注明的简化"而是物理对象错配与量纲性质错误。

**Evidence**: `family_e_framework.py:57-60, 82-85`；`family_c_concentration.py:24-45`；`family_d_vacancy_topo.py:24-30`；`_base.py:18, 45-46`；`_base.py:244-246`；`_base.py:362-366`；`family_e_framework.py:46, 68-70`

**Details**:

- **B-1 (BLOCKER)** 三个描述符是广延量，随晶胞设定线性变化。用 scipy 复现 `find_interstitial_sites` 并在同一材料的 1×1×1 与 2×2×2 晶胞上实测：NaCl 1×1×1: atoms=8, interstitial_count=8；NaCl 2×2×2: atoms=64, interstitial_count=64。`compute_interstitial_count`（`family_d:24-30`）严格 ×8。`compute_na_site_count`（`family_c:42-45`）与 `compute_na_occupancy_sum`（`family_c:24-39`）同理。CIF 的晶胞设定（原胞 vs 常规胞 vs Z 值约定）在跨数据库汇编的数据集中并不统一，**这三个描述符测的是"这个 CIF 用了多大的胞"，而不是材料性质**。而胞大小与体系（NASICON 大胞 / 硫化物中等 / 卤化物小胞）强相关——它们是结构化的体系代理。

- **B-2 (BLOCKER)** `compute_framework_bond_rigidity` 的物理判据不可达且已退化为组分量。见 A-3。`:57` 的注释 "简化: 用阴离子半径的 2 倍作为理想 X-X 距离" **确实注明了简化**（清单 B3 的形式要求满足），但注明的对象与 `:59` 计算的对象不是同一个量，因此注明本身不构成免责。

- **B-3 (HIGH)** H 被无条件列为阴离子。`_base.py:18` 把 "H" 放进 `ANION_ELEMENTS`，`_base.py:46` 赋 r = 1.40 Å（与 O²⁻ 完全相同，可疑）。在硼氢化物类 Na 超离子导体（Na₂B₁₂H₁₂、NaCB₁₁H₁₂）中把 H 当阴离子尚可辩护；但在**水合物/氢氧化物**中 H 是质子（r ≈ 0），O–H ≈ 0.98 Å 会被 `_shell_neighbors` 当作骨架阳离子的第一壳层阴离子近邻收入，直接污染 `bond_ratios` 与 `poly_distortions`。docstring 无任何关于该假设的说明。

- **B-4 (HIGH)** `_shell_neighbors` 的"补至 4"会凭空制造键。`_base.py:245-246`：当 +0.70 Å 窗口内不足 4 个时，直接取 `neighbors[:4]`，**不再受窗口约束**。一个真实二配位骨架阳离子会被补两个任意远（至截断 3.2–4.35 Å）的阴离子，`mean_dist` 被抬高、`poly_distortions` 的 CV 被人为膨胀。该规则原本是为 Na 多面体写的（docstring `:213` 仍写 "Na 位点的第一配位壳层 **Na-X**"），却在 E 族被复用到骨架阳离子上，函数 docstring 从未更新。

- **B-5 (MEDIUM)** `compute_framework_na_distance_stability` 测的是晶胞尺度而非局域环境。`family_e_framework.py:68-70` 对**每个骨架位点 × 每个 Na 位点**的全配对距离取 CV，包含大量跨半个晶胞的无相互作用配对。该 CV 主要由晶胞几何决定，"Na 运动势能面平坦度"（`:104-105`）的物理解释无依据。附带耦合缺陷：`:46` 的 `if not shell: continue` 发生在 Na 距离循环之前，**无阴离子近邻的骨架位点连带被排除出 Na 距离统计**，这一耦合未在任何 docstring 中说明。

- **B-6 (MEDIUM)** `compute_framework_sharing_topology` 的分母不是"阴离子总数"。`family_e_framework.py:136` 除以 `len(anion_sharing)`——只统计**至少被一个骨架阳离子配位过**的阴离子，未配位阴离子被排除，比例系统性偏高。另有一个晶胞设定相关的过计数路径：`n["index"]`（`:129`）是原胞内原子索引，若同一阳离子在截断内看到同一阴离子位点的两个周期镜像，计数 +2，会被 `:135` 的 `v >= 2` 误判为"被两个阳离子共享"。在轴长小于约 2×d(M–X) 的原胞（简单结构的原胞设定）中可触发。

- **B-7 (MEDIUM)** `compute_polyhedron_volume` 混淆了两个体积。`_base.py:363-365` 说"配位多面体体积"，实际累加 `VoronoiNN` 的分面棱锥体积（`:372-373`），得到的是 **Voronoi 元胞体积**——它由全空间镶嵌决定，与由阴离子顶点张成的配位多面体体积是不同的量（前者恒大于后者）。

- **B-8 (PASS 项)** `compute_bvse_barrier_estimate`（`family_d:134-139`）的 NaN 降级在函数 docstring 与模块 docstring（`family_d:5`）中均明确标注——清单 B4 在此项满足。但 `compute_framework_bond_rigidity` 对含 N 结构的 NaN 降级（经 `_effective_anion_radius` 返回 None → `:58` 条件不成立 → 空列表 → NaN）**未在任何描述符级 docstring 中说明**，只在辅助函数 `_base.py:263` 里提了一句。

### C. 单位一致性 (Unit Consistency): WARN

**Evidence**: `_base.py:20, 37, 200-207, 244, 282, 295, 352`；`family_d:68, 95`；`family_e:60`

**Details**:

**亮点（真实通过项）**:
1. 所有距离常量确为 Å 且与 Shannon 半径同尺度：`_anion_cutoff` 3.20–4.35（`_base.py:202-205`）、`max_dist=4.0`（`_base.py:169`）、`+0.70`（`_base.py:244`）、`min_dist_from_atom=1.5`（`_base.py:282`）、`access_threshold=3.0`（`family_d:68`，带 `# Å` 注释）、`cutoff=3.5`（`family_d:95`，带 `# Å` 注释）。
2. `find_interstitial_sites` 返回笛卡尔 Å（`_base.py:295`），下游 `family_d:48, 73` 均先经 `get_fractional_coords` 再交给 `get_distance_and_image`，未出现分数坐标与笛卡尔坐标混用。
3. `bond_ratios`（`family_e:60`）Å/Å、`compute_interstitial_channel_access`（`family_d:80`）计数/计数、`compute_na_concentration`（`family_c:21`）计数/计数——量纲上确为无量纲。
4. 体积口径（`_base.py:295` Å³、`:363` Å³）内部自洽。

**弊端**:
1. **(MEDIUM)** 去重阈值 `0.5`（`_base.py:352`）无单位注释，是本文件唯一一个既无 `# Å` 注释也未在 docstring 出现的裸距离常量。它来自 `get_distance_and_image` 的返回值故确为 Å，但对读者不可自证。
2. **(MEDIUM)** "无量纲"不等于"可跨材料比较"。`bond_ratios` 虽是 Å/Å，但分子分母来自两类不同的键（A-3），无量纲性掩盖了物理对象错配——这是清单 C 的形式检查会漏、而 A/B 必须捕获的情形。
3. **(LOW)** `compute_na_concentration` 的名称与量纲不符。"concentration" 在固态离子学中默认是体积浓度（cm⁻³ 或 Å⁻³），此处是位点分数。docstring `:15` 已注明"不是体积浓度"，故只记 LOW。

单位本身未发现混用，故不触发清单 C 的 FAIL 条件；两条 MEDIUM 使其停在 WARN。

### D. 边界情况与数值稳定性 (Edge Cases & Numerical Stability): FAIL

**Evidence**: `family_d:90-91`；`_base.py:393-400`；`family_e:64`；`family_d:126-131`；`_base.py:244, 328`；`_base.py:130` vs `:139-141`；`_base.py:320-322, 375-376`；`_base.py:297-298, 320-322`

**Details**:

- **D-1 (BLOCKER)** 未定义与真实取值折叠。`family_d:90-91`：`len(sites) < 2` 返回 **0.0**。清单 D1 明确要求空/退化输入返回 NaN。这里 "Voronoi 找不到间隙" 与 "间隙网络确实是 0D" 在下游不可区分，且 0.0 会正常进入 Spearman 与 Ridge，**制造一个假的有限值**——按 README "全 NaN 描述符会失败退出"的契约，本应触发的失败被这条路径掩盖。

- **D-2 (BLOCKER)** `_safe_cv` 在单元素输入上返回 0.0。实测 `_safe_cv([2.5]) = 0.0`。`_base.py:394-395` 只守卫空列表，不守卫 `len < 2`；而同文件 `_safe_std`（`:388`）守卫了 `len < 2`。于是 **只有一个骨架-Na 配对的结构会被报告为"骨架-Na 间距完美均匀"（CV=0，即 `compute_framework_na_distance_stability` 的最优值）**，这是从单个样本推出的零方差，方向上把退化结构推向排名顶端。

- **D-3 (HIGH)** 分类阈值在小 n 上系统性误分。`family_d:126-129` 的 0.3 / 0.6 硬阈值作用在 `max_comp_size/n` 上。间隙位点数常为个位数，可达 ratio 值高度量化：n=3 时只有 {0.333, 0.667, 1.0} → 只能取到 1.0 与 2.0，**0D 分支在 n=3 时不可达**；n=5 时 {0.2, 0.4, 0.6, 0.8, 1.0}，其中 0.6 正好落在边界。验证了浮点行为：`3/10` 与字面量 `0.3` 是同一个 double，故 `ratio < 0.3` 为 False，边界值确定性地落入**上一档**——行为可复现但档位边界本身无任何依据。

- **D-4 (HIGH)** 浮点比较普遍不带容差。`_base.py:244`（`<= first + 0.70`）、`family_d:77`（`<= access_threshold`）、`family_d:103`（`<= cutoff`）均为裸 `<=`。清单 D5 要求用容差。`_base.py:328` 的 `in_cell` 是唯一使用容差的地方，且上下界不对称（`-1e-6` 放宽、`1.0 - 1e-6` 收紧）——净效果是宽度仍为 1.0 的半开区间，此处**判定为可接受**，但它反衬出其余比较全无容差。

- **D-5 (MEDIUM)** 阈值口径在模块内不统一。`get_na_sites` 用 `1e-6` 占位阈值（`_base.py:130`），`get_anion_sites`（`_base.py:139-141`）**完全无阈值**——只要 species 字典里出现该符号即算阴离子位点，含 1e-9 占位的痕量 S 位点会被判为阴离子并从骨架集合中移除。

- **D-6 (MEDIUM)** 宽 `except Exception` 吞掉真实错误。`_base.py:320-322`（Voronoi）与 `_base.py:375-376`（VoronoiNN）都是裸 `except Exception` → 返回 `[]` / NaN。Qhull 的退化输入失败与 `MemoryError`、导入失败、pymatgen API 变更被折叠成同一个静默降级路径。清单 D6 只要求"被捕获"，形式满足；但无日志、无失败原因记录，与 `program.md` "记录该次失败原因并停止该候选" 的纪律相抵触。

- **D-7 (PASS 项，逐条确认)**:
  - 空结构：`_base.py:297-298` 返回 `[]`；`family_c:19-20`、`family_d:41-42, 65-66`、`family_e:29-36, 120-121, 131-132` 均返回 NaN，**未发现任何 IndexError / ZeroDivisionError 崩溃路径**。这是清单 D 的 FAIL 触发条件（"边界情况会导致崩溃"）——该条**未触发**；本项 FAIL 由 D-1/D-2 触发。
  - 部分占位累加：`site_occupancies_by_symbol`（`_base.py:114-120`）正确按元素符号累加（Fe²⁺/Fe³⁺ 合并），实现无误；问题在下游消费（A-1、A-5）。
  - 含 N 降级：`_effective_anion_radius`（`_base.py:270-275`）在 missing 非空时返回 None，行为与 `:263` 一致。但注意这是**全有或全无**：结构中只要出现 N，即使 99% 的骨架由 O 配位，全部 `bond_ratios` 一并丢弃。

### E. 周期性边界条件 (Periodic Boundary Conditions): FAIL

**Evidence**: `family_d_vacancy_topo.py:99-104`；`_base.py:305-315, 333`；`_base.py:343-356`；`_base.py:180-182, 227-229`；`family_e:69`

**Details**:

- **E-1 (BLOCKER)** `compute_interstitial_network_dim` 用裸欧氏距离建邻接表。`family_d:101`：`d = float(np.linalg.norm(coords[i] - coords[j]))`。`coords` 全部位于原胞内（由 `_base.py:328` 的 in-cell 过滤保证），因此**所有跨晶胞边界的连接被 100% 漏掉**。同文件 `:48` 与 `:74` 都正确使用了 `lattice.get_distance_and_image`——这不是"整体未考虑 PBC"，而是**同一模块内三处距离计算里恰好最关键的那一处漏了**。

  量化（随机点在立方胞内实测，3.5 Å 截断下漏掉的配对比例）：

  | 胞边长 | 漏掉的连接 |
  |---|---|
  | 7.0 Å | **46.9 %** |
  | 9.0 Å | 37.4 % |
  | 12.0 Å | 30.4 % |
  | 22.0 Å | 19.0 % |

  方向确定：连接数只会被**低估**，故网络维度只会被**低估**。且低估幅度随胞变小而增大——硫化物/卤化物的小胞受损最重，NASICON 大胞受损最轻，**误差本身沿体系轴分层**，会污染去混杂后的残差信号。

  可执行反例（复现该函数并对比 MIC 版本，40 个随机低对称胞）：
  ```
  L=13.79 A  n_interstitial= 95  as-coded=1.0 (ratio 0.537)   with-PBC=2.0 (ratio 1.000)
  L=12.87 A  n_interstitial= 73  as-coded=1.0 (ratio 0.589)   with-PBC=2.0 (ratio 1.000)
  -> 40 个随机胞中 2 个的维度标签被翻转
  ```
  即真实完全贯通（ratio=1.000）的网络被报告为"链状 1D"。翻转率在随机胞上约 5%，但注意这是**在已经封顶为 2.0 的量表上测的**——真实的 3D↔2D 混淆无法被这个量表表达（A-4）。

- **E-2 (PASS)** 周期性影像生成正确。`_base.py:305-315` 生成完整的 ±1 共 26 个平移影像 + 原胞 = 27N 点，Voronoi 在该点集上剖分。`_base.py:333` 的最近原子距离检查也是对 `all_points_arr`（含影像）做的，注释 `:332` 明确说明了这一点——这一段是本次审计中处理得最干净的部分。

- **E-3 (PASS，附一条 LOW)** 去重考虑周期等价。`_base.py:349-352` 用 `get_distance_and_image` + 0.5 Å 阈值，方法正确。LOW：`:350-351` 在内层循环里重复调用 `get_fractional_coords`，且是贪心去重（只与已接受的 unique 比较），对近似等距的三元组不满足传递性——结果依赖 `vor.vertices` 的枚举顺序。Qhull 顺序确定，故不影响可复现性，只影响正确性边缘情形。

- **E-4 (PASS)** `get_sites_in_sphere(include_image=True)`（`_base.py:180-182`、`:227-229`）按 pymatgen 语义返回周期镜像近邻，PBC 正确；`family_e:69` 的 `struct.get_distance(fw_idx, na_idx)` 在 `jimage=None` 下走最近镜像约定，PBC 正确。

### F. 文献定义一致性 (Literature Definition Consistency): WARN

**Evidence**: `_base.py:24-32`；`_base.py:38-48`（含 `:46` H、`:47` N）；`_base.py:53-64`；`_base.py:217-218, 244-246`；`family_d:1-6, 134-139`；`_base.py:200-207, 282, 352`；`family_d:68, 95`

**Details**:

- **F-1 (PASS)** Na⁺ Shannon 半径逐项核对无误。`_base.py:25-31`：CN=4→0.99、5→1.00、6→1.02、7→1.12、8→1.18、9→1.24、12→1.39——与 Shannon (1976) 有效离子半径表七项**全部一致**。

- **F-2 (PASS/WARN 混合)** 阴离子半径基本一致，两项存疑。`_base.py:39-45`：O 1.40、S 1.84、Se 1.98、F 1.33、Cl 1.81、Br 1.96、I 2.20——与 Shannon CN=6 值一致。两处需要限定：
  - **`:46` H = 1.40** (WARN)：与 O²⁻ 数值完全相同。氢化物 H⁻ 的常用值在 1.30–1.50 Å 区间且强烈依赖化合物，此处既无来源注释也无 CN 标注；结合 B-3，H 在 `ANION_ELEMENTS` 中的存在本身就是未论证的建模决定。
  - **`:47` N = None** (WARN)：注释 `:36` 与 docstring `:263` 均称 "N 无经典值"。这一说法需要核对——Shannon 表中通常给出 N³⁻（CN=4）≈ 1.46 Å。若该值存在，则含 N 结构的**全有或全无 NaN 降级**（D-7）是不必要的数据损失。本条标为需外部核对而非直接判错。

- **F-3 (PASS)** Pauling 电负性逐项无误。`_base.py:54-63`：Na 0.93、O 3.44、S 2.58、F 3.98、Cl 3.16、Br 2.96、I 2.66、Se 2.55、N 3.04、H 2.20——十项与标准 Pauling 表一致。**限定**：该表只覆盖 Na 与九种阴离子，**不含任何骨架阳离子**（Zr/P/Si/Ge/Sn/Sb/Al/Ti/Y/La…），G 族若需要 Δχ(阳离子–阴离子) 将全部落空。G 族不在本次送审范围，此处仅记录。

- **F-4 (WARN，清单明确点名项)** `+0.70 Å` 规则无文献依据。`_base.py:217-218` 注明来源为 "`part1.py` 的简化规则"——**来源已注明，但注明的是本仓库内的另一个脚本，不是文献**。`part1.py` 未在本次送审文件内，规则的原始依据不可追溯。配套的 "补至 4" 分支（`:245-246`）连内部来源都没有。同类无来源常数还有：`min_dist_from_atom=1.5`（`:282`）、去重阈值 `0.5`（`:352`）、`access_threshold=3.0`（`family_d:68`）、`cutoff=3.5`（`family_d:95`）、`_anion_cutoff` 的九个值（`:202-204`）、维度分档 `0.3/0.6`（`family_d:126-128`）——**本次审计范围内共 15+ 个自由参数，零个有文献引用**。

- **F-5 (PASS)** BVSE 依赖标注充分。`family_d:5`（模块 docstring）与 `:136-137`（函数 docstring）双重声明依赖 SoftBV/BVSE 外部数据且当前返回 NaN，`:139` 实现一致。清单 F5 满足。

- **F-6 (不适用/WARN)** CN 定义与 Shannon 表的对齐无法在本范围内验证。`_effective_na_radius`（`_base.py:250-257`）按 CN 索引 Shannon 表，但**本次送审的四个文件中没有任何调用者向它传 CN**（该符号在四文件中仅出现一次，即其定义处）。CN 由谁计算、是否用 `_shell_neighbors` 的 +0.70/补至-4 规则得出，属 A 族范围。若确由该规则得出，则"补至 4"会把真实 2-配位位点的 CN 抬到 4，直接改变查表结果——这是一条跨批次依赖，需在 A 族审计中闭环。

### G. 测试覆盖与可重复性 (Test Coverage & Reproducibility): FAIL

**Evidence**: `test_descriptors.py:1-64`（全文）；`test_descriptors.py:14-15, 24, 30-38`；`run_info.yaml`（`cv_strategies` 两处 `random_seed: 42`、`stability_selection.random_seed`、`evaluation.model.random_seed`、`combination_validation.bootstrap.random_seed`）；`family_d:19-21`；`README.md`、`program.md` 相关段落

**Details**:

- **G-1 (BLOCKER)** `test_descriptors.py` 对被审计的 21 个函数零单元测试。全文 64 行，包含 `parse_audit_args`、`run_structural_audit`、`main` 三个函数，**零个 `test_*` 函数、零个 assert、零个断言性检查**。它是一个 CLI 包装器：`:24` 调 `prepare_structural_evaluation`、`:25-30` 写审计 CSV、`:47-53` 打印指标。清单 G1 问"是否覆盖了 4 个文件中的函数"——答案是**一个都没有**。

- **G-2 (BLOCKER)** "独立审计"的独立性不成立。`test_descriptors.py:15` 从 **`train.py`** 导入 `parse_agent_args`，`:14` 从 `automat_utils` 导入 `prepare_structural_evaluation`。`:20-22` 的 `parse_audit_args` 直接返回 `parse_agent_args(argv)`。即该入口与 `train.py` **共用同一套参数解析与同一条特征计算路径**，唯一差异是输出文件名。一条共享代码路径不可能审计出这条路径自身的实现缺陷——A/B/D/E 段落里的每一条发现，这个"审计"入口都无法捕获。

- **G-3 (BLOCKER)** 无任何边界情况测试。清单 G2 点名的三类（空结构、部分占位、含 N 阴离子）在送审文件中**零覆盖**。而这三类恰好是本次审计中缺陷最密集的区域：部分占位 → A-1/A-5/D-5；含 N → D-7 的全有或全无降级；退化输入 → D-1/D-2。

- **G-4 (PASS)** 随机种子已固定，但与描述符无关。`run_info.yaml` 在 `anion_stratified_cv`、`repeated_subsample`、`stability_selection`、`evaluation.model`、`combination_validation.bootstrap` 五处均设 `random_seed: 42`，清单 G3 满足。**限定**：描述符计算路径中不存在任何随机性来源，这些种子对描述符可复现性零贡献——G3 的 PASS 不应被读作"描述符可复现已验证"。

- **G-5 (PASS，带条件)** Voronoi 确定性。`scipy.spatial.Voronoi` 走 Qhull，对固定输入点序确定；点序由 `_base.py:305-315` 的三重循环确定性生成。集合迭代顺序方面逐处检查过：`_anion_cutoff`（`:207`）用 `max()` 与序无关，`_effective_anion_radius`（`:270`）显式 `sorted()`，`_shell_neighbors`（`:233`）只做成员判断——**未发现受 `PYTHONHASHSEED` 影响的路径**。条件：送审文件中无 `requirements.txt` 或环境锁，而 `_base.py:186, 230` 用 `len(item) >= 3` 防御性地兼容 `get_sites_in_sphere` 的多种返回形状，说明代码本身预期 pymatgen API 会变——**跨版本可复现性未被任何机制保障**。

- **G-6 (MEDIUM，清单明确点名项)** "带缓存效果" 不影响可复现性，但影响成本与可信度。`family_d:20` 的假声明（见 A-6）导致每个结构 4 次重复 Voronoi。因 `find_interstitial_sites` 是纯函数，四次调用返回相同结果，**不产生数值不一致**；G6 问的"是否影响可重复性"答案是**否**。但它是一条会被读者信任的错误注释，且在 84 行 × 4 次 × 27N 点的规模上是实打实的浪费。

- **G-7 (HIGH)** D-1 与 README 的失败契约冲突。README 声明"全 NaN 描述符会失败退出，不会产生假阳性结果"。`compute_interstitial_network_dim` 在退化输入上返回 0.0（`family_d:91`）而非 NaN，使得一个实际上无法计算的结构静默产出有限值——**保护机制被绕过的路径，恰恰不会被任何测试发现，因为没有测试**。

## Action Items

### 阻断级（BLOCKER，5 项——修复前该批描述符的任何数值不可进入结果记录）

1. **`family_e_framework.py:52-60`** — 修正 `bond_rigidity` 的理想键长为 `r_M + r_X`（`fw_sym` 已算好，接上即可），或直接废弃该描述符。同步重写 `:82-85` 的 docstring：删除 "X-X"、删除 "接近 1.0" 判据。若保留，必须在注册表中标注它等价于 r_M/r_X 的组分量，并按 `program.md` "体系代理" 条款优先报告共线性。
2. **`family_d_vacancy_topo.py:101`** — 改用 `struct.lattice.get_distance_and_image`（同文件 `:49`、`:74` 已有正确写法可直接复用）。修复后所有历史 `network_dim` 数值作废重算。
3. **`family_d_vacancy_topo.py:83-131`** — `network_dim` 要么改名为 `interstitial_percolation_fraction`（诚实描述它实际算的量），要么用真正的维度判据重写（推荐：对最大连通分量在 ±1 超胞上做周期展开，看连通性沿三个晶格方向的贯通数）。当前形式**不得**以"维度"名义进入组合搜索或论文。
4. **`_base.py:125` / `:130`** — 二选一：把判据改为多数派（与 docstring 一致、与 `_major_species` 一致），或把 docstring 改为"任意 Na 占位 > 1e-6"并接受混占位点同时不属于骨架的后果。**必须在全仓库统一为一套位点归类规则**，因为 `get_framework_sites` 的补集定义会把这个选择传播到整个 E 族。
5. **`test_descriptors.py`** — 新建真正的单元测试（与该 CLI 入口分开文件，避免名称占位），最小集合：① 空结构 → 每个描述符返回 NaN；② 1×1×1 vs 2×2×2 超胞 → 断言强度量描述符不变、并显式记录广延量描述符（当前有 3 个）；③ Na₀.₅ 分数占位结构 → 断言 `na_concentration` 与 `na_occupancy_sum` 的关系；④ 含 N 结构 → 断言降级路径；⑤ 每个描述符的解析式回归值（golden value）锁版本。

### 高优先（HIGH，6 项）

6. `family_d:90-91` — `len(sites) < 2` 返回 `float("nan")` 而非 0.0。
7. `_base.py:394` — `_safe_cv` 加 `len(values) < 2 → NaN` 守卫，与 `_safe_std:388` 对齐。
8. `family_c_concentration.py:21` — 改为占位加权（`compute_na_occupancy_sum` 的写法），或把 docstring 的 "原子数" 改为 "位点数"。
9. `_base.py:245-246` — "补至 4" 分支加显式标记（返回值中带 `padded: True`），或对骨架阳离子禁用该分支；同步更新 `:213` 的 docstring（当前仍写 "Na 位点"）。
10. `_base.py:18, 46` — 为 H 加入条件判断（按 H 的最近邻是否为 O 区分质子/氢化物），或至少在 docstring 中声明 "H 一律按氢化物处理" 这一建模假设。
11. **为 `descriptors/` 建立描述符级注册表**，每个描述符声明三列：`dimension`（Å / Å³ / 无量纲 / 计数）、`extensivity`（intensive / extensive）、`cell_setting_invariance`（invariant / dependent）。本次范围内 12 个描述符里，**晶胞设定不变且非退化的只有 `compute_framework_poly_distortion` 一个**——这个事实必须被机器可读地记录，否则组合搜索会把广延量与强度量相乘。

### 中优先（MEDIUM，5 项）

12. `family_d:20` — 删除 "带缓存效果" 的假声明，或实装 `functools.lru_cache` / 单次 featurize 内的显式缓存。
13. `_base.py:340` — 实装 Voronoi 区域体积，或从返回字典中删除 `volume` 键并同步改 `:295`。
14. `family_e:64` — 改用 `_safe_cv`，消除重复实现与守卫不一致。
15. `family_e:46` — 把 Na 距离循环移出 `if not shell: continue` 的作用域，或在 docstring 中说明该耦合。
16. `_base.py:320-322, 375-376` — 宽 except 改为记录失败原因（结构 ID + 异常类型）后返回降级值，以满足 `program.md` "记录该次失败原因" 的纪律。

## Claim Impact

| # | 声明 | 来源 | 判定 |
|---|---|---|---|
| 1 | "`test_descriptors.py` 提供同样的**独立**结构审计" | `program.md`「结果记录」段；`README.md`「Agent 轨道」段 | **unsupported** — 该入口从 `train.py:parse_agent_args` 与 `automat_utils:prepare_structural_evaluation` 导入，与被审计路径共享全部代码，且零断言。它是同一管线的别名输出，不构成独立性检验（G-1/G-2）。 |
| 2 | "描述符从 CIF 结构文件计算" | `run_info.yaml: task.description` | **supported** — 四个文件的全部输入均为 `Structure`，未见非结构输入。 |
| 3 | "不使用 log、sqrt、power 或**任意无量纲依据的除法**构造新特征" | `program.md`「描述符纪律」 | **needs_qualifier** — 运算符禁令在描述符**组合**层成立，但描述符**内部**已存在一处无物理依据的除法：`family_e:60` 的 M–X 键长 ÷ 2r_X（A-3）。纪律的作用域需要明确扩展到描述符内部，否则该规则只约束了组合层的表面。 |
| 4 | "某描述符与体系标签高度共线时，先报告它是体系代理的可能性" | `program.md`「描述符纪律」 | **needs_qualifier** — 机制存在（`results.tsv` 有 `system_proxy_ratio` 列），但当前描述符设计**保证**会触发它：3 个广延量随晶胞线性变化（B-1，实测 8→64），`bond_rigidity` 代数上退化为 r_M/r_X 即阳离子身份（A-3），而阳离子身份与体系近乎一一对应。报告机制不能替代设计修正。 |
| 5 | "BVSE 依赖的描述符返回 NaN" | `family_d_vacancy_topo.py:5`；`:136-137` | **supported**（附限定）— 声明与实现一致。限定：结合 README "全 NaN 描述符会失败退出"，`compute_bvse_barrier_estimate` 是一个**注册后必然失败**的描述符，两条契约叠加使其永远无法被评估。 |
| 6 | "使用 scipy.spatial.Voronoi 方法（errata P2 修正版），不使用 `VoronoiNN.get_voronoi_polyhedra`" | `family_d_vacancy_topo.py:3-4` | **supported**（作用域限定 D′ 族）— D′ 族确未调用 `VoronoiNN`；但 `_base.py:371` 的 `compute_polyhedron_volume` 仍在用它，该声明只对 D′ 族成立，不对 `_base` 成立。 |
| 7 | "全 NaN 描述符会失败退出，不会产生假阳性结果" | `README.md`「数据与统计契约」 | **needs_qualifier** — 保护逻辑本身合理，但 `family_d:91` 的 0.0 返回路径可在描述符实际不可计算时产出有限值，绕过该闸门（G-7/D-1）。 |
| 8 | "间隙位点列表 … volume 为对应 Voronoi 区域体积 (Å³)" | `_base.py:295` | **unsupported** — `:340` 硬编码 0.0（A-7）。 |
| 9 | "`_effective_anion_radius` 计算阴离子有效离子半径**加权**平均值" | `_base.py:261` | **unsupported** — `:277` 是对元素种类集合的等权算术平均，无任何权重（A-2）。 |
| 10 | "`get_na_sites`：Na 位点 = 主要物种为 Na 的位点" | `_base.py:125` | **unsupported** — `:130` 用 1e-6 痕量阈值（A-1）。 |
| 11 | "`compute_interstitial_network_dim`：用 DFS 判断最大连通分量的**维度**" | `family_d:86-87` | **unsupported** — DFS 返回基数不返回维度；输出量表封顶 2.0，永不表达 3D（A-4）；且连通性判据缺 PBC，在 7–12 Å 的胞上漏掉 30–47% 的连接（E-1）。 |

## Audit Scope Limitations (审计限定，不可越界解读)

1. 本轮只看四个描述符文件 + 四个配置/文档文件。`train.py`、`automat_utils.py`、`descriptors/__init__.py`（注册表）、`part1.py`、family_a/b/f/g/h **均未送审**，所有涉及"注册表如何声明量纲/族"、"CN 由谁计算"、"+0.70 规则的原始出处"的判断都是**开放的**，不是本轮结论。
2. `results/` 与 `naconductor_featurized.csv` 按要求排除，**本轮不核对任何已保存数值**，只判代码是否会产出自洽产物。
3. 审稿人无法在此环境运行 pymatgen（不可用），涉及 pymatgen 语义的判断（`get_sites_in_sphere` 的 index/image 语义、`get_distance` 的最近镜像约定、`VoronoiNN` 的 volume 字段含义）基于 API 文档语义而非执行验证。涉及 scipy/numpy 的判断（E-1 量化、B-1 广延性、D-2/D-3 数值行为）**均已实际执行**。

## Reviewer Raw Response

<details>
<summary>Click to expand full reviewer response</summary>

完整 Claude 原始回复已逐字保留于本文档上述各章节（A-G Checks、Action Items、Claim Impact、Audit Scope Limitations）。本批次不另存 RAW_RESPONSE.md，因解析全部成功。

</details>
