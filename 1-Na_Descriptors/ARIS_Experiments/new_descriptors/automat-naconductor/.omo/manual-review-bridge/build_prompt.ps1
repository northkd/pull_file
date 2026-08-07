# 构建 research-review prompt 的脚本
# 读取 8 个指定文件，拼装成完整的 Claude 网页端 prompt

$projectRoot = "E:\work\worklist\1-Na离子导体\nasicon-causal-inference-main\experiments\02_组合描述符搜索\automat-naconductor"
$outputFile = "$projectRoot\.omo\manual-review-bridge\prompt_research-review_round1.md"

# 文件列表（相对路径 -> 绝对路径）
$files = @(
    @{ rel = "run_info.yaml"; abs = "$projectRoot\run_info.yaml" },
    @{ rel = "program.md"; abs = "$projectRoot\program.md" },
    @{ rel = "descriptors/deconfound.py"; abs = "$projectRoot\descriptors\deconfound.py" },
    @{ rel = "descriptors/stability.py"; abs = "$projectRoot\descriptors\stability.py" },
    @{ rel = "descriptors/cv_strategies.py"; abs = "$projectRoot\descriptors\cv_strategies.py" },
    @{ rel = "descriptors/combination.py"; abs = "$projectRoot\descriptors\combination.py" },
    @{ rel = "aris/traces/experiment-audit/2026-08-07_run01/001-experiment-audit.response.md (run01 EXPERIMENT_AUDIT)"; abs = "$projectRoot\aris\traces\experiment-audit\2026-08-07_run01\001-experiment-audit.response.md" },
    @{ rel = "aris/EXPERIMENT_AUDIT.md (run02 EXPERIMENT_AUDIT)"; abs = "$projectRoot\aris\EXPERIMENT_AUDIT.md" }
)

# 读取所有文件内容
$fileContents = @{}
foreach ($f in $files) {
    $content = [System.IO.File]::ReadAllText($f.abs, [System.Text.Encoding]::UTF8)
    $fileContents[$f.rel] = $content
    Write-Output "读取: $($f.rel) ($($content.Length) chars)"
}

# 拼装文件嵌入段
$fileEmbedSection = ""
foreach ($f in $files) {
    $fileEmbedSection += "--- 文件开始: $($f.rel) ---`r`n"
    $fileEmbedSection += $fileContents[$f.rel]
    $fileEmbedSection += "`r`n--- 文件结束: $($f.rel) ---`r`n`r`n"
}

# 已知弱点（两轮 audit 的 Top Critical Findings 原文）
$knownWeaknesses = @"
以下为两轮 experiment-audit 的 Top Critical Findings 原文。

=== run01 审计（A-H 八项，7 项 FAIL）关键发现 ===

Overall Verdict: FAIL

A. Target Variable Provenance: FAIL
- 数据模式中不存在任何测量条件列。没有温度、没有测量方法（EIS/直流极化）、没有 total/bulk/grain-boundary 区分、没有样品制备（冷压 vs 烧结 vs 单晶）、没有文献来源 ID。σ 是 Arrhenius 量，同一材料在 25 °C 与 300 K 之外的报道值可差数量级；bulk 与 total 电导率对同一样品可差 2–3 个量级。这些信息不在 schema 里，因此"可通约性"这个问题在当前数据结构下连提都提不出来。
- 异质来源被合并且合并本身就是设计目的。NASICON / sulfide / halide 三体系汇入同一 log_sigma 向量，LOSO-CV 明确要求跨体系外推。

B. Metric Self-Reference: FAIL
- 复合标签可以奖励管线自身定义为失败的结果——这是 B 的 FAIL 条件，且可精确构造。_classify_descriptor 把 |deconf_rho| > 0.3 置于代理比判断之上，注释明写"无论代理比多高"。代入：raw_rho = 0.9, deconf_rho = 0.31 → system_proxy_ratio = 1 − 0.0961/0.81 = 0.881。即一个按管线自己的定义有 88% 的相关（R² 意义上）由体系混杂驱动的描述符，被标为"强物理信号"。
- clip 销毁了方向信息。deconf_rho > raw_rho（抑制效应，或 84 行上 Ridge 对混杂设计的过拟合）会产生负比值，被 clip 成 0.0，即"最纯物理信号"。去混杂反而增强相关这一最该被警惕的情形，被编码为最高信誉等级。
- signal_retention 只报导出量，且是"均值之比"而非"比之均值"。它可以超过 100%——一旦超过，"保留率"这个词就失去了任何字面意义。

