**审计 rubric**：stat-pipeline profile（A–H 八项），拒稿视角。判定锚定在所提供代码/配置本身，不因作者立场调整。

**两点边界声明**（不是判定，是本次审计的可信度前提）：

1. 嵌入文件未带行号，且缩进在传输中已被破坏（`def__init__`、`intercept = np.ones(...)` 等）。缩进异常在 5 个文件中均匀出现，我判定为粘贴伪影，**不作为发现报告**。Evidence 一律用 `文件:符号锚点` + 原文引用定位。
2. `descriptors/featurizer.py`、`combination.py`、`cv_strategies.py`、`automat_utils.py`、`run_config.py` 未提供。凡结论依赖这些模块的，我明确标注"不可核验"，不以缺失充当 FAIL。

---

### A. Target Variable Provenance: FAIL

- **Evidence**: `run_info.yaml:data`（`target_column: log_sigma`，列清单仅 `material_id / formula / system / anion_type / cif_path / log_sigma`）；`run_info.yaml:task.description`（"log10(σ/S·cm⁻¹)"）；`run_pipeline.py:runStage0`（`y = raw_df[args.target_column].values.astype(float)`）；`run_info.yaml:deconfound.confounders`（`system`, `anion_type`）
- **Details**:
  1. **数据模式中不存在任何测量条件列**。没有温度、没有测量方法（EIS/直流极化）、没有 total/bulk/grain-boundary 区分、没有样品制备（冷压 vs 烧结 vs 单晶）、没有文献来源 ID。σ 是 Arrhenius 量，同一材料在 25 °C 与 300 K 之外的报道值可差数量级；bulk 与 total 电导率对同一样品可差 2–3 个量级。**这些信息不在 schema 里，因此"可通约性"这个问题在当前数据结构下连提都提不出来**，更谈不上论证。清单 A2 要求的"units, conditions, measurement methods commensurable"论证，全文零处。
  2. **异质来源被合并且合并本身就是设计目的**。NASICON / sulfide / halide 三体系汇入同一 `log_sigma` 向量，LOSO-CV 明确要求跨体系外推（`run_info.yaml:cv_strategies` 策略 2）。清单 A3 的 FAIL 条件（heterogeneous sources pooled with no stated commensurability argument）直接命中。
  3. **来源级属性与预测变量的相关性有具体机制，且被 system 控制项部分吸收**。硫化物普遍室温冷压测量、氧化物普遍高温烧结后测量——测量条件与 `system` 高度共线。把 `system` 当混杂控制的直接后果是：**温度/制备条件的组间差异被当成"体系效应"扣掉了，而组内的测量异质性完全没有被控制**。于是 Stage 1 声称的"去混杂后残留 = 体系内部物理相关"，实际是"体系内部物理相关 + 体系内部测量异质性"，两者不可分离。这不是保守偏差，方向不确定。
  4. 目标已做 log 变换（配置在 `combination.forbidden_operators` 处以此为由禁 log 算符）。log 变换本身合理，但它把乘性测量误差转成加性——在没有误差量级估计的情况下，Spearman 的秩稳健性被当作免死金牌使用，而秩相关对**系统性**的组间偏移毫无抵抗力。

> A 是本次审计后果最重的一项。它不是代码 bug，改代码解决不了。

---

### B. Metric Self-Reference: FAIL

