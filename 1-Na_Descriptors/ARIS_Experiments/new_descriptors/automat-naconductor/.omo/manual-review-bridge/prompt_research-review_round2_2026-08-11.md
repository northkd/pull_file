【会话指示 - research-review】

1. 本模板支持多轮迭代对话。第 1 轮复制下方"prompt 正文"全部内容，粘贴到新的 Claude 对话。
2. 第 2-N 轮【在同一对话中继续】——不要开新对话。后续轮次可针对未解决的弱点追问。
3. 后续轮次的典型用法：
   - 追问特定算法步骤的细节
   - 请求某个"标准方法"的具体实现方案
   - 请求某个退化条件的构造性证明
   - 请求替代算法设计的草图
4. 何时停止：双方就每个步骤的四问回答达成一致、核心设计问题明确、修复方向确定。
5. 如需全新审稿人视角（防止长期对话的偏见累积），可开新对话重新粘贴完整 prompt。

注意：本次评审的特殊约束——
- 不评估可发表性，不提议新实验
- 只评判算法设计本身（不涉及数值结果，数据集仍在准备中）
- 对每个算法步骤回答四个固定问题

---

I'm going to present a complete ML research project for your critical review.
Please act as a senior ML reviewer (NeurIPS/ICML level) with deep expertise in
causal inference, feature selection, and small-sample statistics.

This project is a **Na-ion conductor structural descriptor search pipeline**.
The goal: find CIF-structure-derived descriptors whose deconfounded Spearman
correlation with log10(conductivity) is maximized, using ~84 samples across
3 material systems (NASICON / sulfide / halide).

**Important scope constraint**: The dataset is still being prepared. You are
reviewing the **algorithm design itself**, not any numerical results. Do not
comment on specific numbers, scores, or outcomes—judge the algorithms as
algorithms.

## 你的任务

For each algorithmic step below, assess:
1. Does the procedure actually accomplish what it is designed to accomplish?
2. Under what conditions does it degenerate to something trivially different?
3. What is the minimal design change that would fix it, and what does that
   change cost?
4. Is there a standard method in the statistics/ML literature that this step
   is an ad-hoc version of? Name it.

Do not propose new experiments. Do not assess publishability. Judge the
algorithms as algorithms.

## 算法步骤清单

以下是从嵌入代码中识别的主要算法步骤，请逐条评估。

适用范围：本清单只覆盖统计管线层。描述符实现层（CIF → 特征值）不在此列，
由 descriptor-impl profile 单独评审。

**去混杂层（descriptors/deconfound.py）**
- 步骤 A1: `build_rank_aware_controls` — 构造 system 为主控制 + 秩感知增量 anion 对比项的设计矩阵（deconfound.py:68）
- 步骤 A2: `rank_corr_of_linear_residuals` — 对 x 与 y 分别做 Ridge 线性残差化，对残差求 Spearman；非文献意义的 partial Spearman（deconfound.py:132）
- 步骤 A3: `analyze_all` — 对每个描述符计算 raw_spearman 与 rank_corr_of_linear_residuals，按 |rho| 降序（deconfound.py:206）

**稳定性选择层（descriptors/stability.py）**
- 步骤 B1: `StabilitySelector.run` — 无放回子采样 + 子样本内独立预处理 + Lasso + 选中频率统计 + 噪声列 95 分位基线（stability.py:100）
- 步骤 B2: `PhysicalGrouper.group_and_select` — 按物理族分组，每组取 |rank_corr_of_linear_residuals| 最高的代表（stability.py:230）

**组合搜索与验证层（descriptors/combination.py）**
- 步骤 C1: `ConstrainedCombinationSearch.search` — 声明式算子注册表约束的二元/三元公式枚举 + 去混杂 Spearman 排序（combination.py:305）
- 步骤 C2: `CombinationValidator._noise_baseline`（V1）— 体系内分量置换零分布（combination.py:552）
- 步骤 C3: `CombinationValidator._factor_spanning`（V2）— 折内残差化 + OOF 公式预测 vs 残差目标。折由 StratifiedKFold 按 system 分层生成，每折均含全部体系；最小体系不足 2 时回退随机 KFold（combination.py:603，分折逻辑见 643–654）
- 步骤 C4: `CombinationValidator._per_system`（V3）— 逐体系原始 Spearman（combination.py:762）
- 步骤 C5: `CombinationValidator._bootstrap_ci`（V4）— 体系分层 bootstrap CI（percentile 法）（combination.py:784）
- 步骤 C6: `CombinationValidator.full_validation` — 组装 V1–V4 与 uncertainty 元数据（combination.py:842）
- 步骤 C7: `CombinationValidator.validate` — 扁平化 V1–V4 至 CSV 行（combination.py:885）

**管线级（run_pipeline.py）**
- 步骤 D1: `runStage0` — 读取原始 CSV 与 CIF，CIF 存在性与可解析性预检（run_pipeline.py:212）
- 步骤 D2: `runStage1` — 全描述符线性残差秩相关分析 + 预筛选（run_pipeline.py:269）
- 步骤 D3: `runStage2` — 稳定性选择 + 物理族代表选择（run_pipeline.py:311）
- 步骤 D4: `runStage3` — 约束组合搜索（run_pipeline.py:403）
- 步骤 D5: `runStage4` — V1–V4 探索性验证 + 单描述符基线（run_pipeline.py:461）
- 步骤 D6: `generateReport` — 汇总报告与 CSV 写出（run_pipeline.py:535）

**跨阶段结构**
- 步骤 E1: Stage 0 → 1 → 2 → 3 → 4 构成全量目标依赖的选择链，全部在同一批样本上完成，无外层循环 CV