D. Dead Path Detection: FAIL
- 声明的过滤器在代码中被绕过。注释声明的是"有效值不足 80% 则跳过"（n=84 时门槛应为 68），代码执行的是 n_valid < 5。一个只有 5 个非 NaN 值（覆盖率 6%）的描述符可以完整走完 Stage 1 并被打上标签。80% 这个数字在整个代码库中不存在。
- deconf_p 是死参数，而"显著"一词建立在它之上。_classify_descriptor 接收 deconf_p 却从不使用；docstring 与行内注释均写"去混杂后仍然显著 → 强物理信号"。实际规则只测 |deconf_rho| > 0.3，管线全程没有对去混杂相关做任何显著性判定。
- 静默回退把"未做去混杂"编码为"最干净的物理信号"。partial_spearman 在 z.shape[1] >= n_samples 时直接返回原始 Spearman 当作去混杂值。此时 deconf_rho == raw_rho → system_proxy_ratio = 0.0 → 落入"弱物理信号"或"强物理信号"。回退事件没有任何记录。

E. Scope and Multiplicity: FAIL
- 零多重性控制。全代码库无 FDR、无 Bonferroni、无置换检验、无嵌套外层选择。deconf_p 被算出来却既不用于分类也不做校正。配置自己承认 nested_outer_group_selection_available: false。
- "一致性优秀"的证据基数是 ≤9 个非独立观测。consistency_desc 遍历 validation_df.head(3) × 3 策略 = 至多 9 个符号，来自同一批 84 行、三个大概率共享分量的公式、三种在同一数据上切分的 CV。这不是 9 个独立复现。

F. Threshold Provenance: FAIL
- 全部决定性阈值零外部依据，且结论对其敏感。0.2 / 0.3 / 0.3 / 0.7 四个分类阈值决定了 Stage 1 的存活集合、标签分布、以及报告里的"物理发现"。四个都没有理论、文献或预注册出处，只标 "errata P3"——"errata"这个词本身就表明规则是在看过输出后修订的。
- 参考类编码 + L2 惩罚 = 结果不随参考类别选择而不变。换一个参考类别，去混杂 ρ 会变。

G. Null Distribution and Selection Effects: FAIL
- 全库唯一的经验零分布是 Stage 2 的注入噪声列。没有任何置换检验、没有 y 打乱、没有跨种子重复。
- 零分布被施加在错误的阶段。真实描述符已经过 Stage 1 预筛选，噪声列则"全部保留"。两臂不可交换：真实特征是在同一个 y 上做过一轮筛选的幸存者，噪声列是未经筛选的新鲜样本。用后者给前者定基线，系统性地低估了通过难度。

H. Randomness and Reproducibility: FAIL
- 配置文件与代码描述的是不同的过程。所提供代码实际读取的 YAML 键只有：data.*、shared_input.*、combination.max_descriptors、tracks.pipeline.output_dir。未被读取的包括：整个 stability_selection 块、整个 deconfound 块、evaluation.model.*、cv_strategies 各策略参数。改 YAML 不会改变行为，而实验记录会显示改过。
- CLI seed 不传播到 CV 阶段。MultiStrategyCV(alpha=alpha) 未收到 seed。--seed 123 会改变稳定性选择与组合搜索，但不改变基线 CV 的折划分。

=== run02 审计（A-L 十二项 stat-pipeline 专项）Top 3 Critical Findings 原文 ===

1. 混杂集可能是中介集——主指标系统性删除答案且不可逆。anion_type 经极化率→键软度→迁移势垒是结构→电导通路本身；system 是结构的下游标签。对中介条件化减掉待测效应，叠加 Stage1 永久剔除，管线可能在删除真实机制。

2. 四级全量目标依赖选择→无外层循环 CV，唯一承认在写盘前被丢掉。Stage1 预筛(38→6)→Stage2 稳定性选择→PhysicalGrouper 代表→Stage3 排序→Stage4 top-k CV，全在同一 84 行上。selection_uncertainty_included: False 在 validate() 扁平化时被丢弃。噪声基线不对称进一步放大偏差。

3. 单列公式下 CV 代数退化为未去混杂的折内原始 Spearman。Spearman(y_val, ŷ)=sign(a)·Spearman(y_val, x_val)，alpha/标准化无效。composite_score 度量原始关联却与 deconfounded_spearman 并列；LOSO≈V3 非独立；anion_stratified 验证折混合阴离子类型在构造上被混杂。"跨 CV 策略一致性"无独立信息量。

=== 补充声明 ===
数据集仍在准备中，本次评审对象是算法设计本身，不涉及任何数值结果。
"@