- **Evidence**: `deconfound.py:_classify_descriptor`（`if abs(deconf_rho) > 0.3: return "强物理信号"` 及其上方注释 "无论代理比多高"）；`deconfound.py:analyze_all`（`system_proxy_ratio = 1.0 - deconf_rho_sq / raw_rho_sq`、`max(0.0, min(1.0, ...))`）；`run_pipeline.py:generateReport`（`signal_retention = (deconf_rho_sq / raw_rho_sq * 100)`、`delta_pct = ((best_comb_score - baseline_composite) / abs(baseline_composite) * 100)`）
- **Details**:
  1. **复合标签可以奖励管线自身定义为失败的结果——这是 B 的 FAIL 条件，且可精确构造**。`_classify_descriptor` 把 `|deconf_rho| > 0.3` 置于代理比判断之上，注释明写"无论代理比多高"。代入：`raw_rho = 0.9, deconf_rho = 0.31` → `system_proxy_ratio = 1 − 0.0961/0.81 = 0.881`。即**一个按管线自己的定义有 88% 的相关（R² 意义上）由体系混杂驱动的描述符，被标为"强物理信号"**。而 `deconfound.py` 模块 docstring 的整个立论是"接近 1 → 描述符是体系代理"。同一份文件里，一条规则宣布另一条规则的失败判据无效。标注为"errata P3 核心修正"说明这是**看过结果之后**做的改动。
  2. **`system_proxy_ratio` 是同一样本、同一次拟合的自指比值**。分子分母均来自同一 n 上的同一对 (x, y)，且分母 `raw_rho²` 在弱信号区本身噪声主导。代码用 `raw_rho_sq < 1e-12` 兜底、用 clip 到 [0,1] 收尾——这是把不稳定性藏起来，不是消除。
  3. **clip 销毁了方向信息**。`deconf_rho > raw_rho`（抑制效应，或 84 行上 Ridge 对混杂设计的过拟合）会产生负比值，被 clip 成 `0.0`，即"最纯物理信号"。**去混杂反而增强相关这一最该被警惕的情形，被编码为最高信誉等级。**
  4. **`signal_retention` 只报导出量，且是"均值之比"而非"比之均值"**。`mean(deconf²)/mean(raw²)` 由 `raw_rho` 最大的那一两个描述符主导，实质是单描述符统计量伪装成聚合指标；且分母含全部"噪声级"描述符。它可以超过 100%——一旦超过，"保留率"这个词就失去了任何字面意义，而报告仍以 `### 稳健性评估` 的标题呈现。原始的两个均值都没有单独报出。
  5. **`delta_pct` 的分母取绝对值，两个分支都错**：若 `composite_score` 是有符号量，`baseline = −0.5 → comb = +0.1` 会输出"提升 120%"，而相关方向已经翻转；若 `composite_score` 是 |ρ| 基础量，则它丢弃了同一份报告在 `consistency_desc` 里当作决定性证据的方向信息（"方向不一致，需谨慎解读"）。`cv_strategies.py` 未提供，无法确定是哪一支——**但两支都构成 B2/B3 的失败，所以这一条不依赖缺失文件即可判定**。
  6. **`composite_score` 跨不同策略子集直接相减**。`composite_strategy_count` 显示可用策略数（x/3），说明被跳过的策略不计入。于是一个 1/3 策略算出的组合 composite，与一个 3/3 策略算出的基线 composite 相减、再除以后者——分子分母的定义域不同。而 `validation_df.iloc[0]` 就是按此量排序后的"最强组合"。

---

### C. Result File Existence: NOT_APPLICABLE

- **Evidence**: `run_pipeline.py:runStage1/runStage2/runStage3/runStage4/generateReport` 的全部 `to_csv` / `write_text` 目标；`run_info.yaml:tracks`
- **Details**:
  1. 本 prompt 未嵌入任何结果产物，无法核验存在性或数值一致性。**缺失清单（9 个 Pipeline 产物）**：`results/pipeline/` 下的 `stage1_deconfound_results.csv`、`stage1_prefiltered_results.csv`、`stage2_stability_results.csv`、`stage2_representatives.csv`、`stage3_combination_candidates.csv`、`stage4_validation_results.csv`、`stage4_single_descriptor_baseline.csv`、`final_report.md`、`final_report.json`；另缺 `data/naconductor_raw.csv`、`data/naconductor_featurized.csv`，以及 `results/agent/` 下四个产物。
  2. 提供的文件中不含任何**已声称的数值**——`generateReport` 是纯 f-string 模板。因此即使有结果文件，本 prompt 内也没有可比对的 claim。C2 无对象。
  3. C3（占位文件 vs 真实输出）**必须优先核查 `data/naconductor_featurized.csv`**：若该文件为占位（例如描述符列全 NaN），则 Stage 0 的 `--skip-featurize` 路径会直接把占位数据送进 Stage 1，而下面 D 项指出的 80% 覆盖度过滤缺失会让极少数偶然非 NaN 的列存活。这一组合下管线**不会报错**，会正常输出一份完整报告。这是本次审计能给出的最高优先级核查项。
  4. 附带可核验项：`run_pipeline.py:runStage0` 的打印串 `"84 个 CIF × 41 个描述符"` 是硬编码字面量，而实际计数走 `len(raw_df)` 与 `len(registered)`。样本或注册表一变，这行输出即失真。

---

### D. Dead Path Detection: FAIL