## 已知弱点（两轮 experiment-audit 的 Top Critical Findings 原文）

注：以下审计发现引用的部分符号名已改名或删除（对照见 RENAME_LOG.md），发现本身仍然有效。

以下为两轮 experiment-audit 的 Top Critical Findings 原文。

=== run01 审计（A-H 八项，7 项 FAIL）关键发现 ===

Overall Verdict: FAIL

A. Target Variable Provenance: FAIL
- 数据模式中不存在任何测量条件列。没有温度、没有测量方法（EIS/直流极化）、没有 total/bulk/grain-boundary 区分、没有样品制备、没有文献来源 ID。σ 是 Arrhenius 量，同一材料在 25°C 与 300 K 之外的报道值可差数量级；bulk 与 total 电导率对同一样品可差 2-3 个量级。
- 异质来源被合并且合并本身就是设计目的。NASICON / sulfide / halide 三体系汇入同一 log_sigma 向量，LOSO-CV 明确要求跨体系外推。

B. Metric Self-Reference: FAIL
- 复合标签可以奖励管线自身定义为失败的结果。_classify_descriptor 把 |deconf_rho| > 0.3 置于代理比判断之上，注释明写"无论代理比多高"。raw_rho=0.9, deconf_rho=0.31 时 system_proxy_ratio=0.881，即 88% 由体系混杂驱动的描述符被标为"强物理信号"。
- clip 销毁了方向信息。deconf_rho > raw_rho（抑制效应）会产生负比值，被 clip 成 0.0，即"最纯物理信号"。去混杂反而增强相关这一最该被警惕的情形，被编码为最高信誉等级。
- signal_retention 是"均值之比"非"比之均值"，可超过 100%。

D. Dead Path Detection: FAIL
- 注释声明"有效值不足 80% 则跳过"，代码执行 n_valid < 5。80% 这个数字在代码库中不存在。
- deconf_p 是死参数，"显著"一词建立在它之上，但 _classify_descriptor 从不使用它。
- partial_spearman 静默回退：z.shape[1] >= n_samples 时返回原始 Spearman 当作去混杂值，回退事件无任何记录。

E. Scope and Multiplicity: FAIL
- 零多重性控制。无 FDR、无 Bonferroni、无置换检验、无嵌套外层选择。
- "一致性优秀"的证据基数是 <=9 个非独立观测。

F. Threshold Provenance: FAIL
- 全部决定性阈值（0.2/0.3/0.3/0.7）零外部依据，标 "errata P3" 表明是看过输出后修订的。
- 参考类编码 + L2 惩罚 = 结果不随参考类别选择而不变。

G. Null Distribution and Selection Effects: FAIL
- 唯一的经验零分布是 Stage 2 注入噪声列。无置换检验、无 y 打乱、无跨种子重复。
- 零分布施加在错误阶段：真实描述符已过 Stage 1 预筛选，噪声列没有——两臂不可交换。

H. Randomness and Reproducibility: FAIL
- 配置文件与代码描述的是不同的过程。大量 YAML 键不被代码读取。改 YAML 不改行为。
- CLI seed 不传播到 CV 阶段。

=== run02 审计（A-L 十二项 stat-pipeline 专项）Top 3 Critical Findings 原文 ===

1. 混杂集可能是中介集——主指标系统性删除答案且不可逆。anion_type 经极化率→键软度→迁移势垒是结构→电导通路本身；system 是结构的下游标签。对中介条件化减掉待测效应，叠加 Stage1 永久剔除，管线可能在删除真实机制。

2. 四级全量目标依赖选择→无外层循环 CV，唯一承认在写盘前被丢掉。Stage1 预筛(38→6)→Stage2 稳定性选择→PhysicalGrouper 代表→Stage3 排序→Stage4 top-k CV，全在同一 84 行上。selection_uncertainty_included: False 在 validate() 扁平化时被丢弃。噪声基线不对称进一步放大偏差。

3. 单列公式下 CV 代数退化为未去混杂的折内原始 Spearman。Spearman(y_val, y_hat)=sign(a)*Spearman(y_val, x_val)，alpha/标准化无效。composite_score 度量原始关联却与 deconfounded_spearman 并列；LOSO 与 V3 非独立；anion_stratified 验证折混合阴离子类型在构造上被混杂。"跨 CV 策略一致性"无独立信息量。

=== 补充声明 ===
数据集仍在准备中，本次评审对象是算法设计本身，不涉及任何数值结果。

## 文件内容

--- 文件开始: run_info.yaml ---
# Na离子导体描述符搜索配置
# 基于 automat 框架，针对 Na 离子固态电解质结构描述符与电导率关系研究

task:
  name: naconductor
  description: >
    搜索 Na 离子固态导体的局域结构描述符组合，
    使其与 log10(σ/S·cm⁻¹) 的线性残差秩相关性最大化。
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

deconfound:
  # 混杂变量列表——这些变量与目标相关但不是因果通路
  # 在计算描述符-目标相关性时需要控制
  confounders:
    - system          # 主控制：体系类型（NASICON/sulfide/halide）
    - anion_type      # 增量控制；报告相对 system 的秩增量/冗余，不作独立因果解释
  categorical_coding: reference_class
  primary_control: system
  report_design_rank: true
  # 残差化方法：偏相关
  method: partial_correlation
  # 线性残差秩相关作为主要评价指标（非文献意义的偏 Spearman，详见 estimand 段）
  primary_metric: rank_corr_of_linear_residuals

