"""构建 research-review prompt 的 Python 脚本。
读取 8 个指定文件，拼装成完整的 Claude 网页端 prompt。
"""
import pathlib

project_root = pathlib.Path(
    r"E:\work\worklist\1-Na离子导体\nasicon-causal-inference-main"
    r"\experiments\02_组合描述符搜索\automat-naconductor"
)
output_file = project_root / ".omo" / "manual-review-bridge" / "prompt_research-review_round1.md"

# 文件列表 (相对路径标签, 绝对路径)
file_list = [
    ("run_info.yaml", project_root / "run_info.yaml"),
    ("program.md", project_root / "program.md"),
    ("descriptors/deconfound.py", project_root / "descriptors" / "deconfound.py"),
    ("descriptors/stability.py", project_root / "descriptors" / "stability.py"),
    ("descriptors/cv_strategies.py", project_root / "descriptors" / "cv_strategies.py"),
    ("descriptors/combination.py", project_root / "descriptors" / "combination.py"),
    (
        "aris/traces/experiment-audit/2026-08-07_run01/001-experiment-audit.response.md (run01 EXPERIMENT_AUDIT)",
        project_root
        / "aris"
        / "traces"
        / "experiment-audit"
        / "2026-08-07_run01"
        / "001-experiment-audit.response.md",
    ),
    (
        "aris/EXPERIMENT_AUDIT.md (run02 EXPERIMENT_AUDIT)",
        project_root / "aris" / "EXPERIMENT_AUDIT.md",
    ),
]

# 读取所有文件
file_contents = {}
for label, path in file_list:
    content = path.read_text(encoding="utf-8")
    file_contents[label] = content
    print(f"读取: {label} ({len(content)} chars)")

# 拼装文件嵌入段
file_embed = ""
for label, _ in file_list:
    file_embed += f"--- 文件开始: {label} ---\n"
    file_embed += file_contents[label]
    if not file_contents[label].endswith("\n"):
        file_embed += "\n"
    file_embed += f"--- 文件结束: {label} ---\n\n"

# 已知弱点
known_weaknesses = r"""以下为两轮 experiment-audit 的 Top Critical Findings 原文。

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
数据集仍在准备中，本次评审对象是算法设计本身，不涉及任何数值结果。"""

# 算法步骤清单
algorithm_steps = """以下是从嵌入代码中识别的主要算法步骤，请逐条评估：

**去混杂层（descriptors/deconfound.py）**
- 步骤 A1: `build_rank_aware_controls` — 构造 system 为主控制 + 秩感知增量 anion 对比项的设计矩阵
- 步骤 A2: `partial_spearman` — 对 X 和 Y 分别做 Ridge 残差化，对残差计算 Spearman 秩相关
- 步骤 A3: `system_proxy_ratio` 计算 — `1 - deconf_rho^2 / raw_rho^2`，带钳位和符号翻转硬置
- 步骤 A4: `_classify_descriptor` — 用阈值 0.2/0.3/0.3/0.7 给描述符打标签

**稳定性选择层（descriptors/stability.py）**
- 步骤 B1: `StabilitySelector.run` — 无放回子采样 + 子样本内独立预处理 + Lasso + 选中频率统计 + 噪声列 95 分位基线
- 步骤 B2: `PhysicalGrouper.group_and_select` — 按物理族分组，每组取 |deconfounded_spearman| 最高的代表

**交叉验证层（descriptors/cv_strategies.py）**
- 步骤 C1: `MultiStrategyCV` 三策略 — 阴离子分层 K 折 / 留一体系（LOSO）/ 重复分层子采样
- 步骤 C2: `summarize_cv_spearman` — composite_score = 可用策略的 |Spearman| 均值

**组合搜索与验证层（descriptors/combination.py）**
- 步骤 D1: `ConstrainedCombinationSearch.search` — 声明式算子注册表约束的二元/三元公式枚举 + 去混杂 Spearman 排序
- 步骤 D2: `CombinationValidator._noise_baseline`（V1）— 体系内分量置换零分布（100 draws）
- 步骤 D3: `CombinationValidator._factor_spanning`（V2）— 折内残差化 + OOF 公式预测 vs 残差目标 Spearman
- 步骤 D4: `CombinationValidator._per_system`（V3）— 逐体系原始 Spearman
- 步骤 D5: `CombinationValidator._bootstrap_ci`（V4）— 体系分层 bootstrap CI（percentile 法，500 次）
- 步骤 D6: `CombinationValidator.validate` — 扁平化 V1-V4 + CV 诊断到 CSV 行

**管线级（跨文件）**
- 步骤 E1: Stage1 -> Stage2 -> Stage3 -> Stage4 的全量目标依赖选择链"""

# 输出格式
output_format = """请按以下结构输出，对每个算法步骤逐条给出四问的回答：

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
3. [recommendation 3]"""

# 会话指示
session_instructions = """【会话指示 - research-review】

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
- 对每个算法步骤回答四个固定问题"""

# 拼装完整 prompt
prompt = f"""{session_instructions}

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

{algorithm_steps}

## 已知弱点（两轮 experiment-audit 的 Top Critical Findings 原文）

{known_weaknesses}

## 文件内容

{file_embed}
## 输出格式

{output_format}
"""

# 写入文件
output_file.parent.mkdir(parents=True, exist_ok=True)
output_file.write_text(prompt, encoding="utf-8")
print()
print(f"Prompt 文件已写入: {output_file}")
print(f"总字符数: {len(prompt)}")
print(f"总行数: {prompt.count(chr(10)) + 1}")