- **Evidence**: `deconfound.py:analyze_all`（注释 `# 跳过 NaN 过多的列：有效值不足 80% 则跳过` 紧接 `if n_valid < 5: continue`）；`deconfound.py:_classify_descriptor`（形参 `deconf_p` 在函数体内零引用）；`deconfound.py:_one_hot_encode`；`deconfound.py:partial_spearman`（`if n_samples < 3 or z.shape[1] == 0 or z.shape[1] >= n_samples:` → `return stats.spearmanr(x, y)`）；`_base.py:CROSS_GROUP_RULES`；`stability.py` / `run_pipeline.py` 全文（`is_high_risk` 无消费点）
- **Details**:
  1. **声明的过滤器在代码中被绕过——D 的 FAIL 条件直接命中**。注释声明的是"有效值不足 80% 则跳过"（n=84 时门槛应为 68），代码执行的是 `n_valid < 5`。**一个只有 5 个非 NaN 值（覆盖率 6%）的描述符可以完整走完 Stage 1 并被打上标签**。80% 这个数字在整个代码库中不存在。
  2. **`deconf_p` 是死参数，而"显著"一词建立在它之上**。`_classify_descriptor` 接收 `deconf_p` 却从不使用；docstring 与行内注释均写"去混杂后仍然显著 → 强物理信号"。实际规则只测 `|deconf_rho| > 0.3`，**管线全程没有对去混杂相关做任何显著性判定**。与第 1 点叠加：`n_valid = 5` 且 `|deconf_rho| = 0.35` 的纯噪声列会被标为"强物理信号"。
  3. **静默回退把"未做去混杂"编码为"最干净的物理信号"**。`partial_spearman` 在 `z.shape[1] >= n_samples` 时直接返回**原始** Spearman 当作去混杂值。此时 `deconf_rho == raw_rho` → `system_proxy_ratio = 0.0` → 落入"弱物理信号"或"强物理信号"。**回退事件没有任何记录**：不进 metadata、不进 DataFrame、不打印。n_valid 小而混杂列数 = 2(system) + k(incremental anion) 时，这条路径可达。
  4. **`|raw_rho| < 0.2` 的前置门禁使 Stage 1 的声明目的部分失效**。`_classify_descriptor` 第一条分支就把 `|raw_rho| < 0.2` 判为"噪声级"并淘汰——**这发生在任何去混杂统计量被检视之前**。于是 `raw_rho = 0.15, deconf_rho = 0.45`（即体系混杂压制了真实的组内物理相关，抑制效应）这一情形被当作噪声丢弃。**去混杂最该负责发现的一类信号，被上游边际相关门禁系统性排除。**
  5. **`is_high_risk` 是不闸任何东西的风险旗标**。它在 `DECONFOUND_RESULT_COLUMNS` 中占一列、写入 CSV，但在 Stage 1 预筛选、Stage 2 eligibility（`eligible = result_df[result_df["is_stable"] & result_df["above_noise_baseline"]]`）、`PhysicalGrouper` 代表选择、报告生成中**全部零引用**。`_base.py:CROSS_GROUP_RULES` 里的 `high_risk_families: ["G","H"]` 同理：该常量在所提供的 5 个文件中从未被 import。
  6. **存在两套竞争的组合规则注册表**。`run_info.yaml:combination.pair_rules.source_of_truth` 指向 `descriptors.combination.PAIR_OPERATOR_RULES`，而 `_base.py` 独立定义了 `CROSS_GROUP_RULES`（`allowed_pairs`、`per_operator_restrictions`，含 A↔C 只许 ratio 不许 multiply）。**两者的关系无任何代码或注释说明**，`_base.py` 的那套在提供的文件里是孤儿。
  7. **D2 行数追踪断裂点（1 处，可判定）**：Stage 1 对 y 做了 NaN 掩码（`valid_mask = ~np.isnan(x_raw) & ~np.isnan(y_arr)`），Stage 4 基线也做了（`valid_mask = ~np.isnan(y_arr)`），**唯独 Stage 2 把未掩码的完整 y 直接送进 `selector.run(X_real, y, ...)`**。`StabilitySelector` 内的 `SimpleImputer` 只处理 X，`Lasso` 遇到 NaN 的 y 会抛错。二选一：y 无 NaN（则 Stage 1/4 的掩码是死码），或 y 有 NaN（则 Stage 2 崩溃）。无论哪种，三个阶段对同一 y 的契约不一致。
  8. **`build_rank_aware_controls` 的秩审计描述的不是实际使用的设计**。秩在**全样本**上计算一次，metadata 随后挂到 `result_df.attrs`；而每个描述符的实际残差化用的是行子集 `conf_valid = confounders_df.loc[valid_mask]`，子集可能使某个 one-hot 列全零，秩随之下降且不重算。另外 `control_columns` 元数据列出了 intercept 与**全部** anion 列，`residualization_columns` 只列 incremental 列——**同一份 metadata 内部就有两个不同的设计描述**。（该 metadata 是否流向报告的 `best_v2_control_audit` 需 `combination.py`，不可核验。）
  9. `_one_hot_encode`、`deconfounded_spearman` 在提供的文件中无调用点（后者可能被 `combination.py` 使用，不可核验）。`runStage3` 中 `_configured_max_descriptors()` 的无参调用会回落到默认 `run_info.yaml`，**忽略 `--run-info`**；当前 `main()` 总是显式传值，故为潜伏缺陷。
  10. 报告 Markdown 表格结构损坏：表头+分隔行之后是 `| {stage1_table} |    |...|`，而 `stage1_table` 已是以 `|` 开头的多行 join 串。首行与末行会被多余的管道符污染。

