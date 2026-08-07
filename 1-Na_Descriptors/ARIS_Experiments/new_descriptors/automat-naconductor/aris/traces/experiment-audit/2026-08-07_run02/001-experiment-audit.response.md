**审计口径（rubric）声明**：本次评审严格按你提供的 A–L 12 项 stat-pipeline 审计清单及其自带的 PASS/WARN/FAIL 判定标准执行，采用拒稿视角。凡我的独立判断严于清单自带上限之处（例如清单把 I/J/K/L 的失效上限定为 WARN），我会分开标注"清单判定"与"审稿人判定"，不混合成一个笼统结论。

**两点前置限制，必须先说明：**

1. **无法给出真实行号。** 嵌入文档没有行号，且传输过程中代码块已被 Markdown 渲染破坏（`def__init__` 缺空格、`f"...{'<empty></empty>'}"` 是 `'<empty>'` 被 HTML 转义、`featurizer.py` 与 `run_pipeline.generateReport` 大段缩进错位）。我不会编造 `file:123` 这种引用——在一份反造假审计里伪造证据定位本身就是造假。下文一律用 `file:符号名` 定位。**同时：我无法区分"传输损坏"与"真实语法/缩进 bug"**，因此 `_base.py:find_interstitial_sites` 中 `interstitial_sites.append(...)` 落在 `for vertex` 循环体外（若为真，则该函数只返回最后一个顶点）这类问题，请你在真实 repo 里自行核对，我不把它计入正式结论。
2. **描述符实现文件 `family_a_polyhedron.py` ~ `family_h_symmetry.py` 未提供。** 41 个描述符的计算逻辑全部不可审。`_base.py` 中 `get_na_x_bonds`、`_shell_neighbors`、`compute_polyhedron_volume`、`_safe_cv` 等是否被调用、如何被调用，均无法验证。本次审计只覆盖统计管线，不覆盖描述符本身的物理正确性。

---

## A. Ground Truth Provenance

- **Status: PASS**
- **Evidence**: `run_info.yaml:data.target_column`；`run_pipeline.py:runStage0`（`y = raw_df[args.target_column].values.astype(float)`）；`automat_utils.py:evaluate_structural_frame`（`y_full = pd.to_numeric(frame[target_column], ...)`）；`combination.py:CombinationValidator._factor_spanning`
- **Details**：
  1. **目标来自数据集，非模型输出。** `log_sigma` 全程由 `data/naconductor_raw.csv` 读入，没有任何路径用模型预测值反填目标。这一项干净。
  2. **唯一的"派生目标"是 V2**：`_factor_spanning` 中 `train_residual = y_oof[train_idx] - control_model.predict(z_train)`，`test_residual` 用训练折拟合的 Ridge 外推。这是模型派生的残差目标，但它**已被显式标注**：`"method": "fold_safe_oof_target_residual_prediction"`、`"interpretation": "predictive_association_after_known_factors_not_causal"`、`"status": "exploratory"`。符合清单第 3 条的"显式 proxy 标注"要求。
  3. **本 benchmark 无官方 eval 脚本**（自建研究数据集），清单第 4 条不适用。
  4. **潜在隐患（非本项失分）**：`featurizer.py:build_feature_matrix` 的 `metadata_cols` 保留了所有非描述符列，**`log_sigma` 因此实际存在于 `feature_df` 里**。当前所有下游都用白名单取列（`analyze_all` 用 `registered_names`、`runStage2` 用 `registered ∩ prefiltered`），目标没有泄进 X。但这是一颗雷：将来任何一处改成 `select_dtypes(np.number)` 就会直接把目标当特征。建议 `build_feature_matrix` 返回时把目标列剥离到单独对象。

## B. Score Normalization

- **Status: WARN**
- **Evidence**: `deconfound.py:DeconfoundAnalyzer.analyze_all`（`system_proxy_ratio` 分支）；`run_pipeline.py:generateReport`（`signal_retention`、`delta_pct`）；`cv_strategies.py:summarize_cv_spearman`
- **Details**：
  1. **清单字面项 PASS**：没有任何指标以模型自身输出的 max/min/mean 作分母。`system_proxy_ratio` 的分母 `raw_rho²` 是描述符与实测目标的相关，不是预测统计量。
  2. **raw 与 normalized 并列报告 PASS**：`raw_spearman`、`deconfounded_spearman`、`system_proxy_ratio` 三列同时进入 `stage1_deconfound_results.csv` 和报告表格。这是本项目做得好的地方。
  3. **`system_proxy_ratio` 存在两处硬饱和，且 1.0 语义二义**：`raw_rho_sq < 1e-12` → 硬置 `0.0`；`raw_rho * deconf_rho < 0` → 硬置 `1.0`；其余 `max(0, min(1, ...))` 钳位。后果是：输出中的 `1.000` 无法区分"符号翻转"和"deconf_rho≈0 触顶钳位"；输出中的 `0.000` 无法区分"raw 相关为零"和"去混杂后相关反而变强（抑制效应）被钳掉"。**报告表格直接印这一列，读者无从判断哪种情况。**
  4. **`signal_retention` 是自指且病态的比值**：`generateReport` 中 `deconf_rho_sq.mean() / raw_rho_sq.mean() * 100`——这是"均值之比"而非"比之均值"，由最大 `raw_rho` 那个描述符单独支配；且它跑在**未经预筛选的全部描述符**上（`generateReport` 收到的是完整 `deconfound_df`），把"噪声级"描述符的近零 rho 一并算进两个均值。**你上一轮实际跑出 102.5%——超过 100% 本身就是这个指标坏掉的直接证明**：它被当作"去混杂后信号保留率"写进结论，但一个"保留率"不可能大于 1。
  5. **`delta_pct` 分母不可比**：`(best_comb_score - baseline_composite) / |baseline_composite|`，两个 `composite_score` 可能基于**不同数量的可用 CV 策略**（一个 2/3、一个 3/3）。对不同策略集合求得的均值直接作差再除，数学上无意义。

## C. Result File Existence