estimand:
  # 主指标定义与诚实命名声明
  name: rank_corr_of_linear_residuals
  definition: >
    对 x 与 y 各自在 {intercept, system, anion_type} 张成的列空间上
    做 Ridge(alpha=1.0) 残差化，在原始尺度上取残差，
    再对两组残差求 Spearman rho。
  not_partial_spearman: >
    本量【不是】文献意义上的 partial Spearman。
    标准做法是先秩变换再偏出，本实现顺序相反——先线性残差化再秩变换。
  monotonic_invariance: >
    本量对 x 的单调变换【不】不变，因线性残差化不保秩。
    对 x 施加 exp/log 等单调非线性变换会改变残差化结果，进而改变 rho。
  decision_date: "2026-08-10"
  decision_precedes_dataset_finalization: true

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
  primary: rank_corr_of_linear_residuals
  # 辅助评价指标
  secondary:
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
      primary_metric: rank_corr_of_linear_residuals
      max_iterations: 30
      patience: 8
      semantics: >
        仅对 status 为 evaluated、keep 或 discard 的有限线性残差秩相关
        计入耐心；crash 和不可用 CV 策略不会伪造改善或消耗耐心。

c9_cross_track_review:
  user_authorization_required: true
  inputs_must_be_completed_and_frozen: true
  read_only_inputs: [results/agent, results/pipeline]
  interpretation: >
    结果一致仅是独立三角验证或优先复核线索，不构成因果证据；
    两条轨道均不建立因果关系。
--- 文件结束: run_info.yaml ---

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
4. 主指标是 `rank_corr_of_linear_residuals`（线性残差秩相关，非文献意义的
   partial Spearman；详见 run_info.yaml 的 estimand 段）。控制设计以 `system`
   为主，仅在秩上提供增量信息时再加入 `anion_type` 对比项。
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

4. 审阅 TSV 中的 `raw_spearman`、`rank_corr_of_linear_residuals`。
   被标为 `skipped` 的策略应保持显式，不可补零或当作支持证据。
5. 在人工复核后，可用下一次命令的 `--status keep|discard|crash` 标记结果；默认
   状态是 `evaluated`。不要只因原始相关高或单一 CV 好看就标记为保留。
6. 运行 `python run_status.py`。它只根据 Agent 的有限线性残差秩相关记录和
   `tracks.agent.status` 停止条件输出 `CONTINUE` 或 `STOP`。

## 结果记录

`results/agent/results.tsv` 由评估器追加。其关键列是：