---

### E. Scope and Multiplicity: FAIL

- **Evidence**: `run_info.yaml`（`# 原始数据 84 行，全量参与交叉验证`）；`run_pipeline.py:runStage3`（`max_candidates=150`）；`run_pipeline.py:parseArgs`（`--top-k` default 10）；`run_pipeline.py:runStage4`（`best_single_row = deconfound_df.iloc[0]`、`best_comb_row = validation_df.iloc[0]`）；`run_info.yaml:combination_validation.selection_uncertainty`（`nested_outer_group_selection_available: false`）；`run_pipeline.py:generateReport`（`consistency_desc` 分支）
- **Details**:
  1. **实际规模**：84 样本，3 个体系组，8 个物理族。LOSO 只有 **3 折**，每折都是向一个全新化学体系外推；anion 分层 3 折；重复子采样 10 次 × 20% ≈ 17 个测试样本。Stage 2 的每次自举只用 `int(84×0.5) = 42` 行拟合 Lasso。
  2. **实际检视的假设数**：Stage 1 遍历全注册表（打印串称 41）；Stage 2 三描述符模式下每族 2 个代表 → 候选池上限 16；Stage 3 枚举至 `max_candidates=150`；Stage 4 验证 top-10 后取 `iloc[0]`。**报告的两个头条数字都是极值统计量**：最佳单描述符 = 41 中取最大 |ρ|，最佳组合 = 150 → 10 → 1。
  3. **零多重性控制——E 的 FAIL 条件命中**。全代码库无 FDR、无 Bonferroni、无置换检验、无嵌套外层选择。`deconf_p` 被算出来却既不用于分类也不做校正（见 D2）。配置自己承认 `nested_outer_group_selection_available: false`。`max_candidates=150` 是**报告截断**，不是校正；且截断发生在按同一统计量排序之后，本身就是又一次选择。
  4. **规模语言全面超出证据**。`stability.py` docstring："频率 > 阈值（默认 0.6）的特征才是'真信号'"；`run_info.yaml:task`："统计稳健的描述符组合"；报告标题 `### 稳健性评估`；一致性判词"全部同向，一致性优秀"。
  5. **"一致性优秀"的证据基数是 ≤9 个非独立观测**。`consistency_desc` 遍历 `validation_df.head(3)` × 3 策略 = 至多 9 个符号，来自**同一批 84 行**、**三个大概率共享分量的公式**、**三种在同一数据上切分的 CV**。这不是 9 个独立复现。更弱的是次级分支：`n_positive > n_negative * 2` 使 3:1 的符号分裂被判为"一致性良好"。
  6. **`np.sign(nan)` 的静默错判**：若某策略 available 但取值为 NaN，它计入 `len(signs)` 却不计入 `n_positive/n_negative`，全 NaN 时输出"所有CV策略均无显著相关"——在**没有做过任何显著性检验**的情况下使用"显著"一词，且把"未定义"报告成了"无相关"。
  7. **基线本身也是极值且未经 Stage 2 检验**：`deconfound_df.iloc[0]` 取的是 Stage 1 存活者中 |ρ| 最大的一个，**不要求它通过稳定性阈值或噪声基线**。这个未经稳定性检验的极值随后成为 `delta_pct` 的分母。