- **Status: WARN**（`results/` 已按你要求排除，本项只评"代码是否会产出自洽产物"）
- **Evidence**: `compute_features.py:main`；`run_pipeline.py:runStage0/runStage4/generateReport`；`descriptors/__init__.py:SEARCHABLE_STRUCTURE_DESCRIPTORS`；`deconfound.py:analyze_all` docstring；`run_info.yaml:evaluation.secondary`
- **Details**：
  1. **"41 个描述符"这个数字在代码里是错的。** `_INACTIVE_FOR_AUTOMATIC_SEARCH` 排除 `max_bond_length`、`bottleneck_anisotropy`、`bvse_barrier_estimate`，`SEARCHABLE_STRUCTURE_DESCRIPTORS` 实际是 **38** 个，`featurize_dataset` 的默认 `descriptor_names` 也走 38 个。但 `compute_features.py` 和 `run_pipeline.py:runStage0` 都硬编码打印"84 个 CIF × 41 个描述符"，`run_info.yaml` 与 README 也称 41。**报告里的 `n_total_desc` 用的是 38，与你手稿/文档里的 41 会对不上。**
  2. **docstring 与实现不符（会误导任何复核者）**：`deconfound.py:analyze_all` 的注释写"跳过 NaN 过多的列：有效值不足 80% 则跳过"，实际代码是 `if n_valid < 5: continue`。真正的覆盖率门槛在别处（`build_feature_matrix` 的 `min_valid_fraction=0.5`）。**80% 这个阈值在代码里根本不存在。**
  3. **报告混用两个不同的描述符总体**：`main()` 把 `filtered_deconfound_df`（预筛后）传给 `runStage4`（形参却叫 `deconfound_df`），基线取的是 `deconfound_df.iloc[0]`；而 `generateReport` 的 Stage 1 表格与 `signal_retention` 用的是完整 `deconfound_df`。当存在抑制效应（`|deconf_rho|` 高但 `|raw_rho| < 0.2` → 标签"噪声级" → 被预筛掉）时，**Stage 1 表格第一行与"最佳单描述符基线"会是两个不同的描述符，报告不做任何说明**。你 102.5% 的保留率恰恰提示这类抑制样本存在。
  4. **配置声明了不存在的产物**：`evaluation.secondary` 列出 `cv_rmse` 和 `stability_score`——全代码无 RMSE 计算，稳定性频率的列名是 `selection_freq`，`stability_score` 这个键不会出现在任何产物里。`deconfound.method` 注释"可选: partial_correlation, dml"，DML 未实现。
  5. **`run_info.yaml` 多处参数不驱动代码（配置漂移）**：`stability_selection` 的 `n_bootstrap/threshold/fraction` 在 `runStage2` 里硬编码为 `StabilitySelector(n_bootstrap=100, threshold=0.6, fraction=0.5, ...)`；`cv_strategies` 的 `folds/n_repeats/test_fraction/random_seed` 全部走函数默认值。**改 YAML 不改行为**——这直接打击"冻结输入契约"的可信度。

## D. Dead Code Detection

- **Status: WARN**
- **Evidence**: `deconfound.py:_one_hot_encode` / `_classify_descriptor`；`_base.py:CROSS_GROUP_RULES`；`run_pipeline.py:runStage0`（`noise_info_df`）；`combination.py:_formula_dimensionally_valid` / `ConstrainedCombinationSearch.__init__`；`train.py:evaluate_descriptor`；`automat_utils.py:evaluate_structural_descriptor`
- **Details**（按危害排序）：
  1. **`_classify_descriptor` 接收 `deconf_p` 但函数体完全不用它。** 分类只看 `|raw_rho|`、`|deconf_rho|`、`system_proxy_ratio` 三个阈值。**这意味着"强物理信号"标签不含任何显著性要求**——一个 n=42、p=0.4 的 `|deconf_rho|=0.31` 会被打成"强物理信号"，进而通过 Stage 1 预筛。这是本项最有实质危害的一条。
  2. **`noise_info_df` 被算出来然后丢弃。** `build_feature_matrix` 逐列计算了 15 个噪声列与目标的实际 Pearson r（`actual_corr_with_target`），`runStage0` 解包后**再也不用、不落盘**。这恰恰是读者判断"这一次噪声抽得多幸运"的唯一凭据（见 H.3）。
  3. **`_base.py:CROSS_GROUP_RULES` 是第二套规则真值源。** `run_info.yaml` 明确声明 `source_of_truth: descriptors.combination.PAIR_OPERATOR_RULES`，但 `_base.py` 里另有一份 `allowed_pairs` + `per_operator_restrictions`，无人调用。当前两份内容基本一致（`combination.py` 多了对称的 `("A","E")`），但**两套规则并存迟早漂移**，且它出现在 `_base.py` 会让复核者误以为它在生效。
  4. **`DeconfoundAnalyzer._one_hot_encode` 全代码零调用**（实际用的是 `_one_hot_frame`）。
  5. **`_formula_dimensionally_valid` 的 multiply/ratio 量纲推导算了但不用**：函数只在 `+` 不匹配时返回 `False`，`current` 拼出的 `"(length)*(count)"` 之类字符串除非后续再遇到 `+` 否则毫无作用。**后果是 `space_group_number`（dimension = `categorical_index`，且 `is_high_risk=True`）可以合法参与 `A×H` 乘法**——把空间群序号当连续量相乘，物理上无意义，量纲检查却放行。
  6. **兼容壳**：`train.py:evaluate_descriptor` 与 `automat_utils.py:evaluate_structural_descriptor` 均未被各自 `main()` 调用（`main` 走 `prepare_structural_evaluation`）。`ConstrainedCombinationSearch.__init__` 存了 `self.seed` 但 `search()` 无随机性，从不使用。
  7. **无法核实**：`README.md` / `program.md` 引用的 `run_status.py`、`plot_run_results.py`、`test_descriptors.py`、`descriptors/idea.md` 均未提供。

## E. Scope Assessment

