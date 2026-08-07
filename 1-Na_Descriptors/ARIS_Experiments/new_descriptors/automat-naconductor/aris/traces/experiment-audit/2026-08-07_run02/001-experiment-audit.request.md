【会话指示 - experiment-audit（stat-pipeline 专项，run02）】

1. 本模板为单轮一次性审计。复制下方"prompt 正文"全部内容，粘贴到【新的】Claude 对话中。
2. 本次审计是 stat-pipeline（统计管线）专项：在标准 A-F 完整性检查基础上，额外执行 G-L 六项统计管线泄露/偏差专项检查（数据泄露、特征选择泄露、去混杂方法学、多重比较、目标与指标定义、因果声明边界）。
3. 审稿人返回回复后，复制回复全文回执行器，执行器解析后写入 aris/EXPERIMENT_AUDIT.md、aris/EXPERIMENT_AUDIT.json 和 aris/traces/experiment-audit/2026-08-07_run02/。
4. 单一对话完成所有 12 项检查（A-L）——不要分多次对话。
5. 如需对单一检查项追问细节，可在同一对话中继续。
6. 何时开新对话：仅当需要重新审计（不同时间点的代码状态）时开新对话。
7. 本项目无 paper/ 目录、无 NARRATIVE_REPORT.md、无 EXPERIMENT_TRACKER.md——声明来源是 README.md + program.md + run_info.yaml。results/ 和 data/naconductor_featurized.csv 已按用户要求排除。
8. 本次为 run02（run01 已于 2026-08-07 完成）；审稿人无需参考既往审计，独立判断。

=====================================================================
prompt 正文（复制以下全部内容到新的 Claude 对话）
=====================================================================

You are an experiment integrity auditor specializing in **statistical pipelines for materials informatics**. Read ALL file contents listed below and check for fraud patterns AND statistical-pipeline leakage/bias.

This is a **stat-pipeline专项 audit**. The project under audit is a Na-ion conductor descriptor search pipeline that:
- Computes 41 CIF-derived structural descriptors for ~84 samples
- Performs deconfounded Spearman correlation (controlling for `system` + incremental `anion_type`)
- Runs stability selection (subsampled Lasso) + physical-family representative selection
- Enumerates physics-constrained descriptor combinations (pairs and bounded triples)
- Validates top-k combinations with multi-strategy CV (anion-stratified, LOSO, repeated subsample) + V1-V4 exploratory evidence

The project explicitly claims **association/predictive robustness, NOT causation**. Your job is to verify the statistical pipeline is leak-free and the claims match the evidence.

## 你的任务

按以下审计清单逐项检查，每项报告 Status (PASS | WARN | FAIL)、Evidence (精确的 file:line 引用)、Details (具体发现)。

## 审计清单

### A. Ground Truth Provenance
For each evaluation script:
1. Where does "ground truth" / "reference" / "target" come from?
2. Is it loaded from the DATASET, or generated/derived from MODEL OUTPUTS?
3. If derived: is it explicitly labeled as proxy evaluation?
4. Are official eval scripts used when available for this benchmark?
FAIL if: GT is derived from model outputs without explicit proxy labeling.

### B. Score Normalization
For each metric computation:
1. Is any metric divided by max/min/mean of the model's OWN output?
2. Are raw scores reported alongside any normalized scores?
3. Are any scores suspiciously close to 1.0 or 100%?
FAIL if: Normalization denominator comes from prediction statistics.

### C. Result File Existence
For each claim in the paper/narrative:
1. Does the referenced result file actually exist?
2. Does the claimed metric key exist in that file?
3. Does the claimed NUMBER match what's in the file?
4. Is the experiment tracker status DONE (not TODO/IN_PROGRESS)?
FAIL if: Claimed results reference nonexistent files or mismatched numbers.
NOTE: results/ directory is excluded from this audit by user request. Focus on whether the CODE would produce consistent artifacts, not on verifying specific saved numbers.

### D. Dead Code Detection
For each metric function defined in eval scripts:
1. Is it actually CALLED in any evaluation pipeline?
2. Does its output appear in any result file?
WARN if: Metric functions exist but are never called.

### E. Scope Assessment
1. How many scenes/datasets/configurations were actually tested?
2. How many seeds/runs per configuration?
3. Does the paper use words like "comprehensive", "extensive", "robust"?
4. Is the actual scope sufficient for those claims?
WARN if: Scope language exceeds actual evidence.

### F. Evaluation Type Classification
Classify each evaluation as:
- real_gt: uses dataset-provided ground truth
- synthetic_proxy: uses model-generated reference
- self_supervised_proxy: no GT by design
- simulation_only: simulated environment
- human_eval: human judges

### G. Data Leakage in Preprocessing (stat-pipeline 专项)
For each preprocessing step (imputation, standardization, noise injection):
1. Is median imputation fitted on the FULL dataset, or only inside each CV training fold?
2. Is StandardScaler fitted on the FULL dataset, or only inside each CV training fold?
3. Are noise columns injected once globally with a fixed seed, or re-injected per fold? (Global fixed-seed injection is acceptable IF they are pure controls, not features that leak target info.)
4. In stability selection's subsampling, is preprocessing fitted on each subsample independently, or on the full dataset?
5. In deconfounding (Ridge residualization), is the Ridge fitted on the full dataset, or only on the training portion within each CV fold?
FAIL if: Any preprocessing that uses target or feature statistics from validation/test data is fitted outside the CV fold.