---

### F. Threshold Provenance: FAIL

- **Evidence**: `deconfound.py:__init__`（`alpha: float = 1.0`，docstring "默认 1.0，对小样本（~100）有一定正则化保护"）；`deconfound.py:_classify_descriptor`（0.2 / 0.3 / 0.3 / 0.7，标注 "errata P3"）；`deconfound.py:analyze_all`（`n_valid < 5`）；`stability.py:__init__`（`n_bootstrap=100, threshold=0.6, fraction=0.5`）；`stability.py:run`（`np.percentile(noise_freqs, 95)`）；`_base.py:_shell_neighbors`（`first + 0.70`，注释 "沿用 part1.py 的简化规则"）；`_base.py:_anion_cutoff`、`find_interstitial_sites`（`min_dist_from_atom=1.5`、去重 `0.5`）
- **Details**:
  1. **全部决定性阈值零外部依据，且结论对其敏感——F 的 FAIL 条件命中**。0.2 / 0.3 / 0.3 / 0.7 四个分类阈值决定了 Stage 1 的存活集合、标签分布、以及报告里的"物理发现"。四个都没有理论、文献或预注册出处，只标 "errata P3"——**"errata"这个词本身就表明规则是在看过输出后修订的**，这正是 F2 要排除的"derived from inspecting results"。
  2. **`threshold = 0.6` 的分辨率细于它所阈值化的统计量的蒙特卡洛误差**。100 次自举下频率的抽样标准误在 0.6 附近约 √(0.6×0.4/100) ≈ 0.049。**"频率 0.60" 与 "频率 0.65" 在一个标准误之内**，而管线用它做二值的 stable/not-stable 判定，且只跑一个种子、不做跨种子重复。Meinshausen–Bühlmann 的稳定性选择有配套的 E[V] 误差界来支撑 π_thr 的取值；此处取了常用区间 [0.6, 0.9] 的**最宽松端**，却没有实现任何误差界。
  3. **`alpha = 1.0` 的偏差方向不利于结论**。Ridge 惩罚施加在 one-hot 混杂设计上 → 类别均值被收缩 → **混杂只被部分扣除** → `deconf_rho` 系统性偏向 `raw_rho` → `system_proxy_ratio` 系统性偏低（偏向"物理信号"）。docstring 给的理由是"有一定正则化保护"，这是手感不是依据。
  4. **参考类编码 + L2 惩罚 = 结果不随参考类别选择而不变**。`pd.get_dummies(..., drop_first=True)` 按字母序丢首类（system ∈ {NASICON, halide, sulfide} → 丢 NASICON），惩罚项因此以 NASICON 为收缩锚点。**换一个参考类别，去混杂 ρ 会变**。这是方法学缺陷，不是调参问题。
  5. **零敏感性分析**。代码中不存在对 alpha、threshold、0.2/0.3/0.7、seed 的任何扫描。清单 F3 要求的 sensitivity check，全库为空。
  6. `n_valid < 5`、`min_dist_from_atom = 1.5`、去重 `0.5 Å`、`max_dist = 4.0`、`_anion_cutoff` 全表（3.20/3.35/3.85/4.05/4.35）均无出处。**对照鲜明**：同一文件里 `NA_EFFECTIVE_RADII_A` 注明 "来源: Shannon 经典有效离子半径表"、`ELECTRONEGATIVITY` 注明 Pauling 标度——**该文件知道怎么引用，未引用的那些因此更显眼**。`+0.70 Å` 的出处是"沿用 part1.py"，即内部旧脚本，属于溯源链而非依据。

---

### G. Null Distribution and Selection Effects: FAIL