```text
run_id  descriptor_name  source_rows  finite_structural_values  analysis_rows
raw_spearman  rank_corr_of_linear_residuals  status
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

--- 文件开始: descriptors/deconfound.py ---
"""线性残差秩相关分析器。

核心思想：混杂变量（如体系分类 system、阴离子类型 anion_type）同时影响
描述符 X 和电导率 Y。不去控制的话，"高相关"可能只是混杂效应而非物理信号。

方法：用 Ridge 回归分别从 X 和 Y 中"减去"混杂变量能解释的部分（残差化），
然后对残差计算 Spearman 秩相关。这样就把"因为属于某个体系而产生的相关"
和"体系内部的物理相关"分离开来。

注意：本分析器计算的 rank_corr_of_linear_residuals 不是文献意义上的
partial Spearman（后者先秩变换再偏出）。本实现先在原始尺度上做 Ridge
线性残差化，再对残差求 Spearman。该量对 x 的单调变换不不变，因线性
残差化不保秩。详见 run_info.yaml 的 estimand 段。
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
    "rank_corr_of_linear_residuals",
]


class DeconfoundAnalyzer:
    """去混杂相关性分析器。

    对每个描述符，计算原始 Spearman 相关和去混杂后的线性残差秩相关。

    注意：本分析器计算的 rank_corr_of_linear_residuals 不是文献意义上的
    partial Spearman（后者先秩变换再偏出）。本实现先在原始尺度上做 Ridge
    线性残差化，再对残差求 Spearman。该量对 x 的单调变换不不变，因线性
    残差化不保秩。详见 run_info.yaml 的 estimand 段。

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

    def rank_corr_of_linear_residuals(
        self,
        x: np.ndarray,
        y: np.ndarray,
        confounders_df: pd.DataFrame,
    ) -> tuple[float, float]:
        """计算控制混杂变量后的线性残差秩相关。

        注意：本方法不是文献意义上的 partial Spearman（后者先秩变换再偏出）。
        本方法先在原始尺度上对 x 与 y 各自做 Ridge(alpha=1.0) 残差化，
        再对两组残差求 Spearman。该量对 x 的单调变换不不变，因线性残差化
        不保秩。

        步骤:
        1. 用 Ridge 分别拟合 x ~ confounders 和 y ~ confounders
        2. 取残差: res_x = x - confounders_predicted_x, res_y 同理
        3. 对残差计算 spearmanr

        参数:
            x: 描述符值向量 (n_samples,)
            y: 目标值向量 (n_samples,)
            confounders_df: 混杂变量矩阵 (n_samples, n_confounders)

        返回:
            (rho, p_value) — 线性残差化后的 Spearman 相关系数和 p 值
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

    def rank_corr_of_linear_residuals_rho(
        self,
        x: np.ndarray,
        y: np.ndarray,
        confounders_df: pd.DataFrame,
    ) -> float:
        """计算线性残差秩相关 rho（便捷方法，只返回 rho）。

        注意：本方法返回的是 rank_corr_of_linear_residuals，不是文献意义上
        的 partial Spearman。详见 run_info.yaml 的 estimand 段。

        参数:
            x: 描述符值向量 (n_samples,)
            y: 目标值向量 (n_samples,)
            confounders_df: 混杂变量矩阵 (n_samples, n_confounders)

        返回:
            线性残差化后的 Spearman rho
        """
        rho, _ = self.rank_corr_of_linear_residuals(x, y, confounders_df)
        return rho

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
        - rank_corr_of_linear_residuals: 控制 system + anion 后的线性残差秩相关 rho

        参数:
            feature_df: 包含描述符列的 DataFrame（已标准化）
            y: log_sigma 目标向量 (n_samples,)
            system_labels: 每个样本的体系标签，如 ["NASICON", ...]
            anion_labels: 每个样本的阴离子标签，如 ["O", ...]

        返回:
            分析结果 DataFrame，列为:
            descriptor, family, is_high_risk, raw_spearman,
            rank_corr_of_linear_residuals
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

            # 线性残差秩相关（非偏 Spearman），只保留 rho
            deconf_rho = self.rank_corr_of_linear_residuals_rho(
                x_valid, y_valid, conf_valid,
            )

            # 查询 family 和 is_high_risk
            _func, family, is_high_risk = SEARCHABLE_STRUCTURE_DESCRIPTORS.get(
                col, (None, "Unknown", False),
            )

            records.append({
                "descriptor": col,
                "family": family,
                "is_high_risk": is_high_risk,
                "raw_spearman": raw_rho,
                "rank_corr_of_linear_residuals": deconf_rho,
            })

        result_df = pd.DataFrame.from_records(
            records,
            columns=DECONFOUND_RESULT_COLUMNS,
        )

        # 按 |rank_corr_of_linear_residuals| 降序排列：物理信号最强的排最前
        if not result_df.empty:
            result_df = result_df.sort_values(
                by="rank_corr_of_linear_residuals",
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
- 代表 = 该族中稳定性通过且 |线性残差秩相关| 最高的描述符（保留符号）
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
    "rank_corr_of_linear_residuals",
    "selection_freq",
    "is_stable",
    "is_representative",
]

STABILITY_RESULT_COLUMNS = [
    "feature_name",
    "selection_freq",
    "is_stable",
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

            records.append({
                "feature_name": name,
                "selection_freq": freq,
                "is_stable": freq > self.threshold,
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
    - 代表 = 族内稳定性通过 + |线性残差秩相关| 最高的描述符
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
                必须包含 feature_name, selection_freq, is_stable
            deconfound_df: 去混杂结果 DataFrame
                必须包含 descriptor (列名=特征名), rank_corr_of_linear_residuals
            descriptor_registry: 描述符注册表，默认使用 SEARCHABLE_STRUCTURE_DESCRIPTORS
                格式: {name: (compute_func, family_key, is_high_risk)}

        返回:
            DataFrame，每行一个稳定描述符，包含:
            - descriptor: 描述符名
            - family: 所属物理族 (A/B/C/D_prime/E/F/G/H)
            - family_name: 物理族中文名
            - rank_corr_of_linear_residuals: 线性残差秩相关 rho
            - selection_freq: 稳定性选中频率
            - is_stable: 是否通过稳定性阈值
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
                "rank_corr_of_linear_residuals": row.get("rank_corr_of_linear_residuals", float("nan")),
                "selection_freq": row.get("selection_freq", 0.0),
                "is_stable": row.get("is_stable", False),
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

        # 筛选: 稳定的描述符才参与代表选择
        eligible = result_df[result_df["is_stable"]]

        # 按物理族分组
        family_groups = eligible.groupby("family")

        # 第一轮: 每族选 rank_corr_of_linear_residuals 最高的代表
        representatives: set[str] = set()

        for family_key in PHYSICAL_FAMILIES:
            if family_key not in family_groups.groups:
                continue

            group = family_groups.get_group(family_key)
            if group.empty:
                continue

            # 代表按 |rho| 排名，但输出保留 rank_corr_of_linear_residuals 的符号。
            top = group.loc[
                group["rank_corr_of_linear_residuals"].abs().nlargest(self.max_per_family).index
            ]
            representatives.update(top["descriptor"].tolist())

        # 标记代表
        result_df["is_representative"] = result_df["descriptor"].isin(representatives)

        return result_df
--- 文件结束: descriptors/stability.py ---

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
    "combined_rank_corr_of_linear_residuals",
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
    "combined_rank_corr_of_linear_residuals",
    "validation_status",
    "causal_claim",
    "uncertainty_method",
    "noise_baseline",
    "factor_spanning",
    "per_system",
    "bootstrap_ci",
    "evidence_blocks",
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
        deconf_rho = DeconfoundAnalyzer(alpha=self.alpha).rank_corr_of_linear_residuals_rho(
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
            "combined_rank_corr_of_linear_residuals": float(deconf_rho),
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
            "combined_rank_corr_of_linear_residuals",
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
        system_rho = analyzer.rank_corr_of_linear_residuals_rho(
            x_valid, y_valid, system_controls
        )
        all_rho = analyzer.rank_corr_of_linear_residuals_rho(x_valid, y_valid, all_controls)

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

    def full_validation(
        self,
        feature_df: pd.DataFrame,
        y: np.ndarray,
        system_labels: list[str],
        anion_labels: list[str],
        candidate: Mapping[str, Any] | pd.Series,
        n_bootstrap: int = 500,
    ) -> dict[str, Any]:
        """Return four named exploratory evidence blocks."""
        candidate_map = candidate.to_dict() if isinstance(candidate, pd.Series) else candidate
        values, _, _ = self._formula_values(feature_df, candidate_map)
        y_arr = np.asarray(y, dtype=float)
        systems = np.asarray(system_labels)
        anions = np.asarray(anion_labels)
        if not (len(values) == len(y_arr) == len(systems) == len(anions)):
            raise ValueError("feature, target, system, and anion lengths must match")
        observed = _safe_spearman(values, y_arr)

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
                    "combined_rank_corr_of_linear_residuals": row.get(
                        "combined_rank_corr_of_linear_residuals", float("nan")
                    ),
                    "validation_status": "exploratory",
                    "causal_claim": False,
                    "uncertainty_method": "system_stratified_bootstrap",
                    **blocks,
                    "evidence_blocks": blocks,
                }
            )
        if not records:
            return pd.DataFrame(columns=COMBINATION_VALIDATION_RESULT_COLUMNS)
        return pd.DataFrame.from_records(
            records, columns=COMBINATION_VALIDATION_RESULT_COLUMNS
        )
--- 文件结束: descriptors/combination.py ---

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
    Stage 1: 单描述符筛选（线性残差秩相关）
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
    "rank_corr_of_linear_residuals",
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
# Stage 1: 单描述符线性残差秩相关筛选
# ============================================================

def runStage1(
    feature_df: pd.DataFrame,
    y: np.ndarray,
    system_labels: list[str],
    anion_labels: list[str],
    alpha: float,
    output_dir: Path,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Stage 1: 对所有描述符执行线性残差秩相关分析。

    返回:
        (完整审计结果, 预筛选结果)。预筛选结果与完整结果一致；
        所有描述符直接进入 Stage 2。
    """
    print("\n" + "=" * 60)
    print("[Stage 1] 单描述符线性残差秩相关筛选")
    print("=" * 60)

    analyzer = DeconfoundAnalyzer(alpha=alpha)
    deconfound_df = analyzer.analyze_all(feature_df, y, system_labels, anion_labels)

    # 保存完整结果
    deconfound_df.to_csv(output_dir / "stage1_deconfound_results.csv", index=False, encoding="utf-8")

    # 所有描述符直接进入 Stage 2
    filtered_df = deconfound_df.copy()
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
    print(f"  稳定描述符: {n_stable}")

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
        rho = row.get("rank_corr_of_linear_residuals", float("nan"))
        freq = row.get("selection_freq", 0.0)
        print(f"  [{row['family']}] {row['descriptor']} ({row['family_name']})"
              f"  残差秩相关ρ={rho:.3f}  频率={freq:.2f}")

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
        print("\nTop 5 组合候选（按 |线性残差秩相关| 降序）:")
        for _, row in top5.iterrows():
            cross_flag = "跨族" if row["is_cross_family"] else "同族"
            print(f"  {row['combined_name']}  "
                  f"残差秩相关ρ={row['combined_rank_corr_of_linear_residuals']:.3f}  [{cross_flag}]")

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
    """Stage 4: exploratory V1--V4 evidence and single baseline.

    返回:
        (validation_df, baseline_df)
        - validation_df: 组合描述符验证结果
        - baseline_df: 最佳单描述符基线结果
    """
    print("\n" + "=" * 60)
    print("[Stage 4] V1–V4 探索性验证")
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
    # 选出线性残差秩相关绝对值最高的描述符作为基线
    if not deconfound_df.empty:
        best_single_row = deconfound_df.iloc[0]  # 已按 |rank_corr_of_linear_residuals| 降序排列
        best_single_name = best_single_row["descriptor"]

        print(f"\n  最佳单描述符基线: {best_single_name}")

        baseline_records = [{
            "descriptor": best_single_name,
            "family": best_single_row["family"],
            "rank_corr_of_linear_residuals": best_single_row["rank_corr_of_linear_residuals"],
        }]
        baseline_df = pd.DataFrame.from_records(
            baseline_records,
            columns=BASELINE_RESULT_COLUMNS,
        )
    else:
        best_single_name = "N/A"

    # 保存基线结果
    if not baseline_df.empty:
        baseline_df.to_csv(output_dir / "stage4_single_descriptor_baseline.csv", index=False, encoding="utf-8")
        print(f"  基线描述符: {best_single_name}")

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
            f"{row['raw_spearman']:.3f} | {row['rank_corr_of_linear_residuals']:.3f} |"
        )
    stage1_table = "\n".join(stage1_table_rows)

    # ---- Stage 2 代表表格 ----
    reps = representative_df[representative_df["is_representative"] == True]  # noqa: E712
    stage2_table_rows = []
    for _, row in reps.iterrows():
        rho = row.get("rank_corr_of_linear_residuals", float("nan"))
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
            f"{row['combined_rank_corr_of_linear_residuals']:.3f} | {cross_flag} |"
        )
    stage3_table = "\n".join(stage3_table_rows)

    # ---- Stage 4 表格 ----
    # 基线行
    if not baseline_df.empty:
        bl = baseline_df.iloc[0]
        bl_rho = bl.get("rank_corr_of_linear_residuals", float("nan"))
        baseline_row = (
            f"| {bl['descriptor']} | {bl_rho:.3f} |"
        )
        best_single_name = bl["descriptor"]
        best_single_family = bl.get("family", "Unknown")
        best_single_rho = bl.get("rank_corr_of_linear_residuals", 0.0)
    else:
        baseline_row = "| N/A | N/A |"
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
            f"{row['combined_rank_corr_of_linear_residuals']:.3f} | "
            f"{availability} | "
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
        best_comb_rho = best_comb_row.get("combined_rank_corr_of_linear_residuals", 0.0)
    else:
        best_comb_name = "N/A"
        best_comb_rho = 0.0

    # ---- 组装 Markdown 报告 ----
    report = f"""# Na离子导体描述符搜索报告

## 数据概览
- 样本数: {n_samples}
- 体系分布: NASICON={n_nasicon}, sulfide={n_sulfide}, halide={n_halide}
- 目标范围: log_sigma ∈ [{y_min:.2f}, {y_max:.2f}]
- 描述符总数: {n_total_desc}, 有效描述符: {n_valid_desc}

## Stage 1: 单描述符线性残差秩相关筛选
| 描述符 | 族 | 原始Spearman | 线性残差秩相关 |
|--------|-----|-------------|---------------|
{stage1_table}

## Stage 2: 稳定性选择与族代表
候选池规则：每个物理族最多保留 {stage2_capacity} 个稳定代表。三描述符模式下，
第二个同族名额仅用于受限的“同族两个 + 相邻族一个”公式构造，不应被解读为第二项独立科学发现。

### 族代表列表
| 描述符 | 族 | 族名 | 线性残差秩相关 | 稳定性频率 |
|--------|-----|------|---------------|-----------|
{stage2_table}

## Stage 3: 约束组合搜索
### Top 10 组合候选
| 组合名 | 描述符数 | 组成 | 运算符序列 | 线性残差秩相关 | 跨族? |
|--------|----------|------|------------|---------------|-------|
{stage3_table}

## Stage 4: V1–V4探索性验证
### 最佳单描述符基线
| 描述符 | 线性残差秩相关 |
|--------|---------------|
{baseline_row}

### Top组合验证结果
| 组合名 | 描述符数 | 线性残差秩相关 | V1/V2/V3/V4 | 体系分层Bootstrap 95% CI | 状态 |
|--------|----------|---------------|-------------|---------------------------|------|
{stage4_table}

注：V1–V4依次为匹配噪声基线、已知因素后关联、体系内原始Spearman、体系分层Bootstrap区间。所有组合证据均为探索性，不作因果解释；完整公式组成、运算符、规则和原始值来源保存在 CSV/JSON provenance 中。

### V2 已知因素后目标残差预测审计（最佳组合）
- {best_v2_summary}
- 控制设计: {best_v2_control_audit}
- 语义: 折安全的探索性预测关联；不是因果效应。双侧偏相关仅作为补充证据保存在 artifact 中。

## 结论
### 物理发现
- 最强单描述符: {best_single_name} ({best_single_family}族), 线性残差秩相关 = {best_single_rho:.3f}
- 最强组合: {best_comb_name}, 线性残差秩相关 = {best_comb_rho:.3f}
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
            "best_combination_rho": float(best_comb_rho),
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

    # Stage 1: 单描述符线性残差秩相关筛选
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

--- 文件开始: .aris/traces/experiment-audit/2026-08-07_run01/001-experiment-audit.response.md (run01 EXPERIMENT_AUDIT) ---
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
--- 文件结束: .aris/traces/experiment-audit/2026-08-07_run01/001-experiment-audit.response.md (run01 EXPERIMENT_AUDIT) ---

--- 文件开始: .aris/EXPERIMENT_AUDIT.md (run02 EXPERIMENT_AUDIT) ---
# Experiment Audit Report

**Date**: 2026-08-07
**Auditor**: Claude Web (manual bridge, read-only cross-model)
**Project**: automat-naconductor（Na 离子导体描述符搜索管线）
**Checklist**: stat-pipeline 专项（A-F 标准 + G-L 六项统计管线泄露/偏差专项）
**Round**: run02（run01 已于同日完成，本轮为 stat-pipeline 专项扩展）
**Compact Level**: 0（全文嵌入，16 个文件）

## Overall Verdict: FAIL

判定由 **H（FAIL）** 单独决定：四级全量目标依赖选择 → 无外层循环的 CV，且项目内唯一的乐观偏差承认（`selection_uncertainty_included: False`）在 `CombinationValidator.validate` 扁平化时被丢弃，不进入任何 CSV 或报告。叠加 H.6（噪声基线不对称）与 K.6（单列公式下 CV 退化为未去混杂的折内原始 Spearman）。

与 run01（A-H 审计，7 项 FAIL）相比：**G 项已从 FAIL 转为 PASS/WARN**——折内填充与标准化、子样本内独立预处理确实做对了，是实质进步。新增 I-L 四项暴露了更深的问题层。

## Integrity Status: fail

## Checks

### A. Ground Truth Provenance: PASS
- 目标 `log_sigma` 全程由 `data/naconductor_raw.csv` 读入，无模型输出反填。
- V2 残差目标已显式标注为 proxy（`fold_safe_oof_target_residual_prediction`）。
- 潜在隐患：`build_feature_matrix` 的 `metadata_cols` 保留了 `log_sigma`，当前白名单取列安全但未来有泄露风险。

### B. Score Normalization: WARN
- 无指标以模型自身输出统计量作分母（PASS）。
- `system_proxy_ratio` 两处硬饱和（`raw_rho_sq<1e-12`→0.0，符号翻转→1.0），1.0 语义二义。
- `signal_retention` 是"均值之比"非"比之均值"，跑在未筛全集上，**上一轮实际产出 102.5%——不可能值**。
- `delta_pct` 分母可能基于不同可用策略数，数学上无意义。

### C. Result File Existence: WARN
（results/ 按用户要求排除，仅评代码自洽性）
- "41 个描述符"在代码里实际是 38（`_INACTIVE_FOR_AUTOMATIC_SEARCH` 排除 3 个）。
- `analyze_all` docstring 写"80% 跳过"实际是 `n_valid < 5`，80% 阈值不存在。
- 报告混用 `filtered_deconfound_df` 与完整 `deconfound_df`，基线与 Stage 1 表格可能指向不同描述符。
- `evaluation.secondary` 声明的 `cv_rmse`/`stability_score` 不存在；`deconfound.method` 的 DML 未实现。
- `run_info.yaml` 多处参数不驱动代码（配置漂移）。

### D. Dead Code Detection: WARN
- **`_classify_descriptor` 接收 `deconf_p` 但完全不用**——"强物理信号"标签不含任何显著性要求（最有实质危害）。
- `noise_info_df` 算出后丢弃——噪声列与目标的实际相关不可见。
- `_base.py:CROSS_GROUP_RULES` 是第二套规则真值源，无人调用。
- `_one_hot_encode` 零调用；`_formula_dimensionally_valid` 的量纲推导对 multiply/ratio 无效。

### E. Scope Assessment: WARN
- 84 样本/3 体系/38 描述符，实际只有 6 个通过 Stage 1 预筛。
- `--seed` 不通到 CV（`StratifiedKFold(random_state=42)` 是字面量）。
- V1 置换仅 100 draws（p<0.01 不可表达）；V4 bootstrap 用 percentile 法（有偏）。
- "一致性优秀"可由单个数据点触发。
- 搜索空间高度不对称（F/G 族无跨族规则）且未披露。

### F. Evaluation Type: real_gt
- 主线全部对实测 `log_sigma`（real_gt）。
- V1=real_gt+体系内置换零分布（设计正确）；V2=real_gt折内残差化派生；V3/V4=real_gt原始 Spearman（未去混杂）。
- 无 human_eval、无 simulation_only。

### G. Data Leakage in Preprocessing: WARN
| 检查项 | 判定 |
|---|---|
| 中位数填充 | PASS（折内） |
| StandardScaler | PASS（折内） |
| 噪声列注入 | PASS（固定种子全局一次，纯标准正态） |
| 稳定性选择子样本 | PASS（循环体内新建 Pipeline） |
| 去混杂残差化 | Stage1全量(允许)/Stage4 V2折内(PASS)/Stage3排序全量(问题在H) |

- **`build_feature_matrix` 明确不做全量填充——工程质量最高的一处。**
- 噪声基线是"零分布的一次抽样"非零分布，基线高低取决于种子运气且不可见。
- `_factor_spanning:encode_controls` 有静默错编码风险（测试折未见类别被当参考类）。

### H. Feature Selection Leakage: FAIL（CRITICAL）
1. **稳定性选择→CV：泄露。** Stage 1 用全量84行含目标统计量预筛（38→6，砍84%），之后同84行做CV。
2. **组合top-k→CV：泄露。** 按全量 `combined_deconf_spearman` 排序取top-10，在同样84行上跑CV，无外层循环。
3. **PhysicalGrouper代表→CV：泄露。** 按全量 `|deconf_rho|` 选代表，报告把同一统计量当评估证据印。
4. V2折内安全，但候选选择条件于全量统计量。
5. **项目部分承认（`selection_uncertainty_included: False`）但该标志在 `validate()` 扁平化时被丢弃，不进CSV不进报告——决定性FAIL理由。**
6. **噪声基线不对称：真实描述符已过Stage1目标筛，15个噪声列没有——假阳性对照系统性偏向真实描述符。**

### I. Deconfounding Methodology: WARN（清单）/ FAIL级修复项（审稿人）
1. 残差化范围：Stage1全量(允许)，V2主指标折内(PASS)，V2补充量全量但已标注。
2. `build_rank_aware_controls` 基本正确，但"冗余"归属由字母序决定（任意）。
3. `system_proxy_ratio` 不是有效分解量：Spearman²≠R²，符号翻转硬置1.0用噪声断言"完全混杂驱动"。
4. **Ridge alpha=1.0 引入系统性偏差**：分类混杂one-hot下OLS即饱和调整，alpha=1.0导致体系组~5%、稀有anion组~26%欠调整，残差保留混杂，`deconfounded_spearman`系统性偏向`raw_spearman`——偏差方向有利于结论。
5. 无双重控制（PASS）。
6. **`partial_spearman` 静默回退**：n<3或z列数≥n时返回原始Spearman无标记，Stage3可达（5个有效点的ratio可冒充`combined_deconf_spearman`排第一）。
7. 先残差化后取秩破坏Spearman单调不变性，与选用Spearman的理由矛盾。

### J. Multiple Testing: WARN（清单）/ FAIL级修复项（审稿人）
1. 无任何多重检验校正，`deconf_p`不扣除已估计混杂参数（反保守），且在标签判定中被完全忽略。
2. `composite_score`只用可用策略——透明度PASS，但`delta_pct`跨不同N相除WARN。
3. top-k乐观性未被承认（同H.5），"最强组合"定义不自洽（按deconf rho选，用composite打分）。
4. **Bootstrap CI算的是原始Spearman非去混杂Spearman，不覆盖选择不确定性，却被题为"体系分层Bootstrap 95% CI"与deconf rho并列——读者会误读。**
5. `consistency_desc`跨候选汇总（应逐候选），`"所有CV策略均无显著相关"`措辞错误。

### K. Target & Metric: WARN（清单）/ 领域级FAIL风险（审稿人）
1. `log_sigma`无校验（log10 vs ln），目标未标准化（PASS）。
2. **混杂集里没有温度/测量方法/体相-晶界——支配性混杂完全缺席。** 文献中这些因素以数量级计，远超结构描述符效应量。
3. Spearman只捕单调关系，而快离子导体经典构效关系非单调（volcano曲线）。
4. **`composite_score`取绝对值双层掩盖方向翻转**：层一策略内带符号平均（折间抵消趋0），层二策略间取绝对值。+0.5/-0.5与+0.5/+0.5不可区分。
5. 过校正风险不可逆：体系间机制被标"体系代理"→Stage1永久剔除→Stage2/3/4无法回收。0.3/0.3/0.7阈值无来源。
6. **单列公式下CV Spearman=sign(a)·Spearman(y_val,x_val)，alpha/标准化/正则化一概无效——三条CV不是"三种模型验证"而是三种划分的原始秩相关平均，且无一条去混杂。** LOSO≈V3（非独立），anion_stratified验证折混合阴离子类型（构造上被混杂）。

### L. Causal Claim Boundary: WARN（清单）/ 全项目最危险一处（审稿人）
- 纪律层面好：`causal_claim: False`一致设置，README/program.md有限制语。
- **但五条抵消：**
  1. **混杂集被断言非论证**：`run_info.yaml`写"不是因果通路"，`deconfound.py`写"同时影响X和Y"——均为未经检验的DAG断言。`anion_type`经极化率→键软度→迁移势垒→电导率，是结构→电导通路本身（中介非混杂）。对中介条件化会减掉待测效应。
  2. **手稿标题"因果去混杂搜索方法"与代码`causal_claim: False`直接冲突**——审稿人一眼可见，最容易导致拒稿。
  3. "deconfounded"在因果推断文献中意味着后门准则可识别，此处实际只是Ridge残差化。
  4. "强物理信号"标签由`|deconf_rho|>0.3`单条件触发（不看p/n/CV/多重性），把统计阈值翻译成物理断言。
  5. 报告免责声明是装饰性的：Stage4表末"探索性"是f-string硬编码不读`causal_claim`；结论段标题"物理发现"；"信号保留率102.5%"配因果味措辞。

## Action Items

### 阻断级（投稿前必须处理，6项）
1. 画DAG辩护`system`/`anion_type`是混杂非中介，或改口径（删断言、`deconfounded_spearman`更名`within_system_partial_spearman`、同时报告去混杂前后）
2. 手稿标题去掉"因果"，或补可识别性论证
3. 加外层嵌套验证（外层按system留出，内层完整重跑Stage1-4），或至少把`selection_uncertainty_included: False`加进产物+报告顶部加乐观偏差明文声明
4. 修正噪声基线对称性（噪声列走完全相同的Stage1预筛），否则删除`above_noise_baseline`
5. `deconf_p`接进`_classify_descriptor`+BH-FDR校正
6. `_evaluate_candidate`加`n_valid`下限(≥30或≥50%)+`partial_spearman`静默回退返回`deconfound_applied: False`标志

### 高优先级（6项）
7. DeconfoundAnalyzer Ridge改`alpha=0`(OLS)，拆分混杂alpha与预测alpha
8. `composite_score`加带符号版本+Fisher z平均
9. 重写`signal_retention`（逐描述符中位数+分位区间）或删除
10. 修`delta_pct`（仅同策略数可比时计算）+统一"最强组合"定义
11. `consistency_desc`改逐候选计算，`len(signs)<3`禁输出"优秀"
12. `_encode_controls`加显式断言（测试折未见类别记skipped）

### 中优先级（8项）
13-20. YAML真驱动代码、noise_info落盘、删死代码、统一41/38口径、增列n_valid、V1≥2000 draws、V4改BCa、披露搜索空间不对称、补温度/测量方法列

## Claim Impact
- Claim 1（关联性/预测稳健性，非因果）: **needs_qualifier**
- Claim 2（去混杂后信号保留）: **unsupported**
- Claim 3（跨CV策略一致性）: **unsupported**
- Claim 4（组合优于单描述符）: **unsupported**

## Top 3 Critical Findings（stat-pipeline 专项）

1. **混杂集可能是中介集——主指标系统性删除答案且不可逆。** `anion_type`经极化率→键软度→迁移势垒是结构→电导通路本身；`system`是结构的下游标签。对中介条件化减掉待测效应，叠加Stage1永久剔除，管线可能在删除真实机制。

2. **四级全量目标依赖选择→无外层循环CV，唯一承认在写盘前被丢掉。** Stage1预筛(38→6)→Stage2稳定性选择→PhysicalGrouper代表→Stage3排序→Stage4 top-k CV，全在同一84行上。`selection_uncertainty_included: False`在`validate()`扁平化时被丢弃。噪声基线不对称进一步放大偏差。

3. **单列公式下CV代数退化为未去混杂的折内原始Spearman。** `Spearman(y_val, ŷ)=sign(a)·Spearman(y_val, x_val)`，alpha/标准化无效。`composite_score`度量原始关联却与`deconfounded_spearman`并列；LOSO≈V3非独立；anion_stratified验证折混合阴离子类型在构造上被混杂。"跨CV策略一致性"无独立信息量。

---

**审计覆盖限制**：(a) 41个描述符实现文件未提供，物理正确性未审；(b) 无真实行号，传输损坏与真实bug不可区分；(c) results/已排除，数字级核对未做；(d) run_status.py/plot_run_results.py/test_descriptors.py未提供。
--- 文件结束: .aris/EXPERIMENT_AUDIT.md (run02 EXPERIMENT_AUDIT) ---


## 输出格式

请按以下结构输出，对每个算法步骤逐条给出四问的回答：

## Overall Assessment
[2-3 段总体评价：这套算法管线作为"结构描述符-电导率去混杂相关性搜索"工具，其设计层面的核心问题是什么？]

## Per-Step Algorithmic Assessment

对每个步骤（A1, A2, A3, A4, B1, B2, C1, C2, D1, D2, D3, D4, D5, D6, E1）逐条输出：

### 步骤 [编号]: [名称]
1. **Does it accomplish its design goal?** [回答]
2. **Degeneration conditions?** [回答]
3. **Minimal fix and cost?** [回答]
4. **Standard method this is an ad-hoc version of?** [回答]

## Cross-Cutting Issues
[跨步骤的系统性问题——如果某些问题不属于单个步骤但在多个步骤中反复出现，在此总结]

## Top 3 Actionable Recommendations
1. [recommendation 1]
2. [recommendation 2]
3. [recommendation 3]