- **Status: WARN**
- **Evidence**: `run_info.yaml:cv_strategies`；`cv_strategies.py:anion_stratified_cv/repeated_subsample`；`combination.py:_noise_baseline`（`n_draws=100`）；`run_pipeline.py:generateReport`（`consistency_desc`）；`combination.py:PAIR_OPERATOR_RULES`
- **Details**：
  1. **规模**：84 样本 / 3 个体系 / 38 个可搜索描述符。**你上一轮只有 6 个描述符通过 Stage 1 预筛**——也就是 Stage 2–4 的全部组合搜索实际建立在 6 个描述符（每族最多 2 个代表）之上，而这 6 个是用全量 84 行、含目标的统计量筛出来的。
  2. **每配置只有 1 个种子，且 `--seed` 不通到 CV。** `anion_stratified_cv` 里 `StratifiedKFold(..., random_state=42)` 是**字面量**；`run_all` 与 `_run_cv_diagnostics` 调 `repeated_subsample(X, y, systems)` 全走默认 `seed=42`。`--seed` 只影响稳定性选择、V1 置换和 V4 bootstrap。**"换个种子看结果稳不稳"这件事在 CV 层面根本做不到。**
  3. **重复次数偏低**：V1 置换只有 `n_draws=100`——`observed_percentile` 的分辨率是 0.01，无法表达 p < 0.01；`noise_95pct_abs_spearman` 由 100 个样本的第 95 百分位估计，本身抖动很大。V4 bootstrap 500 次尚可，但用的是 percentile 法（对相关系数有偏），未用 BCa。
  4. **"稳健"语言超出证据**：`run_info.yaml` 任务描述称"统计稳健的描述符组合"，README 称"预测稳健性"，报告结论段直接生成 `"全部同向，一致性优秀"`。**该判定的触发条件极弱**：`signs` 收集的是 `validation_df.head(3)` 中所有 `*_available == True` 的策略符号，若只有 1 个策略可用，`n_positive == len(signs)` 成立，就印出"一致性优秀"——**一个数据点得出"优秀"**。
  5. **搜索空间高度不对称且未披露**：`PAIR_OPERATOR_RULES` 中**完全没有 F 族和 G 族的任何跨族条目**。F（长程关联）和 G（电子代理）的代表只能做同族 pair，永远无法参与三元组（三元组要求"同族两个 + 显式相邻族一个"）。整个组合空间以 A 族为轴心。报告的 Stage 3 表格不体现这一结构性限制，读者会以为搜索是对称覆盖 8 个族的。

## F. Evaluation Type

- **Classification: real_gt**（主线），V2 为 real_gt 的模型派生残差变体，V1 为置换零分布对照
- **Evidence**: `run_pipeline.py:runStage0`；`combination.py:_noise_baseline` / `_factor_spanning` / `_per_system` / `_bootstrap_ci`
- **Details**：
  1. **主指标 real_gt**：`raw_spearman`、`deconfounded_spearman`、三条 CV 的 Spearman/MAE 全部对实测 `log_sigma`。
  2. **V1 `noise_baseline`：real_gt + 体系内置换零分布。** 这一块**设计是对的，值得给分**——按 `system` 分块置换各分量，保留体系间结构、只破坏体系内关联，因此它检验的正是"扣除体系层面之后还有没有关联"。两点保留：(a) 各分量**独立**置换会破坏 d1/d2 的行内耦合，对 ratio 的零分母模式会改变有效 n；(b) 100 draws 分辨率不足。
  3. **V2 `factor_spanning`：real_gt 的折内残差化派生目标**，标注完整（见 A.2）。
  4. **V3 `per_system`：real_gt**，但注意它算的是 `raw_spearman`（`association: "raw_within_system_spearman"`），未去混杂。
  5. **V4 `bootstrap_ci`：real_gt 重采样**，同样算的是**原始** Spearman，不是去混杂 Spearman（见 J.4）。
  6. **无 human_eval、无 simulation_only。**

## G. Data Leakage in Preprocessing（stat-pipeline 专项）

- **Status: WARN**（清单 5 项字面检查全部通过；扣分来自"目标依赖的全量步骤上游污染"与噪声列单次抽样）
- **Evidence**: `cv_strategies.py:MultiStrategyCV._make_model` / `_fold_metrics`；`stability.py:StabilitySelector.run`；`featurizer.py:build_feature_matrix`；`combination.py:_factor_spanning`；`deconfound.py:partial_spearman`
- **Details（逐项）**：

| 检查项 | 判定 | 依据 |
|---|---|---|
| 1. 中位数填充 | **PASS** | `_make_model()` 每折新建 `Pipeline([imputer, scale, ridge])`，`_fold_metrics` 内 `model.fit(X_train, y_train)`，只见训练折 |
| 2. StandardScaler | **PASS** | 同上，同一 Pipeline 内折内拟合 |
| 3. 噪声列注入 | **PASS（带保留）** | `build_feature_matrix` 中 `rng = RandomState(42)` 全局一次注入，纯独立标准正态，不含目标信息，符合清单豁免条件 |
| 4. 稳定性选择子样本 | **PASS** | `StabilitySelector.run` 的 Pipeline 在 `for _ in range(n_bootstrap)` **循环体内**新建并 `model.fit(X_sub, y_sub)` |
| 5. 去混杂残差化 | **分裂：Stage 1 全量（清单允许）/ Stage 4 V2 折内（PASS）/ Stage 3 排序全量（问题在 H）** | `analyze_all → partial_spearman` 全量；`_factor_spanning` 中 `control_model.fit(z_train, y_oof[train_idx])` 折内 |

  额外发现：
  1. **`build_feature_matrix` 明确不做全量填充**，保留原值与 NaN，注释直书"预测性填充和标准化必须由每个训练折内部的模型 Pipeline 完成"。**这是整份代码里工程质量最高的一处，与你上一轮审计中被判 supported 的两条 claim 之一一致。**
  2. **噪声基线是"零分布的一次抽样"，不是零分布。** 15 个噪声列抽一次后固定，100 次 bootstrap 全部复用同一批实现值。它们各自的实际目标相关（`actual_corr_with_target`）被算出后丢弃（D.2）。n=84 时 15 次抽样中最大 |r| 的期望约 0.25–0.28——**基线高低取决于种子 42 的运气，且这个运气值不可见**。
  3. **`_factor_spanning:encode_controls` 有静默错编码风险**：测试折的设计矩阵按训练折的 `selected_columns` 前缀匹配构造；若某 `anion_type` 类别只出现在测试折（halide 体系的稀有阴离子完全可能），其全部指示列为 0，**被静默当作参考类别处理**，残差因此系统性偏移。当 `unique_systems.size <= 1` 或最小体系样本数 < 2 时代码回落到 `random_kfold`，该风险进一步放大。

## H. Feature Selection Leakage（stat-pipeline 专项 — CRITICAL）