- **Evidence**: `stability.py:run`（`noise_baseline = float(np.percentile(noise_freqs, 95))`、`above_baseline = freq > noise_baseline`）；`run_pipeline.py:runStage2`（`# Stage 2 只允许 Stage 1 预筛选后的真实描述符；固定噪声列全部保留`）；`deconfound.py:_classify_descriptor`；`run_pipeline.py:runStage3/runStage4`
- **Details**:
  1. **全库唯一的经验零分布是 Stage 2 的注入噪声列。没有任何置换检验、没有 y 打乱、没有跨种子重复。**
  2. **零分布被施加在错误的阶段——而且是可证的错误**。`runStage2` 的注释自己写明：真实描述符已经过 Stage 1 预筛选，噪声列则"全部保留"。**两臂不可交换**：真实特征是在同一个 y 上做过一轮筛选的幸存者，噪声列是未经筛选的新鲜样本。用后者给前者定基线，系统性地低估了通过难度。Stage 1 的选择完全没有零分布覆盖。
  3. **按管线自身规则，纯噪声变量的 Stage 1 存活率（构造性计算）**：
     - Stage 1 通过条件 = `|raw_ρ| ≥ 0.2` **且** (`|deconf_ρ| > 0.3` 或 `proxy < 0.7`)，其中 `proxy < 0.7 ⟺ |deconf_ρ| > √0.3·|raw_ρ| ≈ 0.548|raw_ρ|` 且同号。
     - n = 84 时 Spearman 零分布 SD ≈ 1/√83 ≈ 0.110。故 `P(|raw_ρ| ≥ 0.2) = 2Φ(−1.822) ≈ **6.9%**`。**这个门禁比未校正的 α = 0.05 还宽松**，并被重复施加 ~41 次、零校正。
     - 第二子句在给定 `|raw_ρ| ≈ 0.2` 时的条件通过率取决于 system 对 y 的解释力 R²；取 R² ≈ 0.5（`ρ(raw, deconf) ≈ 0.7`）估得约 0.65–0.70。
     - **总存活率 ≈ 4.5–5%；41 个纯噪声描述符期望存活 ≈ 2 个。** 若 Stage 1 实际存活数是个位数，则期望中有相当一部分是构造性噪声——这个背景率不能忽略，而管线从未把它算出来过。
     - 这个数字**管线自己就能精确得到**：把 y 打乱重跑 Stage 1 若干次即可。代码里没有这一步。
  4. **Stage 2 基线本身的两个缺陷**：(a) `np.percentile(noise_freqs, 95)` 按定义就允许 1/20 的噪声列越过基线——它不是一个零通过率的门槛；(b) 噪声列数目由 `featurizer.py` 决定（不可核验），若少于 ~20 列，95 分位数在数值上等同于最大值，**估计量不稳定**，这正是清单 G 的 WARN 条件"too few controls to estimate the quoted quantile stably"。
  5. **Stage 3 与 Stage 4 完全无零分布**。150 中取最优、10 中取最优，两次极值选择都没有对应的零分布对照。头条量 `best_single_rho`、`best_comb_score`、`delta_pct`、`signal_retention` **无一与任何零分布比较过，也无一带置信区间**。
  6. 唯一的不确定性量化是每组合的 `bootstrap_ci`（`system_stratified`, seed 42）。但它是在**选出 top 组合之后**算的条件区间，不是选择校正区间，必然反保守；且报告不为基线计算它。

---

### H. Randomness and Reproducibility: FAIL