### H. Feature Selection Leakage (stat-pipeline 专项 — CRITICAL)
This is the highest-risk area. Check:
1. Stability selection runs on the FULL dataset to select "stable" descriptors, then CV evaluates the SELECTED descriptors. Is this selection-then-evaluate leakage? (Selecting on full data, then CV on selected = optimistically biased CV scores.)
2. Combination search ranks candidates by `combined_deconf_spearman` computed on the FULL dataset, then validates top-k with CV. Is this top-k selection leakage?
3. The `PhysicalGrouper` picks representatives by `|deconfounded_spearman|` computed on full data, then CV validates them. Leakage?
4. In `CombinationValidator.full_validation`, the `_factor_spanning` method does fold-safe OOF residual prediction. But the formula VALUES are computed from raw descriptors on the full dataset (no leakage there since it's just arithmetic on features). However, the deconfounded Spearman used for ranking is on full data. Is the CV independent of the ranking?
5. Does the project acknowledge this selection-then-evaluate structure anywhere (e.g., `selection_uncertainty_included: false`)?
FAIL if: Selection on full data is followed by CV on the same selected features WITHOUT acknowledgment that CV scores are conditional on selection and thus optimistically biased.

### I. Deconfounding Methodology Correctness (stat-pipeline 专项)
1. `DeconfoundAnalyzer.partial_spearman` fits Ridge on x~Z and y~Z using the FULL passed data, then computes Spearman on residuals. When called from `analyze_all` (Stage 1), this is on full data (acceptable for a screening statistic). When called from `_factor_spanning` (Stage 4 V2), is the residualization done fold-locally or on full data?
2. The `build_rank_aware_controls` method does rank-aware incremental selection of anion columns relative to system. Is this implemented correctly (check the rank comparison logic)?
3. The `system_proxy_ratio = 1 - deconf_rho² / raw_rho²` — is this a valid measure? What are its failure modes (e.g., when raw_rho is near zero, or when signs flip)?
4. Is the partial Spearman via Ridge residualization a sound method, or does the Ridge regularization introduce bias that affects the downstream Spearman?
5. Are confounders (system, anion_type) also available as features in the model? If so, is there double-control?
WARN if: Deconfounding is applied in a way that could induce bias or be misinterpreted.

### J. Multiple Testing & Selective Reporting (stat-pipeline 专项)
1. 41 descriptors × 3 CV strategies × V1-V4 blocks = many comparisons. Is there any multiple-testing correction (Bonferroni, FDR, etc.)?
2. The `composite_score` is the mean of |Spearman| across AVAILABLE strategies only (skipped ones excluded). Does this mean a descriptor that skips 2/3 strategies but does well on 1/3 gets a high composite score? Is this reported transparently?
3. Top-k selection (default k=10) for combination validation — is the selection of "top" acknowledged as optimistic?
4. Bootstrap CI: does it cover selection uncertainty? (The README says `selection_uncertainty_included: false` — is this clearly stated in any report?)
WARN if: Multiple testing is unaddressed and the number of implicit comparisons is large.

### K. Target & Metric Definition (stat-pipeline 专项)
1. `log_sigma` is the target. Is it actually log10(σ/S·cm⁻¹)? Is there any preprocessing of the target that could confuse interpretation (e.g., standardization)?
2. Spearman is chosen over Pearson. Is this justified for this data (non-monotonic relationships would be missed)?
3. `composite_score = mean(|spearman|)` across available strategies. Does taking absolute value mask direction inconsistency (e.g., +0.5 in one CV, -0.5 in another averages to 0.5, looking "consistent" when it's not)?
4. The `deconfounded_spearman` is the primary metric. Is it possible that deconfounding removes real signal along with confound (over-correction), especially with small samples (~84)?
WARN if: Metric definitions could mask important failures (direction flips, over-correction).

### L. Causal Claim Boundary (stat-pipeline 专项)
1. Does the code/docstring correctly limit conclusions to "association/predictive robustness" rather than "causation"?
2. Is the `deconfounded_spearman` ever described or could be misread as a "causal effect" or "net effect"? Check variable names, comments, report text.
3. The `system_proxy_ratio` and labels like "强物理信号" (strong physical signal) — could "physical signal" be misread as "physical cause"?
4. Is the V2 factor-spanning method's `causal_claim: False` flag consistently set and surfaced in reports?
5. Are there any places where the language overclaims (e.g., "deconfounded" might imply causal identification to a casual reader)?
WARN if: Language could lead a reader to over-interpret associational findings as causal.

## 文件内容

以下文件按"先配置/文档 → 后代码"的审计逻辑顺序嵌入。所有内容原样保留，不做摘要或修改。

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

--- 文件开始: pyproject.toml ---
[project]
name = "automat-naconductor"
version = "1.1.0"
description = "Independent Agent and pipeline workflows for CIF-derived Na-ion conductor descriptors."
requires-python = ">=3.10,<3.12"
dependencies = [
    "numpy",
    "pandas",
    "pymatgen",
    "ruamel.yaml",
    "scipy",
    "scikit-learn",
    "matplotlib",
]

[tool.pytest.ini_options]
pythonpath = ["."]
--- 文件结束: pyproject.toml ---

--- 文件开始: run_config.py ---
from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from ruamel.yaml import YAML

DEFAULT_RUN_INFO = Path("run_info.yaml")


def load_run_info_arg() -> tuple[argparse.ArgumentParser, dict[str, Any]]:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument(
        "--run-info",
        type=Path,
        default=DEFAULT_RUN_INFO,
        help="YAML file containing run metadata and defaults.",
    )
    args, _ = parser.parse_known_args()
    return parser, load_run_info(args.run_info)


def load_run_info(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Missing required run info file: {path}")
    yaml = YAML(typ="safe")
    data = yaml.load(path)
    if data is None:
        raise ValueError(f"{path} must contain run metadata.")
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a YAML mapping at the top level.")
    return data


def config_get(config: dict[str, Any], dotted_path: str) -> Any:
    value: Any = config
    for key in dotted_path.split("."):
        if not isinstance(value, dict) or key not in value:
            raise KeyError(f"Missing required run_info key: {dotted_path}")
        value = value[key]
    return value


def config_path(config: dict[str, Any], dotted_path: str) -> Path:
    return Path(config_get(config, dotted_path))
--- 文件结束: run_config.py ---

--- 文件开始: descriptors/__init__.py ---
"""Na离子导体结构描述符注册表。

共 41 个描述符，分布在 8 个物理族中。
注册表格式: {name: (compute_func, family_key, is_high_risk)}

高风险族: G (电子代理), H (对称性破缺) 中的部分描述符。
"""
from __future__ import annotations

from collections.abc import Callable

from pymatgen.core import Structure

# ============================================================
# A族: Na多面体 (11个, 无高风险)
# ============================================================
from descriptors.family_a_polyhedron import (
    compute_a2_max_dist,
    compute_bottleneck_anisotropy,
    compute_coordination_number_mean,
    compute_direction_ratio,
    compute_ellipsoid_oblateness,
    compute_max_bond_length,
    compute_mean_bond_length,
    compute_min_bond_length,
    compute_poly_distortion_mean,
    compute_poly_volume_mean,
    compute_target_bond_center,
)

# ============================================================
# B族: Na-Na网络 (5个, 无高风险)
# ============================================================
from descriptors.family_b_network import (
    compute_avg_na_neighbors,
    compute_component_count,
    compute_largest_component_ratio,
    compute_nana_composite,
    compute_network_dimension,
)

# ============================================================
# C族: Na浓度 (3个, 无高风险)
# ============================================================
from descriptors.family_c_concentration import (
    compute_na_concentration,
    compute_na_occupancy_sum,
    compute_na_site_count,
)

# ============================================================
# D'族: 空位拓扑 (5个, 无高风险; BVSE依赖的返回NaN)
# ============================================================
from descriptors.family_d_vacancy_topo import (
    compute_bvse_barrier_estimate,
    compute_interstitial_channel_access,
    compute_interstitial_count,
    compute_interstitial_na_distance,
    compute_interstitial_network_dim,
)

# ============================================================
# E族: 骨架刚性 (4个, 无高风险)
# ============================================================
from descriptors.family_e_framework import (
    compute_framework_bond_rigidity,
    compute_framework_na_distance_stability,
    compute_framework_poly_distortion,
    compute_framework_sharing_topology,
)

# ============================================================
# F族: 长程关联 (4个, 无高风险)
# ============================================================
from descriptors.family_f_longrange import (
    compute_nana_nana_angle_mean,
    compute_nana_second_neighbor_dist,
    compute_nana_spacing_uniformity,
    compute_path_tortuosity,
)

# ============================================================
# G族: 电子代理 (4个, 全部高风险)
# ============================================================
from descriptors.family_g_electronic import (
    compute_charge_balance_deviation,
    compute_covalency_index,
    compute_framework_d_electron_weighted,
    compute_na_x_en_diff,
)

# ============================================================
# H族: 对称性破缺 (5个, 3个高风险)
# ============================================================
from descriptors.family_h_symmetry import (
    compute_coordination_cv,
    compute_partial_occupancy_ratio,
    compute_space_group_number,
    compute_volume_cv,
    compute_wyckoff_diversity,
)

# ============================================================
# 描述符注册表: {name: (compute_func, family_key, is_high_risk)}
# ============================================================
AVAILABLE_STRUCTURE_DESCRIPTORS: dict[str, tuple[Callable[[Structure], float], str, bool]] = {
    # --- A族: Na多面体 (11) ---
    "a2_max_dist": (compute_a2_max_dist, "A", False),
    "poly_distortion_mean": (compute_poly_distortion_mean, "A", False),
    "max_bond_length": (compute_max_bond_length, "A", False),
    "min_bond_length": (compute_min_bond_length, "A", False),
    "mean_bond_length": (compute_mean_bond_length, "A", False),
    "target_bond_center": (compute_target_bond_center, "A", False),
    "poly_volume_mean": (compute_poly_volume_mean, "A", False),
    "coordination_number_mean": (compute_coordination_number_mean, "A", False),
    "ellipsoid_oblateness": (compute_ellipsoid_oblateness, "A", False),
    "direction_ratio": (compute_direction_ratio, "A", False),
    "bottleneck_anisotropy": (compute_bottleneck_anisotropy, "A", True),

    # --- B族: Na-Na网络 (5) ---
    "nana_composite": (compute_nana_composite, "B", False),
    "avg_na_neighbors": (compute_avg_na_neighbors, "B", False),
    "largest_component_ratio": (compute_largest_component_ratio, "B", False),
    "network_dimension": (compute_network_dimension, "B", False),
    "component_count": (compute_component_count, "B", False),

    # --- C族: Na浓度 (3) ---
    "na_concentration": (compute_na_concentration, "C", False),
    "na_occupancy_sum": (compute_na_occupancy_sum, "C", False),
    "na_site_count": (compute_na_site_count, "C", False),

    # --- D'族: 空位拓扑 (5) ---
    "interstitial_count": (compute_interstitial_count, "D_prime", False),
    "interstitial_na_distance": (compute_interstitial_na_distance, "D_prime", False),
    "interstitial_channel_access": (compute_interstitial_channel_access, "D_prime", False),
    "interstitial_network_dim": (compute_interstitial_network_dim, "D_prime", False),
    "bvse_barrier_estimate": (compute_bvse_barrier_estimate, "D_prime", True),

    # --- E族: 骨架刚性 (4) ---
    "framework_bond_rigidity": (compute_framework_bond_rigidity, "E", False),
    "framework_poly_distortion": (compute_framework_poly_distortion, "E", False),
    "framework_na_distance_stability": (compute_framework_na_distance_stability, "E", False),
    "framework_sharing_topology": (compute_framework_sharing_topology, "E", False),

    # --- F族: 长程关联 (4) ---
    "nana_nana_angle_mean": (compute_nana_nana_angle_mean, "F", False),
    "nana_second_neighbor_dist": (compute_nana_second_neighbor_dist, "F", False),
    "path_tortuosity": (compute_path_tortuosity, "F", False),
    "nana_spacing_uniformity": (compute_nana_spacing_uniformity, "F", False),

    # --- G族: 电子代理 (4, 全部高风险) ---
    "na_x_en_diff": (compute_na_x_en_diff, "G", True),
    "charge_balance_deviation": (compute_charge_balance_deviation, "G", True),
    "covalency_index": (compute_covalency_index, "G", True),
    "framework_d_electron_weighted": (compute_framework_d_electron_weighted, "G", True),

    # --- H族: 对称性破缺 (5, 3高风险) ---
    "space_group_number": (compute_space_group_number, "H", True),
    "wyckoff_diversity": (compute_wyckoff_diversity, "H", True),
    "partial_occupancy_ratio": (compute_partial_occupancy_ratio, "H", True),
    "coordination_cv": (compute_coordination_cv, "H", False),
    "volume_cv": (compute_volume_cv, "H", False),
}

# Registry metadata is intentionally separate: the public three-item tuples
# above are used by callers and remain backward compatible.  ``dimension`` is a
# physical-dimension token used by the combination rule checker; ``unit`` is a
# human-readable reporting label.
_DESCRIPTOR_UNITS_AND_DIMENSIONS: dict[str, tuple[str, str]] = {
    "a2_max_dist": ("angstrom", "length"),
    "poly_distortion_mean": ("dimensionless", "dimensionless"),
    "max_bond_length": ("angstrom", "length"),
    "min_bond_length": ("angstrom", "length"),
    "mean_bond_length": ("angstrom", "length"),
    "target_bond_center": ("angstrom", "length"),
    "poly_volume_mean": ("angstrom^3", "volume"),
    "coordination_number_mean": ("count", "count"),
    "ellipsoid_oblateness": ("dimensionless", "dimensionless"),
    "direction_ratio": ("dimensionless", "dimensionless"),
    "bottleneck_anisotropy": ("dimensionless", "dimensionless"),
    "nana_composite": ("dimensionless", "dimensionless"),
    "avg_na_neighbors": ("count", "count"),
    "largest_component_ratio": ("dimensionless", "dimensionless"),
    "network_dimension": ("dimensionless", "dimensionless"),
    "component_count": ("count", "count"),
    "na_concentration": ("angstrom^-3", "number_density"),
    "na_occupancy_sum": ("count", "count"),
    "na_site_count": ("count", "count"),
    "interstitial_count": ("count", "count"),
    "interstitial_na_distance": ("angstrom", "length"),
    "interstitial_channel_access": ("dimensionless", "dimensionless"),
    "interstitial_network_dim": ("dimensionless", "dimensionless"),
    "bvse_barrier_estimate": ("eV", "energy"),
    "framework_bond_rigidity": ("dimensionless", "dimensionless"),
    "framework_poly_distortion": ("dimensionless", "dimensionless"),
    "framework_na_distance_stability": ("dimensionless", "dimensionless"),
    "framework_sharing_topology": ("dimensionless", "dimensionless"),
    "nana_nana_angle_mean": ("degree", "angle"),
    "nana_second_neighbor_dist": ("angstrom", "length"),
    "path_tortuosity": ("dimensionless", "dimensionless"),
    "nana_spacing_uniformity": ("dimensionless", "dimensionless"),
    "na_x_en_diff": ("Pauling", "electronegativity"),
    "charge_balance_deviation": ("elementary_charge", "charge"),
    "covalency_index": ("dimensionless", "dimensionless"),
    "framework_d_electron_weighted": ("electron", "electron_count"),
    "space_group_number": ("index", "categorical_index"),
    "wyckoff_diversity": ("count", "count"),
    "partial_occupancy_ratio": ("dimensionless", "dimensionless"),
    "coordination_cv": ("dimensionless", "dimensionless"),
    "volume_cv": ("dimensionless", "dimensionless"),
}

_INACTIVE_FOR_AUTOMATIC_SEARCH = {
    "max_bond_length",  # compatibility alias of a2_max_dist
    "bottleneck_anisotropy",  # permanently unavailable implementation
    "bvse_barrier_estimate",  # permanently unavailable without BVSE backend
}

STRUCTURE_DESCRIPTOR_METADATA: dict[str, dict[str, object]] = {}
for _name in AVAILABLE_STRUCTURE_DESCRIPTORS:
    _unit, _dimension = _DESCRIPTOR_UNITS_AND_DIMENSIONS[_name]
    _active = _name not in _INACTIVE_FOR_AUTOMATIC_SEARCH
    STRUCTURE_DESCRIPTOR_METADATA[_name] = {
        "unit": _unit,
        "dimension": _dimension,
        "active_for_search": _active,
        # Retain the Task-1 key for existing featurizer/search consumers.
        "searchable": _active,
    }
STRUCTURE_DESCRIPTOR_METADATA["max_bond_length"]["alias_of"] = "a2_max_dist"

SEARCHABLE_STRUCTURE_DESCRIPTORS = {
    name: descriptor
    for name, descriptor in AVAILABLE_STRUCTURE_DESCRIPTORS.items()
    if STRUCTURE_DESCRIPTOR_METADATA[name]["active_for_search"]
}
--- 文件结束: descriptors/__init__.py ---

[由于文件总长度较大，代码类文件（_base.py、featurizer.py、deconfound.py、stability.py、cv_strategies.py、combination.py、compute_features.py、run_pipeline.py、train.py、automat_utils.py）在下方继续嵌入]

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

--- 文件开始: descriptors/featurizer.py ---
"""结构描述符批量计算入口。

提供从 CIF 文件或数据集计算结构描述符的主接口。
单个描述符计算失败时返回 NaN 并记录警告，不影响其他描述符。
"""
from __future__ import annotations

import json
import logging
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from pymatgen.core import Structure
from pymatgen.io.cif import CifParser

from descriptors import (
    AVAILABLE_STRUCTURE_DESCRIPTORS,
    SEARCHABLE_STRUCTURE_DESCRIPTORS,
    STRUCTURE_DESCRIPTOR_METADATA,
)

logger = logging.getLogger(__name__)


def resolve_cif_path(value: str | Path, csv_dir: str | Path) -> Path:
    """Resolve a CIF path, anchoring relative values to the CSV directory."""
    cif_path = Path(value)
    if cif_path.is_absolute():
        return cif_path
    return Path(csv_dir) / cif_path


def load_structure_from_cif(cif_path: str | Path) -> Structure:
    """从 CIF 文件加载 pymatgen Structure 对象。

    参数:
        cif_path: CIF 文件路径

    返回:
        pymatgen Structure 对象

    异常:
        FileNotFoundError: CIF 文件不存在
        ValueError: CIF 解析失败
    """
    cif_path = Path(cif_path)
    if not cif_path.exists():
        raise FileNotFoundError(f"CIF 文件不存在: {cif_path}")

    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            parser = CifParser(str(cif_path), occupancy_tolerance=10)
            structures = parser.parse_structures(primitive=False)
        if not structures:
            raise ValueError(f"CIF 解析未返回结构: {cif_path}")
        return structures[0]
    except Exception as exc:
        raise ValueError(f"CIF 解析失败 ({cif_path}): {exc}") from exc


def featurize_cif(
    cif_path: str | Path,
    descriptor_names: list[str] | None = None,
) -> dict[str, float]:
    """从单个 CIF 文件计算指定描述符。

    参数:
        cif_path: CIF 文件路径
        descriptor_names: 要计算的描述符名称列表。
            None 表示计算全部 41 个描述符。

    返回:
        {descriptor_name: value} 字典，失败的描述符值为 NaN
    """
    try:
        struct = load_structure_from_cif(cif_path)
    except (FileNotFoundError, ValueError) as exc:
        logger.warning("CIF 加载失败: %s", exc)
        names = descriptor_names or list(AVAILABLE_STRUCTURE_DESCRIPTORS.keys())
        return {name: float("nan") for name in names}

    if descriptor_names is None:
        descriptor_names = list(AVAILABLE_STRUCTURE_DESCRIPTORS.keys())

    results: dict[str, float] = {}
    for name in descriptor_names:
        if name not in AVAILABLE_STRUCTURE_DESCRIPTORS:
            logger.warning("未注册的描述符: %s", name)
            results[name] = float("nan")
            continue

        func, _family, _is_high_risk = AVAILABLE_STRUCTURE_DESCRIPTORS[name]
        try:
            value = func(struct)
            # 确保返回 Python float (非 numpy 类型)，以便 JSON 序列化
            if isinstance(value, (np.floating, np.integer)):
                value = float(value)
            elif not isinstance(value, float):
                value = float(value) if value is not None else float("nan")
            # NaN/Inf 转为 NaN
            if np.isnan(value) or np.isinf(value):
                value = float("nan")
            results[name] = value
        except Exception as exc:
            logger.warning("描述符 %s 计算失败: %s", name, exc)
            results[name] = float("nan")

    return results


def featurize_dataset(
    csv_path: str | Path,
    output_path: str | Path,
    cif_column: str = "cif_path",
    descriptor_names: list[str] | None = None,
    strict: bool = True,
) -> pd.DataFrame:
    """批量计算数据集中所有样本的结构描述符。

    读取包含 CIF 路径列的 CSV 文件，对每行计算描述符，
    输出包含描述符列的新 CSV 和 JSON 文件。

    参数:
        csv_path: 输入 CSV 路径，需包含 cif_column 列
        output_path: 输出文件路径前缀 (自动追加 .csv 和 .json)
        cif_column: CIF 路径列名
        descriptor_names: 要计算的描述符名称列表，None 表示全部
        strict: 为 True 时，在创建任何输出前检查全部 CIF 路径是否存在

    返回:
        包含原始列 + 描述符列的 DataFrame
    """
    csv_path = Path(csv_path).resolve()
    output_path = Path(output_path)
    # CSV 文件所在目录，用于解析相对 CIF 路径
    csv_dir = csv_path.parent

    df = pd.read_csv(csv_path, encoding="utf-8")
    if cif_column not in df.columns:
        raise ValueError(f"CSV 中缺少列: {cif_column}")

    if descriptor_names is None:
        descriptor_names = list(SEARCHABLE_STRUCTURE_DESCRIPTORS.keys())

    resolved_paths: dict[object, Path] = {}
    missing_paths: list[tuple[object, object, Path | None]] = []
    for idx, value in df[cif_column].items():
        if pd.isna(value):
            missing_paths.append((idx, value, None))
            continue
        resolved = resolve_cif_path(str(value), csv_dir)
        resolved_paths[idx] = resolved
        if not resolved.exists():
            missing_paths.append((idx, value, resolved))

    if strict and missing_paths:
        details = ", ".join(
            f"row {idx}: {resolved if resolved is not None else '<empty>'}"
            for idx, _value, resolved in missing_paths[:3]
        )
        remainder = len(missing_paths) - 3
        if remainder > 0:
            details += f", ... and {remainder} more"
        raise FileNotFoundError(
            f"CIF preflight failed: {len(missing_paths)} missing path(s); {details}"
        )

    # 初始化描述符列
    for name in descriptor_names:
        df[name] = float("nan")

    # 逐行计算
    total = len(df)
    success_count = 0
    for idx, row in df.iterrows():
        cif_rel = row[cif_column]
        if pd.isna(cif_rel):
            logger.warning("行 %d: CIF 路径为空", idx)
            continue
        cif_path_resolved = resolved_paths[idx]
        if not cif_path_resolved.exists():
            logger.warning("行 %d: CIF 文件不存在: %s (原始: %s)",
                           idx, cif_path_resolved, cif_rel)
            continue

        try:
            results = featurize_cif(str(cif_path_resolved), descriptor_names)
            for name, value in results.items():
                df.at[idx, name] = value
            success_count += 1
        except Exception as exc:
            logger.warning("行 %d: 特征化失败: %s", idx, exc)

    # 保存 CSV
    csv_out = str(output_path) + ".csv" if not str(output_path).endswith(".csv") else str(output_path)
    df.to_csv(csv_out, index=False, encoding="utf-8-sig")

    # 保存 JSON
    json_out = csv_out.replace(".csv", ".json")
    meta = {
        "total_samples": total,
        "success_count": success_count,
        "descriptor_count": len(descriptor_names),
        "descriptor_names": descriptor_names,
    }
    with open(json_out, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

    logger.info("批量计算完成: %d/%d 成功, 输出: %s, %s",
                success_count, total, csv_out, json_out)
    return df


def build_feature_matrix(
    df: pd.DataFrame,
    descriptor_cols: list[str] | None = None,
    target_col: str = "log_sigma",
    n_noise: int = 15,
    noise_seed: int = 42,
    min_valid_fraction: float = 0.5,
) -> tuple[pd.DataFrame, list[str], pd.DataFrame]:
    """构建保留原始值和缺失值的特征矩阵，并注入固定噪声列。

    噪声注入的目的：测量"随机能有多幸运"。
    15个噪声列中，偶尔会有与目标偶然相关的，其选择频率就是"随机基线"。
    真实描述符必须显著高于这个基线才有意义。

    参数:
        df: 含描述符列的DataFrame (已由 featurize_dataset 生成)
        descriptor_cols: 描述符列名列表，None=自动检测
        target_col: 目标列名
        n_noise: 噪声列数
        noise_seed: 噪声种子（预固定为42，不可调）
        min_valid_fraction: 列有效值最低比例（低于此值排除）

    返回:
        feature_df: 原始可搜索描述符 + 固定噪声列 + 非描述符元数据列。
            预测性填充和标准化必须由每个训练折内部的模型 Pipeline 完成。
        valid_cols: 保留的真实描述符列名列表
        noise_info_df: 噪声列元信息
    """
    # --- 1. 自动检测描述符列 ---
    if descriptor_cols is None:
        registered = set(SEARCHABLE_STRUCTURE_DESCRIPTORS.keys())
        descriptor_cols = [c for c in df.columns if c in registered]
    else:
        descriptor_cols = [
            c for c in descriptor_cols
            if STRUCTURE_DESCRIPTOR_METADATA.get(c, {"searchable": True})["searchable"]
        ]

    if not descriptor_cols:
        raise ValueError("未在 DataFrame 中找到任何已注册的描述符列")

    n_samples = len(df)

    # --- 2. 过滤有效值不足的列 ---
    min_valid_count = n_samples * min_valid_fraction
    valid_cols: list[str] = []
    dropped_cols: list[str] = []
    for col in descriptor_cols:
        if col not in df.columns:
            logger.warning("描述符列 %s 不在 DataFrame 中，跳过", col)
            dropped_cols.append(col)
            continue
        valid_count = df[col].notna().sum()
        if valid_count >= min_valid_count:
            valid_cols.append(col)
        else:
            nan_ratio = 1.0 - valid_count / n_samples
            logger.info(
                "排除列 %s: 有效值 %.1f%% (阈值 %.1f%%)",
                col, (1 - nan_ratio) * 100, min_valid_fraction * 100,
            )
            dropped_cols.append(col)

    if dropped_cols:
        logger.info("排除 %d 个描述符列 (有效值不足): %s",
                     len(dropped_cols), dropped_cols)

    # --- 3. 保留描述符原始值和缺失值 ---
    X_real = df[valid_cols].copy()

    # --- 4. 生成固定噪声列（不做数据依赖的全局拟合） ---
    rng = np.random.RandomState(noise_seed)
    noise_data = rng.randn(n_samples, n_noise)
    noise_cols = [f"noise_{i:03d}" for i in range(n_noise)]
    X_noise = pd.DataFrame(noise_data, columns=noise_cols, index=df.index)

    # --- 5. 记录噪声信息 ---
    target_values = df[target_col].values
    noise_records = []
    for col_name in noise_cols:
        col_values = X_noise[col_name].values
        # Pearson r 与目标
        r = np.corrcoef(col_values, target_values)[0, 1]
        noise_records.append({
            "column": col_name,
            "seed": noise_seed,
            "distribution": "standard_normal",
            "actual_corr_with_target": float(r),
        })
    noise_info_df = pd.DataFrame(noise_records)

    # --- 6. 拼接元数据列 (保留非描述符列，包括目标列) ---
    registered_descriptor_names = set(AVAILABLE_STRUCTURE_DESCRIPTORS)
    metadata_cols = [c for c in df.columns if c not in registered_descriptor_names]
    feature_df = pd.concat(
        [df[metadata_cols], X_real, X_noise],
        axis=1,
    )

    logger.info(
        "特征矩阵构建完成: %d 样本, %d 真实描述符, %d 噪声列, %d 元数据列",
        n_samples, len(valid_cols), n_noise, len(metadata_cols),
    )

    return feature_df, valid_cols, noise_info_df

--- 文件结束: descriptors/featurizer.py ---

--- 文件开始: descriptors/deconfound.py ---
"""去混杂分析器。

核心思想：混杂变量（如体系分类 system、阴离子类型 anion_type）同时影响
描述符 X 和电导率 Y。不去控制的话，"高相关"可能只是混杂效应而非物理信号。

方法：用 Ridge 回归分别从 X 和 Y 中"减去"混杂变量能解释的部分（残差化），
然后对残差计算 Spearman 秩相关。这样就把"因为属于某个体系而产生的相关"
和"体系内部的物理相关"分离开来。

体系代理比 system_proxy_ratio = 1 - (deconf_rho² / raw_rho²)：
  - 接近 1 → 相关几乎全由混杂驱动，描述符是体系代理
  - 接近 0 → 去混杂后相关依然强，是真实物理信号
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats
from sklearn.linear_model import Ridge


DECONFOUND_RESULT_COLUMNS = [
    "descriptor",
    "family",
    "is_high_risk",
    "raw_spearman",
    "deconfounded_spearman",
    "deconf_p",
    "system_proxy_ratio",
    "label",
]


class DeconfoundAnalyzer:
    """去混杂相关性分析器。

    对每个描述符，计算原始 Spearman 相关和去混杂后的偏 Spearman 相关，
    并据此判断描述符是"物理信号"还是"体系代理"。

    参数:
        alpha: Ridge 回归正则化强度。
            去混杂时用 Ridge 做残差化，alpha 控制正则化程度。
            alpha=0 等价于普通最小二乘；alpha 越大，残差化越保守。
            默认 1.0，对小样本（~100）有一定正则化保护。
    """

    def __init__(self, alpha: float = 1.0) -> None:
        self.alpha = alpha

    # ------------------------------------------------------------------
    # 内部工具
    # ------------------------------------------------------------------

    @staticmethod
    def _one_hot_encode(labels_list: list[str], column_name: str) -> np.ndarray:
        """将分类标签列表转为带参考类别的 one-hot 矩阵。

        参数:
            labels_list: 分类标签列表，如 ["NASICON", "β-alumina", ...]
            column_name: 列名，仅用于 DataFrame 构造

        返回:
            one-hot 矩阵 (n_samples, n_categories - 1)，float64 类型
        """
        encoded = DeconfoundAnalyzer._one_hot_frame(labels_list, column_name)
        return encoded.values

    @staticmethod
    def _one_hot_frame(labels_list: list[str], column_name: str) -> pd.DataFrame:
        """Return reference-coded dummy variables with stable, named columns."""
        labels = pd.Series(labels_list, name=column_name, dtype="string")
        return pd.get_dummies(
            labels,
            prefix=column_name,
            drop_first=True,
            dtype=float,
        )

    @staticmethod
    def build_rank_aware_controls(
        system_labels: list[str],
        anion_labels: list[str],
    ) -> tuple[pd.DataFrame, dict[str, object]]:
        """Build system-primary controls and audit redundant anion contrasts."""
        if len(system_labels) != len(anion_labels):
            raise ValueError("system and anion label lengths must match")
        system_frame = DeconfoundAnalyzer._one_hot_frame(
            system_labels, "system"
        ).reset_index(drop=True)
        anion_frame = DeconfoundAnalyzer._one_hot_frame(
            anion_labels, "anion_type"
        ).reset_index(drop=True)

        intercept = np.ones((len(system_labels), 1), dtype=float)
        system_design = np.column_stack(
            [intercept, system_frame.to_numpy(dtype=float)]
        )
        combined_design = np.column_stack(
            [system_design, anion_frame.to_numpy(dtype=float)]
        )
        system_rank = int(np.linalg.matrix_rank(system_design))
        confounder_rank = int(np.linalg.matrix_rank(combined_design))

        current_design = system_design
        current_rank = system_rank
        incremental: list[str] = []
        redundant: list[str] = []
        for column in anion_frame.columns:
            candidate = np.column_stack(
                [current_design, anion_frame[[column]].to_numpy(dtype=float)]
            )
            candidate_rank = int(np.linalg.matrix_rank(candidate))
            if candidate_rank > current_rank:
                incremental.append(str(column))
                current_design = candidate
                current_rank = candidate_rank
            else:
                redundant.append(str(column))

        controls = pd.concat([system_frame, anion_frame[incremental]], axis=1)
        metadata: dict[str, object] = {
            "primary_control": "system",
            "system_design_rank": system_rank,
            "confounder_rank": confounder_rank,
            "anion_incremental_rank": confounder_rank - system_rank,
            "anion_redundant_count": len(redundant),
            "anion_incremental_columns": incremental,
            "anion_redundant_columns": redundant,
            "anion_is_independent_control": False,
            "control_coding": "reference_class_with_intercept",
            "control_columns": [
                "intercept",
                *map(str, system_frame.columns),
                *map(str, anion_frame.columns),
            ],
            "residualization_columns": list(map(str, controls.columns)),
        }
        return controls, metadata

    # ------------------------------------------------------------------
    # 核心方法
    # ------------------------------------------------------------------

    def partial_spearman(
        self,
        x: np.ndarray,
        y: np.ndarray,
        confounders_df: pd.DataFrame,
    ) -> tuple[float, float]:
        """计算控制混杂变量后的偏 Spearman 秩相关。

        步骤:
        1. 用 Ridge 分别拟合 x ~ confounders 和 y ~ confounders
        2. 取残差: res_x = x - confounders_predicted_x, res_y 同理
        3. 对残差计算 spearmanr

        参数:
            x: 描述符值向量 (n_samples,)
            y: 目标值向量 (n_samples,)
            confounders_df: 混杂变量矩阵 (n_samples, n_confounders)

        返回:
            (rho, p_value) — 去混杂后的 Spearman 相关系数和 p 值
        """
        z = confounders_df.values.astype(float)

        # 样本数不足时无法残差化，回退到原始相关
        n_samples = len(x)
        if n_samples < 3 or z.shape[1] == 0 or z.shape[1] >= n_samples:
            rho, p_val = stats.spearmanr(x, y)
            return float(rho), float(p_val)

        # Ridge 残差化: 对 x 和 y 分别做 x ~ Z, y ~ Z
        ridge = Ridge(alpha=self.alpha)

        # 残差 = 原始值 - 混杂预测值
        ridge.fit(z, x)
        res_x = x - ridge.predict(z)

        ridge.fit(z, y)
        res_y = y - ridge.predict(z)

        # 残差上的 Spearman 相关
        rho, p_val = stats.spearmanr(res_x, res_y)
        return float(rho), float(p_val)

    def deconfounded_spearman(
        self,
        x: np.ndarray,
        y: np.ndarray,
        confounders_df: pd.DataFrame,
    ) -> float:
        """计算去混杂 Spearman rho（便捷方法，只返回 rho）。

        参数:
            x: 描述符值向量 (n_samples,)
            y: 目标值向量 (n_samples,)
            confounders_df: 混杂变量矩阵 (n_samples, n_confounders)

        返回:
            去混杂后的 Spearman rho
        """
        rho, _ = self.partial_spearman(x, y, confounders_df)
        return rho

    # ------------------------------------------------------------------
    # 标签分类
    # ------------------------------------------------------------------

    @staticmethod
    def _classify_descriptor(
        raw_rho: float,
        deconf_rho: float,
        system_proxy_ratio: float,
        deconf_p: float,
    ) -> str:
        """根据去混杂结果给描述符打标签。

        分类规则 (errata P3):
        - 去混杂后 |deconf_rho| > 0.3 → '强物理信号'（无论代理比多高，
          去混杂后仍显著相关，说明物理信号确实存在）
        - |deconf_rho| <= 0.3 且 system_proxy_ratio < 0.3 → '弱物理信号'
          （代理比低，但去混杂后信号也不强）
        - |deconf_rho| <= 0.3 且 0.3 <= system_proxy_ratio < 0.7 → '混合信号'
          （部分来自体系混杂，部分可能是物理）
        - |deconf_rho| <= 0.3 且 system_proxy_ratio >= 0.7 → '体系代理'
          （大部分相关由混杂驱动）
        - |raw_rho| < 0.2 → '噪声级'（连原始相关都极弱）

        参数:
            raw_rho: 原始 Spearman rho
            deconf_rho: 去混杂后 Spearman rho
            system_proxy_ratio: 体系代理比 [0, 1]
            deconf_p: 去混杂后 p 值

        返回:
            分类标签字符串
        """
        # 原始相关极弱 → 噪声级
        if abs(raw_rho) < 0.2:
            return "噪声级"

        # 去混杂后仍然显著 → 强物理信号（errata P3 核心修正）
        if abs(deconf_rho) > 0.3:
            return "强物理信号"

        # 去混杂后信号弱，根据代理比分
        if system_proxy_ratio < 0.3:
            return "弱物理信号"
        if system_proxy_ratio < 0.7:
            return "混合信号"
        return "体系代理"

    # ------------------------------------------------------------------
    # 主入口
    # ------------------------------------------------------------------

    def analyze_all(
        self,
        feature_df: pd.DataFrame,
        y: np.ndarray,
        system_labels: list[str],
        anion_labels: list[str],
    ) -> pd.DataFrame:
        """对所有描述符列执行去混杂分析。

        对每个描述符计算:
        - raw_spearman: 原始 Spearman rho
        - deconfounded_spearman: 控制 system + anion 后的 rho
        - deconf_p: 去混杂后的 p 值
        - system_proxy_ratio: 体系代理比（1 - deconf_rho² / raw_rho²）
        - label: 分类标签

        参数:
            feature_df: 包含描述符列的 DataFrame（已标准化）
            y: log_sigma 目标向量 (n_samples,)
            system_labels: 每个样本的体系标签，如 ["NASICON", ...]
            anion_labels: 每个样本的阴离子标签，如 ["O", ...]

        返回:
            分析结果 DataFrame，列为:
            descriptor, family, is_high_risk, raw_spearman,
            deconfounded_spearman, deconf_p, system_proxy_ratio, label
        """
        # --- 构造混杂变量矩阵 ---
        confounders_df, control_metadata = self.build_rank_aware_controls(
            system_labels, anion_labels
        )

        # --- 获取描述符注册表，用于查询 family 和 is_high_risk ---
        from descriptors import SEARCHABLE_STRUCTURE_DESCRIPTORS

        y_arr = np.asarray(y, dtype=float)

        # --- 确定描述符列 ---
        registered_names = set(SEARCHABLE_STRUCTURE_DESCRIPTORS.keys())
        descriptor_cols = [c for c in feature_df.columns if c in registered_names]

        records: list[dict] = []
        for col in descriptor_cols:
            x_raw = feature_df[col].values.astype(float)

            # 跳过 NaN 过多的列：有效值不足 80% 则跳过
            valid_mask = ~np.isnan(x_raw) & ~np.isnan(y_arr)
            n_valid = int(valid_mask.sum())
            if n_valid < 5:
                continue

            x_valid = x_raw[valid_mask]
            y_valid = y_arr[valid_mask]
            conf_valid = confounders_df.loc[valid_mask].reset_index(drop=True)

            # 原始 Spearman 相关
            raw_rho, _raw_p = stats.spearmanr(x_valid, y_valid)
            raw_rho = float(raw_rho)

            # 去混杂偏 Spearman 相关
            deconf_rho, deconf_p = self.partial_spearman(
                x_valid, y_valid, conf_valid,
            )

            # 体系代理比
            raw_rho_sq = raw_rho ** 2
            deconf_rho_sq = deconf_rho ** 2

            if raw_rho_sq < 1e-12:
                # 原始相关几乎为零，代理比无意义，设为 0
                system_proxy_ratio = 0.0
            elif raw_rho * deconf_rho < 0:
                # 原始和去混杂后符号相反 → 相关完全由混杂驱动
                system_proxy_ratio = 1.0
            else:
                system_proxy_ratio = 1.0 - deconf_rho_sq / raw_rho_sq
                # 钳位到 [0, 1]
                system_proxy_ratio = max(0.0, min(1.0, system_proxy_ratio))

            # 查询 family 和 is_high_risk
            _func, family, is_high_risk = SEARCHABLE_STRUCTURE_DESCRIPTORS.get(
                col, (None, "Unknown", False),
            )

            # 分类标签
            label = self._classify_descriptor(
                raw_rho, deconf_rho, system_proxy_ratio, deconf_p,
            )

            records.append({
                "descriptor": col,
                "family": family,
                "is_high_risk": is_high_risk,
                "raw_spearman": raw_rho,
                "deconfounded_spearman": deconf_rho,
                "deconf_p": deconf_p,
                "system_proxy_ratio": system_proxy_ratio,
                "label": label,
            })

        result_df = pd.DataFrame.from_records(
            records,
            columns=DECONFOUND_RESULT_COLUMNS,
        )

        # 按 |deconfounded_spearman| 降序排列：物理信号最强的排最前
        if not result_df.empty:
            result_df = result_df.sort_values(
                by="deconfounded_spearman",
                key=lambda s: s.abs(),
                ascending=False,
            ).reset_index(drop=True)

        result_df.attrs.update(control_metadata)

        return result_df

--- 文件结束: descriptors/deconfound.py ---

--- 文件开始: descriptors/stability.py ---
"""稳定性选择（Stability Selection）与物理族代表选择。

稳定性选择的核心思想：多次自举采样，每次做特征选择，
统计每个特征被选中的频率。频率越高，说明该特征越稳定可靠。

为什么需要稳定性选择？
- 小样本（~84 行）+ 多描述符 → 特征选择容易过拟合
- 单次选择可能因随机性选中噪声特征
- 频率 > 阈值（默认 0.6）的特征才是"真信号"

噪声基线校准：加入随机噪声列，若真实描述符的选中频率
不高于噪声列的 95 分位数，则该描述符不比随机更好。

物理族代表选择（errata P4）：
- 每个物理族最多选 1 个代表（默认 max_per_family=1）
- 代表 = 该族中稳定性通过且 |去混杂 Spearman| 最高的描述符（保留符号）
- 此容量是硬上限；缺少其它物理族不会增加任一族的名额
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.linear_model import Lasso
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

# 描述符注册表和物理族定义
from descriptors import SEARCHABLE_STRUCTURE_DESCRIPTORS
from descriptors._base import PHYSICAL_FAMILIES


PHYSICAL_GROUP_RESULT_COLUMNS = [
    "descriptor",
    "family",
    "family_name",
    "deconfounded_spearman",
    "selection_freq",
    "is_stable",
    "above_noise_baseline",
    "is_representative",
]

STABILITY_RESULT_COLUMNS = [
    "feature_name",
    "selection_freq",
    "is_stable",
    "above_noise_baseline",
    "selection_method",
    "selection_alpha",
    "noise_baseline",
]


class StabilitySelector:
    """稳定性选择器：通过多次子采样 + Lasso 筛选稳定描述符。

    算法流程：
    1. 每次自举：随机抽取 fraction 比例的样本（无放回）
    2. 在子样本内部做中位数填充、标准化并拟合 Lasso
    3. 按 Lasso 非零系数判断"被选中"
    4. 统计每个特征在 n_bootstrap 次迭代中被选中的频率
    5. 若提供了噪声列，用噪声频率的 95 分位数作为基线校准
    """

    def __init__(
        self,
        n_bootstrap: int = 100,
        threshold: float = 0.6,
        fraction: float = 0.5,
        alpha: float = 1.0,
        seed: int = 42,
    ) -> None:
        """初始化稳定性选择器。

        参数:
            n_bootstrap: 自举迭代次数，越多越稳定但越慢
            threshold: 选中频率阈值，高于此值视为稳定描述符
            fraction: 每次自举的采样比例（0.5 = 抽一半样本）
            alpha: Lasso 选择正则化强度，越大选择越稀疏
            seed: 随机种子，保证可复现
        """
        self.n_bootstrap = n_bootstrap
        self.threshold = threshold
        self.fraction = fraction
        self.alpha = alpha
        self.seed = seed

    def _result_metadata(self, noise_baseline: float) -> dict[str, object]:
        """Return metadata shared by populated and schema-only results."""
        return {
            "selection_method": "subsampled_lasso",
            "selection_alpha": float(self.alpha),
            "preprocessing": ["median_imputation", "standard_scaling"],
            "noise_baseline": float(noise_baseline),
            "noise_baseline_quantile": 0.95,
            "n_subsamples": int(self.n_bootstrap),
            "subsample_fraction": float(self.fraction),
            "seed": int(self.seed),
        }

    def run(
        self,
        X_real: np.ndarray,
        y: np.ndarray,
        X_noise: np.ndarray | None = None,
        real_col_names: list[str] | None = None,
        noise_col_names: list[str] | None = None,
    ) -> pd.DataFrame:
        """运行稳定性选择。

        参数:
            X_real: 原始真实描述符矩阵 (n_samples, n_real_features)，可含缺失值
            y: 目标向量 log_sigma (n_samples,)
            X_noise: 噪声列矩阵 (n_samples, n_noise)，用于基线校准
            real_col_names: 真实描述符列名列表
            noise_col_names: 噪声列列名列表

        返回:
            DataFrame，每行一个特征，包含:
            - feature_name: 特征名
            - selection_freq: 被选中的频率 (0~1)
            - is_stable: 频率是否 > threshold
            - above_noise_baseline: 频率是否 > 噪声基线（无噪声列时为 True）
        """
        n_samples, n_real = X_real.shape

        # 生成默认列名
        if real_col_names is None:
            real_col_names = [f"real_{i}" for i in range(n_real)]
        if noise_col_names is None and X_noise is not None:
            n_noise = X_noise.shape[1]
            noise_col_names = [f"noise_{i}" for i in range(n_noise)]

        # 拼接真实描述符和噪声列（若提供）
        if X_noise is not None:
            X_all = np.hstack([X_real, X_noise])
            all_names = list(real_col_names) + list(noise_col_names)
        else:
            X_all = X_real
            all_names = list(real_col_names)

        n_features = X_all.shape[1]
        selection_counts = np.zeros(n_features, dtype=int)

        if n_features == 0:
            empty_result = pd.DataFrame(columns=STABILITY_RESULT_COLUMNS)
            empty_result.attrs.update(self._result_metadata(noise_baseline=0.0))
            return empty_result

        # 每次自举的样本数
        subset_size = max(2, int(n_samples * self.fraction))

        rng = np.random.RandomState(self.seed)

        for _ in range(self.n_bootstrap):
            # 无放回采样
            indices = rng.choice(n_samples, size=subset_size, replace=False)
            X_sub = X_all[indices]
            y_sub = y[indices]

            # 每个子样本独立拟合预处理，避免全数据填充/缩放泄漏。
            model = Pipeline([
                ("imputer", SimpleImputer(strategy="median")),
                ("scale", StandardScaler()),
                ("lasso", Lasso(alpha=self.alpha, max_iter=20_000)),
            ])
            model.fit(X_sub, y_sub)
            coefs = model.named_steps["lasso"].coef_
            selected = np.abs(coefs) > 1e-12
            selection_counts += selected.astype(int)

        # 计算选中频率
        selection_freq = selection_counts / self.n_bootstrap

        # 计算噪声基线
        if X_noise is not None:
            n_real_feat = n_real
            noise_freqs = selection_freq[n_real_feat:]
            # 噪声基线 = 噪声列选中频率的 95 分位数
            noise_baseline = float(np.percentile(noise_freqs, 95)) if len(noise_freqs) > 0 else 0.0
        else:
            noise_baseline = 0.0

        # 构建结果 DataFrame
        records = []
        for i, name in enumerate(all_names):
            freq = float(selection_freq[i])
            is_real = i < n_real

            # above_noise_baseline: 真实描述符需要 > 噪声基线
            # 噪声列本身不参与此判断
            if is_real:
                above_baseline = freq > noise_baseline
            else:
                above_baseline = True  # 噪声列标记为 True，不影响筛选

            records.append({
                "feature_name": name,
                "selection_freq": freq,
                "is_stable": freq > self.threshold,
                "above_noise_baseline": above_baseline,
                "is_noise": not is_real,
                "selection_method": "subsampled_lasso",
                "selection_alpha": float(self.alpha),
                "noise_baseline": noise_baseline,
            })

        result_df = pd.DataFrame.from_records(
            records,
            columns=[*STABILITY_RESULT_COLUMNS, "is_noise"],
        )

        # 仅返回真实描述符的结果（噪声列信息已用于计算基线）
        real_df = result_df[~result_df["is_noise"]].drop(columns=["is_noise"]).reset_index(drop=True)
        real_df.attrs.update(self._result_metadata(noise_baseline))

        return real_df


class PhysicalGrouper:
    """物理族代表选择器：从稳定描述符中按物理族挑选代表。

    策略（errata P4）：
    - 八大物理族 A, B, C, D', E, F, G, H
    - 每族默认最多选 max_per_family 个代表
    - 代表 = 族内稳定性通过 + |去混杂 Spearman| 最高的描述符
    - ``max_per_family`` 是硬上限；不以缺失族为由扩容

    注意：D' 族在代码中用 "D_prime" 表示。
    """

    def __init__(self, max_per_family: int = 1) -> None:
        """初始化物理族选择器。

        参数:
            max_per_family: 每族最大代表数，默认 1（errata P4）
        """
        self.max_per_family = max_per_family

    def group_and_select(
        self,
        stability_df: pd.DataFrame,
        deconfound_df: pd.DataFrame,
        descriptor_registry: dict[str, tuple] | None = None,
    ) -> pd.DataFrame:
        """按物理族分组并选择代表描述符。

        参数:
            stability_df: StabilitySelector.run() 的输出 DataFrame
                必须包含 feature_name, selection_freq, is_stable, above_noise_baseline
            deconfound_df: 去混杂结果 DataFrame
                必须包含 descriptor (列名=特征名), deconfounded_spearman
            descriptor_registry: 描述符注册表，默认使用 SEARCHABLE_STRUCTURE_DESCRIPTORS
                格式: {name: (compute_func, family_key, is_high_risk)}

        返回:
            DataFrame，每行一个稳定描述符，包含:
            - descriptor: 描述符名
            - family: 所属物理族 (A/B/C/D_prime/E/F/G/H)
            - family_name: 物理族中文名
            - deconfounded_spearman: 去混杂 Spearman rho
            - selection_freq: 稳定性选中频率
            - is_stable: 是否通过稳定性阈值
            - above_noise_baseline: 是否超过噪声基线
            - is_representative: 是否被选为族代表
        """
        if descriptor_registry is None:
            descriptor_registry = SEARCHABLE_STRUCTURE_DESCRIPTORS

        # 构建描述符 → 物理族映射
        desc_to_family: dict[str, str] = {}
        for name, (_, family_key, _) in descriptor_registry.items():
            desc_to_family[name] = family_key

        # 合并稳定性结果和去混杂结果
        # stability_df 用 feature_name，deconfound_df 用 descriptor 列名
        merged = stability_df.merge(
            deconfound_df,
            left_on="feature_name",
            right_on="descriptor",
            how="left",
        )

        # 填充物理族信息
        records = []
        for _, row in merged.iterrows():
            desc_name = row["feature_name"]
            family_key = desc_to_family.get(desc_name, "unknown")
            family_info = PHYSICAL_FAMILIES.get(family_key, {})
            family_name = family_info.get("name", "未知")

            records.append({
                "descriptor": desc_name,
                "family": family_key,
                "family_name": family_name,
                "deconfounded_spearman": row.get("deconfounded_spearman", float("nan")),
                "selection_freq": row.get("selection_freq", 0.0),
                "is_stable": row.get("is_stable", False),
                "above_noise_baseline": row.get("above_noise_baseline", True),
                "is_representative": False,
            })

        result_df = pd.DataFrame.from_records(
            records,
            columns=PHYSICAL_GROUP_RESULT_COLUMNS,
        )
        result_df.attrs.update(stability_df.attrs)
        result_df.attrs.update(deconfound_df.attrs)

        if result_df.empty:
            return result_df

        # 筛选: 稳定 + 超过噪声基线的描述符才参与代表选择
        eligible = result_df[result_df["is_stable"] & result_df["above_noise_baseline"]]

        # 按物理族分组
        family_groups = eligible.groupby("family")

        # 第一轮: 每族选 deconfounded_spearman 最高的代表
        representatives: set[str] = set()

        for family_key in PHYSICAL_FAMILIES:
            if family_key not in family_groups.groups:
                continue

            group = family_groups.get_group(family_key)
            if group.empty:
                continue

            # 代表按 |rho| 排名，但输出保留 deconfounded_spearman 的符号。
            top = group.loc[
                group["deconfounded_spearman"].abs().nlargest(self.max_per_family).index
            ]
            representatives.update(top["descriptor"].tolist())

        # 标记代表
        result_df["is_representative"] = result_df["descriptor"].isin(representatives)

        return result_df

--- 文件结束: descriptors/stability.py ---

--- 文件开始: descriptors/cv_strategies.py ---
"""交叉验证策略实现。

支持多种 CV 策略以评估描述符在不同数据划分下的稳健性：
1. 阴离子分层 K 折（按阴离子类型 O/S/Se/F/Cl/Br/I 分层）
2. 留一体系交叉验证（LOSO-CV，按 NASICON/sulfide/halide 分组）
3. 重复随机子采样（按体系分层，多次重复评估波动范围）

所有策略统一使用 Ridge 回归模型，评价指标为 Spearman 秩相关和 MAE。
"""
from __future__ import annotations

from typing import Any

import numpy as np
from scipy.stats import spearmanr
from sklearn.impute import SimpleImputer
from sklearn.linear_model import Ridge
from sklearn.model_selection import (
    LeaveOneGroupOut,
    StratifiedKFold,
    StratifiedShuffleSplit,
)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler


def _fold_metrics(
    model: Pipeline,
    X_train: np.ndarray,
    y_train: np.ndarray,
    X_val: np.ndarray,
    y_val: np.ndarray,
) -> tuple[float, float]:
    """训练模型并返回单折 (spearman_rho, mae)。"""
    model.fit(X_train, y_train)
    y_pred = model.predict(X_val)
    rho = spearmanr(y_val, y_pred).statistic
    mae = float(np.mean(np.abs(y_val - y_pred)))
    return rho, mae


def _mean_or_nan(values: list[float]) -> float:
    """Return the finite-value mean, or NaN when no fold produced one."""
    finite = np.asarray(values, dtype=float)
    finite = finite[np.isfinite(finite)]
    return float(finite.mean()) if finite.size else float("nan")


CV_SPEARMAN_SUMMARY_COLUMNS = [
    "anion_stratified_spearman",
    "anion_stratified_skipped",
    "anion_stratified_skip_reason",
    "anion_stratified_available",
    "anion_stratified_downshifted",
    "anion_stratified_requested_n_folds",
    "anion_stratified_effective_n_folds",
    "loso_spearman",
    "loso_skipped",
    "loso_skip_reason",
    "loso_available",
    "repeated_subsample_spearman",
    "repeated_subsample_skipped",
    "repeated_subsample_skip_reason",
    "repeated_subsample_available",
    "composite_score",
    "composite_strategy_count",
    "composite_is_complete",
    "composite_score_basis",
]


def summarize_cv_spearman(
    cv_results: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    """Summarize CV without counting skipped/unavailable strategies as evidence."""
    strategies = (
        ("anion_stratified_cv", "anion_stratified"),
        ("leave_one_system_out", "loso"),
        ("repeated_subsample", "repeated_subsample"),
    )
    summary: dict[str, Any] = {}
    available_scores: list[float] = []

    for strategy_key, prefix in strategies:
        result = cv_results[strategy_key]
        spearman = float(result.get("mean_spearman", float("nan")))
        skipped = bool(result.get("skipped", False))
        available = bool(not skipped and np.isfinite(spearman))
        summary[f"{prefix}_spearman"] = spearman
        summary[f"{prefix}_skipped"] = skipped
        summary[f"{prefix}_skip_reason"] = result.get("reason") if skipped else None
        summary[f"{prefix}_available"] = available
        if available:
            available_scores.append(abs(spearman))

    anion_result = cv_results["anion_stratified_cv"]
    summary.update({
        "anion_stratified_downshifted": bool(
            anion_result.get("downshifted", False)
        ),
        "anion_stratified_requested_n_folds": int(
            anion_result.get("requested_n_folds", 0)
        ),
        "anion_stratified_effective_n_folds": int(
            anion_result.get("effective_n_folds", 0)
        ),
        "composite_score": (
            float(np.mean(available_scores))
            if available_scores else float("nan")
        ),
        "composite_strategy_count": len(available_scores),
        "composite_is_complete": len(available_scores) == len(strategies),
        "composite_score_basis": "mean_absolute_spearman_available_strategies",
    })
    return summary


class MultiStrategyCV:
    """多策略交叉验证评估器。

    用同一个 Ridge 模型在不同数据划分下评估描述符预测能力，
    检验"相关性是否稳健"而非"在某一划分下恰好好"。

    参数:
        alpha: Ridge 正则化强度，越大惩罚越重
    """

    def __init__(self, alpha: float = 1.0) -> None:
        self.alpha = alpha

    def _make_model(self) -> Pipeline:
        """Create a fresh fold-local imputation/scaling/Ridge pipeline."""
        return Pipeline([
            ("imputer", SimpleImputer(strategy="median")),
            ("scale", StandardScaler()),
            ("ridge", Ridge(alpha=self.alpha)),
        ])

    def anion_stratified_cv(
        self,
        X: np.ndarray,
        y: np.ndarray,
        anion_labels: np.ndarray,
        n_folds: int = 3,
    ) -> dict[str, Any]:
        """阴离子分层 K 折交叉验证。

        按阴离子类型（O/S/Se/F/Cl/Br/I）分层，确保每折中
        各阴离子类型的比例大致相同。避免某类阴离子全部落在
        验证集导致"预测好只是因为记住该类"。

        参数:
            X: 特征矩阵 (n_samples, n_features)
            y: 目标向量 (n_samples,)
            anion_labels: 阴离子类型标签 (n_samples,)
            n_folds: 折数

        返回:
            {strategy, fold_results, mean_spearman, mean_mae}
        """
        X = np.asarray(X, dtype=float)
        y = np.asarray(y, dtype=float)
        anion_labels = np.asarray(anion_labels)

        # 将阴离子字符串标签编码为整数以供 StratifiedKFold 使用
        unique_anions, class_counts = np.unique(anion_labels, return_counts=True)
        requested_n_folds = int(n_folds)
        min_class_count = int(class_counts.min()) if class_counts.size else 0

        if requested_n_folds < 2 or min_class_count < 2:
            reason = (
                "anion-stratified CV skipped: at least one label has fewer than two samples"
            )
            return {
                "strategy": "anion_stratified_cv",
                "skipped": True,
                "reason": reason,
                "fold_results": [],
                "mean_spearman": float("nan"),
                "mean_mae": float("nan"),
                "requested_n_folds": requested_n_folds,
                "effective_n_folds": 0,
                "downshifted": False,
                "class_counts": {
                    str(label): int(count)
                    for label, count in zip(unique_anions, class_counts)
                },
            }

        effective_n_folds = min(requested_n_folds, min_class_count)
        anion_map = {a: i for i, a in enumerate(unique_anions)}
        anion_codes = np.array([anion_map[a] for a in anion_labels], dtype=int)

        skf = StratifiedKFold(
            n_splits=effective_n_folds,
            shuffle=True,
            random_state=42,
        )
        fold_results: list[dict[str, Any]] = []

        for fold, (train_idx, val_idx) in enumerate(skf.split(X, anion_codes), start=1):
            rho, mae = _fold_metrics(
                self._make_model(),
                X[train_idx], y[train_idx],
                X[val_idx], y[val_idx],
            )
            fold_results.append({
                "fold": fold,
                "train_idx": train_idx,
                "val_idx": val_idx,
                "spearman": rho,
                "mae": mae,
            })

        spearmans = [f["spearman"] for f in fold_results]
        maes = [f["mae"] for f in fold_results]
        return {
            "strategy": "anion_stratified_cv",
            "skipped": False,
            "reason": (
                f"requested {requested_n_folds} folds but class support allows "
                f"only {effective_n_folds}"
                if effective_n_folds != requested_n_folds else None
            ),
            "fold_results": fold_results,
            "mean_spearman": _mean_or_nan(spearmans),
            "mean_mae": _mean_or_nan(maes),
            "requested_n_folds": requested_n_folds,
            "effective_n_folds": effective_n_folds,
            "downshifted": effective_n_folds != requested_n_folds,
            "class_counts": {
                str(label): int(count)
                for label, count in zip(unique_anions, class_counts)
            },
        }

    def leave_one_system_out(
        self,
        X: np.ndarray,
        y: np.ndarray,
        system_labels: np.ndarray,
    ) -> dict[str, Any]:
        """留一体系交叉验证（LOSO-CV）。

        每次留出一个体系（NASICON / sulfide / halide）的全部样本
        作为验证集，其余体系作为训练集。检验描述符跨体系的泛化
        能力——如果只在 NASICON 上有效，对硫化物/卤化物无效，
        说明"相关性"可能是体系特异的而非普适的。

        参数:
            X: 特征矩阵 (n_samples, n_features)
            y: 目标向量 (n_samples,)
            system_labels: 体系分组标签 (n_samples,)

        返回:
            {strategy, fold_results, mean_spearman, mean_mae}
        """
        X = np.asarray(X, dtype=float)
        y = np.asarray(y, dtype=float)
        system_labels = np.asarray(system_labels)

        # 将体系字符串标签编码为整数组号以供 LeaveOneGroupOut 使用
        unique_systems = np.unique(system_labels)
        system_map = {s: i for i, s in enumerate(unique_systems)}
        groups = np.array([system_map[s] for s in system_labels], dtype=int)

        logo = LeaveOneGroupOut()
        fold_results: list[dict[str, Any]] = []

        for fold, (train_idx, val_idx) in enumerate(logo.split(X, y, groups), start=1):
            # 跳过训练集为空或验证集为空的极端情况
            if len(train_idx) == 0 or len(val_idx) == 0:
                continue

            rho, mae = _fold_metrics(
                self._make_model(),
                X[train_idx], y[train_idx],
                X[val_idx], y[val_idx],
            )
            fold_results.append({
                "fold": fold,
                "train_idx": train_idx,
                "val_idx": val_idx,
                "spearman": rho,
                "mae": mae,
            })

        spearmans = [f["spearman"] for f in fold_results]
        maes = [f["mae"] for f in fold_results]
        return {
            "strategy": "leave_one_system_out",
            "fold_results": fold_results,
            "mean_spearman": _mean_or_nan(spearmans),
            "mean_mae": _mean_or_nan(maes),
        }

    def repeated_subsample(
        self,
        X: np.ndarray,
        y: np.ndarray,
        system_labels: np.ndarray,
        n_repeats: int = 10,
        test_fraction: float = 0.2,
        seed: int = 42,
    ) -> dict[str, Any]:
        """重复随机子采样交叉验证。

        按体系标签分层，多次随机划分训练/验证集，评估结果的
        波动范围。如果 10 次重复的 Spearman 相关波动很大，
        说明结果对数据划分敏感，不够稳健。

        参数:
            X: 特征矩阵 (n_samples, n_features)
            y: 目标向量 (n_samples,)
            system_labels: 体系分组标签，用于分层
            n_repeats: 重复次数
            test_fraction: 验证集比例
            seed: 基础随机种子

        返回:
            {strategy, fold_results, mean_spearman, mean_mae}
        """
        X = np.asarray(X, dtype=float)
        y = np.asarray(y, dtype=float)
        system_labels = np.asarray(system_labels)

        # 将体系字符串标签编码为整数以供 StratifiedShuffleSplit 使用
        unique_systems = np.unique(system_labels)
        system_map = {s: i for i, s in enumerate(unique_systems)}
        system_codes = np.array([system_map[s] for s in system_labels], dtype=int)

        fold_results: list[dict[str, Any]] = []

        _, class_counts = np.unique(system_codes, return_counts=True)
        n_classes = len(class_counts)
        n_samples = len(system_codes)
        valid_fraction = 0.0 < test_fraction < 1.0
        n_test = int(np.ceil(n_samples * test_fraction)) if valid_fraction else 0
        n_train = n_samples - n_test
        infeasible_reason: str | None = None
        if n_repeats < 1:
            infeasible_reason = "n_repeats must be at least one"
        elif not valid_fraction:
            infeasible_reason = "test_fraction must be strictly between zero and one"
        elif class_counts.size == 0 or int(class_counts.min()) < 2:
            infeasible_reason = (
                "stratified subsampling requires at least two samples per system label"
            )
        elif n_test < n_classes or n_train < n_classes:
            infeasible_reason = (
                f"test_fraction={test_fraction} yields train/test sizes "
                f"{n_train}/{n_test}, which cannot represent all {n_classes} system labels"
            )

        if infeasible_reason is not None:
            return {
                "strategy": "repeated_subsample",
                "skipped": True,
                "reason": infeasible_reason,
                "fold_results": [],
                "mean_spearman": float("nan"),
                "mean_mae": float("nan"),
                "n_repeats": int(n_repeats),
                "test_fraction": float(test_fraction),
                "seed": int(seed),
            }

        splitter = StratifiedShuffleSplit(
            n_splits=n_repeats,
            test_size=test_fraction,
            random_state=seed,
        )
        for repeat_idx, (train_idx, val_idx) in enumerate(
            splitter.split(X, system_codes), start=1
        ):
            rho, mae = _fold_metrics(
                self._make_model(),
                X[train_idx], y[train_idx],
                X[val_idx], y[val_idx],
            )
            fold_results.append({
                "fold": repeat_idx,
                "train_idx": train_idx,
                "val_idx": val_idx,
                "spearman": rho,
                "mae": mae,
            })

        spearmans = [f["spearman"] for f in fold_results]
        maes = [f["mae"] for f in fold_results]
        return {
            "strategy": "repeated_subsample",
            "skipped": False,
            "reason": None,
            "fold_results": fold_results,
            "mean_spearman": _mean_or_nan(spearmans),
            "mean_mae": _mean_or_nan(maes),
            "n_repeats": int(n_repeats),
            "test_fraction": float(test_fraction),
            "seed": int(seed),
        }

    def run_all(
        self,
        X: np.ndarray,
        y: np.ndarray,
        system_labels: np.ndarray,
        anion_labels: np.ndarray,
    ) -> dict[str, dict[str, Any]]:
        """依次运行全部三种 CV 策略。

        参数:
            X: 特征矩阵 (n_samples, n_features)
            y: 目标向量 (n_samples,)
            system_labels: 体系分组标签 (n_samples,)
            anion_labels: 阴离子类型标签 (n_samples,)

        返回:
            {anion_stratified_cv: {...}, leave_one_system_out: {...}, repeated_subsample: {...}}
        """
        return {
            "anion_stratified_cv": self.anion_stratified_cv(X, y, anion_labels),
            "leave_one_system_out": self.leave_one_system_out(X, y, system_labels),
            "repeated_subsample": self.repeated_subsample(X, y, system_labels),
        }

--- 文件结束: descriptors/cv_strategies.py ---

--- 文件开始: descriptors/combination.py ---
"""Physics-constrained descriptor combination search and validation.

Formula construction is deliberately small and auditable: raw descriptor
values are combined with ``+``, multiplication, or explicitly permitted ratio
directions.  Pair and triple rules live in a declarative registry below, and
every candidate carries the rule and raw-value provenance that admitted it.
"""
from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from itertools import combinations
from typing import Any

import numpy as np
import pandas as pd
from scipy import stats
from sklearn.impute import SimpleImputer
from sklearn.linear_model import Ridge
from sklearn.model_selection import KFold, StratifiedKFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from descriptors import (
    AVAILABLE_STRUCTURE_DESCRIPTORS,
    STRUCTURE_DESCRIPTOR_METADATA,
)
from descriptors.cv_strategies import (
    CV_SPEARMAN_SUMMARY_COLUMNS,
    MultiStrategyCV,
    summarize_cv_spearman,
)
from descriptors.deconfound import DeconfoundAnalyzer


# Rules are directional.  Commutative operations are copied in both directions;
# a ratio exists only in the physically named numerator -> denominator direction.
PAIR_OPERATOR_RULES: dict[tuple[str, str], tuple[str, ...]] = {
    ("A", "B"): ("+", "multiply"),
    ("B", "A"): ("+", "multiply"),
    ("A", "D_prime"): ("multiply",),
    ("D_prime", "A"): ("multiply",),
    ("A", "C"): ("ratio",),
    ("B", "D_prime"): ("+", "multiply"),
    ("D_prime", "B"): ("+", "multiply"),
    ("A", "H"): ("+", "multiply"),
    ("H", "A"): ("+", "multiply"),
    ("E", "A"): ("multiply",),
    ("A", "E"): ("multiply",),
}
SAME_FAMILY_OPERATOR_RULES: dict[str, tuple[str, ...]] = {
    family: ("+", "multiply")
    for family in ("A", "B", "C", "D_prime", "E", "F", "G", "H")
}

COMBINATION_RESULT_COLUMNS = [
    "combined_name",
    "d1",
    "d2",
    "operator",
    "components",
    "operators",
    "component_families",
    "n_components",
    "d1_family",
    "d2_family",
    "is_cross_family",
    "combined_raw_spearman",
    "combined_deconf_spearman",
    "n_valid",
    "raw_value_source",
    "formula_provenance",
]

FORMULA_JSON_COLUMNS = (
    "components",
    "operators",
    "component_families",
    "formula_provenance",
)
VALIDATION_JSON_COLUMNS = (
    *FORMULA_JSON_COLUMNS,
    "noise_baseline",
    "factor_spanning",
    "per_system",
    "bootstrap_ci",
    "evidence_blocks",
    "cv_diagnostics",
)

COMBINATION_VALIDATION_RESULT_COLUMNS = [
    "combined_name",
    "d1",
    "d2",
    "operator",
    "components",
    "operators",
    "component_families",
    "n_components",
    "raw_value_source",
    "formula_provenance",
    "combined_deconf_spearman",
    *CV_SPEARMAN_SUMMARY_COLUMNS,
    "validation_status",
    "causal_claim",
    "uncertainty_method",
    "noise_baseline",
    "factor_spanning",
    "per_system",
    "bootstrap_ci",
    "evidence_blocks",
    "cv_diagnostics",
]


def _safe_spearman(x: np.ndarray, y: np.ndarray) -> float:
    """Return finite-pair Spearman, or NaN for insufficient/constant data."""
    x_arr = np.asarray(x, dtype=float)
    y_arr = np.asarray(y, dtype=float)
    mask = np.isfinite(x_arr) & np.isfinite(y_arr)
    if int(mask.sum()) < 3:
        return float("nan")
    x_valid = x_arr[mask]
    y_valid = y_arr[mask]
    if np.unique(x_valid).size < 2 or np.unique(y_valid).size < 2:
        return float("nan")
    return float(stats.spearmanr(x_valid, y_valid).statistic)


def _json_ready(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _json_ready(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, np.ndarray)):
        return [_json_ready(item) for item in list(value)]
    if isinstance(value, (np.integer, np.bool_)):
        return value.item()
    if isinstance(value, (float, np.floating)):
        return None if not np.isfinite(value) else float(value)
    return value


def _containers_to_csv_frame(
    dataframe: pd.DataFrame, columns: Sequence[str]
) -> pd.DataFrame:
    serialised = dataframe.copy()
    for column in columns:
        if column not in serialised.columns:
            continue

        def encode(value: Any) -> Any:
            if isinstance(value, (list, tuple, np.ndarray, Mapping)):
                return json.dumps(
                    _json_ready(value),
                    ensure_ascii=False,
                    separators=(",", ":"),
                    allow_nan=False,
                )
            if value is None or (isinstance(value, float) and np.isnan(value)):
                return value
            raise ValueError(
                f"formula field {column!r} must be a list/dict before CSV serialisation"
            )

        serialised[column] = serialised[column].map(encode)
    return serialised


def combination_candidates_to_csv_frame(candidates_df: pd.DataFrame) -> pd.DataFrame:
    """Return a CSV-safe copy with formula containers encoded as strict JSON."""
    return _containers_to_csv_frame(candidates_df, FORMULA_JSON_COLUMNS)


def combination_validation_to_csv_frame(validation_df: pd.DataFrame) -> pd.DataFrame:
    """Return a CSV-safe copy with formula/evidence artifacts encoded as JSON."""
    return _containers_to_csv_frame(validation_df, VALIDATION_JSON_COLUMNS)


class ConstrainedCombinationSearch:
    """Enumerate plan-constrained formulas and rank their raw-value signal."""

    def __init__(self, alpha: float = 1.0, seed: int = 42) -> None:
        self.alpha = alpha
        self.seed = seed

    @staticmethod
    def _getAllowedOperators(family1: str, family2: str) -> list[str]:
        """Return only operators explicitly registered for this direction."""
        if family1 == family2:
            return list(SAME_FAMILY_OPERATOR_RULES.get(family1, ()))
        return list(PAIR_OPERATOR_RULES.get((family1, family2), ()))

    @staticmethod
    def _generateCombinedFeature(
        d1_values: np.ndarray,
        d2_values: np.ndarray,
        operator: str,
    ) -> np.ndarray:
        """Apply one allowed operation without imputation or denominator hacks."""
        d1 = np.asarray(d1_values, dtype=float)
        d2 = np.asarray(d2_values, dtype=float)
        if operator == "+":
            return d1 + d2
        if operator == "multiply":
            return d1 * d2
        if operator == "ratio":
            result = np.full(np.broadcast_shapes(d1.shape, d2.shape), np.nan)
            valid = np.isfinite(d1) & np.isfinite(d2) & (d2 != 0.0)
            np.divide(d1, d2, out=result, where=valid)
            return result
        raise ValueError(f"Unsupported combination operator: {operator}")

    @staticmethod
    def _apply_formula(arrays: Sequence[np.ndarray], operators: Sequence[str]) -> np.ndarray:
        if len(arrays) < 2 or len(operators) != len(arrays) - 1:
            raise ValueError("A formula requires n components and n-1 operators")
        result = np.asarray(arrays[0], dtype=float)
        for values, operator in zip(arrays[1:], operators):
            result = ConstrainedCombinationSearch._generateCombinedFeature(
                result, np.asarray(values, dtype=float), operator
            )
        return result

    @staticmethod
    def _descriptor_dimension(name: str, reps: pd.DataFrame) -> str | None:
        metadata = STRUCTURE_DESCRIPTOR_METADATA.get(name)
        if metadata is not None:
            return str(metadata["dimension"])
        if "dimension" in reps.columns:
            values = reps.loc[reps["descriptor"] == name, "dimension"]
            if not values.empty and pd.notna(values.iloc[0]):
                return str(values.iloc[0])
        return None

    @classmethod
    def _operator_dimensionally_valid(
        cls,
        d1: str,
        d2: str,
        operator: str,
        reps: pd.DataFrame,
    ) -> bool:
        # Addition is only meaningful for equal known dimensions. Unknown custom
        # descriptors remain usable for compatibility with external registries.
        if operator != "+":
            return True
        dim1 = cls._descriptor_dimension(d1, reps)
        dim2 = cls._descriptor_dimension(d2, reps)
        return dim1 is None or dim2 is None or dim1 == dim2

    @classmethod
    def _formula_dimensionally_valid(
        cls,
        components: Sequence[str],
        operators: Sequence[str],
        reps: pd.DataFrame,
    ) -> bool:
        current = cls._descriptor_dimension(components[0], reps)
        for component, operator in zip(components[1:], operators):
            other = cls._descriptor_dimension(component, reps)
            if operator == "+":
                if current is not None and other is not None and current != other:
                    return False
                current = current or other
            elif operator == "multiply":
                current = (
                    f"({current})*({other})"
                    if current is not None and other is not None else None
                )
            elif operator == "ratio":
                current = (
                    "dimensionless"
                    if current is not None and current == other
                    else f"({current})/({other})"
                    if current is not None and other is not None
                    else None
                )
        return True

    @staticmethod
    def _is_active(name: str) -> bool:
        metadata = STRUCTURE_DESCRIPTOR_METADATA.get(name)
        return metadata is None or bool(metadata.get("active_for_search", True))

    def _evaluate_candidate(
        self,
        feature_df: pd.DataFrame,
        y: np.ndarray,
        confounders: pd.DataFrame,
        components: list[str],
        families: list[str],
        operators: list[str],
        rule_ids: list[str],
    ) -> dict[str, Any] | None:
        if any(name not in feature_df.columns for name in components):
            return None
        arrays = [feature_df[name].to_numpy(dtype=float) for name in components]
        values = self._apply_formula(arrays, operators)
        valid = np.isfinite(values) & np.isfinite(y)
        n_valid = int(valid.sum())
        if n_valid < 5:
            return None

        raw_rho = _safe_spearman(values[valid], y[valid])
        deconf_rho = DeconfoundAnalyzer(alpha=self.alpha).deconfounded_spearman(
            values[valid],
            y[valid],
            confounders.loc[valid].reset_index(drop=True),
        )
        symbols = {"+": "+", "multiply": "×", "ratio": "/"}
        name = components[0]
        for component, operator in zip(components[1:], operators):
            name = f"({name} {symbols[operator]} {component})"

        provenance = {
            "components": list(components),
            "component_families": list(families),
            "operators": list(operators),
            "rules": list(rule_ids),
            "raw_value_source": "feature_df",
            "missing_value_policy": "mask_nonfinite_and_zero_denominators",
            "standardisation": "finished_formula_only_in_model_fit",
        }
        return {
            "combined_name": name,
            "d1": components[0],
            "d2": components[1],
            "operator": operators[0],
            "components": list(components),
            "operators": list(operators),
            "component_families": list(families),
            "n_components": len(components),
            "d1_family": families[0],
            "d2_family": families[1],
            "is_cross_family": len(set(families)) > 1,
            "combined_raw_spearman": raw_rho,
            "combined_deconf_spearman": float(deconf_rho),
            "n_valid": n_valid,
            "raw_value_source": "feature_df",
            "formula_provenance": provenance,
        }

    def search(
        self,
        feature_df: pd.DataFrame,
        y: np.ndarray,
        system_labels: list[str],
        anion_labels: list[str],
        representative_df: pd.DataFrame,
        max_candidates: int = 150,
        max_descriptors: int = 3,
    ) -> pd.DataFrame:
        """Search explicit pairs and plan-constrained triples from raw columns."""
        if max_descriptors not in (2, 3):
            raise ValueError("max_descriptors must be 2 or 3")
        if representative_df.empty:
            return pd.DataFrame(columns=COMBINATION_RESULT_COLUMNS)
        representative_mask = (
            representative_df["is_representative"]
            if "is_representative" in representative_df.columns
            else pd.Series(True, index=representative_df.index)
        )
        reps = representative_df.loc[representative_mask == True].copy()  # noqa: E712
        if reps.empty:
            return pd.DataFrame(columns=COMBINATION_RESULT_COLUMNS)
        reps = reps.loc[reps["descriptor"].map(self._is_active)]
        rep_names = list(dict.fromkeys(reps["descriptor"].astype(str).tolist()))
        desc_to_family = dict(zip(reps["descriptor"], reps["family"]))
        for name, (_, family, _) in AVAILABLE_STRUCTURE_DESCRIPTORS.items():
            desc_to_family.setdefault(name, family)

        y_arr = np.asarray(y, dtype=float)
        deconf = DeconfoundAnalyzer(alpha=self.alpha)
        confounders, _control_metadata = deconf.build_rank_aware_controls(
            system_labels, anion_labels
        )
        confounders.index = feature_df.index
        candidates: list[dict[str, Any]] = []

        # Commutative pairs appear once. Ratio direction is emitted only when
        # the exact ordered family rule admits it.
        for d1, d2 in combinations(rep_names, 2):
            f1, f2 = desc_to_family[d1], desc_to_family[d2]
            forward = self._getAllowedOperators(f1, f2)
            reverse = self._getAllowedOperators(f2, f1)
            for operator in ("+", "multiply"):
                if operator not in forward and operator not in reverse:
                    continue
                if not self._operator_dimensionally_valid(d1, d2, operator, reps):
                    continue
                record = self._evaluate_candidate(
                    feature_df,
                    y_arr,
                    confounders,
                    [d1, d2],
                    [f1, f2],
                    [operator],
                    [f"pair:{min(f1, f2)}-{max(f1, f2)}:{operator}"],
                )
                if record is not None:
                    candidates.append(record)
            if "ratio" in forward:
                record = self._evaluate_candidate(
                    feature_df,
                    y_arr,
                    confounders,
                    [d1, d2],
                    [f1, f2],
                    ["ratio"],
                    [f"directional_ratio:{f1}->{f2}"],
                )
                if record is not None:
                    candidates.append(record)
            if "ratio" in reverse:
                record = self._evaluate_candidate(
                    feature_df,
                    y_arr,
                    confounders,
                    [d2, d1],
                    [f2, f1],
                    ["ratio"],
                    [f"directional_ratio:{f2}->{f1}"],
                )
                if record is not None:
                    candidates.append(record)

        if max_descriptors == 3:
            by_family: dict[str, list[str]] = {}
            for name in rep_names:
                by_family.setdefault(desc_to_family[name], []).append(name)
            for repeated_family, family_names in by_family.items():
                for d1, d2 in combinations(family_names, 2):
                    for adjacent_family, adjacent_names in by_family.items():
                        if adjacent_family == repeated_family:
                            continue
                        cross_ops = self._getAllowedOperators(
                            repeated_family, adjacent_family
                        )
                        if not cross_ops:
                            continue
                        for d3 in adjacent_names:
                            for within_op in SAME_FAMILY_OPERATOR_RULES.get(
                                repeated_family, ()
                            ):
                                if not self._operator_dimensionally_valid(
                                    d1, d2, within_op, reps
                                ):
                                    continue
                                for cross_op in cross_ops:
                                    if not self._formula_dimensionally_valid(
                                        [d1, d2, d3],
                                        [within_op, cross_op],
                                        reps,
                                    ):
                                        continue
                                    record = self._evaluate_candidate(
                                        feature_df,
                                        y_arr,
                                        confounders,
                                        [d1, d2, d3],
                                        [repeated_family, repeated_family, adjacent_family],
                                        [within_op, cross_op],
                                        [
                                            f"triple:two_from:{repeated_family}",
                                            f"triple:adjacent:{repeated_family}->{adjacent_family}:{cross_op}",
                                        ],
                                    )
                                    if record is not None:
                                        candidates.append(record)

        if not candidates:
            return pd.DataFrame(columns=COMBINATION_RESULT_COLUMNS)
        result = pd.DataFrame.from_records(candidates, columns=COMBINATION_RESULT_COLUMNS)
        result = result.sort_values(
            "combined_deconf_spearman",
            key=lambda values: values.abs(),
            ascending=False,
            na_position="last",
        ).reset_index(drop=True)
        return result.head(max_candidates).reset_index(drop=True)


class CombinationValidator:
    """Generate exploratory V1--V4 evidence plus existing CV diagnostics."""

    def __init__(self, alpha: float = 1.0, seed: int = 42) -> None:
        self.alpha = alpha
        self.seed = seed

    @staticmethod
    def _is_missing_field(value: Any) -> bool:
        return value is None or (
            isinstance(value, (float, np.floating)) and np.isnan(value)
        )

    @classmethod
    def _parse_formula_list(cls, value: Any, field: str) -> list[str]:
        if isinstance(value, str):
            try:
                value = json.loads(value)
            except json.JSONDecodeError as exc:
                raise ValueError(
                    f"formula field {field!r} is not valid JSON"
                ) from exc
        elif isinstance(value, (tuple, np.ndarray)):
            value = list(value)
        if not isinstance(value, list) or not all(
            isinstance(item, str) and item for item in value
        ):
            raise ValueError(f"formula field {field!r} must be a list[str]")
        return list(value)

    @classmethod
    def _parse_formula_provenance(cls, value: Any) -> dict[str, Any] | None:
        if cls._is_missing_field(value):
            return None
        if isinstance(value, str):
            try:
                value = json.loads(value)
            except json.JSONDecodeError as exc:
                raise ValueError("formula provenance is not valid JSON") from exc
        if not isinstance(value, Mapping):
            raise ValueError("formula provenance must be a JSON object")
        return dict(value)

    @classmethod
    def _candidate_formula(cls, candidate: Mapping[str, Any]) -> tuple[list[str], list[str]]:
        raw_components = candidate.get("components")
        raw_operators = candidate.get("operators")
        components_missing = cls._is_missing_field(raw_components)
        operators_missing = cls._is_missing_field(raw_operators)

        # Backward compatibility is limited to the legacy pair API where both
        # structured fields are genuinely absent. Partially present/corrupt
        # structured formula data is never silently downgraded.
        if components_missing and operators_missing:
            try:
                components = [candidate["d1"], candidate["d2"]]
                operators = [candidate["operator"]]
            except KeyError as exc:
                raise ValueError("legacy formula is missing d1/d2/operator") from exc
            if not all(isinstance(item, str) and item for item in components + operators):
                raise ValueError("legacy formula fields must be non-empty strings")
        elif components_missing or operators_missing:
            raise ValueError(
                "formula components and operators must be provided together"
            )
        else:
            components = cls._parse_formula_list(raw_components, "components")
            operators = cls._parse_formula_list(raw_operators, "operators")

        if not 2 <= len(components) <= 3:
            raise ValueError("formula must contain two or three components")
        if len(operators) != len(components) - 1:
            raise ValueError("formula operator count must equal component count minus one")
        if any(operator not in {"+", "multiply", "ratio"} for operator in operators):
            raise ValueError("formula contains an unsupported operator")

        declared_n = candidate.get("n_components")
        if not cls._is_missing_field(declared_n) and int(declared_n) != len(components):
            raise ValueError("formula n_components is inconsistent with components")
        for key, expected in (
            ("d1", components[0]),
            ("d2", components[1]),
            ("operator", operators[0]),
        ):
            declared = candidate.get(key)
            if not cls._is_missing_field(declared) and declared != expected:
                raise ValueError(f"formula field {key!r} is inconsistent with structured formula")

        provenance = cls._parse_formula_provenance(candidate.get("formula_provenance"))
        if provenance is not None:
            if "components" not in provenance or "operators" not in provenance:
                raise ValueError("formula provenance must contain components and operators")
            provenance_components = cls._parse_formula_list(
                provenance["components"], "formula_provenance.components"
            )
            provenance_operators = cls._parse_formula_list(
                provenance["operators"], "formula_provenance.operators"
            )
            if provenance_components != components or provenance_operators != operators:
                raise ValueError("formula provenance is inconsistent with formula fields")
        return components, operators

    def _formula_values(
        self, feature_df: pd.DataFrame, candidate: Mapping[str, Any]
    ) -> tuple[np.ndarray, list[str], list[str]]:
        components, operators = self._candidate_formula(candidate)
        missing = [name for name in components if name not in feature_df.columns]
        if missing:
            raise KeyError(f"Candidate components absent from feature_df: {missing}")
        arrays = [feature_df[name].to_numpy(dtype=float) for name in components]
        values = ConstrainedCombinationSearch._apply_formula(arrays, operators)
        return values, components, operators

    def _noise_baseline(
        self,
        feature_df: pd.DataFrame,
        candidate: Mapping[str, Any],
        y: np.ndarray,
        system_labels: np.ndarray,
        observed: float,
        n_draws: int = 100,
    ) -> dict[str, Any]:
        components, operators = self._candidate_formula(candidate)
        arrays = [feature_df[name].to_numpy(dtype=float) for name in components]
        rng = np.random.default_rng(self.seed)
        noise_scores: list[float] = []
        for _ in range(n_draws):
            permuted: list[np.ndarray] = []
            for values in arrays:
                shuffled = values.copy()
                for system in np.unique(system_labels):
                    idx = np.flatnonzero(system_labels == system)
                    shuffled[idx] = values[rng.permutation(idx)]
                permuted.append(shuffled)
            noise = ConstrainedCombinationSearch._apply_formula(permuted, operators)
            score = _safe_spearman(noise, y)
            if np.isfinite(score):
                noise_scores.append(abs(score))
        observed_abs = abs(observed) if np.isfinite(observed) else float("nan")
        if not noise_scores:
            return {
                "status": "exploratory",
                "available": False,
                "reason": "no finite matched-noise formula correlations",
                "n_requested": n_draws,
                "n_success": 0,
            }
        noise_arr = np.asarray(noise_scores)
        return {
            "status": "exploratory",
            "available": np.isfinite(observed_abs),
            "reason": None if np.isfinite(observed_abs) else "observed association unavailable",
            "observed_abs_spearman": observed_abs,
            "noise_median_abs_spearman": float(np.median(noise_arr)),
            "noise_95pct_abs_spearman": float(np.quantile(noise_arr, 0.95)),
            "observed_percentile": (
                float(np.mean(noise_arr <= observed_abs))
                if np.isfinite(observed_abs) else float("nan")
            ),
            "n_requested": n_draws,
            "n_success": len(noise_scores),
            "comparison": "matched_formula_within_system_component_permutation",
        }

    def _factor_spanning(
        self,
        values: np.ndarray,
        y: np.ndarray,
        system_labels: np.ndarray,
        anion_labels: np.ndarray,
    ) -> dict[str, Any]:
        target_mask = np.isfinite(y)
        finite_pair_mask = np.isfinite(values) & target_mask
        if int(target_mask.sum()) < 6 or int(np.isfinite(values[target_mask]).sum()) < 3:
            return {
                "status": "exploratory",
                "available": False,
                "reason": "V2 requires at least six targets and three observed formula values",
                "method": "fold_safe_oof_target_residual_prediction",
                "causal_claim": False,
                "n_oof_samples": 0,
                "n_folds_requested": 0,
                "n_folds_available": 0,
            }
        analyzer = DeconfoundAnalyzer(alpha=self.alpha)
        x_valid, y_valid = values[finite_pair_mask], y[finite_pair_mask]
        system_valid = system_labels[finite_pair_mask]
        anion_valid = anion_labels[finite_pair_mask]
        system_controls = analyzer._one_hot_frame(
            system_valid.tolist(), "system"
        ).reset_index(drop=True)
        all_controls, control_metadata = analyzer.build_rank_aware_controls(
            system_valid.tolist(), anion_valid.tolist()
        )
        system_rho = analyzer.deconfounded_spearman(
            x_valid, y_valid, system_controls
        )
        all_rho = analyzer.deconfounded_spearman(x_valid, y_valid, all_controls)

        values_oof = values[target_mask]
        y_oof = y[target_mask]
        systems_oof = system_labels[target_mask]
        anions_oof = anion_labels[target_mask]
        unique_systems, system_counts = np.unique(systems_oof, return_counts=True)
        if unique_systems.size > 1 and int(system_counts.min()) >= 2:
            n_splits = min(5, int(system_counts.min()))
            splitter = StratifiedKFold(
                n_splits=n_splits, shuffle=True, random_state=self.seed
            )
            split_iter = splitter.split(values_oof, systems_oof)
            split_basis = "system_stratified"
        else:
            n_splits = min(5, len(y_oof))
            splitter = KFold(n_splits=n_splits, shuffle=True, random_state=self.seed)
            split_iter = splitter.split(values_oof)
            split_basis = "random_kfold"

        heldout_residuals: list[np.ndarray] = []
        heldout_predictions: list[np.ndarray] = []
        fold_details: list[dict[str, Any]] = []
        for fold, (train_idx, test_idx) in enumerate(split_iter, start=1):
            train_values = values_oof[train_idx]
            if int(np.isfinite(train_values).sum()) < 2:
                fold_details.append({
                    "fold": fold,
                    "status": "skipped",
                    "reason": "fewer than two observed training formula values",
                    "n_train": len(train_idx),
                    "n_test": len(test_idx),
                })
                continue
            train_controls, fold_control_metadata = analyzer.build_rank_aware_controls(
                systems_oof[train_idx].tolist(), anions_oof[train_idx].tolist()
            )
            selected_columns = list(train_controls.columns)

            def encode_controls(indices: np.ndarray) -> np.ndarray:
                encoded = np.zeros((len(indices), len(selected_columns)), dtype=float)
                for col_idx, column in enumerate(selected_columns):
                    if column.startswith("system_"):
                        category = column[len("system_"):]
                        encoded[:, col_idx] = systems_oof[indices].astype(str) == category
                    elif column.startswith("anion_type_"):
                        category = column[len("anion_type_"):]
                        encoded[:, col_idx] = anions_oof[indices].astype(str) == category
                return encoded

            z_train = train_controls.to_numpy(dtype=float)
            z_test = encode_controls(test_idx)
            if z_train.shape[1]:
                control_model = Ridge(alpha=self.alpha)
                control_model.fit(z_train, y_oof[train_idx])
                train_residual = y_oof[train_idx] - control_model.predict(z_train)
                test_residual = y_oof[test_idx] - control_model.predict(z_test)
            else:
                train_mean = float(np.mean(y_oof[train_idx]))
                train_residual = y_oof[train_idx] - train_mean
                test_residual = y_oof[test_idx] - train_mean

            formula_model = Pipeline([
                ("imputer", SimpleImputer(strategy="median")),
                ("scale", StandardScaler()),
                ("ridge", Ridge(alpha=self.alpha)),
            ])
            try:
                formula_model.fit(train_values.reshape(-1, 1), train_residual)
                prediction = formula_model.predict(values_oof[test_idx].reshape(-1, 1))
            except ValueError as exc:
                fold_details.append({
                    "fold": fold,
                    "status": "skipped",
                    "reason": str(exc),
                    "n_train": len(train_idx),
                    "n_test": len(test_idx),
                })
                continue
            heldout_residuals.append(test_residual)
            heldout_predictions.append(prediction)
            fold_details.append({
                "fold": fold,
                "status": "available",
                "n_train": len(train_idx),
                "n_test": len(test_idx),
                "residualization_columns": selected_columns,
                "anion_incremental_rank": fold_control_metadata[
                    "anion_incremental_rank"
                ],
            })

        if heldout_residuals:
            residual_target = np.concatenate(heldout_residuals)
            formula_prediction = np.concatenate(heldout_predictions)
            oof_rho = _safe_spearman(residual_target, formula_prediction)
            n_oof_samples = len(residual_target)
        else:
            oof_rho = float("nan")
            n_oof_samples = 0
        n_folds_available = sum(
            detail["status"] == "available" for detail in fold_details
        )
        available = bool(np.isfinite(oof_rho) and n_folds_available >= 2)
        return {
            "status": "exploratory",
            "available": available,
            "reason": None if available else "insufficient nondegenerate OOF residual evidence",
            "method": "fold_safe_oof_target_residual_prediction",
            "causal_claim": False,
            "oof_residual_target_vs_formula_prediction_spearman": oof_rho,
            "n_oof_samples": n_oof_samples,
            "n_folds_requested": n_splits,
            "n_folds_available": n_folds_available,
            "split_basis": split_basis,
            "folds": fold_details,
            "interpretation": "predictive_association_after_known_factors_not_causal",
            "supplementary_partial_association": {
                "system_primary_spearman": float(system_rho),
                "known_factors_spearman": float(all_rho),
                "n_finite_pairs": int(finite_pair_mask.sum()),
            },
            **control_metadata,
        }

    @staticmethod
    def _per_system(
        values: np.ndarray, y: np.ndarray, system_labels: np.ndarray
    ) -> dict[str, Any]:
        groups: dict[str, dict[str, Any]] = {}
        for system in sorted(np.unique(system_labels).astype(str)):
            mask = (system_labels.astype(str) == system) & np.isfinite(values) & np.isfinite(y)
            n = int(mask.sum())
            rho = _safe_spearman(values[mask], y[mask])
            groups[system] = {
                "n": n,
                "raw_spearman": rho,
                "available": bool(np.isfinite(rho)),
                "reason": None if np.isfinite(rho) else "insufficient or constant within-system data",
            }
        return {
            "status": "exploratory",
            "available": any(group["available"] for group in groups.values()),
            "reason": None if groups else "no system groups",
            "groups": groups,
            "association": "raw_within_system_spearman",
        }

    def _bootstrap_ci(
        self,
        values: np.ndarray,
        y: np.ndarray,
        system_labels: np.ndarray,
        n_bootstrap: int,
    ) -> dict[str, Any]:
        mask = np.isfinite(values) & np.isfinite(y)
        values_valid, y_valid = values[mask], y[mask]
        systems_valid = system_labels[mask]
        estimate = _safe_spearman(values_valid, y_valid)
        if n_bootstrap < 1 or len(values_valid) < 5:
            return {
                "status": "exploratory",
                "available": False,
                "reason": "bootstrap requires at least five observations and one draw",
                "estimate": estimate,
                "n_requested": int(n_bootstrap),
                "n_success": 0,
                "method": "system_stratified_bootstrap",
            }
        rng = np.random.default_rng(self.seed)
        group_indices = [
            np.flatnonzero(systems_valid == system)
            for system in np.unique(systems_valid)
        ]
        samples: list[float] = []
        for _ in range(n_bootstrap):
            draw = np.concatenate(
                [rng.choice(idx, size=len(idx), replace=True) for idx in group_indices]
            )
            rho = _safe_spearman(values_valid[draw], y_valid[draw])
            if np.isfinite(rho):
                samples.append(rho)
        if not samples:
            return {
                "status": "exploratory",
                "available": False,
                "reason": "all stratified bootstrap draws were degenerate",
                "estimate": estimate,
                "n_requested": int(n_bootstrap),
                "n_success": 0,
                "method": "system_stratified_bootstrap",
            }
        sample_arr = np.asarray(samples)
        return {
            "status": "exploratory",
            "available": True,
            "reason": None,
            "estimate": estimate,
            "ci_lower": float(np.quantile(sample_arr, 0.025)),
            "ci_upper": float(np.quantile(sample_arr, 0.975)),
            "confidence_level": 0.95,
            "n_requested": int(n_bootstrap),
            "n_success": len(samples),
            "method": "system_stratified_bootstrap",
        }

    @staticmethod
    def _unavailable_cv(reason: str) -> tuple[dict[str, Any], dict[str, Any]]:
        raw = {
            key: {
                "strategy": key,
                "skipped": True,
                "reason": reason,
                "mean_spearman": float("nan"),
                "fold_results": [],
            }
            for key in (
                "anion_stratified_cv",
                "leave_one_system_out",
                "repeated_subsample",
            )
        }
        raw["anion_stratified_cv"].update(
            requested_n_folds=3, effective_n_folds=0, downshifted=False
        )
        return raw, summarize_cv_spearman(raw)

    def _run_cv_diagnostics(
        self,
        X: np.ndarray,
        y: np.ndarray,
        systems: np.ndarray,
        anions: np.ndarray,
    ) -> tuple[dict[str, dict[str, Any]], dict[str, Any]]:
        """Run strategies independently so one unavailable split cannot hide others."""
        cv = MultiStrategyCV(alpha=self.alpha)
        results: dict[str, dict[str, Any]] = {}
        try:
            results["anion_stratified_cv"] = cv.anion_stratified_cv(X, y, anions)
        except (ValueError, RuntimeError) as exc:
            results["anion_stratified_cv"] = {
                "strategy": "anion_stratified_cv",
                "skipped": True,
                "reason": str(exc),
                "mean_spearman": float("nan"),
                "fold_results": [],
                "requested_n_folds": 3,
                "effective_n_folds": 0,
                "downshifted": False,
            }

        if np.unique(systems).size < 2:
            results["leave_one_system_out"] = {
                "strategy": "leave_one_system_out",
                "skipped": True,
                "reason": "LOSO CV requires at least two system groups",
                "mean_spearman": float("nan"),
                "fold_results": [],
            }
        else:
            try:
                results["leave_one_system_out"] = cv.leave_one_system_out(
                    X, y, systems
                )
            except (ValueError, RuntimeError) as exc:
                results["leave_one_system_out"] = {
                    "strategy": "leave_one_system_out",
                    "skipped": True,
                    "reason": str(exc),
                    "mean_spearman": float("nan"),
                    "fold_results": [],
                }

        try:
            results["repeated_subsample"] = cv.repeated_subsample(X, y, systems)
        except (ValueError, RuntimeError) as exc:
            results["repeated_subsample"] = {
                "strategy": "repeated_subsample",
                "skipped": True,
                "reason": str(exc),
                "mean_spearman": float("nan"),
                "fold_results": [],
            }
        return results, summarize_cv_spearman(results)

    def full_validation(
        self,
        feature_df: pd.DataFrame,
        y: np.ndarray,
        system_labels: list[str],
        anion_labels: list[str],
        candidate: Mapping[str, Any] | pd.Series,
        n_bootstrap: int = 500,
    ) -> dict[str, Any]:
        """Return four named exploratory evidence blocks and CV diagnostics."""
        candidate_map = candidate.to_dict() if isinstance(candidate, pd.Series) else candidate
        values, _, _ = self._formula_values(feature_df, candidate_map)
        y_arr = np.asarray(y, dtype=float)
        systems = np.asarray(system_labels)
        anions = np.asarray(anion_labels)
        if not (len(values) == len(y_arr) == len(systems) == len(anions)):
            raise ValueError("feature, target, system, and anion lengths must match")
        observed = _safe_spearman(values, y_arr)
        finite = np.isfinite(values) & np.isfinite(y_arr)
        target_observed = np.isfinite(y_arr)

        if int(finite.sum()) < 5 or int(target_observed.sum()) < 5:
            cv_results, cv_summary = self._unavailable_cv(
                "fewer than five finite formula-target pairs"
            )
        else:
            cv_results, cv_summary = self._run_cv_diagnostics(
                values[target_observed].reshape(-1, 1),
                y_arr[target_observed],
                systems[target_observed],
                anions[target_observed],
            )

        blocks = {
            "noise_baseline": self._noise_baseline(
                feature_df, candidate_map, y_arr, systems, observed
            ),
            "factor_spanning": self._factor_spanning(
                values, y_arr, systems, anions
            ),
            "per_system": self._per_system(values, y_arr, systems),
            "bootstrap_ci": self._bootstrap_ci(
                values, y_arr, systems, n_bootstrap=n_bootstrap
            ),
        }
        return {
            **blocks,
            "cv_diagnostics": {
                "status": "exploratory",
                "summary": cv_summary,
                "strategies": cv_results,
                "n_target_observed": int(target_observed.sum()),
                "n_formula_observed": int(finite.sum()),
                "missing_formula_policy": "fold_local_median_imputation",
            },
            "status": "exploratory",
            "causal_claim": False,
            "uncertainty": {
                "status": "exploratory",
                "method": "system_stratified_bootstrap",
                "selection_uncertainty_included": False,
                "reason": "nested outer-group selection validation is not available",
            },
        }

    def validate(
        self,
        feature_df: pd.DataFrame,
        y: np.ndarray,
        system_labels: list[str],
        anion_labels: list[str],
        candidates_df: pd.DataFrame,
        top_k: int = 10,
        n_bootstrap: int = 500,
    ) -> pd.DataFrame:
        """Validate top candidates and flatten V1--V4 beside the pair API."""
        if candidates_df.empty:
            return pd.DataFrame(columns=COMBINATION_VALIDATION_RESULT_COLUMNS)
        records: list[dict[str, Any]] = []
        for _, row in candidates_df.head(top_k).iterrows():
            try:
                evidence = self.full_validation(
                    feature_df,
                    y,
                    system_labels,
                    anion_labels,
                    row,
                    n_bootstrap=n_bootstrap,
                )
            except KeyError:
                continue
            cv_summary = evidence["cv_diagnostics"]["summary"]
            blocks = {
                name: evidence[name]
                for name in (
                    "noise_baseline",
                    "factor_spanning",
                    "per_system",
                    "bootstrap_ci",
                )
            }
            components, operators = self._candidate_formula(row)
            raw_component_families = row.get("component_families")
            if self._is_missing_field(raw_component_families):
                component_families: list[str] = []
            else:
                component_families = self._parse_formula_list(
                    raw_component_families, "component_families"
                )
                if len(component_families) != len(components):
                    raise ValueError(
                        "formula component_families count must match components"
                    )
            provenance = self._parse_formula_provenance(row.get("formula_provenance"))
            if provenance is None:
                provenance = {
                    "components": components,
                    "operators": operators,
                    "raw_value_source": row.get("raw_value_source", "feature_df"),
                }
            elif "component_families" in provenance:
                provenance_families = self._parse_formula_list(
                    provenance["component_families"],
                    "formula_provenance.component_families",
                )
                if component_families and provenance_families != component_families:
                    raise ValueError(
                        "formula provenance component families are inconsistent"
                    )
                if not component_families:
                    component_families = provenance_families
            records.append(
                {
                    "combined_name": row["combined_name"],
                    "d1": row["d1"],
                    "d2": row["d2"],
                    "operator": row["operator"],
                    "components": components,
                    "operators": operators,
                    "component_families": list(component_families),
                    "n_components": len(components),
                    "raw_value_source": row.get("raw_value_source", "feature_df"),
                    "formula_provenance": dict(provenance),
                    "combined_deconf_spearman": row.get(
                        "combined_deconf_spearman", float("nan")
                    ),
                    **cv_summary,
                    "validation_status": "exploratory",
                    "causal_claim": False,
                    "uncertainty_method": "system_stratified_bootstrap",
                    **blocks,
                    "evidence_blocks": blocks,
                    "cv_diagnostics": evidence["cv_diagnostics"],
                }
            )
        if not records:
            return pd.DataFrame(columns=COMBINATION_VALIDATION_RESULT_COLUMNS)
        return pd.DataFrame.from_records(
            records, columns=COMBINATION_VALIDATION_RESULT_COLUMNS
        )

--- 文件结束: descriptors/combination.py ---

--- 文件开始: compute_features.py ---
#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""计算所有样本的结构描述符。

用法（在 automat-naconductor 目录下运行）:
    python compute_features.py

输出:
    data/naconductor_featurized.csv
    data/naconductor_featurized.json
"""
import sys
sys.stdout.reconfigure(encoding='utf-8')

import logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

from pathlib import Path
from descriptors.featurizer import featurize_dataset


def main():
    csv_path = Path("data/naconductor_raw.csv")
    output_path = Path("data/naconductor_featurized")

    if not csv_path.exists():
        print(f"错误: 找不到输入文件 {csv_path}")
        sys.exit(1)

    print(f"正在计算 {csv_path} 中所有样本的结构描述符...")
    print("预计耗时 3-5 分钟（84 个 CIF × 41 个描述符）")

    df = featurize_dataset(csv_path, output_path, cif_column="cif_path")

    # 统计摘要
    desc_cols = [c for c in df.columns if c not in [
        'material_id', 'cif_path', 'formula', 'space_group',
        'system', 'anion_type', 'log_sigma'
    ]]
    valid_total = df[desc_cols].notna().sum().sum()
    total_cells = len(df) * len(desc_cols)
    print(f"\n完成: {len(df)} 个样本, {len(desc_cols)} 个描述符")
    print(f"有效值: {valid_total}/{total_cells} ({100*valid_total/total_cells:.1f}%)")

    # NaN 统计
    nan_counts = df[desc_cols].isna().sum()
    high_nan = nan_counts[nan_counts > len(df) * 0.3]
    if len(high_nan) > 0:
        print(f"\n高NaN描述符 (>30% 缺失):")
        for col, cnt in high_nan.items():
            print(f"  {col}: {cnt}/{len(df)} ({100*cnt/len(df):.0f}%)")


if __name__ == "__main__":
    main()
--- 文件结束: compute_features.py ---

--- 文件开始: run_pipeline.py ---
#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""4阶段管线：从原始数据到最终报告。

用法（在 automat-naconductor 目录下运行）:
    python run_pipeline.py
    python run_pipeline.py --skip-featurize    # 跳过Stage 0（已有特征化数据）
    python run_pipeline.py --top-k 20          # 验证前20个组合（默认10）

4个阶段:
    Stage 0: 特征化（compute_features.py的等价脚本版）
    Stage 1: 单描述符筛选（去混杂分析）
    Stage 2: 稳定性选择 + 物理族代表
    Stage 3: 约束组合搜索
    Stage 4: 多策略CV验证 + 最终报告
"""
from __future__ import annotations

import sys
sys.stdout.reconfigure(encoding='utf-8')

import argparse
import json
import logging
import time
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from automat_utils import resolve_frozen_input_identity
from descriptors import SEARCHABLE_STRUCTURE_DESCRIPTORS
from descriptors.featurizer import featurize_dataset, build_feature_matrix
from descriptors.deconfound import DeconfoundAnalyzer
from descriptors.stability import StabilitySelector, PhysicalGrouper
from descriptors.combination import (
    CombinationValidator,
    ConstrainedCombinationSearch,
    combination_candidates_to_csv_frame,
    combination_validation_to_csv_frame,
)
from descriptors.cv_strategies import (
    CV_SPEARMAN_SUMMARY_COLUMNS,
    MultiStrategyCV,
    summarize_cv_spearman,
)
from run_config import config_get, load_run_info

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s: %(message)s",
    encoding="utf-8",
)
logger = logging.getLogger(__name__)


class InsufficientFeatureDataError(RuntimeError):
    """Raised when no structural descriptor has enough valid data to analyze."""


BASELINE_RESULT_COLUMNS = [
    "descriptor",
    "family",
    "deconfounded_spearman",
    *CV_SPEARMAN_SUMMARY_COLUMNS,
]


def _configured_max_descriptors(
    config_path: Path | None = None,
) -> int:
    """Read and validate the Stage-3 formula-size contract from run_info.yaml."""
    path = config_path or Path(__file__).with_name("run_info.yaml")
    config = load_run_info(path)
    value = int(config_get(config, "combination.max_descriptors"))
    if value not in (2, 3):
        raise ValueError("combination.max_descriptors must be 2 or 3")
    return value


def _resolve_config_input_path(value: str | Path, config_path: Path) -> Path:
    """Resolve a frozen input relative to the selected run-info file."""
    path = Path(value)
    if path.is_absolute():
        return path
    return (config_path.resolve().parent / path).resolve()


def _frozen_pipeline_input_contract(config_path: Path) -> dict[str, Any]:
    """Validate and resolve the raw/registry inputs shared with the Agent track."""
    config = load_run_info(config_path)
    identity = resolve_frozen_input_identity(config, config_path)
    return {
        "raw_file": identity.raw_file,
        "featurized_file": _resolve_config_input_path(
            config_get(config, "data.featurized_file"), config_path
        ),
        "structure_column": str(config_get(config, "data.structure_column")),
        "target_column": str(config_get(config, "data.target_column")),
        "system_column": str(config_get(config, "data.system_column")),
        "anion_column": str(config_get(config, "data.anion_type_column")),
        "descriptor_registry": identity.descriptor_registry,
        "registry_revision": identity.registry_revision,
        "frozen_identity": identity,
    }


def _configured_pipeline_output_dir(
    config_path: Path | None = None,
) -> str:
    """Read the isolated Pipeline output directory from the shared run contract."""
    path = config_path or Path(__file__).with_name("run_info.yaml")
    config = load_run_info(path)
    return _validate_pipeline_output_dir(config_get(config, "tracks.pipeline.output_dir"))


def _validate_pipeline_output_dir(value: str | Path) -> str:
    """Reject an output path that could overwrite Agent-track artifacts."""
    output_dir = Path(value)
    expected_prefix = ("results", "pipeline")
    if (
        output_dir.is_absolute()
        or output_dir.parts[: len(expected_prefix)] != expected_prefix
        or ".." in output_dir.parts
    ):
        raise ValueError(
            "tracks.pipeline.output_dir must be a relative results/pipeline/ path"
        )
    return str(output_dir)


def _format_cv_metric(row: pd.Series, prefix: str) -> str:
    """Format a CV metric while keeping skipped strategies visibly distinct."""
    if bool(row.get(f"{prefix}_skipped", False)):
        return "SKIPPED"
    value = float(row.get(f"{prefix}_spearman", float("nan")))
    return f"{value:.3f}"


# ============================================================
# 命令行参数
# ============================================================

def parseArgs(argv: list[str] | None = None) -> argparse.Namespace:
    """解析命令行参数。"""
    config_probe = argparse.ArgumentParser(add_help=False)
    config_probe.add_argument(
        "--run-info",
        type=Path,
        default=Path(__file__).with_name("run_info.yaml"),
    )
    probe_args, _unknown = config_probe.parse_known_args(argv)
    try:
        frozen_input = _frozen_pipeline_input_contract(probe_args.run_info)
        configured_output_dir = _configured_pipeline_output_dir(probe_args.run_info)
        configured_max_descriptors = _configured_max_descriptors(probe_args.run_info)
    except (KeyError, ValueError) as exc:
        config_probe.error(str(exc))

    parser = argparse.ArgumentParser(
        description="Na离子导体描述符搜索 4阶段管线",
    )
    parser.add_argument(
        "--run-info",
        type=Path,
        default=probe_args.run_info,
        help="冻结共享输入与 Pipeline 输出目录的 YAML 配置。",
    )
    parser.add_argument(
        "--skip-featurize",
        action="store_true",
        help="跳过Stage 0（已有特征化数据时使用）",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=10,
        help="Stage 4中验证前k个组合候选（默认10）",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=configured_output_dir,
        help="Pipeline 输出目录（默认 results/pipeline/；不读取 Agent 输出）",
    )
    parser.add_argument(
        "--alpha",
        type=float,
        default=1.0,
        help="Ridge正则化强度（默认1.0）",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="随机种子（默认42）",
    )
    parser.add_argument(
        "--selection-alpha",
        type=float,
        default=0.05,
        help="Lasso稳定性选择正则化强度（默认0.05）",
    )
    parser.add_argument(
        "--max-descriptors",
        type=int,
        choices=(2, 3),
        default=configured_max_descriptors,
        help="Stage 3公式最大描述符数（默认读取run_info.yaml）",
    )
    args = parser.parse_args(argv)
    try:
        args.output_dir = _validate_pipeline_output_dir(args.output_dir)
    except ValueError as exc:
        parser.error(str(exc))
    for key, value in frozen_input.items():
        setattr(args, key, value)
    return args


# ============================================================
# Stage 0: 特征化
# ============================================================

def runStage0(args: argparse.Namespace) -> tuple[pd.DataFrame, pd.DataFrame, list[str], list[str], np.ndarray]:
    """Stage 0: 从原始数据计算结构描述符，构建保留原值的特征矩阵。

    返回:
        (feature_df, raw_df, system_labels, anion_labels, y)
        - feature_df: 原始描述符矩阵（含固定噪声列、缺失值和元数据列）
        - raw_df: 原始特征化数据（含描述符原始值）
        - system_labels: 体系标签列表
        - anion_labels: 阴离子类型标签列表
        - y: log_sigma 目标向量
    """
    featurized_path = Path(args.featurized_file)

    if args.skip_featurize and featurized_path.exists():
        print("[Stage 0] 跳过特征化，加载已有数据...")
        raw_df = pd.read_csv(featurized_path, encoding="utf-8")
    else:
        raw_csv = Path(args.raw_file)
        if not raw_csv.exists():
            print(f"错误: 找不到输入文件 {raw_csv}")
            sys.exit(1)

        print("[Stage 0] 正在计算结构描述符...")
        print("  预计耗时 3-5 分钟（84 个 CIF × 41 个描述符）")
        raw_df = featurize_dataset(
            str(raw_csv),
            str(featurized_path),
            cif_column=args.structure_column,
        )

    # 构建保留原始值的特征矩阵；预测预处理在每个训练折内完成。
    print("[Stage 0] 构建原始特征矩阵...")
    feature_df, valid_cols, noise_info_df = build_feature_matrix(
        raw_df, target_col=args.target_column
    )

    # 提取标签和目标
    system_labels = raw_df[args.system_column].tolist()
    anion_labels = raw_df[args.anion_column].tolist()
    y = raw_df[args.target_column].values.astype(float)

    n_real = len(valid_cols)
    n_noise = len([c for c in feature_df.columns if c.startswith("noise_")])
    if n_real == 0:
        raise InsufficientFeatureDataError(
            "No valid structural descriptor values are available after coverage "
            "filtering; regenerate the featurized dataset from valid CIF inputs."
        )
    print(f"[Stage 0] 完成: {len(raw_df)} 样本, {n_real} 有效描述符, {n_noise} 噪声列")

    return feature_df, raw_df, system_labels, anion_labels, y


# ============================================================
# Stage 1: 单描述符去混杂筛选
# ============================================================

def runStage1(
    feature_df: pd.DataFrame,
    y: np.ndarray,
    system_labels: list[str],
    anion_labels: list[str],
    alpha: float,
    output_dir: Path,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Stage 1: 对所有描述符执行去混杂分析，筛选有效信号。

    返回:
        (完整审计结果, 预筛选结果)。预筛选结果仅保留标签为
        强物理/弱物理/混合的描述符。
    """
    print("\n" + "=" * 60)
    print("[Stage 1] 单描述符去混杂筛选")
    print("=" * 60)

    analyzer = DeconfoundAnalyzer(alpha=alpha)
    deconfound_df = analyzer.analyze_all(feature_df, y, system_labels, anion_labels)

    # 保存完整结果
    deconfound_df.to_csv(output_dir / "stage1_deconfound_results.csv", index=False, encoding="utf-8")

    # 标签分布统计
    label_counts = deconfound_df["label"].value_counts()
    print("\n标签分布:")
    for label_name in ["强物理信号", "弱物理信号", "混合信号", "体系代理", "噪声级"]:
        count = label_counts.get(label_name, 0)
        print(f"  {label_name}: {count}")

    # 预筛选: 保留标签为强物理信号/弱物理信号/混合信号的描述符 (errata P5)
    pass_labels = {"强物理信号", "弱物理信号", "混合信号"}
    filtered_df = deconfound_df[deconfound_df["label"].isin(pass_labels)].copy()
    filtered_df.to_csv(
        output_dir / "stage1_prefiltered_results.csv",
        index=False,
        encoding="utf-8",
    )
    n_pass = len(filtered_df)
    n_total = len(deconfound_df)
    print(f"\nStage 1: {n_pass} 描述符通过预筛选（共 {n_total} 个）")

    return deconfound_df, filtered_df


# ============================================================
# Stage 2: 稳定性选择 + 物理族代表
# ============================================================

def runStage2(
    feature_df: pd.DataFrame,
    y: np.ndarray,
    deconfound_df: pd.DataFrame,
    alpha: float,
    seed: int,
    output_dir: Path,
    max_descriptors: int = 2,
) -> pd.DataFrame:
    """Stage 2: stability selection and the bounded Stage-3 candidate pool.

    Pair-only search keeps one stable representative per family.  A permitted
    three-descriptor search retains up to two stable representatives per
    family: the second slot is a narrowly scoped formula-candidate slot needed
    for the plan-approved ``two from one family + adjacent family`` triples,
    rather than a second independent scientific finding.

    Returns:
        Candidate-representative DataFrame with ``is_representative``.
    """
    if max_descriptors not in (2, 3):
        raise ValueError("max_descriptors must be 2 or 3")
    print("\n" + "=" * 60)
    print("[Stage 2] 稳定性选择与物理族代表")
    print("=" * 60)

    # Stage 2 只允许 Stage 1 预筛选后的真实描述符；固定噪声列全部保留。
    registered = set(SEARCHABLE_STRUCTURE_DESCRIPTORS.keys())
    prefiltered = set(deconfound_df["descriptor"].tolist())
    real_col_names = [
        c for c in feature_df.columns
        if c in registered and c in prefiltered
    ]
    noise_col_names = [c for c in feature_df.columns if c.startswith("noise_")]

    X_real = feature_df[real_col_names].values.astype(float)
    X_noise = feature_df[noise_col_names].values.astype(float) if noise_col_names else None

    # 稳定性选择
    print("  运行稳定性选择（100次自举）...")
    selector = StabilitySelector(
        n_bootstrap=100,
        threshold=0.6,
        fraction=0.5,
        alpha=alpha,
        seed=seed,
    )
    stability_df = selector.run(X_real, y, X_noise, real_col_names, noise_col_names)

    # 保存稳定性结果
    stability_df.to_csv(output_dir / "stage2_stability_results.csv", index=False, encoding="utf-8")

    n_stable = stability_df["is_stable"].sum()
    n_above_noise = stability_df["above_noise_baseline"].sum()
    print(f"  稳定描述符: {n_stable}, 超过噪声基线: {n_above_noise}")

    # 物理族代表选择
    print("  按物理族选择代表...")
    # A triple cannot be constructed from a one-per-family pool.  Keep the
    # legacy primary-representative capacity for pair-only search, and open
    # exactly one additional stable slot per family only when triples are
    # explicitly enabled by the frozen Pipeline contract.
    max_per_family = 2 if max_descriptors == 3 else 1
    grouper = PhysicalGrouper(max_per_family=max_per_family)
    representative_df = grouper.group_and_select(stability_df, deconfound_df)
    representative_df.attrs["max_descriptors"] = max_descriptors
    representative_df.attrs["max_representatives_per_family"] = max_per_family

    # 保存代表结果
    representative_df.to_csv(output_dir / "stage2_representatives.csv", index=False, encoding="utf-8")

    # 统计
    n_reps = representative_df["is_representative"].sum()
    print(
        f"\nStage 2: {n_reps} 个组合候选代表"
        f"（来自 {n_stable} 个稳定描述符；每族最多 {max_per_family} 个）"
    )

    # 打印每个代表
    reps = representative_df[representative_df["is_representative"] == True]  # noqa: E712
    for _, row in reps.iterrows():
        rho = row.get("deconfounded_spearman", float("nan"))
        freq = row.get("selection_freq", 0.0)
        print(f"  [{row['family']}] {row['descriptor']} ({row['family_name']})"
              f"  去混杂ρ={rho:.3f}  频率={freq:.2f}")

    return representative_df


# ============================================================
# Stage 3: 约束组合搜索
# ============================================================

def runStage3(
    feature_df: pd.DataFrame,
    y: np.ndarray,
    system_labels: list[str],
    anion_labels: list[str],
    representative_df: pd.DataFrame,
    alpha: float,
    seed: int,
    output_dir: Path,
    max_descriptors: int | None = None,
) -> pd.DataFrame:
    """Stage 3: Search explicit raw-value pair and bounded-triple formulas.

    返回:
        组合候选 DataFrame
    """
    print("\n" + "=" * 60)
    print("[Stage 3] 约束组合搜索")
    print("=" * 60)

    searcher = ConstrainedCombinationSearch(alpha=alpha, seed=seed)
    effective_max_descriptors = (
        _configured_max_descriptors()
        if max_descriptors is None else int(max_descriptors)
    )
    candidates_df = searcher.search(
        feature_df, y, system_labels, anion_labels,
        representative_df,
        max_candidates=150,
        max_descriptors=effective_max_descriptors,
    )

    # 保存结果
    combination_candidates_to_csv_frame(candidates_df).to_csv(
        output_dir / "stage3_combination_candidates.csv",
        index=False,
        encoding="utf-8",
    )

    n_candidates = len(candidates_df)
    print(f"\nStage 3: {n_candidates} 个有效二/三描述符组合候选")

    # 打印 top 5
    if not candidates_df.empty:
        top5 = candidates_df.head(5)
        print("\nTop 5 组合候选（按 |去混杂Spearman| 降序）:")
        for _, row in top5.iterrows():
            cross_flag = "跨族" if row["is_cross_family"] else "同族"
            print(f"  {row['combined_name']}  "
                  f"去混杂ρ={row['combined_deconf_spearman']:.3f}  [{cross_flag}]")

    return candidates_df


# ============================================================
# Stage 4: 多策略CV验证
# ============================================================

def runStage4(
    feature_df: pd.DataFrame,
    y: np.ndarray,
    system_labels: list[str],
    anion_labels: list[str],
    deconfound_df: pd.DataFrame,
    candidates_df: pd.DataFrame,
    alpha: float,
    seed: int,
    top_k: int,
    output_dir: Path,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Stage 4: exploratory V1--V4 evidence, CV, and single baseline.

    返回:
        (validation_df, baseline_df)
        - validation_df: 组合描述符验证结果
        - baseline_df: 最佳单描述符基线结果
    """
    print("\n" + "=" * 60)
    print("[Stage 4] 多策略CV验证")
    print("=" * 60)

    # --- 组合验证 ---
    print(f"  验证 Top-{top_k} 组合候选（V1–V4，探索性证据）...")
    validator = CombinationValidator(alpha=alpha, seed=seed)
    validation_df = validator.validate(
        feature_df, y, system_labels, anion_labels,
        candidates_df, top_k=top_k,
    )

    # 保存验证结果
    combination_validation_to_csv_frame(validation_df).to_csv(
        output_dir / "stage4_validation_results.csv",
        index=False,
        encoding="utf-8",
    )

    n_validated = len(validation_df)
    print(f"  成功验证 {n_validated} 个组合")

    # --- 单描述符基线 ---
    baseline_df = pd.DataFrame(columns=BASELINE_RESULT_COLUMNS)
    # 选出去混杂Spearman绝对值最高的描述符作为基线
    if not deconfound_df.empty:
        best_single_row = deconfound_df.iloc[0]  # 已按 |deconfounded_spearman| 降序排列
        best_single_name = best_single_row["descriptor"]

        print(f"\n  最佳单描述符基线: {best_single_name}")
        print("  运行多策略CV...")

        # 获取该描述符的特征列
        if best_single_name in feature_df.columns:
            x_single = feature_df[best_single_name].values.astype(float)
            X_single = x_single.reshape(-1, 1)
            y_arr = np.asarray(y, dtype=float)

            # 有效样本掩码
            valid_mask = ~np.isnan(y_arr)
            if valid_mask.sum() >= 5:
                cv = MultiStrategyCV(alpha=alpha)
                cv_results = cv.run_all(
                    X_single[valid_mask],
                    y_arr[valid_mask],
                    np.asarray(system_labels)[valid_mask],
                    np.asarray(anion_labels)[valid_mask],
                )
                cv_summary = summarize_cv_spearman(cv_results)

                baseline_records = [{
                    "descriptor": best_single_name,
                    "family": best_single_row["family"],
                    "deconfounded_spearman": best_single_row["deconfounded_spearman"],
                    **cv_summary,
                }]
                baseline_df = pd.DataFrame.from_records(
                    baseline_records,
                    columns=BASELINE_RESULT_COLUMNS,
                )
            else:
                print("  警告: 有效样本不足，跳过单描述符基线CV")
        else:
            print(f"  警告: 描述符 {best_single_name} 不在特征矩阵中，跳过基线CV")
    else:
        best_single_name = "N/A"

    # 保存基线结果
    if not baseline_df.empty:
        baseline_df.to_csv(output_dir / "stage4_single_descriptor_baseline.csv", index=False, encoding="utf-8")
        print(f"  基线描述符: {best_single_name}")
        for _, row in baseline_df.iterrows():
            print(f"    阴离子分层: {_format_cv_metric(row, 'anion_stratified')}")
            print(f"    LOSO:       {_format_cv_metric(row, 'loso')}")
            print(f"    重复子采样: {_format_cv_metric(row, 'repeated_subsample')}")
            print(
                f"    综合得分:   {row['composite_score']:.3f} "
                f"({int(row['composite_strategy_count'])}/3 strategies)"
            )

    return validation_df, baseline_df


# ============================================================
# 报告生成
# ============================================================

def generateReport(
    raw_df: pd.DataFrame,
    deconfound_df: pd.DataFrame,
    filtered_deconfound_df: pd.DataFrame,
    representative_df: pd.DataFrame,
    candidates_df: pd.DataFrame,
    validation_df: pd.DataFrame,
    baseline_df: pd.DataFrame,
    output_dir: Path,
) -> None:
    """生成最终 Markdown 报告和 JSON 报告。"""
    print("\n" + "=" * 60)
    print("生成最终报告")
    print("=" * 60)

    # ---- 收集报告数据 ----
    n_samples = len(raw_df)
    system_counts = raw_df["system"].value_counts().to_dict()
    n_nasicon = system_counts.get("NASICON", 0)
    n_sulfide = system_counts.get("sulfide", 0)
    n_halide = system_counts.get("halide", 0)

    y_values = raw_df["log_sigma"].dropna().values
    y_min = float(y_values.min()) if len(y_values) > 0 else 0.0
    y_max = float(y_values.max()) if len(y_values) > 0 else 0.0

    registered = set(SEARCHABLE_STRUCTURE_DESCRIPTORS.keys())
    n_total_desc = len(registered)
    n_valid_desc = len(filtered_deconfound_df)

    # ---- Stage 1 表格 ----
    top10_deconf = deconfound_df.head(10)
    stage1_table_rows = []
    for _, row in top10_deconf.iterrows():
        stage1_table_rows.append(
            f"| {row['descriptor']} | {row['family']} | "
            f"{row['raw_spearman']:.3f} | {row['deconfounded_spearman']:.3f} | "
            f"{row['system_proxy_ratio']:.3f} | {row['label']} |"
        )
    stage1_table = "\n".join(stage1_table_rows)

    # 标签分布
    label_counts = deconfound_df["label"].value_counts().to_dict()

    # ---- Stage 2 代表表格 ----
    reps = representative_df[representative_df["is_representative"] == True]  # noqa: E712
    stage2_table_rows = []
    for _, row in reps.iterrows():
        rho = row.get("deconfounded_spearman", float("nan"))
        freq = row.get("selection_freq", 0.0)
        stage2_table_rows.append(
            f"| {row['descriptor']} | {row['family']} | {row['family_name']} | "
            f"{rho:.3f} | {freq:.2f} |"
        )
    stage2_table = "\n".join(stage2_table_rows)
    stage2_capacity = int(
        representative_df.attrs.get("max_representatives_per_family", 1)
    )

    # ---- Stage 3 Top10 组合表格 ----
    top10_comb = candidates_df.head(10)
    stage3_table_rows = []
    for _, row in top10_comb.iterrows():
        cross_flag = "是" if row["is_cross_family"] else "否"
        components = row.get("components", [row["d1"], row["d2"]])
        operators = row.get("operators", [row["operator"]])
        stage3_table_rows.append(
            f"| {row['combined_name']} | {len(components)} | "
            f"{', '.join(map(str, components))} | {', '.join(map(str, operators))} | "
            f"{row['combined_deconf_spearman']:.3f} | {cross_flag} |"
        )
    stage3_table = "\n".join(stage3_table_rows)

    # ---- Stage 4 表格 ----
    # 基线行
    if not baseline_df.empty:
        bl = baseline_df.iloc[0]
        baseline_row = (
            f"| {bl['descriptor']} | {_format_cv_metric(bl, 'anion_stratified')} | "
            f"{_format_cv_metric(bl, 'loso')} | "
            f"{_format_cv_metric(bl, 'repeated_subsample')} |"
        )
        best_single_name = bl["descriptor"]
        best_single_family = bl.get("family", "Unknown")
        best_single_rho = bl.get("deconfounded_spearman", 0.0)
    else:
        baseline_row = "| N/A | N/A | N/A | N/A |"
        best_single_name = "N/A"
        best_single_family = "N/A"
        best_single_rho = 0.0

    # 组合验证表格
    stage4_table_rows = []
    for _, row in validation_df.iterrows():
        blocks = row.get("evidence_blocks", {})
        availability = "/".join(
            "OK" if bool(blocks.get(name, {}).get("available", False)) else "N/A"
            for name in ("noise_baseline", "factor_spanning", "per_system", "bootstrap_ci")
        )
        bootstrap = row.get("bootstrap_ci", {})
        if bool(bootstrap.get("available", False)):
            uncertainty = (
                f"[{bootstrap['ci_lower']:.3f}, {bootstrap['ci_upper']:.3f}]"
            )
        else:
            uncertainty = "UNAVAILABLE"
        stage4_table_rows.append(
            f"| {row['combined_name']} | {int(row.get('n_components', 2))} | "
            f"{row['combined_deconf_spearman']:.3f} | "
            f"{_format_cv_metric(row, 'anion_stratified')} | "
            f"{_format_cv_metric(row, 'loso')} | "
            f"{_format_cv_metric(row, 'repeated_subsample')} | "
            f"{row['composite_score']:.3f} "
            f"({int(row['composite_strategy_count'])}/3) | {availability} | "
            f"{uncertainty} | 探索性 |"
        )
    stage4_table = "\n".join(stage4_table_rows)

    if not validation_df.empty:
        best_v2 = validation_df.iloc[0].get("factor_spanning", {})
        best_v2_rho = best_v2.get(
            "oof_residual_target_vs_formula_prediction_spearman", float("nan")
        )
        best_v2_summary = (
            f"OOF残差预测Spearman={best_v2_rho:.3f}, "
            f"可用折={best_v2.get('n_folds_available', 0)}/"
            f"{best_v2.get('n_folds_requested', 0)}, "
            f"OOF样本={best_v2.get('n_oof_samples', 0)}"
        )
        best_v2_control_audit = (
            f"primary={best_v2.get('primary_control', 'unavailable')}, "
            f"system_rank={best_v2.get('system_design_rank', 'N/A')}, "
            f"combined_rank={best_v2.get('confounder_rank', 'N/A')}, "
            f"anion_incremental_rank={best_v2.get('anion_incremental_rank', 'N/A')}, "
            f"redundant_anion_columns="
            f"{best_v2.get('anion_redundant_columns', [])}"
        )
    else:
        best_v2_summary = "UNAVAILABLE"
        best_v2_control_audit = "UNAVAILABLE"

    # ---- 结论 ----
    # 最强组合
    if not validation_df.empty:
        best_comb_row = validation_df.iloc[0]
        best_comb_name = best_comb_row["combined_name"]
        best_comb_score = best_comb_row["composite_score"]
    else:
        best_comb_name = "N/A"
        best_comb_score = 0.0

    # 组合相比单描述符提升
    if not baseline_df.empty and not validation_df.empty:
        baseline_composite = baseline_df.iloc[0]["composite_score"]
        delta_pct = ((best_comb_score - baseline_composite) / abs(baseline_composite) * 100
                     if abs(baseline_composite) > 1e-8 else 0.0)
    else:
        delta_pct = 0.0

    # 跨CV策略一致性评估
    if not validation_df.empty:
        # 仅检查实际可用（未跳过且有限）的策略；跳过不计作证据。
        signs = []
        for _, row in validation_df.head(3).iterrows():
            for prefix in (
                "anion_stratified",
                "loso",
                "repeated_subsample",
            ):
                if bool(row.get(f"{prefix}_available", False)):
                    signs.append(np.sign(row[f"{prefix}_spearman"]))
        n_positive = sum(1 for s in signs if s > 0)
        n_negative = sum(1 for s in signs if s < 0)
        if not signs:
            consistency_desc = "无可用CV策略"
        elif n_positive == 0 and n_negative == 0:
            consistency_desc = "所有CV策略均无显著相关"
        elif n_positive == len(signs) or n_negative == len(signs):
            consistency_desc = "全部同向，一致性优秀"
        elif n_positive > n_negative * 2 or n_negative > n_positive * 2:
            consistency_desc = "多数同向，一致性良好"
        else:
            consistency_desc = "方向不一致，需谨慎解读"
    else:
        consistency_desc = "无验证结果"

    # 去混杂后信号保留率
    if not deconfound_df.empty:
        raw_rho_sq = deconfound_df["raw_spearman"].pow(2).mean()
        deconf_rho_sq = deconfound_df["deconfounded_spearman"].pow(2).mean()
        signal_retention = (deconf_rho_sq / raw_rho_sq * 100) if raw_rho_sq > 1e-12 else 0.0
    else:
        signal_retention = 0.0

    # ---- 组装 Markdown 报告 ----
    report = f"""# Na离子导体描述符搜索报告

## 数据概览
- 样本数: {n_samples}
- 体系分布: NASICON={n_nasicon}, sulfide={n_sulfide}, halide={n_halide}
- 目标范围: log_sigma ∈ [{y_min:.2f}, {y_max:.2f}]
- 描述符总数: {n_total_desc}, 有效描述符: {n_valid_desc}

## Stage 1: 单描述符去混杂筛选
| 描述符 | 族 | 原始Spearman | 去混杂Spearman | 体系代理比 | 标签 |
|--------|-----|-------------|---------------|-----------|------|
{stage1_table}

### 标签分布
- 强物理信号: {label_counts.get('强物理信号', 0)}
- 弱物理信号: {label_counts.get('弱物理信号', 0)}
- 混合信号: {label_counts.get('混合信号', 0)}
- 体系代理: {label_counts.get('体系代理', 0)}
- 噪声级: {label_counts.get('噪声级', 0)}

## Stage 2: 稳定性选择与族代表
候选池规则：每个物理族最多保留 {stage2_capacity} 个稳定代表。三描述符模式下，
第二个同族名额仅用于受限的“同族两个 + 相邻族一个”公式构造，不应被解读为第二项独立科学发现。

### 族代表列表
| 描述符 | 族 | 族名 | 去混杂Spearman | 稳定性频率 |
|--------|-----|------|---------------|-----------|
{stage2_table}

## Stage 3: 约束组合搜索
### Top 10 组合候选
| 组合名 | 描述符数 | 组成 | 运算符序列 | 去混杂Spearman | 跨族? |
|--------|----------|------|------------|---------------|-------|
{stage3_table}

## Stage 4: V1–V4探索性验证与多策略CV
### 最佳单描述符基线
| 描述符 | 阴离子分层 | LOSO | 重复子采样 |
|--------|-----------|------|-----------|
{baseline_row}

### Top组合验证结果
| 组合名 | 描述符数 | 去混杂Spearman | 阴离子分层 | LOSO | 重复子采样 | 综合得分 | V1/V2/V3/V4 | 体系分层Bootstrap 95% CI | 状态 |
|--------|----------|---------------|-----------|------|-----------|---------|-------------|---------------------------|------|
{stage4_table}

注：V1–V4依次为匹配噪声基线、已知因素后关联、体系内原始Spearman、体系分层Bootstrap区间。`SKIPPED` 策略不计入综合得分；括号显示可用策略数/3。所有组合证据均为探索性，不作因果解释；完整公式组成、运算符、规则和原始值来源保存在 CSV/JSON provenance 中。

### V2 已知因素后目标残差预测审计（最佳组合）
- {best_v2_summary}
- 控制设计: {best_v2_control_audit}
- 语义: 折安全的探索性预测关联；不是因果效应。双侧偏相关仅作为补充证据保存在 artifact 中。

## 结论
### 物理发现
- 最强单描述符: {best_single_name} ({best_single_family}族), 去混杂Spearman = {best_single_rho:.3f}
- 最强组合: {best_comb_name}, 综合得分 = {best_comb_score:.3f}
- 组合相比单描述符提升: {delta_pct:.1f}%

### 稳健性评估
- 跨CV策略一致性: {consistency_desc}
- 去混杂后信号保留率: {signal_retention:.1f}%
"""

    report_path = output_dir / "final_report.md"
    report_path.write_text(report, encoding="utf-8")
    print(f"  Markdown 报告: {report_path}")

    # ---- 组装 JSON 报告 ----
    report_json = {
        "data_overview": {
            "n_samples": n_samples,
            "system_distribution": {"NASICON": n_nasicon, "sulfide": n_sulfide, "halide": n_halide},
            "log_sigma_range": [y_min, y_max],
            "n_total_descriptors": n_total_desc,
            "n_valid_descriptors": n_valid_desc,
        },
        "stage1_deconfound": {
            "label_distribution": label_counts,
            "top10": deconfound_df.head(10).to_dict(orient="records"),
        },
        "stage2_stability": {
            "representatives": reps.to_dict(orient="records") if not reps.empty else [],
        },
        "stage3_combination": {
            "n_candidates": len(candidates_df),
            "top10": candidates_df.head(10).to_dict(orient="records") if not candidates_df.empty else [],
        },
        "stage4_validation": {
            "baseline": baseline_df.to_dict(orient="records") if not baseline_df.empty else [],
            "top_combinations": validation_df.to_dict(orient="records") if not validation_df.empty else [],
        },
        "conclusion": {
            "best_single_descriptor": best_single_name,
            "best_single_family": best_single_family,
            "best_single_rho": float(best_single_rho),
            "best_combination": best_comb_name,
            "best_combination_score": float(best_comb_score),
            "combination_improvement_pct": float(delta_pct),
            "cv_consistency": consistency_desc,
            "signal_retention_pct": float(signal_retention),
        },
    }

    json_path = output_dir / "final_report.json"
    json_path.write_text(
        json.dumps(report_json, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )
    print(f"  JSON 报告: {json_path}")


# ============================================================
# 主入口
# ============================================================

def main() -> None:
    """管线主入口。"""
    t_start = time.time()

    args = parseArgs()
    output_dir = Path(args.output_dir)

    print("=" * 60)
    print("Na离子导体描述符搜索管线")
    print(
        f"  ridge_alpha={args.alpha}, selection_alpha={args.selection_alpha}, "
        f"seed={args.seed}, top_k={args.top_k}, "
        f"max_descriptors={args.max_descriptors}"
    )
    print(f"  输出目录: {output_dir.resolve()}")
    print("=" * 60)

    # Stage 0: 特征化
    feature_df, raw_df, system_labels, anion_labels, y = runStage0(args)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Stage 1: 单描述符去混杂筛选
    deconfound_df, filtered_deconfound_df = runStage1(
        feature_df, y, system_labels, anion_labels, args.alpha, output_dir
    )

    # Stage 2: 稳定性选择 + 物理族代表
    representative_df = runStage2(
        feature_df,
        y,
        filtered_deconfound_df,
        args.selection_alpha,
        args.seed,
        output_dir,
        max_descriptors=args.max_descriptors,
    )

    # Stage 3: 约束组合搜索
    candidates_df = runStage3(
        feature_df, y, system_labels, anion_labels,
        representative_df, args.alpha, args.seed, output_dir,
        max_descriptors=args.max_descriptors,
    )

    # Stage 4: 多策略CV验证
    validation_df, baseline_df = runStage4(
        feature_df, y, system_labels, anion_labels,
        filtered_deconfound_df,
        candidates_df,
        args.alpha,
        args.seed,
        args.top_k,
        output_dir,
    )

    # 生成报告
    generateReport(
        raw_df, deconfound_df, filtered_deconfound_df,
        representative_df, candidates_df, validation_df, baseline_df,
        output_dir,
    )

    # 结束
    elapsed = time.time() - t_start
    print("\n" + "=" * 60)
    print(f"管线完成! 总耗时: {elapsed:.1f} 秒")
    print(f"所有结果保存在: {output_dir.resolve()}")
    print("=" * 60)


if __name__ == "__main__":
    try:
        main()
    except (InsufficientFeatureDataError, FileNotFoundError) as exc:
        # A missing raw/CIF input is a controlled data-integrity failure, not a
        # Python crash.  Keep the diagnosis concise and preserve the guarantee
        # that Stage 0 failed before ``results/pipeline`` was created.
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(2) from None

--- 文件结束: run_pipeline.py ---

--- 文件开始: train.py ---
"""Evaluate one explicit CIF-derived descriptor in the independent Agent track.

This is intentionally not a train/validation/test-split runner.  It reads the
frozen raw structural CSV, performs strict CIF preflight, and evaluates one
registered descriptor using the shared fold-local Ridge CV and rank-aware
deconfounding implementations.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

from automat_utils import (
    AgentContractError,
    format_agent_metrics,
    prepare_structural_evaluation,
    resolve_frozen_input_identity,
    validate_agent_output_path,
    validate_agent_audit_batch,
    validate_agent_result_batch,
    write_agent_result,
    write_structural_audit,
)
from run_config import DEFAULT_RUN_INFO, config_get, load_run_info


def parse_agent_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse the explicit structural Agent contract without legacy defaults."""
    parser = argparse.ArgumentParser(
        description=(
            "Evaluate one registered CIF-derived descriptor in the isolated "
            "Agent track (results/agent only)."
        )
    )
    parser.add_argument(
        "--run-info",
        type=Path,
        default=DEFAULT_RUN_INFO,
        help="YAML file with frozen shared inputs and Agent-track settings.",
    )
    parser.add_argument(
        "--descriptor-name",
        required=True,
        help="Explicit key from descriptors.AVAILABLE_STRUCTURE_DESCRIPTORS.",
    )
    parser.add_argument(
        "--results-file",
        type=Path,
        default=None,
        help="Agent result TSV under results/agent/.",
    )
    parser.add_argument(
        "--audit-file",
        type=Path,
        default=None,
        help="Agent structural audit CSV under results/agent/.",
    )
    parser.add_argument(
        "--run-id",
        default="manual",
        help="Opaque Agent iteration identifier recorded in results.tsv.",
    )
    parser.add_argument(
        "--status",
        choices=("evaluated", "keep", "discard", "crash"),
        default="evaluated",
        help="Human-reviewed iteration status; defaults to evaluated.",
    )
    args = parser.parse_args(argv)

    config = load_run_info(args.run_info)
    args.run_config = config
    try:
        args.frozen_identity = resolve_frozen_input_identity(config, args.run_info)
        args.raw_file = args.frozen_identity.raw_file
        args.descriptor_registry = args.frozen_identity.descriptor_registry
        args.registry_revision = args.frozen_identity.registry_revision
        args.structure_column = config_get(config, "data.structure_column")
        args.target_column = config_get(config, "data.target_column")
        args.system_column = config_get(config, "data.system_column")
        args.anion_column = config_get(config, "data.anion_type_column")
        args.ridge_alpha = float(config_get(config, "evaluation.model.alpha"))
        args.results_file = validate_agent_output_path(
            args.results_file or config_get(config, "tracks.agent.results_file")
        )
        args.audit_file = validate_agent_output_path(
            args.audit_file or config_get(config, "tracks.agent.feature_cache_file")
        )
    except (AgentContractError, KeyError, ValueError) as exc:
        parser.error(str(exc))
    return args


def evaluate_descriptor(args: argparse.Namespace) -> dict[str, Any]:
    """Compatibility-named entry point for the structural Agent evaluator."""
    _frame, metrics = prepare_structural_evaluation(args)
    return metrics


def main(argv: list[str] | None = None) -> None:
    args = parse_agent_args(argv)
    try:
        frame, metrics = prepare_structural_evaluation(args)
    except (FileNotFoundError, KeyError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(2) from None

    try:
        # This preflight must precede the audit write; a conflicting TSV must
        # never overwrite the current batch's audit artifact.
        validate_agent_result_batch(metrics, args.results_file)
        validate_agent_audit_batch(metrics, args.audit_file)
        audit_path = write_structural_audit(
            frame,
            descriptor_name=args.descriptor_name,
            audit_file=args.audit_file,
            metrics=metrics,
        )
        results_path = write_agent_result(
            metrics,
            results_file=args.results_file,
            run_id=str(args.run_id),
            status=str(args.status),
        )
    except AgentContractError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(2) from None
    for line in format_agent_metrics(metrics):
        print(line)
    print(f"structural_audit_file:      {audit_path}")
    print(f"agent_results_file:         {results_path}")
    print("track_isolation:             agent writes results/agent only; no pipeline output read")


if __name__ == "__main__":
    main()

--- 文件结束: train.py ---

--- 文件开始: automat_utils.py ---
"""Shared utilities for the independent structural Agent track.

The Agent track evaluates one explicitly named, registered structural
descriptor at a time.  It uses the frozen raw CIF dataset and never accesses
Pipeline result files.  Both tracks may use the same frozen raw CSV and
descriptor registry, but each writes only to its own results directory.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import descriptors as descriptor_module
import numpy as np
import pandas as pd

from descriptors import (
    AVAILABLE_STRUCTURE_DESCRIPTORS,
    SEARCHABLE_STRUCTURE_DESCRIPTORS,
    STRUCTURE_DESCRIPTOR_METADATA,
)
from descriptors.cv_strategies import MultiStrategyCV, summarize_cv_spearman
from descriptors.deconfound import DeconfoundAnalyzer
from descriptors.featurizer import load_structure_from_cif, resolve_cif_path
from run_config import config_get


AGENT_RESULTS_ROOT = Path("results") / "agent"
FROZEN_IDENTITY_COLUMNS = (
    "shared_raw_file",
    "descriptor_registry",
    "registry_revision",
)

AGENT_RESULT_COLUMNS = [
    "run_id",
    "descriptor_name",
    "shared_raw_file",
    "descriptor_registry",
    "registry_revision",
    "source_rows",
    "target_rows",
    "finite_structural_values",
    "analysis_rows",
    "descriptor_failure_count",
    "raw_spearman",
    "deconfounded_spearman",
    "deconf_p",
    "system_proxy_ratio",
    "label",
    "anion_stratified_spearman",
    "anion_stratified_mae",
    "anion_stratified_skipped",
    "anion_stratified_skip_reason",
    "anion_stratified_available",
    "anion_stratified_downshifted",
    "anion_stratified_requested_n_folds",
    "anion_stratified_effective_n_folds",
    "loso_spearman",
    "loso_mae",
    "loso_skipped",
    "loso_skip_reason",
    "loso_available",
    "repeated_subsample_spearman",
    "repeated_subsample_mae",
    "repeated_subsample_skipped",
    "repeated_subsample_skip_reason",
    "repeated_subsample_available",
    "composite_score",
    "composite_strategy_count",
    "composite_is_complete",
    "composite_score_basis",
    "status",
]


class AgentContractError(ValueError):
    """Raised when the Agent track would violate its isolated contract."""


@dataclass(frozen=True)
class FrozenInputIdentity:
    """Canonical identity of the raw data and registry used by both tracks."""

    raw_file: Path
    descriptor_registry: Path
    registry_revision: str


def _resolve_run_info_relative_path(value: str | Path, run_info: Path) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path.resolve()
    return (run_info.resolve().parent / path).resolve()


def resolve_frozen_input_identity(
    config: dict[str, Any], run_info: Path
) -> FrozenInputIdentity:
    """Validate and canonicalize the single input batch shared by both tracks."""
    if config_get(config, "shared_input.frozen") is not True:
        raise AgentContractError("shared_input.frozen must be true")

    declared_raw = _resolve_run_info_relative_path(
        config_get(config, "data.raw_file"), run_info
    )
    frozen_raw = _resolve_run_info_relative_path(
        config_get(config, "shared_input.raw_file"), run_info
    )
    if declared_raw != frozen_raw:
        raise AgentContractError(
            "data.raw_file and shared_input.raw_file must resolve to the same frozen CSV"
        )

    registry_value = str(config_get(config, "shared_input.descriptor_registry")).strip()
    registry_revision = str(config_get(config, "shared_input.registry_revision")).strip()
    if not registry_value or not registry_revision:
        raise AgentContractError(
            "shared_input.descriptor_registry and shared_input.registry_revision are required"
        )
    configured_registry = _resolve_run_info_relative_path(registry_value, run_info)
    if not configured_registry.exists():
        raise AgentContractError(
            f"shared_input.descriptor_registry does not exist: {configured_registry}"
        )
    actual_registry = Path(descriptor_module.__file__).resolve()
    if configured_registry != actual_registry:
        raise AgentContractError(
            "shared_input.descriptor_registry must resolve to the active "
            f"descriptors module ({actual_registry}), got {configured_registry}"
        )
    return FrozenInputIdentity(
        raw_file=frozen_raw,
        descriptor_registry=actual_registry,
        registry_revision=registry_revision,
    )


def _identity_from_mapping(metrics: dict[str, Any]) -> FrozenInputIdentity:
    missing = [
        column
        for column in FROZEN_IDENTITY_COLUMNS
        if pd.isna(metrics.get(column)) or not str(metrics.get(column, "")).strip()
    ]
    if missing:
        raise AgentContractError(
            f"Agent metrics are missing frozen batch identity values: {missing}"
        )
    return FrozenInputIdentity(
        raw_file=Path(str(metrics["shared_raw_file"])).resolve(),
        descriptor_registry=Path(str(metrics["descriptor_registry"])).resolve(),
        registry_revision=str(metrics["registry_revision"]).strip(),
    )


def validate_agent_result_frame_identity(
    frame: pd.DataFrame,
    identity: FrozenInputIdentity,
    *,
    source: str | Path,
) -> None:
    """Reject a TSV containing missing, mixed, or foreign frozen identities."""
    missing_columns = set(FROZEN_IDENTITY_COLUMNS) - set(frame.columns)
    if missing_columns:
        raise AgentContractError(
            f"{source} is missing frozen batch identity columns: {sorted(missing_columns)}"
        )
    if frame.empty:
        return

    expected = {
        "shared_raw_file": str(identity.raw_file),
        "descriptor_registry": str(identity.descriptor_registry),
        "registry_revision": identity.registry_revision,
    }
    for column, expected_value in expected.items():
        raw_values = frame[column]
        normalized = raw_values.map(
            lambda value: None
            if pd.isna(value) or not str(value).strip()
            else str(value).strip()
        )
        if normalized.isna().any():
            raise AgentContractError(
                f"{source} has missing frozen batch identity values in {column}"
            )
        values = set(normalized.tolist())
        if len(values) != 1 or values != {expected_value}:
            raise AgentContractError(
                f"{source} frozen batch identity mismatch for {column}: "
                f"expected {expected_value!r}, found {sorted(values)!r}"
            )


def validate_agent_artifact_batch(
    metrics: dict[str, Any], artifact_file: str | Path
) -> Path:
    """Validate any existing Agent artifact before it can be overwritten."""
    path = validate_agent_output_path(artifact_file)
    identity = _identity_from_mapping(metrics)
    if path.exists():
        separator = "\t" if path.suffix.lower() == ".tsv" else ","
        existing = pd.read_csv(path, sep=separator)
        validate_agent_result_frame_identity(existing, identity, source=path)
    return path


def validate_agent_result_batch(
    metrics: dict[str, Any], results_file: str | Path
) -> Path:
    """Validate the Agent results TSV before any Agent artifact is written."""
    return validate_agent_artifact_batch(metrics, results_file)


def validate_agent_audit_batch(
    metrics: dict[str, Any], audit_file: str | Path
) -> Path:
    """Validate the Agent audit CSV before it can overwrite another batch."""
    return validate_agent_artifact_batch(metrics, audit_file)


def validate_agent_output_path(value: str | Path) -> Path:
    """Return a relative ``results/agent`` path or reject cross-track output.

    Restricting paths at the boundary prevents an Agent command from writing
    into ``results/pipeline`` (or an arbitrary external path) by accident.
    """
    path = Path(value)
    expected_prefix = AGENT_RESULTS_ROOT.parts
    if (
        path.is_absolute()
        or path.parts[: len(expected_prefix)] != expected_prefix
        or ".." in path.parts
    ):
        raise AgentContractError(
            "Agent artifacts must be relative paths under results/agent/; "
            f"got {path}"
        )
    return path


def _validate_structural_descriptor_name(descriptor_name: str) -> None:
    if descriptor_name not in AVAILABLE_STRUCTURE_DESCRIPTORS:
        available = ", ".join(sorted(SEARCHABLE_STRUCTURE_DESCRIPTORS))
        raise KeyError(
            f"Unknown structural descriptor '{descriptor_name}'. "
            f"Active descriptors: {available}"
        )
    if descriptor_name not in SEARCHABLE_STRUCTURE_DESCRIPTORS:
        alias_of = STRUCTURE_DESCRIPTOR_METADATA.get(descriptor_name, {}).get("alias_of")
        detail = f"; use {alias_of} instead" if alias_of else ""
        raise ValueError(
            f"Structural descriptor '{descriptor_name}' is inactive for Agent search{detail}."
        )


def validate_structural_columns(
    frame: pd.DataFrame,
    *,
    target_column: str,
    structure_column: str,
    system_column: str,
    anion_column: str,
) -> None:
    """Fail before featurization if the raw structural contract is incomplete."""
    required = {
        "target": target_column,
        "structure": structure_column,
        "system": system_column,
        "anion": anion_column,
    }
    missing = [f"{role}={column}" for role, column in required.items() if column not in frame]
    if missing:
        raise ValueError("Raw structural CSV is missing required columns: " + ", ".join(missing))


def load_and_featurize_structural_frame(
    raw_file: str | Path,
    *,
    descriptor_name: str,
    target_column: str,
    structure_column: str,
    system_column: str,
    anion_column: str,
) -> pd.DataFrame:
    """Load raw data, strictly preflight CIFs, and compute one descriptor.

    All paths are resolved relative to the raw CSV.  Every CIF must both exist
    and parse before any Agent output is created.  Individual descriptor
    failures are retained as missing values for audit, but an all-missing
    descriptor is rejected later by :func:`evaluate_structural_frame`.
    """
    _validate_structural_descriptor_name(descriptor_name)
    raw_path = Path(raw_file)
    if not raw_path.exists():
        raise FileNotFoundError(f"Missing raw structural CSV: {raw_path}")

    frame = pd.read_csv(raw_path)
    validate_structural_columns(
        frame,
        target_column=target_column,
        structure_column=structure_column,
        system_column=system_column,
        anion_column=anion_column,
    )

    csv_dir = raw_path.resolve().parent
    resolved_paths: list[Path | None] = []
    missing: list[tuple[object, Path | None]] = []
    for index, value in frame[structure_column].items():
        if pd.isna(value):
            resolved_paths.append(None)
            missing.append((index, None))
            continue
        resolved = resolve_cif_path(str(value), csv_dir)
        resolved_paths.append(resolved)
        if not resolved.exists():
            missing.append((index, resolved))

    if missing:
        preview = ", ".join(
            f"row {index}: {path if path is not None else '<empty>'}"
            for index, path in missing[:3]
        )
        suffix = f", ... and {len(missing) - 3} more" if len(missing) > 3 else ""
        raise FileNotFoundError(
            f"CIF preflight failed: {len(missing)} missing path(s); {preview}{suffix}"
        )

    structures = []
    parse_failures: list[tuple[object, Path, str]] = []
    for index, path in zip(frame.index, resolved_paths):
        assert path is not None
        try:
            structures.append(load_structure_from_cif(path))
        except ValueError as exc:
            parse_failures.append((index, path, str(exc)))

    if parse_failures:
        preview = "; ".join(
            f"row {index}: {path} ({message})"
            for index, path, message in parse_failures[:2]
        )
        suffix = f"; ... and {len(parse_failures) - 2} more" if len(parse_failures) > 2 else ""
        raise ValueError(
            f"CIF structural preflight failed: {len(parse_failures)} unparsable file(s); "
            f"{preview}{suffix}"
        )

    descriptor_fn, _family, _high_risk = AVAILABLE_STRUCTURE_DESCRIPTORS[descriptor_name]
    values: list[float] = []
    descriptor_failures: list[tuple[object, str]] = []
    for index, structure in zip(frame.index, structures):
        try:
            value = float(descriptor_fn(structure))
            values.append(value if np.isfinite(value) else float("nan"))
        except Exception as exc:  # Descriptor implementations are audited below.
            values.append(float("nan"))
            descriptor_failures.append((index, str(exc)))

    result = frame.copy()
    result[descriptor_name] = values
    result["_resolved_cif_path"] = [str(path) for path in resolved_paths]
    result.attrs["descriptor_failures"] = descriptor_failures
    return result


def _skipped_cv_result(strategy: str, exc: Exception) -> dict[str, Any]:
    """Represent an infeasible split as unavailable evidence, not a crash."""
    return {
        "strategy": strategy,
        "skipped": True,
        "reason": f"{strategy} skipped: {exc}",
        "fold_results": [],
        "mean_spearman": float("nan"),
        "mean_mae": float("nan"),
    }


def _run_structural_cv_safely(
    X: np.ndarray,
    y: np.ndarray,
    systems: np.ndarray,
    anions: np.ndarray,
    *,
    ridge_alpha: float,
) -> dict[str, dict[str, Any]]:
    """Run shared CV strategies independently so one infeasible split is explicit."""
    evaluator = MultiStrategyCV(alpha=ridge_alpha)
    calls = {
        "anion_stratified_cv": lambda: evaluator.anion_stratified_cv(X, y, anions),
        "leave_one_system_out": lambda: evaluator.leave_one_system_out(X, y, systems),
        "repeated_subsample": lambda: evaluator.repeated_subsample(X, y, systems),
    }
    results: dict[str, dict[str, Any]] = {}
    for strategy, call in calls.items():
        try:
            results[strategy] = call()
        except ValueError as exc:
            results[strategy] = _skipped_cv_result(strategy, exc)
    return results


def evaluate_structural_frame(
    frame: pd.DataFrame,
    *,
    descriptor_name: str,
    target_column: str,
    system_column: str,
    anion_column: str,
    ridge_alpha: float,
) -> dict[str, Any]:
    """Evaluate one structural descriptor with shared deconfounding and CV."""
    _validate_structural_descriptor_name(descriptor_name)
    validate_structural_columns(
        frame,
        target_column=target_column,
        structure_column="_resolved_cif_path" if "_resolved_cif_path" in frame else "cif_path",
        system_column=system_column,
        anion_column=anion_column,
    )
    if descriptor_name not in frame:
        raise ValueError(f"Missing computed structural descriptor column: {descriptor_name}")

    y_full = pd.to_numeric(frame[target_column], errors="coerce").to_numpy(dtype=float)
    x_full = pd.to_numeric(frame[descriptor_name], errors="coerce").to_numpy(dtype=float)
    target_mask = np.isfinite(y_full)
    finite_structural_mask = np.isfinite(x_full)
    analysis_mask = target_mask & finite_structural_mask
    if int(target_mask.sum()) < 5:
        raise ValueError("At least five finite target values are required for structural evaluation.")
    if int(finite_structural_mask.sum()) < 5:
        raise ValueError(
            "No valid structural descriptor values are available for reliable evaluation; "
            "the descriptor is all-NaN or has fewer than five finite values."
        )
    if int(analysis_mask.sum()) < 5:
        raise ValueError(
            "Fewer than five rows contain both target and structural descriptor values."
        )

    system_labels = frame[system_column].astype(str).tolist()
    anion_labels = frame[anion_column].astype(str).tolist()
    feature_df = frame[[descriptor_name]].copy()
    deconfound = DeconfoundAnalyzer(alpha=ridge_alpha).analyze_all(
        feature_df, y_full, system_labels, anion_labels
    )
    if deconfound.empty:
        raise ValueError(
            f"Deconfounding produced no valid result for structural descriptor '{descriptor_name}'."
        )
    deconf_row = deconfound.iloc[0].to_dict()

    # Keep all finite-target rows for fold-local median imputation.  This is
    # intentionally the same leakage-safe CV implementation as the pipeline.
    X = x_full[target_mask].reshape(-1, 1)
    y = y_full[target_mask]
    systems = np.asarray(system_labels, dtype=object)[target_mask]
    anions = np.asarray(anion_labels, dtype=object)[target_mask]
    cv_results = _run_structural_cv_safely(
        X, y, systems, anions, ridge_alpha=ridge_alpha
    )
    cv_summary = summarize_cv_spearman(cv_results)

    failures = frame.attrs.get("descriptor_failures", [])
    return {
        "descriptor_name": descriptor_name,
        "source_rows": int(len(frame)),
        "target_rows": int(target_mask.sum()),
        "finite_structural_values": int(finite_structural_mask.sum()),
        "analysis_rows": int(analysis_mask.sum()),
        "descriptor_failure_count": int(len(failures)),
        "raw_spearman": float(deconf_row["raw_spearman"]),
        "deconfounded_spearman": float(deconf_row["deconfounded_spearman"]),
        "deconf_p": float(deconf_row["deconf_p"]),
        "system_proxy_ratio": float(deconf_row["system_proxy_ratio"]),
        "label": str(deconf_row["label"]),
        "anion_stratified_mae": float(
            cv_results["anion_stratified_cv"].get("mean_mae", float("nan"))
        ),
        "loso_mae": float(cv_results["leave_one_system_out"].get("mean_mae", float("nan"))),
        "repeated_subsample_mae": float(
            cv_results["repeated_subsample"].get("mean_mae", float("nan"))
        ),
        **cv_summary,
    }


def prepare_structural_evaluation(args: Any) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Execute strict raw-CIF loading followed by one-descriptor evaluation."""
    frame = load_and_featurize_structural_frame(
        args.raw_file,
        descriptor_name=args.descriptor_name,
        target_column=args.target_column,
        structure_column=args.structure_column,
        system_column=args.system_column,
        anion_column=args.anion_column,
    )
    metrics = evaluate_structural_frame(
        frame,
        descriptor_name=args.descriptor_name,
        target_column=args.target_column,
        system_column=args.system_column,
        anion_column=args.anion_column,
        ridge_alpha=float(args.ridge_alpha),
    )
    # Persist the frozen batch identity with both emitted Agent artifacts.
    frame = frame.copy()
    frame["shared_raw_file"] = str(args.raw_file)
    frame["descriptor_registry"] = str(args.descriptor_registry)
    frame["registry_revision"] = str(args.registry_revision)
    metrics.update(
        {
            "shared_raw_file": str(args.raw_file),
            "descriptor_registry": str(args.descriptor_registry),
            "registry_revision": str(args.registry_revision),
        }
    )
    return frame, metrics


def evaluate_structural_descriptor(args: Any) -> dict[str, Any]:
    """Public evaluator used by the Agent CLI and regression tests."""
    _frame, metrics = prepare_structural_evaluation(args)
    return metrics


def write_agent_result(
    metrics: dict[str, Any],
    *,
    results_file: str | Path,
    run_id: str,
    status: str,
) -> Path:
    """Append one evaluated descriptor row inside ``results/agent`` only."""
    row = {column: metrics.get(column, float("nan")) for column in AGENT_RESULT_COLUMNS}
    row["run_id"] = run_id
    row["status"] = status
    path = validate_agent_result_batch(row, results_file)
    path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame([row], columns=AGENT_RESULT_COLUMNS).to_csv(
        path,
        sep="\t",
        index=False,
        mode="a" if path.exists() else "w",
        header=not path.exists(),
    )
    return path


def write_structural_audit(
    frame: pd.DataFrame,
    *,
    descriptor_name: str,
    audit_file: str | Path,
    metrics: dict[str, Any],
) -> Path:
    """Write only the structural inputs and computed value for reproducibility."""
    path = validate_agent_audit_batch(metrics, audit_file)
    preferred_columns = [
        "material_id",
        "cif_path",
        "_resolved_cif_path",
        "shared_raw_file",
        "descriptor_registry",
        "registry_revision",
        "system",
        "anion_type",
        "log_sigma",
        descriptor_name,
    ]
    columns = [column for column in preferred_columns if column in frame.columns]
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.loc[:, columns].to_csv(path, index=False)
    return path


def format_agent_metrics(metrics: dict[str, Any]) -> list[str]:
    """Return concise, explicit structural metrics for both Agent entry points."""
    return [
        f"descriptor_name:             {metrics['descriptor_name']}",
        f"source_rows:                 {metrics['source_rows']}",
        f"finite_structural_values:    {metrics['finite_structural_values']}",
        f"analysis_rows:               {metrics['analysis_rows']}",
        f"raw_spearman:                {metrics['raw_spearman']:.6f}",
        f"deconfounded_spearman:       {metrics['deconfounded_spearman']:.6f}",
        f"system_proxy_ratio:          {metrics['system_proxy_ratio']:.6f}",
        f"label:                       {metrics['label']}",
        f"anion_stratified_spearman:   {metrics['anion_stratified_spearman']:.6f}",
        f"loso_spearman:               {metrics['loso_spearman']:.6f}",
        f"repeated_subsample_spearman: {metrics['repeated_subsample_spearman']:.6f}",
        f"cv_composite_score:          {metrics['composite_score']:.6f}",
    ]

--- 文件结束: automat_utils.py ---

## 输出格式

For each check (A-L), report:
- Status: PASS | WARN | FAIL
- Evidence: exact file:line references (use the relative paths shown in the file markers above)
- Details: what specifically was found

Overall verdict: PASS | WARN | FAIL

Be thorough. Read every eval/statistical script line by line. For the stat-pipeline专项 checks (G-L), cite specific file:line evidence and explain the mechanism of any leakage/bias you identify.

请按以下结构输出：

## A. Ground Truth Provenance
- Status: [PASS | WARN | FAIL]
- Evidence: [file:line references]
- Details: [findings]

## B. Score Normalization
- Status: [PASS | WARN | FAIL]
- Evidence: [file:line references]
- Details: [findings]

## C. Result File Existence
- Status: [PASS | WARN | FAIL]
- Evidence: [file:line references]
- Details: [findings]

## D. Dead Code Detection
- Status: [PASS | WARN | FAIL]
- Evidence: [file:line references]
- Details: [findings]

## E. Scope Assessment
- Status: [PASS | WARN | FAIL]
- Evidence: [file:line references]
- Details: [findings]

## F. Evaluation Type
- Classification: [real_gt | synthetic_proxy | self_supervised_proxy | simulation_only | human_eval]
- Evidence: [file:line references]
- Details: [findings]

## G. Data Leakage in Preprocessing (stat-pipeline 专项)
- Status: [PASS | WARN | FAIL]
- Evidence: [file:line references]
- Details: [逐项报告：imputation/standardization/noise injection/stability subsampling/deconfound residualization 是否在 CV 折内拟合]

## H. Feature Selection Leakage (stat-pipeline 专项 — CRITICAL)
- Status: [PASS | WARN | FAIL]
- Evidence: [file:line references]
- Details: [逐项报告：stability selection → CV、combination top-k → CV、PhysicalGrouper representative → CV 是否存在 selection-then-evaluate 泄露；项目是否承认这一结构（如 selection_uncertainty_included: false）]

## I. Deconfounding Methodology Correctness (stat-pipeline 专项)
- Status: [PASS | WARN | FAIL]
- Evidence: [file:line references]
- Details: [逐项报告：partial_spearman 在 Stage1 vs Stage4 V2 的残差化范围、rank_aware_controls 实现、system_proxy_ratio 失效模式、Ridge 正则化对 Spearman 的影响、confounder 是否同时作为特征]

## J. Multiple Testing & Selective Reporting (stat-pipeline 专项)
- Status: [PASS | WARN | FAIL]
- Evidence: [file:line references]
- Details: [逐项报告：41 描述符 × 3 CV × V1-V4 的多重比较校正、composite_score 只用可用策略的透明度、top-k 选择的乐观性、bootstrap CI 是否覆盖选择不确定性]

## K. Target & Metric Definition (stat-pipeline 专项)
- Status: [PASS | WARN | FAIL]
- Evidence: [file:line references]
- Details: [逐项报告：log_sigma 定义、Spearman vs Pearson 选择、composite_score 取绝对值是否掩盖方向不一致、小样本下 deconfound 过校正风险]

## L. Causal Claim Boundary (stat-pipeline 专项)
- Status: [PASS | WARN | FAIL]
- Evidence: [file:line references]
- Details: [逐项报告：代码/文档是否正确限制为关联性、deconfounded_spearman 是否可能被误读为因果效应、"强物理信号"等标签是否可能被误读为因果、V2 causal_claim: False 是否一致、是否有过度声称的语言]

## Overall Verdict: [PASS | WARN | FAIL]

## Action Items
- [specific fixes if WARN or FAIL, ordered by severity]

## Claim Impact
- Claim 1 (关联性/预测稳健性，非因果): [supported | needs_qualifier | unsupported]
- Claim 2 (去混杂后信号保留): [supported | needs_qualifier | unsupported]
- Claim 3 (跨 CV 策略一致性): [supported | needs_qualifier | unsupported]
- Claim 4 (组合优于单描述符): [supported | needs_qualifier | unsupported]

## Top 3 Critical Findings (stat-pipeline 专项)
1. [最关键的统计管线发现]
2. [次关键]
3. [第三关键]