- **Status: FAIL**
- **Evidence**: `run_pipeline.py:runStage1`（`pass_labels` 预筛）→ `runStage2`（`real_col_names` 限定 `prefiltered`）→ `stability.py:PhysicalGrouper.group_and_select`（按 `|deconfounded_spearman|` 取代表）→ `combination.py:ConstrainedCombinationSearch.search`（按 `combined_deconf_spearman` 排序）→ `CombinationValidator.validate`（`candidates_df.head(top_k)`）；`combination.py:full_validation`（`uncertainty` 字典）与 `COMBINATION_VALIDATION_RESULT_COLUMNS`
- **Details（逐项）**：

  **1. 稳定性选择 → CV：是泄露。** `runStage2` 的 `real_col_names = [c for c in feature_df.columns if c in registered and c in prefiltered]`——进入稳定性选择的特征集**已经被 Stage 1 用全量 84 行、含目标的 `deconfounded_spearman` 标签筛过一遍**（`pass_labels = {强物理信号, 弱物理信号, 混合信号}`）。子样本内独立预处理无法撤销这一步。你上一轮 **38 → 6** 的通过率意味着 84 行目标信息被用来砍掉了 84% 的特征，之后同样这 84 行又被用来做 CV。

  **2. 组合 top-k → CV：是泄露。** `search()` 末尾 `sort_values("combined_deconf_spearman", key=abs, ascending=False).head(150)`，`validate()` 取 `candidates_df.head(top_k)`（默认 10），随后 `full_validation` 在**全部 84 行**上跑三条 CV。选择与评估共用同一批行，无外层循环。

  **3. `PhysicalGrouper` 代表选择 → CV：是泄露，且报告把选择统计量当评估统计量印。** `group.loc[group["deconfounded_spearman"].abs().nlargest(max_per_family).index]`——代表按 Stage 1 全量统计量选出，而报告 Stage 2 表格印的就是这同一个 `deconfounded_spearman`。**用于选择的量不能同时充当该选择的证据。**

  **4. V2 的 CV 与排序不独立。** 你在清单里的判断（公式值只是特征算术，无泄露）**成立**，`_factor_spanning` 的 OOF 残差化确实折内安全。但问题不在 V2 内部，在于**哪个候选进得了 V2**：候选是按全量 `combined_deconf_spearman` 排序后取前 10 的。折内安全的 V2 跑在一个被全量统计量挑出来的候选上，得到的仍是条件于选择的估计。

  **5. 项目是否承认这一结构？——部分承认，但承认从未到达任何产物。这是本项判 FAIL 的决定性理由。**
  - `run_info.yaml` 有 `selection_uncertainty.nested_outer_group_selection_available: false`；
  - `combination.py:full_validation` 返回的 `uncertainty` 字典含 `"selection_uncertainty_included": False` 和 `"reason": "nested outer-group selection validation is not available"`；
  - **但 `CombinationValidator.validate` 在扁平化时只取了 `uncertainty_method`（且是硬编码字符串 `"system_stratified_bootstrap"`），把 `selection_uncertainty_included` 整个丢掉了。** `COMBINATION_VALIDATION_RESULT_COLUMNS` 中没有这一列，`stage4_validation_results.csv` 里不会有它，`final_report.md` 里也不会有它。
  - 更进一步：这句话说的是"我们**没做**嵌套验证"，**不等于**"因此下表 CV 分数被系统性高估"。读者拿到的报告里，唯一的免责声明是脚注"所有组合证据均为探索性，不作因果解释"——**它讲的是因果，不是乐观偏差。**

  **6. 追加发现：噪声基线的比较是不对称的，项目自带的假阳性对照因此失效。** `runStage2` 里真实描述符列被限定为 `prefiltered`（已过目标筛），而 `noise_col_names = [c for c in feature_df.columns if c.startswith("noise_")]` 是**全部 15 列，未经任何筛选**。于是 `above_noise_baseline = freq > noise_baseline` 是在拿"已经赢过一轮目标筛选的真实描述符"去比"没参加过那轮筛选的噪声列"。**这个对照系统性偏向真实描述符，`above_noise_baseline` 通过与否几乎不携带假阳性控制信息。**

## I. Deconfounding Methodology Correctness（stat-pipeline 专项）

- **清单判定: WARN**（清单为本项设定的失效上限即 WARN）／**审稿人判定: FAIL 级修复项 2 条**
- **Evidence**: `deconfound.py:partial_spearman` / `build_rank_aware_controls` / `analyze_all`；`combination.py:_evaluate_candidate` / `_factor_spanning`
- **Details（逐项）**：

  **1. 残差化范围：Stage 1 全量（清单允许），Stage 4 V2 主指标折内（PASS），V2 补充量全量但已标注。** `_factor_spanning` 中 `system_rho` / `all_rho` 由 `analyzer.deconfounded_spearman(x_valid, y_valid, ...)` 在全量有效行上算出，落在 `supplementary_partial_association` 下，`run_info.yaml` 亦标 `partial_association_role: supplementary_only`。**这一处标注是到位的。**

  **2. `build_rank_aware_controls` 实现基本正确，但"冗余"的归属是任意的。** 贪心前向逐列加入 anion 对比项、只保留提升秩的列，其保留数必然等于独立计算的 `confounder_rank - system_rank`——这一点数学上成立。但**遍历顺序由 `pd.get_dummies` 的字母序决定**，因此"哪一个 anion 对比项被标为 redundant"是任意的，而 `anion_redundant_columns` 会原样进报告的控制设计审计行。另注：`controls` 不含截距列，秩却是带截距算的——因 `Ridge(fit_intercept=True)` 补上，**一致，无误**。`anion_is_independent_control: False` 这个标注是诚实的，给分。

  **3. `system_proxy_ratio = 1 - deconf_rho²/raw_rho²` 不是有效的分解量。** 失效模式三条：(a) `raw_rho → 0` 时分母爆炸，抑制效应（`|deconf| > |raw|`）产生的负值被 `max(0, ...)` 钳成 0，信息销毁；(b) 符号翻转硬置 1.0 并注释"相关完全由混杂驱动"——但 raw=+0.02 / deconf=−0.02 这种纯噪声翻转也会得到 1.0，**用噪声断言"完全由混杂驱动"**；(c) 根本问题是 **Spearman² 不是 R²**，秩相关平方之比没有方差分解意义，"体系代理比"这个名字却直接邀请方差解释读法（→ L）。

  **4. Ridge 正则化引入系统性、且方向有利于结论的偏差。** 混杂设计是纯 0/1 one-hot，**OLS 残差化在该设计下等于组均值中心化，本身就是对分类混杂的饱和（非参数）调整——不需要任何正则化**。`alpha=1.0` 的后果是组均值被向全局均值收缩，收缩因子约 $n_g(1-n_g/n)/[n_g(1-n_g/n)+\alpha]$：
  - `system` 组 $n_g \approx 28$：约 5% 的体系效应残留在残差里；
  - **稀有 anion 类别 $n_g = 3$：约 26% 的该类效应残留。**
  
  即：**调整不足，残差保留部分混杂，`deconfounded_spearman` 被系统性推向 `raw_spearman`，`system_proxy_ratio` 被推向 0，描述符看起来比实际更"物理"。** 偏差方向恰好有利于论文结论，且在样本最少、最需要谨慎的 halide/稀有阴离子格子里最严重。

  **5. 混杂变量未同时作为特征，无双重控制（PASS）**，见 A.4。

  **6. 追加发现 A：`partial_spearman` 有静默回退，且该路径在 Stage 3 可达。** 守卫 `if n_samples < 3 or z.shape[1] == 0 or z.shape[1] >= n_samples:` 直接 `return stats.spearmanr(x, y)`——**返回原始 Spearman 却不打任何标记**。Stage 1 因 `min_valid_fraction=0.5` 保证 ≥42 行，该路径不可达；但 `combination.py:_evaluate_candidate` 的门槛只有 `if n_valid < 5: return None`。**一个零分母众多的 ratio 组合若剩 5–6 个有效行，会拿到"5 个点上的原始 Spearman"（极易接近 ±1.0）冒充 `combined_deconf_spearman`，按 |rho| 排到第一名，然后进 top-k 被"验证"。** `n_valid` 虽写入 `stage3_combination_candidates.csv`，但排序不看它，**Stage 3 与 Stage 4 的报告表格都不显示它**。

  **7. 追加发现 B：先残差化原值再取秩，破坏了 Spearman 的单调不变性。** `partial_spearman` 对**原始** x、y 做线性残差化，再对残差算 Spearman。因此 `deconfounded_spearman` **不再对描述符的单调重参数化不变**——`x` 与 `x³` 会给出不同的去混杂 rho。这与 `run_info.yaml` 中选用 Spearman 的理由（"非参数，适合小样本"）以及禁用 log/√/power 的理由（"目标已是 log"）自相矛盾：项目一边禁止对描述符做单调变换，一边使用了一个对单调变换敏感的主指标。（对分类混杂而言线性残差化本身是饱和的，无函数形式误设——问题只在"先残差化后取秩"的次序。）