- **Evidence**: `run_pipeline.py:runStage4`（`cv = MultiStrategyCV(alpha=alpha)` — 无 seed 实参）vs `validator = CombinationValidator(alpha=alpha, seed=seed)`；`run_info.yaml:stability_selection` / `deconfound` / `evaluation` 全块；`run_pipeline.py:runStage2`（`StabilitySelector(n_bootstrap=100, threshold=0.6, fraction=0.5, ...)` 字面量）；`run_pipeline.py:generateReport`（`_format_cv_metric` 读 `{prefix}_skipped`，`consistency_desc` 读 `{prefix}_available`）
- **Details**:
  1. **配置文件与代码描述的是不同的过程——H 的 FAIL 条件命中，且可精确列举**。所提供代码实际读取的 YAML 键**只有**：`data.*`、`shared_input.*`（经 `resolve_frozen_input_identity`）、`combination.max_descriptors`、`tracks.pipeline.output_dir`。**未被读取的包括**：整个 `stability_selection` 块（`selection_alpha` / `n_bootstrap` / `threshold` / `fraction` / `random_seed`）、整个 `deconfound` 块（`confounders` / `method` / `categorical_coding` / `primary_control` / `primary_metric`）、`evaluation.model.*`、`cv_strategies` 各策略参数、`combination.min_descriptors`、`combination.forbidden_operators`。数值目前**碰巧一致**（YAML 0.6 / 100 / 0.5 / 42 ↔ 代码字面量与 CLI 默认值），**因此改 YAML 不会改变行为，而实验记录会显示改过**。这是最危险的一类不一致：静默、不报错、且看起来是可复现的。
  2. **`deconfound.method: dml` 是无实现的可选项**。注释 `# 可选: partial_correlation, dml` 承诺了一个 DML 分支；`DeconfoundAnalyzer` 只有硬编码的 Ridge 残差化。同理 `deconfound.confounders` 的列表是装饰性的——混杂变量由 `analyze_all(system_labels, anion_labels)` 的函数签名固定，YAML 里加第三个混杂变量不会有任何效果。
  3. **CLI seed 不传播到 CV 阶段**。`MultiStrategyCV(alpha=alpha)` 未收到 seed，而 `CombinationValidator(alpha, seed)` 收到了。因此 `--seed 123` 会改变稳定性选择与组合搜索，**但（很可能）不改变基线 CV 的折划分**。更严重的是：基线 CV 与组合 CV 由**两个不同的调用点**构造，二者的折划分是否相同不可保证——**而它们的 composite_score 被直接相减产出 `delta_pct`**。两臂用不同折划分做的比较，其差值不可解释。（内部行为需 `cv_strategies.py` / `combination.py`，标为不可核验；但调用点的差异是可证的。）
  4. **单一种子 42 贯穿全部随机组件**：`stability_selection.random_seed`、`combination.bootstrap.random_seed`、`anion_stratified_cv.random_seed`、`repeated_subsample.random_seed`、`evaluation.model.random_seed` 全为 42，CLI 默认亦为 42。报告把 V1–V4 当四个证据块并以其一致性为佐证；**若这些块共享重采样划分，一致性有一部分是机械的，不是独立复现**。
  5. **`_available` 与 `_skipped` 是同一状态的两套键名，且都用 `.get()` 带默认值**。若 `cv_strategies.py` 只发 `_skipped`，则 `row.get(f"{prefix}_available", False)` 恒为 False → `signs` 恒空 → 一致性判词恒为"无可用CV策略"；若只发 `_available`，则 `_format_cv_metric` 永不输出 "SKIPPED"。**两种失效都不抛异常、不留痕迹。** 没有断言、没有 schema 校验。
  6. `Lasso(max_iter=20_000)` 未捕获 ConvergenceWarning；未收敛的系数可能 `|coef| > 1e-12` 从而虚增选中频率。风险低但无检查。
  7. **值得记入的正确做法**（拒稿视角不等于只记缺点）：`Pipeline([SimpleImputer, StandardScaler, Lasso])` 在每个子样本内独立拟合，注释明写"避免全数据填充/缩放泄漏"——**这一点做对了**；`build_rank_aware_controls` 显式做秩审计并记录冗余 anion 列，方法学意识在线；`_validate_pipeline_output_dir` 对双轨隔离的强制校验（拒绝绝对路径、拒绝 `..`、强制 `results/pipeline/` 前缀）是真正的防污染设计；`run` 中噪声列注入基线校准的**意图**正确（问题在施加阶段，不在概念）。

---

## Overall Verdict: FAIL

## Action Items

**必须修复（阻断性，按修复顺序）**

1. **B1 / D1 优先**：删除 `_classify_descriptor` 中 `|deconf_rho| > 0.3` 对代理比的无条件覆盖，或明确把该分支的适用域限制为 `system_proxy_ratio < 0.7`。当前形态下 88% 体系代理的描述符可被标为"强物理信号"，此项不修复则 Stage 1 的全部标签不可用。
2. **D1**：把 `if n_valid < 5` 改为注释所声明的 80% 覆盖度门槛（n=84 → 68），或改注释以匹配代码并另行论证 5 这个数。二选一，不能并存。
3. **D3**：`partial_spearman` 的回退分支必须**记录**（返回 `fallback=True` 并写入结果列），且回退样本的 `system_proxy_ratio` 应置 NaN 而非 0.0。
4. **D1**：把 `|raw_rho| < 0.2` 的"噪声级"判定移到去混杂统计量**之后**评估，或对 `raw_rho` 小但 `deconf_rho` 大的抑制效应单开一个标签。当前顺序使去混杂无法发现被混杂压制的信号。
5. **H4**：让代码真正读取 `run_info.yaml` 的 `stability_selection` / `deconfound` / `evaluation` 块，或从 YAML 中删除这些键。保留一份不被读取的配置比没有配置更危险。同时删除 `deconfound.method: dml` 或实现它。
6. **H1/H3**：把 `--seed` 传入 `MultiStrategyCV`；确保基线 CV 与组合 CV 使用**同一折划分**，否则 `delta_pct` 不可解释。为 bootstrap / stability / CV 分配**不同**的派生种子（如 `seed`, `seed+1`, `seed+2`）。
7. **H5**：统一 `_available` / `_skipped` 键名，并加断言使缺键抛错而非静默取默认值。
8. **G3**：加置换零分布——把 y 打乱重跑**完整 Stage 1→Stage 4**（≥200 次），报告头条 ρ 的置换分位数。这是唯一能同时解决 E3（多重性）和 G2（零分布施加阶段错误）的改动，优先级高于其余统计修补。
9. **G2**：噪声列必须**与真实描述符走同一条 Stage 1 路径**，否则 Stage 2 基线无意义。
10. **B5/B6**：`delta_pct` 必须要求两臂 `composite_strategy_count` 相同才计算，否则输出 `INCOMPARABLE`；分母不取绝对值或改报差值而非百分比。
11. **C3**：核查 `data/naconductor_featurized.csv` 是否为占位文件。在第 2 项修复前，占位数据可以静默走完全流程并产出一份格式完整的报告。