# 算法步骤清单
$algorithmSteps = @"
以下是从嵌入代码中识别的主要算法步骤，请逐条评估：

**去混杂层（descriptors/deconfound.py）**
- 步骤 A1: `build_rank_aware_controls` — 构造 system 为主控制 + 秩感知增量 anion 对比项的设计矩阵
- 步骤 A2: `partial_spearman` — 对 X 和 Y 分别做 Ridge 残差化，对残差计算 Spearman 秩相关
- 步骤 A3: `system_proxy_ratio` 计算 — `1 - deconf_rho² / raw_rho²`，带钳位和符号翻转硬置
- 步骤 A4: `_classify_descriptor` — 用阈值 0.2/0.3/0.3/0.7 给描述符打标签（噪声级/强物理信号/弱物理信号/混合信号/体系代理）

**稳定性选择层（descriptors/stability.py）**
- 步骤 B1: `StabilitySelector.run` — 无放回子采样 + 子样本内独立预处理 + Lasso + 选中频率统计 + 噪声列 95 分位基线
- 步骤 B2: `PhysicalGrouper.group_and_select` — 按物理族分组，每组取 |deconfounded_spearman| 最高的代表（max_per_family=1）

**交叉验证层（descriptors/cv_strategies.py）**
- 步骤 C1: `MultiStrategyCV` 三策略 — 阴离子分层 K 折 / 留一体系（LOSO）/ 重复分层子采样，统一用 Ridge Pipeline
- 步骤 C2: `summarize_cv_spearman` — composite_score = 可用策略的 |Spearman| 均值

**组合搜索与验证层（descriptors/combination.py）**
- 步骤 D1: `ConstrainedCombinationSearch.search` — 声明式算子注册表约束的二元/三元公式枚举 + 去混杂 Spearman 排序
- 步骤 D2: `CombinationValidator._noise_baseline`（V1）— 体系内分量置换零分布（100 draws）
- 步骤 D3: `CombinationValidator._factor_spanning`（V2）— 折内残差化 + OOF 公式预测 vs 残差目标 Spearman
- 步骤 D4: `CombinationValidator._per_system`（V3）— 逐体系原始 Spearman
- 步骤 D5: `CombinationValidator._bootstrap_ci`（V4）— 体系分层 bootstrap CI（percentile 法，500 次）
- 步骤 D6: `CombinationValidator.validate` — 扁平化 V1-V4 + CV 诊断到 CSV 行

**管线级（跨文件）**
- 步骤 E1: Stage1→Stage2→Stage3→Stage4 的全量目标依赖选择链（预筛→稳定性→代表→排序→top-k CV）
"@

# 输出格式
$outputFormat = @"
请按以下结构输出，对每个算法步骤逐条给出四问的回答：

## Overall Assessment
[2-3 段总体评价：这套算法管线作为"结构描述符-电导率去混杂相关性搜索"工具，其设计层面的核心问题是什么？]

## Per-Step Algorithmic Assessment

### 步骤 A1: build_rank_aware_controls
1. **Does it accomplish its design goal?** [回答]
2. **Degeneration conditions?** [回答]
3. **Minimal fix and cost?** [回答]
4. **Standard method this is an ad-hoc version of?** [回答]

### 步骤 A2: partial_spearman
1. **Does it accomplish its design goal?** [回答]
2. **Degeneration conditions?** [回答]
3. **Minimal fix and cost?** [回答]
4. **Standard method this is an ad-hoc version of?** [回答]

[... 对步骤 A3, A4, B1, B2, C1, C2, D1, D2, D3, D4, D5, D6, E1 逐条重复上述四问 ...]

## Cross-Cutting Issues
[跨步骤的系统性问题，如选择链泄露、混杂/中介混淆、指标退化等——如果某些问题不属于单个步骤但在多个步骤中反复出现，在此总结]

## Top 3 Actionable Recommendations
1. [recommendation 1]
2. [recommendation 2]
3. [recommendation 3]
"@

# 会话指示
$sessionInstructions = @"
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
"@

# 拼装完整 prompt
$prompt = @"
$sessionInstructions

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

$algorithmSteps

## 已知弱点（两轮 experiment-audit 的 Top Critical Findings 原文）

$knownWeaknesses

## 文件内容

$fileEmbedSection

## 输出格式

$outputFormat
"@

# 写入文件
[System.IO.File]::WriteAllText($outputFile, $prompt, [System.Text.UTF8Encoding]::new($false))
Write-Output ""
Write-Output "Prompt 文件已写入: $outputFile"
Write-Output "总字符数: $($prompt.Length)"
Write-Output "总行数: $(($prompt -split "`n").Count)"