## J. Multiple Testing & Selective Reporting（stat-pipeline 专项）

- **清单判定: WARN**（清单上限）／**审稿人判定: 含 FAIL 级修复项**
- **Evidence**: 全代码无 `bonferroni` / `fdr` / `multipletests`；`deconfound.py:analyze_all`（`deconf_p`）；`cv_strategies.py:summarize_cv_spearman`；`run_pipeline.py:generateReport`；`combination.py:_bootstrap_ci`
- **Details（逐项）**：

  **1. 无任何多重检验校正，且 p 值本身是反保守的。** 隐含比较量级：Stage 1 的 38 个描述符 × 2 个统计量；Stage 3 最多 150 个候选公式的排序；Stage 4 的 10 × 3 CV 策略 × 4 证据块。`deconf_p` 由 `stats.spearmanr(res_x, res_y)` 给出——**它按原始样本量算自由度，完全不扣除已估计的混杂参数**，因此即便不考虑多重性，单个 p 值也偏小。这个 p 值会原样写入 `stage1_deconfound_results.csv` 和 `results/agent/results.tsv`，无任何校正或警示。**同时它在标签判定里被完全忽略（D.1）。**

  **2. `composite_score` 只用可用策略——透明度这一项 PASS，比较方式 WARN。** `summarize_cv_spearman` 同时输出 `composite_strategy_count`、`composite_is_complete`、`composite_score_basis = "mean_absolute_spearman_available_strategies"`，报告表格印 `(N/3)`，`_format_cv_metric` 把跳过的策略印成 `SKIPPED` 而非 0——**这一整套设计是诚实的，明确给分**。问题在使用端：`delta_pct` 直接拿不同 N 的 composite 相减相除（B.5）。

  **3. top-k 的乐观性未被承认（同 H.5）。** 且"最强组合"的定义与打分不自洽：`best_comb_row = validation_df.iloc[0]` 取的是 **`|combined_deconf_spearman|` 排序第一**，而 `best_comb_score = best_comb_row["composite_score"]`。**一个去混杂 rho 最高、但只有 1/3 策略可用、composite 平平的候选，会以"最强组合"之名带着它的 composite 分数进结论段。**

  **4. Bootstrap CI 不覆盖选择不确定性，且它算的根本不是主指标。** `_bootstrap_ci` 内 `rho = _safe_spearman(values_valid[draw], y_valid[draw])`——**对固定公式的原始 Spearman 重采样**。它既不重跑选择，也不重跑去混杂。但报告把这一列题为"体系分层Bootstrap 95% CI"，与同一行的 `去混杂Spearman` 和 `综合得分` 并列。**读者会自然把这个区间读成后两者的区间，而它对二者都不适用。** 加上 `selection_uncertainty_included: False` 在扁平化时被丢弃（H.5），报告中不存在任何提示。

  **5. 追加发现：`consistency_desc` 把跨候选一致性与跨策略一致性混为一谈。** `generateReport` 中 signs 在 `validation_df.head(3)` **三个不同候选**上跨策略汇总。若候选 1 三条策略全为 +0.4、候选 2 三条策略全为 −0.4，二者各自内部完全一致，代码却判为"方向不一致，需谨慎解读"；反之亦可造出假的"一致性优秀"。另：`"所有CV策略均无显著相关"` 的触发条件是所有 `np.sign` 恰为 0（rho 严格等于 0.0），与"显著性"毫无关系，标签措辞是错的。

## K. Target & Metric Definition（stat-pipeline 专项）