**应修复（非阻断）**

12. **F5**：补 alpha ∈ {0.1, 1, 10}、threshold ∈ {0.6, 0.7, 0.8}、0.2/0.3/0.7 各 ±0.05 的敏感性表。若结论随之改变，则该结论本就不该报告。
13. **F4**：把参考类编码换成 sum-to-zero 编码，或对 one-hot 列不施惩罚（`Ridge` 前把混杂设计正交化），消除结果对参考类别选择的依赖。
14. **D8**：秩审计改为在**实际残差化用的行子集**上重算；修正 `control_columns` 与 `residualization_columns` 的自相矛盾。
15. **D5/D6**：`is_high_risk` 要么接入筛选，要么从结果 schema 中移除；`_base.py:CROSS_GROUP_RULES` 与 `combination.PAIR_OPERATOR_RULES` 二选一，另一个删除。
16. **B4**：`signal_retention` 改为逐描述符比值的分布（中位数 + IQR），并排除"噪声级"描述符；或直接从报告中删除——它现在能超过 100%，超过后这个词就没有字面意义了。
17. **A**：在数据 schema 中增加 `measurement_temperature`、`conductivity_type`（total/bulk/gb）、`source_doi` 三列。这不是代码改动，是数据重建，但 A 项在补齐前无法转为 PASS。
18. **D10 / C4**：修复报告 Markdown 表格拼装；把 `"84 个 CIF × 41 个描述符"` 改为 f-string。

## Claim Impact

- Claim 1（"最强单描述符 X，去混杂 Spearman = ρ" 作为物理发现）: **unsupported** — 41 中取极值、零多重性校正、零零分布对照；且 Ridge 收缩使 ρ 系统性偏高、参考类编码使其不唯一。
- Claim 2（"最强组合 …，综合得分 …"）: **unsupported** — 150→10→1 的三重极值选择，无零分布；`composite_score` 可跨不同策略子集比较。
- Claim 3（"组合相比单描述符提升 X%"）: **unsupported** — 分母取绝对值、两臂策略子集可不同、两臂折划分可不同；基线本身是未经稳定性检验的极值。
- Claim 4（"跨CV策略一致性：全部同向，一致性优秀"）: **unsupported** — 证据基数 ≤9 个非独立符号观测；且该分支可能因 `_available`/`_skipped` 键名不一致而永不可达。
- Claim 5（"去混杂后信号保留率 X%"）: **unsupported** — 均值之比、由最大 raw_ρ 单点主导、分母含噪声级描述符、可超过 100%。
- Claim 6（描述符标签"强物理信号"）: **needs_qualifier** — 该标签当前允许 `system_proxy_ratio ≤ 0.91`、不含任何显著性检验、且可由 `n_valid = 5` 的列或未实际执行去混杂的回退路径获得。修复 Action Item 1–3 后可降级为可用。
- Claim 7（双轨隔离与冻结输入契约有效）: **supported** — `_validate_pipeline_output_dir` 与 `resolve_frozen_input_identity` 在代码层面确实强制执行了 `run_info.yaml:tracks` 的 `must_not_read` 约定。这是本次审计中唯一一条经代码验证成立的声明。
- Claim 8（"每个子样本独立拟合预处理，避免泄漏"）: **supported** — `stability.py:run` 的 Pipeline 构造与该声明一致。