- **清单判定: WARN**（清单上限）／**审稿人判定: 含 1 条领域级 FAIL 风险（温度混杂）**
- **Evidence**: `run_info.yaml:data.target_column`；`cv_strategies.py:_fold_metrics` / `_mean_or_nan` / `summarize_cv_spearman`；`deconfound.py:_classify_descriptor`；`run_pipeline.py:runStage1`
- **Details（逐项）**：

  **1. `log_sigma` 无任何校验，且目标未被标准化（后者 PASS）。** 全代码只有 `pd.to_numeric(...)` 读取，没有单位检查、没有量程检查、没有 log10 vs ln 的校验。`StandardScaler` 只作用于 X，目标始终是原尺度——**这一点是对的，不存在隐藏变换**。但若 CSV 里混入一行未取对数的 σ，管线会静默接受。

  **2. 最严重的领域级问题：混杂集里没有温度。** 数据集列为 `system` / `anion_type` / `formula` / `space_group`——**没有测量温度、没有测量方法（交流阻抗 vs 直流）、没有体相/晶界/致密度区分**。文献汇编的离子电导率对这些因素的敏感度以数量级计，远超任何结构描述符的效应量。**整套"去混杂"机器控制的是次要变量，而支配性混杂完全缺席。** 这是审稿人会第一个提出、且无法用统计手段补救的问题。

  **3. Spearman vs Pearson：选择有理由，但与目标物理不匹配。** 配置注释"非参数，适合小样本"成立，但：(a) **Spearman 只捕捉单调关系，而快离子导体最经典的构效关系恰恰是非单调的**——瓶颈尺寸有最优值、Na 占位率有 volcano 曲线。用单调统计量筛描述符，会系统性漏掉物理上最有意思的那批；(b) 单调不变性已被"先残差化后取秩"破坏（I.7），"非参数"的辩护部分落空。

  **4. `composite_score` 取绝对值确实掩盖方向翻转——你的怀疑成立。** `summarize_cv_spearman` 中 `available_scores.append(abs(spearman))` 后取均值：+0.5 与 −0.5 得 0.5，与两次都是 +0.5 完全不可区分。**且这是两层掩盖：**
  - 层一（策略内）：`_mean_or_nan(spearmans)` 对**带符号**的逐折 rho 求算术均值——折间符号相反会互相抵消趋近 0，且未做 Fisher z 变换，平均本身向 0 有偏；
  - 层二（策略间）：再取绝对值求均值。
  
  报告里唯一的方向检查是 `consistency_desc`，而它有 J.5 的缺陷、只看前 3 个候选、且**不与表格中的 composite 逐行绑定**。

  **5. 小样本下的过校正风险是真实且结构性不可逆的。** 若真实机制在**体系之间**运作（例如硫化物导得好正是因为 S 更易极化，`covalency_index` 恰好捕捉这一点），对 `system` 残差化会把机制本身减掉。`_classify_descriptor` 的 `|deconf_rho| > 0.3 → 强物理信号` 规则对**反向**情形有一定保护，但另一方向没有：**这类描述符会被打成"体系代理"，随即被 `runStage1` 的 `pass_labels` 永久剔除，此后 Stage 2/3/4 再也不可能把它捡回来。** 0.3 / 0.3 / 0.7 三个阈值无任何来源说明、无敏感性分析，却是这道不可逆闸门的唯一依据。

  **6. 追加发现（本项最重要的一条）：单列公式下，三条 CV 的 Spearman 在代数上等于折内原始 Spearman，与 Ridge 无关，且未去混杂。** `_fold_metrics` 做 `model.fit(X_train, y_train)` → `y_pred = model.predict(X_val)` → `spearmanr(y_val, y_pred)`。X 只有一列时 Pipeline 是 `imputer → scaler → Ridge`，预测为 $\hat y = a\cdot x_{scaled} + b$，**严格单调**。故
  $$\text{Spearman}(y_{val}, \hat y) = \operatorname{sign}(a)\cdot \text{Spearman}(y_{val}, x_{val})$$
  **`alpha`、标准化、正则化对这个指标一概无影响**（只影响 MAE）。三条 CV 因此不是"三种模型验证"，而是三种**划分方式下的原始秩相关平均**——**并且没有任何一条做去混杂**。三个直接后果：
  - `composite_score` 是**原始**关联的度量，却与 `deconfounded_spearman` 并排放在同一张表里、并被用作"最强组合"和"组合优于单描述符"的判据；
  - LOSO 的每折 Spearman ≈ 留出体系内的原始 Spearman（符号取自另两体系），**与 V3 `per_system` 几乎是同一个量**，二者作为"独立证据块"并列呈现；
  - `anion_stratified_cv` 按 anion **分层**意味着验证折内**混合多种阴离子类型**，其 Spearman 因此大量由阴离子间的差异驱动——**这正是管线声称要消除的那个混杂**。该指标在构造上就是被混杂的。

## L. Causal Claim Boundary（stat-pipeline 专项）

- **清单判定: WARN**（清单上限）／**审稿人判定: 这是全项目最危险的一处，且与你手稿标题直接冲突**
- **Evidence**: `deconfound.py` 模块 docstring；`run_info.yaml:deconfound.confounders` 注释；`deconfound.py:_classify_descriptor`；`combination.py:full_validation` / `_factor_spanning`（`causal_claim: False`）；`run_pipeline.py:generateReport`（Stage 4 表末列硬编码 `探索性`、结论段 `物理发现` / `signal_retention`）；`README.md`；`program.md`
- **Details（逐项）**：

  **先给分——纪律层面做得比多数同类项目好：** `run_info.yaml` 有 `combination_validation.causal_claim: false` 与 `c9_cross_track_review.interpretation`（"结果一致…不构成因果证据"）；README 写"当前检出的是关联性/预测稳健性证据，不建立因果关系"；`program.md` 写"结果应标明探索性，不作因果陈述"并要求"某描述符与体系标签高度共线时，先报告它是体系代理的可能性"；代码里 `causal_claim: False` 在 `_factor_spanning`、`full_validation`、每条 `validate` 记录中一致设置，且 `COMBINATION_VALIDATION_RESULT_COLUMNS` 含该列，能进 CSV。

  **但以下五条抵消了上述纪律：**

  **1. 混杂集是被断言的，不是被论证的；而 `system` / `anion_type` 更像中介变量而非混杂变量。** `run_info.yaml` 的注释白纸黑字写着"**这些变量与目标相关但不是因果通路**"——**这是一个明确的、承重的、未经任何检验的因果论断。** `deconfound.py` 的模块 docstring 更进一步："混杂变量（如体系分类 system、阴离子类型 anion_type）**同时影响**描述符 X 和电导率 Y"——这是在陈述一个 DAG。
  
  问题在于反向更可信：`anion_type`（O/S/Cl/Br/I）通过阴离子极化率 → Na–阴离子键软度 → 迁移势垒作用于电导率，**这是结构→电导的因果通路本身**；`system`（NASICON/sulfide/halide）是骨架族的粗标签，很大程度上是结构的**下游后果**。**对中介变量做条件化会减掉你要找的效应；若 `system` 同时受某个未观测因素影响，条件化还会开启对撞路径引入新的偏倚。** 项目从未画出、也从未辩护这个 DAG。
  
  **叠加 K.5 的不可逆闸门，后果是：真实机制若走体系间通路，会被标成"体系代理"并在 Stage 1 被永久删除。** 这不是措辞问题，是**主指标可能在系统性地删除答案**。

  **2. 你的手稿标题与代码的免责声明直接冲突。** 你的方法章节题为**"因果去混杂搜索方法"**，而代码里每一条记录都写 `causal_claim: False`、`"interpretation": "predictive_association_after_known_factors_not_causal"`。**审稿人只要同时看到标题和 SI 里的 `causal_claim: False`，就会认定标题过度声称。** 这一条我建议在投稿前优先处理——它比本审计里任何一条统计问题都更容易导致直接拒稿。

  **3. "去混杂 / deconfounded" 这个术语本身就是 term-of-art 越界。** 在因果推断文献里 deconfounding 意味着满足后门准则的充分调整，即可识别因果效应。此处它的实际内容是"对两个观测到的分类协变量做 Ridge 残差化"。**当 `deconfounded_spearman` 被指定为 `primary_metric`，读者的默认读法就是"扣除混杂之后的效应"。**

  **4. 标签体系把统计阈值直接翻译成物理断言。** "强物理信号"仅由 `|deconf_rho| > 0.3` 单条件触发——不看 p（`deconf_p` 参数被忽略，D.1）、不看 n、不看 CV、不做多重性校正、且建立在一个欠调整的残差上（I.4）。**"物理信号"离"物理原因"只有一步，而报告把标签分布当作 headline 印在 Stage 1 结论里。** "体系代理比"同理（I.3）。

  **5. 报告层的免责声明是装饰性的、且有一处自相矛盾的 headline。**
  - Stage 4 表末列的 `探索性` 是 f-string **硬编码**，不读 `row["causal_claim"]`——该标志若哪天翻成 True，报告照印"探索性"。免责声明与数据脱钩。
  - 结论段小标题是 **"物理发现"**（physical findings），下辖"最强单描述符""最强组合"。
  - **"去混杂后信号保留率: 102.5%"**（你上一轮的实际输出）会被读成"扣除混杂后 102.5% 的信号得以保留"——一个大于 100% 的"保留率"，配上因果味的措辞，是审稿人一眼就会圈出来的。

---

## Overall Verdict: **FAIL**

判定由 **H（FAIL）** 单独决定：四级全量目标依赖选择 → 无外层循环的 CV，且项目内唯一的乐观偏差承认（`selection_uncertainty_included: False`）在 `CombinationValidator.validate` 扁平化时被丢弃，不进入任何 CSV 或报告。叠加 H.6（噪声基线不对称，项目自带的假阳性对照失效）与 K.6（单列公式下 CV 退化为未去混杂的折内原始 Spearman），**报告中"稳健性"一节的三个数字目前都没有支撑它们的证据结构。**

与你上一轮 A–H 审计（7 项 FAIL）相比：**G 项已从 FAIL 转为 PASS/WARN**——折内填充与标准化、子样本内独立预处理确实做对了，这是实质进步。新增的 I–L 四项则暴露了上一轮清单覆盖不到的、更深的问题层（欠调整的 Ridge、被忽略的 p 值、绝对值掩盖方向、中介变量当混杂变量）。

## Action Items

**阻断级（投稿前必须处理）**

1. **画出并辩护 DAG，或改口径。** 明确论证 `system` / `anion_type` 是混杂而非中介。若无法论证——我认为很难——则删除 `run_info.yaml` 中"这些变量与目标相关但不是因果通路"的断言，把 `deconfounded_spearman` 更名为 `within_system_partial_spearman`（描述性、无因果承诺），并**同时报告去混杂前后两组结果**，让读者自行判断被减掉的是混杂还是机制。
2. **手稿标题去掉"因果"**，或补上可识别性论证。改成"分层偏相关描述符搜索方法"之类，与代码的 `causal_claim: False` 对齐。
3. **加外层嵌套验证**：外层按 `system` 分组留出，内层完整重跑 Stage 1 预筛 + 稳定性选择 + 代表选择 + 组合排序 + top-k，仅在外层留出组上报分。这是唯一能给出无偏 CV 数字的做法。若算力不允许，**至少把 `selection_uncertainty_included: False` 加进 `COMBINATION_VALIDATION_RESULT_COLUMNS`，并在 `final_report.md` 顶部加一句明文："下表所有 CV 分数条件于在同一 84 行上完成的特征选择，为乐观偏差估计。"**
4. **修正噪声基线的对称性**：让噪声列与真实描述符走**完全相同**的 Stage 1 预筛（噪声列同样计算 `deconfounded_spearman`、同样按 `pass_labels` 过滤），否则 `above_noise_baseline` 应从产物中删除而非误导读者。
5. **把 `deconf_p` 接进 `_classify_descriptor`，并加 BH-FDR 校正**（38 个描述符一族、150 个组合候选另一族分别控制）。当前"强物理信号"不含任何显著性要求。
6. **给 `_evaluate_candidate` 加 `n_valid` 下限**（建议 ≥ 30 或 ≥ 全样本 50%），并让 `partial_spearman` 的静默回退**返回一个 `deconfound_applied: False` 标志**而非默默返回原始 rho。当前 5 个有效点的 ratio 可以排到第一名。

**高优先级**

7. **`DeconfoundAnalyzer` 的 Ridge 改用 `alpha=0`（即 OLS）**。分类混杂的 one-hot 设计经 `drop_first` 后满秩，OLS 残差化等于组均值中心化，是精确的饱和调整；`alpha=1.0` 只带来偏差，且对小 anion 组高达 26% 的欠调整。同时**把混杂残差化的 alpha 与预测 Ridge 的 alpha 拆成两个参数**——当前两个角色共用 `args.alpha`。
8. **`composite_score` 增加带符号版本**（`composite_signed_score` + `direction_consistent: bool`），并把逐折 rho 改为 Fisher z 平均后反变换。当前 +0.5/−0.5 与 +0.5/+0.5 在表格里完全无法区分。
9. **重写 `signal_retention`**：改为逐描述符 `deconf_rho²/raw_rho²` 的中位数并给分位区间，或直接删除。当前的"均值之比"产出了 102.5% 这个自我否定的数字。
10. **修 `delta_pct`**：仅在两侧 `composite_strategy_count` 相等时计算，否则输出 `不可比`。并统一"最强组合"的定义（按 composite 还是按 deconf rho，二选一）。
11. **`consistency_desc` 改为逐候选计算**，不跨候选汇总；`len(signs) < 3` 时禁止输出"优秀"；修正 `"所有CV策略均无显著相关"` 这个错误措辞。
12. **`_encode_controls` 加显式断言**：测试折出现训练折未见的 `system`/`anion_type` 类别时，记 `fold status = skipped` 并给出 reason，不静默当参考类。

**中优先级**

13. 让 `run_info.yaml` 真正驱动代码（`stability_selection` 三参数、`cv_strategies` 四参数、`anion_stratified_cv` 的 `random_state`），并让 `--seed` 通到全部 CV。当前"冻结契约"名不副实。
14. 把 `noise_info_df` 落盘（`stage2_noise_columns.csv`），并跑 ≥5 个噪声种子报告基线的抖动范围。
15. 删除 `_base.py:CROSS_GROUP_RULES`（第二套规则真值源）、`_one_hot_encode`；把 `_formula_dimensionally_valid` 的 multiply/ratio 量纲结论真正用起来，或至少禁止 `categorical_index`（`space_group_number`）参与任何算术。
16. 统一 41 / 38 的口径；修 `analyze_all` docstring 的"80%"（实际不存在）；`runStage4` 的形参改名以区分 `filtered_deconfound_df` 与 `deconfound_df`。
17. Stage 3 / Stage 4 报告表格增列 `n_valid`。
18. V1 置换从 100 提到 ≥2000；V4 bootstrap 改 BCa。
19. 报告 F/G 族无跨族规则、只能同族配对且无法进三元组——当前搜索空间的不对称对读者不可见。
20. 在数据层补 **温度 / 测量方法 / 体相-晶界** 列并纳入混杂集；若确实拿不到，必须在 Limitations 里明写这是未受控的支配性混杂。

## Claim Impact

- **Claim 1（关联性/预测稳健性，非因果）: needs_qualifier。** 非因果的**措辞纪律**在 README/program.md/代码标志层面到位（给分）；但主指标名为 `deconfounded`、配置断言 confounders"不是因果通路"、手稿标题含"因果"，三者合起来构成实质因果声称。"预测稳健性"部分则**不成立**——CV 条件于选择、且未去混杂。
- **Claim 2（去混杂后信号保留）: unsupported。** `signal_retention` 是"均值之比"、跑在未筛集合上、由最大 raw rho 单独支配，并已产出 102.5% 这个不可能值；叠加 Ridge 欠调整（I.4）使残差保留 5%–26% 的混杂，"保留"的一部分本来就是没减干净的混杂。
- **Claim 3（跨 CV 策略一致性）: unsupported。** 四条独立理由：`composite_score` 取绝对值掩盖符号翻转；折内先做带符号平均再取绝对值，双层掩盖；LOSO 与 V3 在单列公式下近乎同一个量，非独立证据；`anion_stratified_spearman` 因验证折混合阴离子类型而在构造上被混杂。`consistency_desc` 可由单个符号印出"一致性优秀"。
- **Claim 4（组合优于单描述符）: unsupported。** 用"~150 选 10"的组合对比"38 选 1"的单描述符，两者在同一批 84 行上选出、无外层循环，选择优势不对等；composite 在不同可用策略数下直接相除；"最强组合"按 deconf rho 选出却用 composite 打分。**并且你上一轮的实际结果（组合 0.475 vs 单描述符 0.479）本身就没有支持这条 claim——在偏差全部有利于组合的条件下它仍然输了，这实际上是比数字本身更强的负面证据。**

## Top 3 Critical Findings（stat-pipeline 专项）

**1. 混杂集可能是中介集——主指标有系统性删除答案的风险，且这是不可逆的。**
`run_info.yaml` 断言 `system` / `anion_type`"不是因果通路"，`deconfound.py` docstring 断言二者"同时影响 X 和 Y"，**两条论断均未经检验**。而 `anion_type` 经极化率→键软度→迁移势垒作用于电导率，正是结构→电导通路本身；`system` 是骨架族标签，很可能是结构的下游。对中介条件化会减掉待测效应。叠加 `runStage1` 的 `pass_labels` 会把被打成"体系代理"的描述符**永久剔除**（Stage 2/3/4 无法回收），管线可能在系统性删除真实机制。这一条同时决定了 L 的判定和你手稿标题的存亡。

**2. 四级全量目标依赖选择 → 无外层循环的 CV，而项目内唯一的承认在写盘前被丢掉。**
Stage 1 预筛（你的数据上 38→6，砍掉 84%）→ Stage 2 稳定性选择（限定在已筛集合内）→ `PhysicalGrouper` 按全量 `|deconf_rho|` 选代表 → Stage 3 按全量 `combined_deconf_spearman` 排序 → Stage 4 取 top-10 在**同样 84 行**上跑 CV。`full_validation` 确实生成了 `"selection_uncertainty_included": False`，但 `validate()` 只提取 `uncertainty_method`（还是硬编码字符串），该标志**不在 `COMBINATION_VALIDATION_RESULT_COLUMNS` 中，不进 CSV，不进 `final_report.md`**。读者拿到的唯一免责声明讲的是因果，不是乐观偏差。**并且这个偏差还被放大了：`runStage2` 里真实描述符已过 Stage 1 目标筛，15 个噪声列没有——项目自带的假阳性对照因此系统性偏向真实描述符，`above_noise_baseline` 基本不携带控制信息。**

**3. 单列公式下，"多策略 CV 验证"在代数上退化为未去混杂的折内原始 Spearman，因而无法佐证任何去混杂结论。**
`_fold_metrics` 对单列 X 走 `imputer→scaler→Ridge` 后预测是严格单调变换，故 `Spearman(y_val, ŷ) = sign(a)·Spearman(y_val, x_val)`——**`alpha`、标准化、正则化对该指标一概无效**（只影响 MAE）。于是：`composite_score` 度量的是**原始**关联，却与 `deconfounded_spearman` 并列在同一张表、并充当"最强组合""组合优于单描述符"的判据；LOSO 与 V3 `per_system` 近乎同一个量却被当作两个独立证据块；`anion_stratified_spearman` 因验证折内混合阴离子类型，在构造上恰恰被它声称要消除的那个混杂污染。**"跨 CV 策略一致性"这一节目前没有独立信息量。**

---

**本次审计的覆盖限制（明确列出，勿视为已通过）**：(a) 41 个描述符的实现文件未提供，描述符物理正确性完全未审；(b) 无真实行号，定位为 `file:符号名`，且传输损坏与真实 bug 不可区分（`_base.py:find_interstitial_sites` 的缩进、`generateReport` 的缩进请自行核对）；(c) `results/` 按你要求排除，所有数字级核对未做——**其中 `naconductor_featurized.csv` 为全 NaN 占位、results/ 未提交这两项已知复现性缺口仍然悬着，在数据集定稿前，上述所有 claim 的数字都是暂定的**；(d) `run_status.py` / `plot_run_results.py` / `test_descriptors.py` 未提供，Agent 轨的停止判据未审。
